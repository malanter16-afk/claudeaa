#!/usr/bin/env python3
"""Turn manually downloaded assets into normalised Blender/Unreal-ready files.

    python ingest.py run   --blender PATH [--inbox assets/inbox] [--out assets/normalized]
                           [--manifest assets/manifest.json] [--only SOURCE/ITEM] [--force] [--usd]
    python ingest.py setup --blender PATH [--skp-zip pyslapi-release.zip]

Layout: every download lives in assets/inbox/<source>/<item>/ (zips are fine, kept as
downloaded) or as assets/inbox/<source>/<item>.zip. An optional asset.json in the item
folder pins licence data, the file to use and the real size (see README.md).

Standard library only; Blender does the conversion (blender_convert.py).
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
CONVERTER = os.path.join(HERE, "blender_convert.py")

# Best first. .skp needs the pyslapi add-on (Windows/macOS); .dae needs Blender <= 4.5;
# .3ds and .max need the extensions installed by `setup`.
MODEL_PRIORITY = [".blend", ".glb", ".gltf", ".fbx", ".usdc", ".usd", ".usdz", ".usda",
                  ".obj", ".dae", ".skp", ".3ds", ".max", ".stl", ".ply"]
EXTENSIONS = ["autodesk_3ds_format", "io_scene_max"]  # ids on extensions.blender.org
UNSUPPORTED = {".rfa", ".rvt", ".rte", ".dwg", ".dxf", ".c4d", ".3dm", ".skb", ".ifc",
               ".pln", ".gsm", ".vwx", ".ma", ".mb"}
PHOTOMETRY = {".ies", ".ldt"}
SKIP_DIRS = {"__MACOSX"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_items(inbox):
    """Yield (source, item, path) for each item folder or item zip."""
    for source in sorted(os.listdir(inbox)):
        sdir = os.path.join(inbox, source)
        if not os.path.isdir(sdir) or source.startswith((".", "_")):
            continue
        for entry in sorted(os.listdir(sdir)):
            path = os.path.join(sdir, entry)
            if entry.startswith("."):
                continue
            if os.path.isdir(path):
                yield source, entry, path
            elif entry.lower().endswith(".zip"):
                yield source, os.path.splitext(entry)[0], path


def fingerprint(path):
    """Hash of every file in an item (or the zip itself) to detect new downloads."""
    if os.path.isfile(path):
        return sha256(path)
    h = hashlib.sha256()
    for root, dirs, files in os.walk(path):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(root, name)
            h.update(os.path.relpath(full, path).encode())
            h.update(sha256(full).encode())
    return h.hexdigest()


def extract_all(path, work):
    """Copy/extract an item into a work folder, unpacking zips up to two levels deep."""
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)
    if os.path.isfile(path):
        zipfile.ZipFile(path).extractall(work)
    else:
        shutil.copytree(path, work, dirs_exist_ok=True)
    for _ in range(2):
        zips = [os.path.join(r, f) for r, _, fs in os.walk(work) for f in fs if f.lower().endswith(".zip")]
        for z in zips:
            target = os.path.splitext(z)[0]
            try:
                zipfile.ZipFile(z).extractall(target)
            except zipfile.BadZipFile:
                print(f"  ! bad zip skipped: {os.path.relpath(z, work)}")
            os.remove(z)


def list_files(work):
    out = []
    for root, dirs, files in os.walk(work):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        out += [os.path.join(root, f) for f in files if not f.startswith("._")]
    return out


def pick_model(files, sidecar):
    if sidecar.get("source_file"):
        wanted = sidecar["source_file"].lower()
        for f in files:
            if os.path.basename(f).lower() == wanted:
                return f
        raise SystemExit(f"asset.json source_file '{sidecar['source_file']}' not found")
    by_ext = {}
    for f in files:
        by_ext.setdefault(os.path.splitext(f)[1].lower(), []).append(f)
    for ext in MODEL_PRIORITY:
        if ext in by_ext:
            # Several of the same type (e.g. per-version FBX exports): take the largest.
            return max(by_ext[ext], key=os.path.getsize)
    return None


def load_sidecar(path):
    """Per-source defaults (inbox/<source>/source.json) overlaid by per-item asset.json."""
    data = {}
    source_defaults = os.path.join(os.path.dirname(path), "source.json")
    item_file = os.path.join(path, "asset.json") if os.path.isdir(path) else None
    for side in (source_defaults, item_file):
        if side and os.path.isfile(side):
            with open(side) as f:
                data.update(json.load(f))
    return data


def rel_to_manifest(path, opts):
    """Store output paths relative to the manifest so the project folder can move."""
    return os.path.relpath(os.path.abspath(path), os.path.dirname(os.path.abspath(opts.manifest)))


def run_blender(blender, args, log_path):
    cmd = [blender, "-b", "--python-exit-code", "1", "--python", CONVERTER, "--"] + args
    with open(log_path, "w") as log:
        return subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT).returncode


def ingest_item(opts, source, item, path, manifest):
    key = f"{source}/{item}"
    fp = fingerprint(path)
    prev = manifest.get(key)
    if (prev and prev.get("fingerprint") == fp and prev.get("status") in ("ok", "photometry-only")
            and not opts.force):
        print(f"= {key}: unchanged, skipped")
        return prev

    sidecar = load_sidecar(path)
    work = os.path.join(opts.out, "_work", source, item)
    out_dir = os.path.join(opts.out, source, item)
    extract_all(path, work)
    files = list_files(work)
    exts = {os.path.splitext(f)[1].lower() for f in files}

    entry = {
        "id": key, "source": source, "item": item, "fingerprint": fp,
        "licence": sidecar.get("licence", "TODO"), "url": sidecar.get("url", "TODO"),
        "attribution": sidecar.get("attribution"), "commercial_ok": sidecar.get("commercial_ok"),
        "ingested": datetime.date.today().isoformat(),
        "unsupported_files": sorted(os.path.relpath(f, work) for f in files
                                    if os.path.splitext(f)[1].lower() in UNSUPPORTED),
        "warnings": [],
    }

    photometry = [f for f in files if os.path.splitext(f)[1].lower() in PHOTOMETRY]
    if photometry:
        pdir = os.path.join(out_dir, "photometry")
        os.makedirs(pdir, exist_ok=True)
        for f in photometry:
            shutil.copy2(f, pdir)
        entry["photometry"] = sorted(rel_to_manifest(os.path.join(pdir, os.path.basename(f)), opts)
                                     for f in photometry)
        if ".ies" not in exts:
            entry["warnings"].append("only .ldt photometry: Unreal needs .ies (convert or download the IES)")

    model = pick_model(files, sidecar)
    if model is None:
        entry["status"] = "photometry-only" if photometry else "no-usable-model"
        if not photometry:
            entry["warnings"].append(f"no importable model; found: {', '.join(sorted(exts)) or 'nothing'}")
        print(f"{'+' if photometry else '!'} {key}: {entry['status']}")
        for w in entry["warnings"]:
            print(f"    - {w}")
        return entry

    os.makedirs(out_dir, exist_ok=True)
    args = ["--src", model, "--out-dir", out_dir, "--name", item, "--search-dir", work]
    if sidecar.get("real_height_m"):
        args += ["--real-height", str(sidecar["real_height_m"])]
    if sidecar.get("kind"):
        args += ["--kind", sidecar["kind"]]
    if opts.usd:
        args.append("--usd")
    code = run_blender(opts.blender, args, os.path.join(out_dir, "convert.log"))

    report_path = os.path.join(out_dir, "report.json")
    report = json.load(open(report_path)) if os.path.isfile(report_path) else {}
    entry.update({k: report.get(k) for k in ("format", "dims_m", "triangles", "unit_factor",
                                            "unit_method", "meshes_without_uv")})
    entry["outputs"] = {k: rel_to_manifest(v, opts) for k, v in (report.get("outputs") or {}).items()}
    entry["source_file"] = os.path.relpath(model, work)
    entry["warnings"] += report.get("warnings", [])
    if code == 0 and report.get("ok"):
        entry["status"] = "ok"
        dims = "x".join(f"{d:.2f}" for d in report["dims_m"])
        print(f"+ {key}: {entry['format']} -> {dims} m, {report['triangles']} tris")
    else:
        entry["status"] = "failed"
        entry["error"] = report.get("error", f"blender exit code {code}; see convert.log")
        print(f"! {key}: {entry['error']}")
    for w in entry["warnings"]:
        print(f"    - {w}")
    return entry


def cmd_run(opts):
    if not os.path.isdir(opts.inbox):
        sys.exit(f"inbox not found: {opts.inbox}")
    manifest = {}
    if os.path.isfile(opts.manifest):
        with open(opts.manifest) as f:
            manifest = {e["id"]: e for e in json.load(f)}
    failed = 0
    for source, item, path in find_items(opts.inbox):
        if opts.only and opts.only != f"{source}/{item}":
            continue
        entry = ingest_item(opts, source, item, path, manifest)
        manifest[entry["id"]] = entry
        failed += entry["status"] in ("failed", "no-usable-model")
    os.makedirs(os.path.dirname(os.path.abspath(opts.manifest)), exist_ok=True)
    with open(opts.manifest, "w") as f:
        json.dump(sorted(manifest.values(), key=lambda e: e["id"]), f, indent=2)
    todo = [e["id"] for e in manifest.values() if e.get("licence") == "TODO"]
    if todo:
        print(f"\n{len(todo)} item(s) still need licence data in asset.json: {', '.join(todo)}")
    print(f"manifest: {opts.manifest}")
    return 1 if failed else 0


def cmd_setup(opts):
    """Install the 3DS/MAX importer extensions (and optionally the SketchUp add-on)."""
    steps = [[opts.blender, "--online-mode", "-c", "extension", "sync"]]
    steps += [[opts.blender, "--online-mode", "-c", "extension", "install", "-s", "-e", ext]
              for ext in EXTENSIONS]
    if opts.skp_zip:
        steps.append([opts.blender, "-b", "--python-exit-code", "1", "--python", CONVERTER,
                      "--", "--install-addon", opts.skp_zip])
    for cmd in steps:
        print("$", " ".join(cmd[1:]))
        subprocess.run(cmd)  # "already installed" exits non-zero; the check below decides
    wanted = ["import_scene.max3ds", "import_scene.max"] + (["import_scene.skp"] if opts.skp_zip else [])
    check = ("import bpy, addon_utils, sys\n"
             "addon_utils.enable('sketchup_importer', default_set=True)\n"
             "def ok(op):\n"
             "    m, n = op.split('.')\n"
             "    try:\n"
             "        getattr(getattr(bpy.ops, m), n).get_rna_type(); return True\n"
             "    except (KeyError, AttributeError):\n"
             "        return False\n"
             f"missing = [op for op in {wanted!r} if not ok(op)]\n"
             "print('MISSING', missing)\n"
             "sys.exit(1 if missing else 0)\n")
    result = subprocess.run([opts.blender, "-b", "--python-exit-code", "1", "--python-expr", check],
                            capture_output=True, text=True)
    line = next((l for l in result.stdout.splitlines() if l.startswith("MISSING")), "MISSING ?")
    print("importers ready" if result.returncode == 0 else f"setup incomplete: {line}")
    return result.returncode


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    blender_default = os.environ.get("BLENDER_CONVERTER", "blender")

    r = sub.add_parser("run", help="convert everything in the inbox")
    r.add_argument("--blender", default=blender_default, help="converter Blender (4.5 LTS recommended)")
    r.add_argument("--inbox", default="assets/inbox")
    r.add_argument("--out", default="assets/normalized")
    r.add_argument("--manifest", default="assets/manifest.json")
    r.add_argument("--only", help="convert one item, e.g. knoll/barcelona-stool")
    r.add_argument("--force", action="store_true", help="reconvert unchanged items")
    r.add_argument("--usd", action="store_true", help="also export .usdc")

    s = sub.add_parser("setup", help="install importers into the converter Blender (run once)")
    s.add_argument("--blender", default=blender_default)
    s.add_argument("--skp-zip", help="pyslapi release zip (SketchUp; Windows/macOS only)")

    opts = p.parse_args()
    sys.exit(cmd_run(opts) if opts.cmd == "run" else cmd_setup(opts))


if __name__ == "__main__":
    main()
