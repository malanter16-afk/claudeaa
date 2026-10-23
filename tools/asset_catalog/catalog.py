#!/usr/bin/env python3
"""Asset catalogue: what's downloaded, previews, AI tagging, Blender asset library, HTML browser.

    python catalog.py inventory --wanted wanted/*.json --scan assets/inbox ~/Downloads
    python catalog.py thumbs    --blender <blender-4.5>
    python catalog.py classify  --taxonomy config/taxonomy.json [--model M] [--effort low] [--yes]
    python catalog.py collect
    python catalog.py library   --blender <blender> [--library assets/library]
    python catalog.py browse

Works on the outputs of tools/asset_ingest (assets/manifest.json + assets/normalized/).
State: assets/catalog.json (tags per asset), assets/catalog_batches.json (submitted batches).
Only `classify --yes` and `collect` call the Claude API (Message Batches, 50% price).
"""
import argparse
import base64
import csv
import datetime
import difflib
import glob
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
STOPWORDS = {"free", "3d", "model", "models", "dc", "designconnected", "max", "fbx", "obj", "skp",
             "vray", "corona", "v", "by", "the", "and", "zip", "rar", "files", "all", "file"}
ARCHIVES = {".zip", ".rar", ".7z"}
# USD per million tokens, standard rates; batches bill half. Unknown models skip the estimate.
PRICES = {"claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00),
          "claude-haiku-5-5": (0.10, 0.50), "claude-fable-5-1": (10.00, 50.00)}
BATCH_BYTES = 200 * 1024 * 1024  # API limit is 256 MB per batch


