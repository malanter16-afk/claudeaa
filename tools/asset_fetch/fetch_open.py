#!/usr/bin/env python3
"""Download open-licence assets (no login needed) straight into assets/inbox/, ready for ingest.

    python tools/asset_fetch/fetch_open.py [--list wanted/open_assets.json] [--res 2k]
                                           [--sketchfab-token TOKEN] [--only ID]

List entries (JSON array):
    {"source": "polyhaven", "kind": "model|texture|hdri", "id": "potted_plant_01"}
    {"source": "ambientcg", "id": "Marble012", "real_size_m": 2.0}
    {"source": "url", "id": "survey-of-india-map", "url": "https://...pdf", "dest": "assets/reference"}
    {"source": "sketchfab", "id": "<model uid>", "slug": "rolling-mill"}    (needs your API token)

Each item lands in assets/inbox/<source>/<id>/ with an asset.json (licence, URL, attribution), so
`ingest.py run` converts it and the licence trail stays complete. Existing items are skipped (no
duplicates). Poly Haven asks for a unique User-Agent and no mirroring: this fetches only what's listed.
Standard library only.
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import zipfile

UA = {"User-Agent": "kixr-sail-viz/1.0 (asset pipeline; contact via project owner)"}


def get(url, headers=None, binary=False):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    return data if binary else json.loads(data)


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def write_sidecar(folder, **fields):
    with open(os.path.join(folder, "asset.json"), "w") as f:
        json.dump({k: v for k, v in fields.items() if v is not None}, f, indent=2)


def polyhaven(item, inbox, res):
    aid, kind = item["id"], item.get("kind", "model")
    files = get(f"https://api.polyhaven.com/files/{aid}")
    info = get(f"https://api.polyhaven.com/info/{aid}")
    page = f"https://polyhaven.com/a/{aid}"
    if kind == "hdri":
        hdr = files["hdri"].get(res) or files["hdri"][sorted(files["hdri"])[0]]
        url = hdr["exr"]["url"] if "exr" in hdr else hdr["hdr"]["url"]
        dest = os.path.join(item.get("dest", "assets/hdri"), os.path.basename(url))
        save(dest, get(url, binary=True))
        return dest
    folder = os.path.join(inbox, "polyhaven", aid)
    if kind == "model":
        g = files["gltf"].get(res) or files["gltf"][sorted(files["gltf"])[0]]
        gl = g["gltf"]
        save(os.path.join(folder, os.path.basename(gl["url"])), get(gl["url"], binary=True))
        for rel, inc in gl.get("include", {}).items():
            save(os.path.join(folder, rel), get(inc["url"], binary=True))
            time.sleep(0.2)
        size = None
    else:  # texture: save maps under names the ingest material builder recognises
        maps = {"Diffuse": "color", "Rough": "rough", "nor_gl": "normal", "Displacement": "height",
                "Metal": "metal"}
        for key, slot in maps.items():
            if key in files:
                entry = files[key].get(res) or files[key][sorted(files[key])[0]]
                url = (entry.get("jpg") or entry.get("png") or next(iter(entry.values())))["url"]
                save(os.path.join(folder, f"{aid}_{slot}{os.path.splitext(url)[1]}"), get(url, binary=True))
                time.sleep(0.2)
        dims = info.get("dimensions")  # millimetres, [width, height]
        size = round(dims[0] / 1000, 3) if dims else None
    write_sidecar(folder, licence="CC0 1.0 (Poly Haven)", url=page, commercial_ok=True,
                  attribution=None, real_size_m=item.get("real_size_m") or size)
    return folder


def ambientcg(item, inbox, res):
    aid = item["id"]
    folder = os.path.join(inbox, "ambientcg", aid)
    tag = res.upper()  # e.g. 2K
    data = get(f"https://ambientcg.com/get?file={aid}_{tag}-JPG.zip", binary=True)
    tmp = os.path.join(folder, f"{aid}_{tag}-JPG.zip")
    save(tmp, data)
    with zipfile.ZipFile(tmp) as z:
        z.extractall(folder)
    os.remove(tmp)
    # Keep only the PBR maps: the zip also carries a .blend/.usdc/.mtlx, a preview PNG and a DirectX normal.
    keep = ("_Color", "_Roughness", "_NormalGL", "_Displacement", "_Metalness", "_AmbientOcclusion", "_Opacity")
    for f in os.listdir(folder):
        if f != "asset.json" and not (f.lower().endswith((".jpg", ".png")) and any(k in f for k in keep)):
            os.remove(os.path.join(folder, f))
    write_sidecar(folder, licence="CC0 1.0 (ambientCG)", url=f"https://ambientcg.com/view?id={aid}",
                  commercial_ok=True, attribution=None, real_size_m=item.get("real_size_m"))
    return folder


def sketchfab(item, inbox, token):
    if not token:
        raise RuntimeError("needs --sketchfab-token (Sketchfab › Settings › Password & API)")
    uid = item["id"]
    meta = get(f"https://api.sketchfab.com/v3/models/{uid}")
    licence = (meta.get("license") or {}).get("label", "unknown")
    if "NonCommercial" in licence or "NoDerivs" in licence:
        raise RuntimeError(f"licence '{licence}' is not usable for commercial renders")
    links = get(f"https://api.sketchfab.com/v3/models/{uid}/download", headers={"Authorization": f"Token {token}"})
    url = (links.get("gltf") or links.get("glb") or {}).get("url")
    if not url:
        raise RuntimeError("no glTF download offered")
    folder = os.path.join(inbox, "sketchfab", item.get("slug") or uid)
    save(os.path.join(folder, "model.zip"), get(url, binary=True))
    author = (meta.get("user") or {}).get("displayName")
    write_sidecar(folder, licence=licence, url=meta.get("viewerUrl"), commercial_ok=True,
                  attribution=f"\"{meta.get('name')}\" by {author}, {licence}, via Sketchfab")
    return folder


def plain_url(item):
    dest = os.path.join(item.get("dest", "assets/reference"), os.path.basename(item["url"]))
    save(dest, get(item["url"], binary=True))
    return dest


def target(item, inbox):
    if item["source"] == "url":
        return os.path.join(item.get("dest", "assets/reference"), os.path.basename(item["url"]))
    if item["source"] == "polyhaven" and item.get("kind") == "hdri":
        return None  # file name unknown until fetched; HDRIs are skipped by folder check below
    sub = item.get("slug") if item["source"] == "sketchfab" else item["id"]
    return os.path.join(inbox, item["source"], sub)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--list", default="wanted/open_assets.json")
    p.add_argument("--inbox", default="assets/inbox")
    p.add_argument("--res", default="2k", help="1k/2k/4k (Poly Haven, ambientCG)")
    p.add_argument("--sketchfab-token", default=os.environ.get("SKETCHFAB_TOKEN"))
    p.add_argument("--only", help="fetch one id")
    opts = p.parse_args()

    items = json.load(open(opts.list))
    done = skipped = failed = 0
    hdri_dir_cache = {}
    for item in items:
        if opts.only and item["id"] != opts.only:
            continue
        dest = target(item, opts.inbox)
        if item["source"] == "polyhaven" and item.get("kind") == "hdri":
            d = item.get("dest", "assets/hdri")
            have = hdri_dir_cache.setdefault(d, os.listdir(d) if os.path.isdir(d) else [])
            if any(f.startswith(item["id"] + "_") for f in have):
                skipped += 1
                continue
        elif dest and os.path.exists(dest) and (os.path.isfile(dest) or os.listdir(dest)):
            print(f"= {item['source']}/{item['id']}: already there")
            skipped += 1
            continue
        try:
            if item["source"] == "polyhaven":
                out = polyhaven(item, opts.inbox, opts.res)
            elif item["source"] == "ambientcg":
                out = ambientcg(item, opts.inbox, opts.res)
            elif item["source"] == "sketchfab":
                out = sketchfab(item, opts.inbox, opts.sketchfab_token)
            elif item["source"] == "url":
                out = plain_url(item)
            else:
                raise RuntimeError(f"unknown source {item['source']}")
            print(f"+ {item['source']}/{item['id']} → {out}")
            done += 1
        except Exception as exc:  # keep going, report at the end
            print(f"! {item['source']}/{item['id']}: {exc}")
            failed += 1
        time.sleep(0.5)
    print(f"\n{done} fetched, {skipped} already present, {failed} failed. Next: python tools/asset_ingest/ingest.py run")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
