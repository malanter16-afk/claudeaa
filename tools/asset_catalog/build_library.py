"""Write one Blender asset per catalogued item (runs inside Blender).

    blender -b --python build_library.py -- jobs.json
jobs.json: [{"blend", "thumb", "out", "catalog_id", "name", "description", "author", "tags"}].
Each output .blend holds one collection marked as an asset, with catalog, tags and preview, so the
library folder can be added under Preferences › File Paths › Asset Libraries.
"""
import json
import os
import sys

import bpy


def main():
    jobs = json.load(open(sys.argv[sys.argv.index("--") + 1]))
    failed = 0
    for job in jobs:
        try:
            bpy.ops.wm.open_mainfile(filepath=job["blend"])
            scene = bpy.context.scene
            coll = bpy.data.collections.new(job["name"])
            scene.collection.children.link(coll)
            for obj in list(scene.objects):
                if obj.name not in coll.objects:
                    coll.objects.link(obj)
                for parent in list(obj.users_collection):
                    if parent is not coll:
                        parent.objects.unlink(obj)
            coll.asset_mark()
            data = coll.asset_data
            data.catalog_id = job["catalog_id"]
            data.description = job["description"]
            data.author = job["author"]
            for tag in job["tags"]:
                data.tags.new(tag, skip_if_exists=True)
            if job.get("thumb"):
                with bpy.context.temp_override(id=coll):
                    bpy.ops.ed.lib_id_load_custom_preview(filepath=job["thumb"])
            os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=job["out"], compress=True)
            print(f"[library] {job['name']} -> {job['out']}")
        except Exception as exc:
            failed += 1
            print(f"[library] FAILED {job['name']}: {exc}")
    if failed:
        sys.exit(1)


main()