def load_json(path, default):
    if os.path.isfile(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def manifest_entries(opts):
    root = os.path.dirname(os.path.abspath(opts.manifest))
    for e in load_json(opts.manifest, []):
        if e.get("status") == "ok" and (e.get("outputs") or {}).get("blend"):
            out = {k: os.path.join(root, v) for k, v in e["outputs"].items()}
            yield e, out, os.path.join(os.path.dirname(out["blend"]), "thumb.png")


# ---------------------------------------------------------------- inventory
def tokens(text):
    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    words = re.split(r"[^a-z0-9]+", words.lower())
    return {w for w in words if w and w not in STOPWORDS and not re.fullmatch(r"\d{1,2}", w)}


def load_wanted(patterns):
    items = []
    for pattern in patterns:
        for path in sorted(glob.glob(os.path.expanduser(pattern))):
            if path.endswith(".csv"):
                with open(path, newline="") as f:
                    rows = list(csv.DictReader(f))
            else:
                rows = load_json(path, [])
            src = os.path.splitext(os.path.basename(path))[0]
            for r in rows:
                if r.get("name"):
                    items.append({"source": r.get("source") or src, **r})
    return items


def scan_local(dirs, depth=3):
    found = []
    for d in dirs:
        d = os.path.expanduser(d)
        base = d.rstrip(os.sep).count(os.sep)
        for root, subdirs, files in os.walk(d):
            if root.count(os.sep) - base >= depth:
                subdirs[:] = []
            subdirs[:] = [s for s in subdirs if not s.startswith((".", "_"))]
            for name in subdirs + [f for f in files if os.path.splitext(f)[1].lower() in ARCHIVES]:
                found.append(os.path.join(root, name))
    return found


def match(wanted, local):
    want_t = tokens(wanted["name"])
    best, best_score = None, 0.0
    for path in local:
        stem = os.path.splitext(os.path.basename(path))[0]
        cand_t = tokens(stem)
        if not want_t or not cand_t:
            continue
        contain = len(want_t & cand_t) / len(want_t)
        ratio = difflib.SequenceMatcher(None, " ".join(sorted(want_t)), " ".join(sorted(cand_t))).ratio()
        score = max(contain, ratio)
        if score > best_score:
            best, best_score = path, score
    return (best, best_score) if best_score >= 0.75 else (None, best_score)


def cmd_inventory(opts):
    wanted = load_wanted(opts.wanted)
    if not wanted:
        sys.exit("no wanted items found (expects JSON lists or CSV with a 'name' column)")
    local = scan_local(opts.scan)
    used, have, missing = set(), [], []
    for w in wanted:
        path, score = match(w, local)
        (have if path else missing).append((w, path, score))
        if path:
            used.add(path)
    lines = [f"# Download status ({datetime.date.today().isoformat()})", "",
             f"**{len(have)} downloaded · {len(missing)} missing** out of {len(wanted)} wanted. "
             f"Scanned: {', '.join(opts.scan)}", "",
             f"## Missing ({len(missing)})", ""]
    for source in sorted({w['source'] for w, _, _ in missing}):
        lines.append(f"### {source}")
        for w, _, score in missing:
            if w["source"] == source:
                link = f"[{w['name']}]({w['url']})" if w.get("url") else w["name"]
                hint = f" _(closest local match {score:.0%})_" if score >= 0.5 else ""
                lines.append(f"- [ ] {link}{hint}")
        lines.append("")
    lines += [f"## Downloaded ({len(have)})", ""]
    lines += [f"- [x] {w['name']} → `{os.path.relpath(p)}`" for w, p, _ in have]
    # Only leaf downloads: skip folders that merely contain other found items.
    extra = [p for p in local if p not in used
             and not any(q != p and q.startswith(p + os.sep) for q in local)]
    lines += ["", f"## Local downloads not in any wanted list ({len(extra)})", ""]
    lines += [f"- `{os.path.relpath(p)}`" for p in extra]
    with open(opts.out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"{len(have)} downloaded, {len(missing)} missing → {opts.out}")


# ---------------------------------------------------------------- thumbnails
def cmd_thumbs(opts):
    jobs = []
    for e, out, thumb in manifest_entries(opts):
        stale = not os.path.isfile(thumb) or os.path.getmtime(thumb) < os.path.getmtime(out["blend"])
        if stale or opts.force:
            jobs.append({"id": e["id"], "blend": out["blend"], "out": thumb, "size": opts.size})
    if not jobs:
        print("all thumbnails up to date")
        return 0
    job_file = os.path.join(os.path.dirname(os.path.abspath(opts.manifest)), "_thumb_jobs.json")
    save_json(job_file, jobs)
    print(f"rendering {len(jobs)} thumbnail(s)…")
    code = subprocess.run([opts.blender, "-b", "--python-exit-code", "1", "--python",
                           os.path.join(HERE, "render_thumb.py"), "--", job_file]).returncode
    os.remove(job_file)
    return code


# ---------------------------------------------------------------- classify (Claude Batch API)
def build_schema(tax):
    themes = list(tax["themes"]) + ["both", "neither"]
    arr = lambda items=None: {"type": "array", "items": {"type": "string", **({"enum": items} if items else {})}}
    props = {
        "display_name": {"type": "string"},
        "category": {"type": "string", "enum": list(tax["categories"])},
        "subcategory": {"type": "string"},
        "function": {"type": "string"},
        "description": {"type": "string"},
        "materials": arr(), "colours": arr(), "style": arr(),
        "zones": arr(list(tax["zones"])),
        "theme_fit": {"type": "string", "enum": themes},
        "tier": {"type": "string", "enum": ["hero", "mid", "background"]},
        "tags": arr(),
        "scale_plausible": {"type": "boolean"},
        "issues": arr(),
    }
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def build_system(tax):
    cats = "\n".join(f"- {k}: {', '.join(v)}" for k, v in tax["categories"].items())
    zones = "\n".join(f"- {k}: {v}" for k, v in tax["zones"].items())
    themes = "\n".join(f"- {k}: {v}" for k, v in tax["themes"].items())
    return (
        f"You catalogue 3D assets for an architectural visualisation project: {tax['project']}\n\n"
        "For each asset you get a preview render and its measured metadata (real size in metres, "
        "triangle count, source). Describe the object as it appears and say how this project would "
        "use it. Use the measured size, not guesses; set scale_plausible to false if the size "
        "doesn't fit the object (e.g. a 3 m chair) and say why in issues. Note other problems "
        "(missing textures, low detail for close-ups, broken geometry) in issues.\n\n"
        f"Categories (category: example subcategories):\n{cats}\n\n"
        f"Zones (list every zone where it fits; use 'general' if it fits anywhere):\n{zones}\n\n"
        f"Interior themes (theme_fit; 'both' or 'neither' allowed):\n{themes}\n\n"
        "Tier: hero = detailed enough for close-ups; mid = fine at 2-5 m; background = distance only.\n"
        "Tags: 5-12 short lowercase search words (object type, material, style, use)."
    )


def cmd_classify(opts):
    tax = load_json(opts.taxonomy, None) or sys.exit(f"taxonomy not found: {opts.taxonomy}")
    tax["zones"].setdefault("general", "fits anywhere / not zone-specific")
    catalog = load_json(opts.catalog, {})
    state = load_json(opts.batches, [])
    pending_ids = {aid for b in state if not b.get("collected") for aid in b["map"].values()}
    todo = []
    for e, out, thumb in manifest_entries(opts):
        done = catalog.get(e["id"], {}).get("status") == "ok"
        if (opts.redo or not done) and e["id"] not in pending_ids and os.path.isfile(thumb):
            todo.append((e, thumb))
    missing_thumbs = [e["id"] for e, _, t in manifest_entries(opts) if not os.path.isfile(t)]
    if missing_thumbs:
        print(f"{len(missing_thumbs)} asset(s) have no thumbnail yet; run `thumbs` first")
    if not todo:
        print("nothing to classify")
        return 0

    system = [{"type": "text", "text": build_system(tax), "cache_control": {"type": "ephemeral"}}]
    fmt = {"type": "json_schema", "schema": build_schema(tax)}
    requests, mapping = [], {}
    for i, (e, thumb) in enumerate(todo):
        cid = f"a{i}-{hashlib.sha1(e['id'].encode()).hexdigest()[:12]}"
        mapping[cid] = e["id"]
        with open(thumb, "rb") as f:
            img = base64.standard_b64encode(f.read()).decode()
        meta = {k: e.get(k) for k in ("id", "source", "item", "source_file", "dims_m", "triangles",
                                      "warnings", "licence")}
        requests.append({"custom_id": cid, "params": {
            "model": opts.model,
            "max_tokens": 4000,
            "system": system,
            "output_config": {"effort": opts.effort, "format": fmt},
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img}},
                {"type": "text", "text": "Asset metadata:\n" + json.dumps(meta, indent=1)},
            ]}],
        }})

    if opts.model in PRICES:
        p_in, p_out = PRICES[opts.model]
        est = len(requests) * (1800 * p_in + 1200 * p_out) / 1e6 * 0.5
        print(f"{len(requests)} request(s) on {opts.model}, effort {opts.effort}: "
              f"estimated ≈ ${est:.2f} at batch prices (rough: ~1.8k in / ~1.2k out tokens each)")
    else:
        print(f"{len(requests)} request(s) on {opts.model} (no price table entry; no estimate)")
    if opts.dry_run:
        path = os.path.splitext(opts.batches)[0] + "_dryrun.jsonl"
        with open(path, "w") as f:
            for r in requests:
                f.write(json.dumps(r) + "\n")
        print(f"dry run: requests written to {path}; nothing sent")
        return 0
    if not opts.yes:
        print("re-run with --yes to submit (this spends API credits)")
        return 0

    import anthropic  # only needed for API calls
    client = anthropic.Anthropic()
    chunks, cur, size = [], [], 0
    for r in requests:
        n = len(json.dumps(r))
        if cur and size + n > BATCH_BYTES:
            chunks.append(cur)
            cur, size = [], 0
        cur.append(r)
        size += n
    chunks.append(cur)
    for chunk in chunks:
        batch = client.messages.batches.create(requests=chunk)
        state.append({"batch_id": batch.id, "model": opts.model, "submitted": datetime.datetime.now().isoformat(),
                      "map": {r["custom_id"]: mapping[r["custom_id"]] for r in chunk}, "collected": False})
        save_json(opts.batches, state)
        print(f"submitted {batch.id} ({len(chunk)} requests); run `collect` later (most finish within an hour)")
    return 0


