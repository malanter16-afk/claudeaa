"""Import everything ingest.py produced into an Unreal project (runs inside Unreal's Python).

Headless:
    UnrealEditor-Cmd.exe Project.uproject -run=pythonscript -script="C:/path/ue_import.py"
In the editor: Tools > Execute Python Script.

Environment:
    INGEST_MANIFEST  path to assets/manifest.json (default: <project>/../assets/manifest.json)
    INGEST_UE_ROOT   content folder to import into (default: /Game/Assets)

Each ok entry's .fbx (or .glb) goes to <root>/<source>/<item>; .ies files go to .../IES as
light profiles. Re-running replaces existing assets in place.
"""
import json
import os
import re

import unreal

MANIFEST = os.environ.get("INGEST_MANIFEST") or os.path.join(
    unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()), "..", "assets", "manifest.json")
ROOT = os.environ.get("INGEST_UE_ROOT", "/Game/Assets").rstrip("/")


def content_name(text):
    return re.sub(r"[^A-Za-z0-9_]", "_", text)


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

    tasks = []
    for entry in entries:
        dest = f"{ROOT}/{content_name(entry['source'])}/{content_name(entry['item'])}"
        outputs = entry.get("outputs") or {}
        model = outputs.get("fbx") or outputs.get("glb")
        if entry.get("status") == "ok" and model:
            tasks.append(import_task(os.path.join(manifest_dir, model), dest))
        for profile in entry.get("photometry") or []:
            if profile.lower().endswith(".ies"):
                tasks.append(import_task(os.path.join(manifest_dir, profile), f"{dest}/IES"))

    if not tasks:
        unreal.log_warning(f"[ingest] nothing to import from {MANIFEST}")
        return
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    for task in tasks:
        imported = list(task.imported_object_paths)
        log = unreal.log if imported else unreal.log_warning
        log(f"[ingest] {os.path.basename(task.filename)} -> {imported or 'FAILED'}")


main()
