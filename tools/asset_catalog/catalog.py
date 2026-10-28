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
import zipfile

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
                    items.append({**r, "source": r.get("source") or src})
    seen, unique = set(), []
    for it in items:  # the same file can match two patterns; the same URL can be listed twice
        key = (it.get("url"), it["source"], it["name"])
        if key not in seen:
            seen.add(key)
            unique.append(it)
    return unique


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


EASY_FORMATS = {".fbx", ".obj", ".glb", ".gltf", ".usd", ".usdc", ".usdz", ".3ds", ".blend", ".dae",
                ".step", ".stp", ".iges", ".igs"}
HARD_FORMATS = {".max", ".skp"}


def local_formats(path):
    """Model formats inside a local download (zip contents or folder files)."""
    names = []
    try:
        if os.path.isdir(path):
            names = [f for _, _, fs in os.walk(path) for f in fs]
        elif path.lower().endswith(".zip"):
            names = zipfile.ZipFile(path).namelist()
    except (OSError, zipfile.BadZipFile):
        return set()
    return {os.path.splitext(n)[1].lower() for n in names}


def format_note(path):
    exts = local_formats(path)
    if exts & HARD_FORMATS and not exts & EASY_FORMATS:
        return f" ⚠ only {'/'.join(sorted(exts & HARD_FORMATS))}: get an FBX/OBJ/3DS version if a source offers one"
    return ""


def cmd_inventory(opts):
    """Wanted items vs local downloads. Items may carry:
    match  short phrase used for matching (file names rarely contain the brand)
    group  need-group, e.g. "Z1 lounge chair"; need = how many items of the group to get (default 1).
           Once a group has enough downloads, its other alternatives count as covered, not missing.
    type   "category" = a browse-and-pick task (no file to match); priority 1-3 sorts the missing list."""
    wanted = load_wanted(opts.wanted)
    if not wanted:
        sys.exit("no wanted items found (expects JSON lists or CSV with a 'name' column)")
    local = scan_local(opts.scan)
    used, rows = set(), []
    for w in wanted:
        if w.get("type") == "category":
            rows.append((w, None, 0.0))
            continue
        path, score = match({"name": w.get("match") or w["name"]}, local)
        rows.append((w, path, score))
        if path:
            used.add(path)

    groups = {}
    for w, path, _ in rows:
        g = groups.setdefault(w.get("group") or f"_single:{w['name']}", {"need": int(w.get("need", 1)), "have": 0})
        g["have"] += bool(path)
    have = [(w, p) for w, p, _ in rows if p]
    covered = [(w, groups[w.get("group")]) for w, p, _ in rows
               if not p and w.get("group") and groups[w["group"]]["have"] >= groups[w["group"]]["need"]]
    covered_ids = {id(w) for w, _ in covered}
    tasks = [w for w, p, _ in rows if w.get("type") == "category" and id(w) not in covered_ids]
    missing = [(w, s) for w, p, s in rows
               if not p and w.get("type") != "category" and id(w) not in covered_ids]
    missing.sort(key=lambda ws: (int(ws[0].get("priority", 2)), ws[0].get("group") or "", ws[0]["source"]))

    def link(w):
        return f"[{w['name']}]({w['url']})" if w.get("url") else w["name"]

    lines = [f"# Download status ({datetime.date.today().isoformat()})", "",
             f"**{len(have)} downloaded · {len(missing)} missing · {len(covered)} covered by an alternative · "
             f"{len(tasks)} browse tasks** out of {len(wanted)} wanted. Scanned: {', '.join(opts.scan)}", "",
             f"## Missing, by priority ({len(missing)})", ""]
    last = None
    for w, score in missing:
        head = f"P{w.get('priority', 2)} · {w.get('group') or 'single items'}"
        if w.get("group"):
            g = groups[w["group"]]
            head += f" (need {g['need'] - g['have']} more of {g['need']}; pick ONE alternative per need)"
        if head != last:
            lines += ["", f"### {head}"]
            last = head
        hint = f" _(closest local match {score:.0%}; check it)_" if score >= 0.5 else ""
        extra = " · ".join(x for x in (w.get("zone"), w.get("use"), w.get("notes")) if x)
        lines.append(f"- [ ] {link(w)} [{w['source']}]{hint}" + (f": {extra}" if extra else ""))
    lines += ["", f"## Browse-and-pick tasks ({len(tasks)})", ""]
    lines += [f"- [ ] {link(w)} [{w['source']}]: {w.get('use') or ''} {w.get('notes') or ''}".rstrip() for w in tasks]
    lines += ["", f"## Downloaded ({len(have)})", ""]
    lines += [f"- [x] {w['name']} [{w['source']}] → `{os.path.abspath(p)}`{format_note(p)}" for w, p in have]
    lines += ["", f"## Covered by an alternative ({len(covered)}): skip these", ""]
    lines += [f"- {w['name']} [{w['source']}] ({w['group']}: {g['have']}/{g['need']} downloaded)" for w, g in covered]
    # Only leaf downloads: skip folders that merely contain other found items.
    extra = [p for p in local if p not in used
             and not any(q != p and q.startswith(p + os.sep) for q in local)]
    lines += ["", f"## Local downloads not in any wanted list ({len(extra)})", ""]
    lines += [f"- `{os.path.abspath(p)}`" for p in extra]
    with open(opts.out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"{len(have)} downloaded, {len(missing)} missing, {len(covered)} covered, {len(tasks)} browse tasks → {opts.out}")


