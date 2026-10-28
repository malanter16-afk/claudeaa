"""Import everything ingest.py produced into an Unreal project (runs inside Unreal's Python).

Headless:
    UnrealEditor-Cmd.exe Project.uproject -run=pythonscript -script="C:/path/ue_import.py"
In the editor: Tools > Execute Python Script.

Environment:
    INGEST_MANIFEST  path to assets/manifest.json (default: <project>/../assets/manifest.json)
    INGEST_CATALOG   path to assets/catalog.json from tools/asset_catalog (default: next to the manifest)
    INGEST_UE_ROOT   content folder to import into (default: /Game/Assets)

Each ok entry's .fbx (or .glb) goes to <root>/<Category>/<Subcategory>/<item> when the asset has
been catalogued, else <root>/<source>/<item>. Catalogue fields (category, zones, theme, tier, tags,
licence) are written as asset metadata, searchable in the Content Browser. .ies files go to .../IES
as light profiles. Re-running replaces existing assets in place.
"""
import json
import os
import re

import unreal

MANIFEST = os.environ.get("INGEST_MANIFEST") or os.path.join(
    unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()), "..", "assets", "manifest.json")
ROOT = os.environ.get("INGEST_UE_ROOT", "/Game/Assets").rstrip("/")
CATALOG = os.environ.get("INGEST_CATALOG") or os.path.join(os.path.dirname(MANIFEST), "catalog.json")


def content_name(text):
    return re.sub(r"[^A-Za-z0-9_]", "_", text)


def destination(entry, tags):
    if tags.get("status") == "ok":
        parts = [tags["category"], tags.get("subcategory") or "General", entry["item"]]
        return ROOT + "/" + "/".join(content_name(p.title() if i < 2 else p) for i, p in enumerate(parts))
    return f"{ROOT}/{content_name(entry['source'])}/{content_name(entry['item'])}"


def tag_assets(task, entry, tags):
    meta = {"source": entry["source"], "licence": entry.get("licence") or "TODO"}
    if tags.get("status") == "ok":
        meta.update(category=tags["category"], subcategory=tags.get("subcategory", ""),
                    zones=",".join(tags["zones"]), theme=tags["theme_fit"], tier=tags["tier"],
                    tags=",".join(tags["tags"]), function=tags["function"],
                    appearance=tags.get("appearance", ""), finishes=",".join(tags.get("finishes", [])),
                    form=",".join(tags.get("form", [])), space_types=",".join(tags.get("space_types", [])),
                    colours=",".join(f"{c['name']} {c['hex']}" for c in tags.get("colour_palette", [])))
    for path in task.imported_object_paths:
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if asset is None:
            continue
        for key, value in meta.items():
            unreal.EditorAssetLibrary.set_metadata_tag(asset, key, str(value))
        unreal.EditorAssetLibrary.save_loaded_asset(asset)


def import_task(filename, destination):
    task = unreal.AssetImportTask()
    task.filename = filename
    task.destination_path = destination
    task.automated = True
    task.replace_existing = True
    task.save = True
    return task


def main():
    manifest_dir = os.path.dirname(os.path.abspath(MANIFEST))
    with open(MANIFEST) as f:
        entries = json.load(f)

    catalog = {}
    if os.path.isfile(CATALOG):
        with open(CATALOG) as f:
            catalog = json.load(f)

    tasks = []  # (task, entry, tags)
    for entry in entries:
        tags = catalog.get(entry["id"], {})
        dest = destination(entry, tags)
        outputs = entry.get("outputs") or {}
        model = outputs.get("fbx") or outputs.get("glb")
        if entry.get("status") == "ok" and model:
            tasks.append((import_task(os.path.join(manifest_dir, model), dest), entry, tags))
        for profile in entry.get("photometry") or []:
            if profile.lower().endswith(".ies"):
                tasks.append((import_task(os.path.join(manifest_dir, profile), f"{dest}/IES"), entry, tags))

    if not tasks:
        unreal.log_warning(f"[ingest] nothing to import from {MANIFEST}")
        return
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t for t, _, _ in tasks])
    for task, entry, tags in tasks:
        imported = list(task.imported_object_paths)
        log = unreal.log if imported else unreal.log_warning
        log(f"[ingest] {os.path.basename(task.filename)} -> {imported or 'FAILED'}")
        if imported:
            tag_assets(task, entry, tags)


main()