def cmd_collect(opts):
    import anthropic
    client = anthropic.Anthropic()
    catalog = load_json(opts.catalog, {})
    state = load_json(opts.batches, [])
    waiting = 0
    for b in state:
        if b.get("collected"):
            continue
        batch = client.messages.batches.retrieve(b["batch_id"])
        if batch.processing_status != "ended":
            c = batch.request_counts
            print(f"{b['batch_id']}: {batch.processing_status} ({c.processing} processing, {c.succeeded} done)")
            waiting += 1
            continue
        counts = {}
        for result in client.messages.batches.results(b["batch_id"]):
            aid = b["map"].get(result.custom_id)
            if aid is None:
                continue
            entry = {"status": result.result.type, "model": b["model"],
                     "classified": datetime.date.today().isoformat()}
            if result.result.type == "succeeded":
                msg = result.result.message
                if msg.stop_reason == "refusal":
                    entry["status"] = "refused"
                elif msg.stop_reason == "max_tokens":
                    entry["status"] = "truncated"
                else:
                    text = next((blk.text for blk in msg.content if blk.type == "text"), "")
                    try:
                        entry.update(json.loads(text), status="ok")
                    except json.JSONDecodeError:
                        entry["status"] = "bad-json"
            elif result.result.type == "errored":
                entry["error"] = result.result.error.type
            counts[entry["status"]] = counts.get(entry["status"], 0) + 1
            catalog[aid] = entry
        b["collected"] = True
        save_json(opts.catalog, catalog)
        save_json(opts.batches, state)
        print(f"{b['batch_id']}: collected {counts}")
    retry = [k for k, v in catalog.items() if v.get("status") != "ok"]
    if retry:
        print(f"{len(retry)} asset(s) not ok (refused/errored/expired); `classify --redo` resends them")
    return 1 if waiting else 0