# ---------------------------------------------------------------- thumbnails
def cmd_thumbs(opts):
    jobs = []
    views = [v.strip() for v in opts.views.split(",") if v.strip()]
    for e, out, thumb in manifest_entries(opts):
        vdir = os.path.join(os.path.dirname(thumb), "views")
        stale = (not os.path.isfile(thumb) or os.path.getmtime(thumb) < os.path.getmtime(out["blend"])
                 or not os.path.isfile(os.path.join(vdir, "palette.json"))
                 or any(not os.path.isfile(os.path.join(vdir, v + ".png")) for v in views if v != "hero"))
        if stale or opts.force:
            jobs.append({"id": e["id"], "blend": out["blend"], "out": thumb, "size": opts.size, "views": views})
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
PHOTO_WORDS = {"preview", "render", "photo", "thumb", "thumbnail", "cover", "product", "image", "main", "img"}


def b64_image(path, max_px=768):
    """Image block; downscaled with Pillow when available (the API resizes large images anyway)."""
    ext = os.path.splitext(path)[1].lower()
    media = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(ext)
    if not media:
        return None
    data = open(path, "rb").read()
    try:
        from PIL import Image
        import io
        im = Image.open(io.BytesIO(data))
        if max(im.size) > max_px:
            im.thumbnail((max_px, max_px))
            buf = io.BytesIO()
            im.convert("RGB").save(buf, "JPEG", quality=88)
            data, media = buf.getvalue(), "image/jpeg"
    except ImportError:
        if len(data) > 4_500_000:
            return None
    return {"type": "image", "source": {"type": "base64", "media_type": media,
                                        "data": base64.standard_b64encode(data).decode()}}


def view_blocks(thumb):
    """Hero thumbnail first, then front/side/detail views if rendered."""
    blocks = [b64_image(thumb)]
    vdir = os.path.join(os.path.dirname(thumb), "views")
    for view in ("front", "side", "detail"):
        path = os.path.join(vdir, view + ".png")
        if os.path.isfile(path):
            blocks.append(b64_image(path))
    blocks = [b for b in blocks if b]
    return blocks, len(blocks)


def maker_photo(entry, thumb):
    """The manufacturer's preview image from the unpacked download, if one is recognisable."""
    if entry.get("kind") == "material":
        return None
    item_dir = os.path.dirname(thumb)
    work = os.path.join(os.path.dirname(os.path.dirname(item_dir)), "_work", entry["source"], entry["item"])
    best = None
    for root, _, files in os.walk(work):
        for f in files:
            stem, ext = os.path.splitext(f)
            toks = set(re.split(r"[^a-z0-9]+", stem.lower()))
            if ext.lower() in (".jpg", ".jpeg", ".png", ".webp") and toks & PHOTO_WORDS:
                path = os.path.join(root, f)
                if best is None or os.path.getsize(path) > os.path.getsize(best):
                    best = path
    return b64_image(best) if best else None