# ---------------------------------------------------------------- library + browser
def catalog_rows(opts):
    catalog = load_json(opts.catalog, {})
    for e, out, thumb in manifest_entries(opts):
        tags = catalog.get(e["id"], {})
        if tags.get("status") == "ok":
            yield e, out, thumb, tags


def cat_path(tags):
    clean = lambda s: re.sub(r"[^\w &-]+", "", s).strip().title() or "Other"
    return f"{clean(tags['category'].replace('_', ' '))}/{clean(tags.get('subcategory') or 'General')}"


def cmd_library(opts):
    lib = os.path.abspath(opts.library)
    jobs, cats = [], {}
    for e, out, thumb, tags in catalog_rows(opts):
        path = cat_path(tags)
        cid = str(uuid.uuid5(uuid.NAMESPACE_URL, "asset-catalog:" + path))
        cats[path] = cid
        safe = re.sub(r"[^\w-]+", "_", e["id"])
        jobs.append({"blend": out["blend"], "thumb": thumb if os.path.isfile(thumb) else None,
                     "out": os.path.join(lib, *path.split("/"), safe + ".blend"),
                     "catalog_id": cid, "name": tags["display_name"],
                     "description": f"{tags['description']} | {tags['function']} | licence: {e.get('licence')}",
                     "author": e["source"],
                     "tags": sorted(set(tags["tags"] + tags["zones"] + [tags["tier"], tags["theme_fit"]]))})
    if not jobs:
        sys.exit("no classified assets; run classify + collect first")
    os.makedirs(lib, exist_ok=True)
    lines = ["# This is an Asset Catalog Definition file for Blender.", "", "VERSION 1", ""]
    parents = {p.split("/")[0] for p in cats}
    for p in sorted(parents):
        lines.append(f"{uuid.uuid5(uuid.NAMESPACE_URL, 'asset-catalog:' + p)}:{p}:{p}")
    lines += [f"{cid}:{p}:{p.replace('/', '-')}" for p, cid in sorted(cats.items())]
    with open(os.path.join(lib, "blender_assets.cats.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    job_file = os.path.join(lib, "_library_jobs.json")
    save_json(job_file, jobs)
    code = subprocess.run([opts.blender, "-b", "--python-exit-code", "1", "--python",
                           os.path.join(HERE, "build_library.py"), "--", job_file]).returncode
    os.remove(job_file)
    print(f"library: {lib} ({len(jobs)} assets, {len(cats)} catalogs). "
          "Add it in Blender: Preferences › File Paths › Asset Libraries.")
    return code


def cmd_browse(opts):
    out_dir = os.path.dirname(os.path.abspath(opts.html))
    items = []
    for e, out, thumb, tags in catalog_rows(opts):
        items.append({
            "id": e["id"], "name": tags["display_name"], "category": tags["category"],
            "sub": tags.get("subcategory", ""), "function": tags["function"], "desc": tags["description"],
            "zones": tags["zones"], "theme": tags["theme_fit"], "tier": tags["tier"], "tags": tags["tags"],
            "materials": tags["materials"], "issues": tags["issues"], "dims": e.get("dims_m"),
            "source": e["source"], "licence": e.get("licence"),
            "thumb": os.path.relpath(thumb, out_dir) if os.path.isfile(thumb) else "",
            "blend": os.path.relpath(out["blend"], out_dir), "fbx": os.path.relpath(out.get("fbx", ""), out_dir),
        })
    page = open(os.path.join(HERE, "browser_template.html")).read()
    page = page.replace("/*DATA*/[]", json.dumps(items).replace("</", "<\\/"))
    page = page.replace("<!--TITLE-->", html.escape(opts.title))
    with open(opts.html, "w") as f:
        f.write(page)
    print(f"{len(items)} assets → {opts.html}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--manifest", default="assets/manifest.json")
    p.add_argument("--catalog", default="assets/catalog.json")
    p.add_argument("--batches", default="assets/catalog_batches.json")
    sub = p.add_subparsers(dest="cmd", required=True)
    blender = os.environ.get("BLENDER_CONVERTER", "blender")

    s = sub.add_parser("inventory", help="compare wanted lists with what's downloaded")
    s.add_argument("--wanted", nargs="+", default=["wanted/*.json", "wanted/*.csv"])
    s.add_argument("--scan", nargs="+", default=["assets/inbox"])
    s.add_argument("--out", default="DOWNLOAD_STATUS.md")

    s = sub.add_parser("thumbs", help="render preview images")
    s.add_argument("--blender", default=blender)
    s.add_argument("--size", type=int, default=512)
    s.add_argument("--force", action="store_true")

    s = sub.add_parser("classify", help="tag assets with Claude (Message Batches API)")
    s.add_argument("--taxonomy", default="config/taxonomy.json")
    s.add_argument("--model", default="claude-opus-5-5")
    s.add_argument("--effort", default="low", choices=["low", "medium", "high", "xhigh", "max"])
    s.add_argument("--redo", action="store_true", help="resend assets already classified or failed")
    s.add_argument("--dry-run", action="store_true", help="write the requests to a file, send nothing")
    s.add_argument("--yes", action="store_true", help="actually submit (spends API credits)")

    sub.add_parser("collect", help="fetch finished batch results into catalog.json")

    s = sub.add_parser("library", help="build a Blender Asset Browser library")
    s.add_argument("--blender", default=blender)
    s.add_argument("--library", default="assets/library")

    s = sub.add_parser("browse", help="write a filterable HTML catalogue")
    s.add_argument("--html", default="assets/catalog.html")
    s.add_argument("--title", default="Asset catalogue")

    opts = p.parse_args()
    handler = {"inventory": cmd_inventory, "thumbs": cmd_thumbs, "classify": cmd_classify,
               "collect": cmd_collect, "library": cmd_library, "browse": cmd_browse}[opts.cmd]
    sys.exit(handler(opts) or 0)


if __name__ == "__main__":
    main()