def build_schema(tax):
    themes = list(tax["themes"]) + ["both", "neither"]
    arr = lambda items=None: {"type": "array", "items": {"type": "string", **({"enum": items} if items else {})}}
    props = {
        "display_name": {"type": "string"},
        "category": {"type": "string", "enum": list(tax["categories"])},
        "subcategory": {"type": "string"},
        "function": {"type": "string"},
        "description": {"type": "string"},
        "appearance": {"type": "string"},
        "form": arr(),
        "finishes": arr(),
        "colour_palette": {"type": "array", "items": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "hex": {"type": "string"},
                           "role": {"type": "string", "enum": ["primary", "secondary", "accent"]}},
            "required": ["name", "hex", "role"], "additionalProperties": False}},
        "design_reference": {"type": "string"},
        "visual_quality": {"type": "string", "enum": ["photoreal", "good", "basic", "placeholder"]},
        "matches_maker_photo": {"type": "string", "enum": ["yes", "partly", "no", "no_photo"]},
        "materials": arr(), "colours": arr(), "style": arr(),
        "zones": arr(list(tax["zones"])),
        "theme_fit": {"type": "string", "enum": themes},
        "tier": {"type": "string", "enum": ["hero", "mid", "background"]},
        "tags": arr(),
        "scale_plausible": {"type": "boolean"},
        "issues": arr(),
    }
    if tax.get("space_types"):  # optional: lets one library serve homes, offices, plants, sites...
        props["space_types"] = arr(list(tax["space_types"]))
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
        "Tags: 5-12 short lowercase search words (object type, material, colour, finish, form, style, use).\n\n"
        "Describe how the object ACTUALLY LOOKS in the renders, not what the product name suggests:\n"
        "- appearance: 2-3 sentences on silhouette, proportions, structure and details (e.g. 'low, wide "
        "lounge chair; chromed flat-bar X-frame; six tufted tan leather cushions on straps').\n"
        "- form: shape words (cantilever, four-leg, sled base, swivel, curved, angular, slender, chunky, "
        "upholstered, tufted, open frame, monolithic).\n"
        "- finishes: material + finish pairs as seen (brushed stainless, polished chrome, matte black powder "
        "coat, oiled oak, tan aniline leather, boucle, honed marble).\n"
        "- colour_palette: 2-5 colours. Start from the MEASURED surface colours given in the metadata "
        "(true albedo, area-weighted; renders are lit in a grey studio and shift colours); keep their hex "
        "values, give each a plain name and a role.\n"
        "- design_reference: the design language or iconic piece it resembles, if any (else empty).\n"
        "- visual_quality: photoreal / good / basic / placeholder, judged from the close-up view.\n"
        "- matches_maker_photo: if a maker's product photo is included, does our render match it "
        "(shape, colours, materials)? Note any mismatch (missing textures, wrong colour, different model) in "
        "issues. 'no_photo' if none is included.\n"
        "Images come in this order: hero 3/4 view, then front, side, close-up detail (when present), then the "
        "maker's photo (when present, labelled)."
        + ("\n\nSpace types (space_types: every kind of space where this asset would look right, "
           "beyond this project):\n" + "\n".join(f"- {k}: {v}" for k, v in tax["space_types"].items())
           if tax.get("space_types") else "")
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
    requests, mapping, image_count = [], {}, 0
    for i, (e, thumb) in enumerate(todo):
        cid = f"a{i}-{hashlib.sha1(e['id'].encode()).hexdigest()[:12]}"
        mapping[cid] = e["id"]
        meta = {k: e.get(k) for k in ("id", "source", "item", "kind", "source_file", "dims_m",
                                      "triangles", "warnings", "licence")}
        if e.get("kind") == "material":
            meta["note"] = "Texture/material swatch shown on 1.2 m sample panels; classify the material."
        content, n_img = view_blocks(thumb)
        meta["measured_surface_colours"] = load_json(
            os.path.join(os.path.dirname(thumb), "views", "palette.json"), [])
        photo = maker_photo(e, thumb)
        if photo:
            content += [{"type": "text", "text": "Maker's product photo (from the download):"}, photo]
            n_img += 1
        content.append({"type": "text", "text": "Asset metadata:\n" + json.dumps(meta, indent=1)})
        image_count += n_img
        requests.append({"custom_id": cid, "params": {
            "model": opts.model,
            "max_tokens": 4000,
            "system": system,
            "output_config": {"effort": opts.effort, "format": fmt},
            "messages": [{"role": "user", "content": content}],
        }})

    if opts.model in PRICES:
        p_in, p_out = PRICES[opts.model]
        tok_in = len(requests) * 1500 + image_count * 330  # text + ~330 tokens per 512 px image
        tok_out = len(requests) * 1600
        est = (tok_in * p_in + tok_out * p_out) / 1e6 * 0.5
        print(f"{len(requests)} request(s), {image_count} image(s) on {opts.model}, effort {opts.effort}: "
              f"estimated ≈ ${est:.2f} at batch prices (rough: {tok_in // len(requests)} in / 1.6k out tokens each)")
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
        jobs.append({"kind": e.get("kind"), "blend": out["blend"], "thumb": thumb if os.path.isfile(thumb) else None,
                     "out": os.path.join(lib, *path.split("/"), safe + ".blend"),
                     "catalog_id": cid, "name": tags["display_name"],
                     "description": (f"{tags.get('appearance') or tags['description']} | {tags['function']} | "
                                     f"licence: {e.get('licence')}"),
                     "author": e["source"],
                     "tags": sorted(set(tags["tags"] + tags["zones"] + [tags["tier"], tags["theme_fit"]]
                                        + tags.get("form", []) + tags.get("finishes", [])
                                        + [c["name"] for c in tags.get("colour_palette", [])]))})
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
            "zones": tags["zones"], "theme": tags["theme_fit"], "tier": tags["tier"],
            "tags": tags["tags"] + tags.get("space_types", []),
            "materials": tags["materials"], "issues": tags["issues"], "dims": e.get("dims_m"),
            "appearance": tags.get("appearance", ""), "form": tags.get("form", []),
            "finishes": tags.get("finishes", []), "palette": tags.get("colour_palette", []),
            "ref": tags.get("design_reference", ""), "quality": tags.get("visual_quality", ""),
            "match": tags.get("matches_maker_photo", ""),
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
    s.add_argument("--views", default="hero,front,side,detail",
                   help="comma list from hero,front,side,detail (hero is the main thumbnail)")
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
