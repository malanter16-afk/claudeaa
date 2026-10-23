"""Convert one downloaded asset into normalised .blend/.glb/.fbx (runs inside Blender).

Usage (called by ingest.py, not by hand):
    blender -b --python blender_convert.py -- --src FILE --out-dir DIR --name NAME
                [--search-dir DIR] [--real-height M] [--kind furniture|prop|light|architecture]
                [--usd]
    blender -b --python blender_convert.py -- --install-addon PYSLAPI.zip

Normalisation: 1 unit = 1 m, transforms applied, origin at the bottom centre of the
bounding box, cameras/lights/edge-only meshes removed, textures relinked and packed.
Writes report.json next to the outputs.
"""
import json
import os
import sys

import addon_utils
import bpy
from mathutils import Matrix, Vector

SKP_ADDON = "sketchup_importer"

# Unit factors tried, in order, when no real size is given. The first that puts the
# largest dimension inside PLAUSIBLE_M wins. SketchUp works in inches, so .skp tries
# inches before centimetres; most other untyped formats (OBJ) are centimetres.
UNIT_CANDIDATES = {
    ".skp": [1.0, 0.0254, 0.01, 0.001],
    "default": [1.0, 0.01, 0.001, 0.0254],
}
PLAUSIBLE_M = (0.02, 8.0)


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = {"usd": False}
    i = 0
    while i < len(argv):
        key = argv[i].lstrip("-").replace("-", "_")
        if key == "usd":
            args["usd"] = True
            i += 1
        else:
            args[key] = argv[i + 1]
            i += 2
    return args


def install_addon(zip_path):
    bpy.ops.preferences.addon_install(filepath=os.path.abspath(zip_path), overwrite=True)
    addon_utils.enable(SKP_ADDON, default_set=True, persistent=True)
    bpy.ops.wm.save_userpref()
    print(f"[convert] installed and enabled {SKP_ADDON}")


def ensure_skp_importer():
    if not hasattr(bpy.ops.import_scene, "skp"):
        addon_utils.enable(SKP_ADDON, default_set=True)
    if not hasattr(bpy.ops.import_scene, "skp"):
        raise RuntimeError(
            "SketchUp importer not available. Run `ingest.py setup-skp --zip <pyslapi release zip>` "
            "on Windows or macOS (the SketchUp SDK has no Linux build).")


def import_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext in (".usd", ".usda", ".usdc", ".usdz"):
        bpy.ops.wm.usd_import(filepath=path)
    elif ext == ".dae":
        if not hasattr(bpy.ops.wm, "collada_import"):
            raise RuntimeError("This Blender has no Collada importer; use Blender 4.5 LTS as the converter.")
        bpy.ops.wm.collada_import(filepath=path)
    elif ext == ".stl":
        bpy.ops.wm.stl_import(filepath=path)
    elif ext == ".ply":
        bpy.ops.wm.ply_import(filepath=path)
    elif ext == ".3ds":
        if not hasattr(bpy.ops.import_scene, "max3ds"):
            raise RuntimeError("3DS importer extension (io_scene_3ds) is not installed in the converter Blender.")
        bpy.ops.import_scene.max3ds(filepath=path)
    elif ext == ".skp":
        ensure_skp_importer()
        bpy.ops.import_scene.skp(filepath=path, import_camera=False, scenes_as_camera=False,
                                 reuse_material=True)
    elif ext == ".blend":
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.objects = list(src.objects)
        for obj in dst.objects:
            if obj is not None:
                bpy.context.scene.collection.objects.link(obj)
    else:
        raise RuntimeError(f"Unsupported format: {ext}")
    return ext


def clean_scene():
    removed = []
    for obj in list(bpy.data.objects):
        drop = obj.type in {"CAMERA", "LIGHT", "LIGHT_PROBE", "SPEAKER"}
        if obj.type == "MESH" and len(obj.data.polygons) == 0:
            drop = True  # 2D linework / guides from CAD-derived files
        if drop:
            removed.append(f"{obj.type}:{obj.name}")
            bpy.data.objects.remove(obj, do_unlink=True)
    return removed


def mesh_objects():
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def world_bbox(objs):
    lo = Vector((float("inf"),) * 3)
    hi = Vector((float("-inf"),) * 3)
    for obj in objs:
        for corner in obj.bound_box:
            p = obj.matrix_world @ Vector(corner)
            lo = Vector(map(min, lo, p))
            hi = Vector(map(max, hi, p))
    return lo, hi


def choose_unit_factor(ext, dims, real_height, kind, warnings):
    if real_height:
        if dims.z <= 0:
            raise RuntimeError("Asset has zero height; cannot scale to real height.")
        return float(real_height) / dims.z, "real_height"
    if kind == "architecture":
        return 1.0, "kind=architecture (no guess)"
    largest = max(dims)
    for f in UNIT_CANDIDATES.get(ext, UNIT_CANDIDATES["default"]):
        if PLAUSIBLE_M[0] <= largest * f <= PLAUSIBLE_M[1]:
            if f != 1.0:
                warnings.append(f"unit guessed: x{f} (largest dim {largest:.3f} -> {largest * f:.3f} m); "
                                "set real_height_m in asset.json to pin it")
            return f, "guess"
    warnings.append(f"no plausible unit for largest dim {largest:.3f}; left at x1")
    return 1.0, "fallback"


def normalise(ext, real_height, kind, warnings):
    meshes = mesh_objects()
    if not meshes:
        raise RuntimeError("No mesh geometry after import.")
    lo, hi = world_bbox(meshes)
    factor, how = choose_unit_factor(ext, hi - lo, real_height, kind, warnings)
    offset = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    xform = Matrix.Scale(factor, 4) @ Matrix.Translation(-offset)

    for obj in bpy.context.scene.objects:
        if obj.parent is None:
            obj.matrix_world = xform @ obj.matrix_world

    # Linked duplicates (common in SketchUp components) block transform_apply.
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.make_single_user(object=True, obdata=True, material=False)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.select_all(action="DESELECT")
    return factor, how


def relink_and_pack(search_dir, warnings):
    if search_dir and os.path.isdir(search_dir):
        bpy.ops.file.find_missing_files(directory=search_dir)
    missing = []
    for img in bpy.data.images:
        if img.source != "FILE" or img.packed_file:
            continue
        path = bpy.path.abspath(img.filepath)
        if not os.path.isfile(path):
            missing.append(img.name)
    if missing:
        warnings.append(f"missing textures: {', '.join(sorted(missing))}")
    try:
        bpy.ops.file.pack_all()
    except RuntimeError as exc:
        warnings.append(f"pack_all: {exc}")
    return missing


def stats():
    tris = 0
    no_uv = []
    for obj in mesh_objects():
        tris += sum(len(p.vertices) - 2 for p in obj.data.polygons)
        if not obj.data.uv_layers:
            no_uv.append(obj.name)
    lo, hi = world_bbox(mesh_objects())
    return {
        "dims_m": [round(v, 4) for v in (hi - lo)],
        "triangles": tris,
        "mesh_objects": len(mesh_objects()),
        "materials": len([m for m in bpy.data.materials if m.users]),
        "meshes_without_uv": no_uv,
    }


def join_for_unreal(name):
    """One mesh per asset so Unreal imports it as a single static mesh (materials kept)."""
    meshes = mesh_objects()
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
        bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = joined.data.name = name
    for obj in list(bpy.context.scene.objects):
        if obj is not joined:
            bpy.data.objects.remove(obj, do_unlink=True)


def export_all(out_dir, name, want_usd, kind, warnings):
    os.makedirs(out_dir, exist_ok=True)
    outputs = {}
    # .blend and .glb keep the original hierarchy for Blender work.
    blend = os.path.join(out_dir, f"{name}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    outputs["blend"] = blend

    glb = os.path.join(out_dir, f"{name}.glb")
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB")
    outputs["glb"] = glb

    # .fbx/.usdc are for Unreal: joined into one mesh unless it is a room or building.
    if kind != "architecture":
        join_for_unreal(name)

    fbx = os.path.join(out_dir, f"{name}.fbx")
    bpy.ops.export_scene.fbx(filepath=fbx, apply_scale_options="FBX_SCALE_UNITS", path_mode="COPY",
                             embed_textures=True, add_leaf_bones=False, mesh_smooth_type="FACE")
    outputs["fbx"] = fbx

    if want_usd:
        usd = os.path.join(out_dir, f"{name}.usdc")
        try:
            bpy.ops.wm.usd_export(filepath=usd, export_materials=True, generate_preview_surface=True,
                                  relative_paths=True)
            outputs["usd"] = usd
        except (RuntimeError, TypeError) as exc:
            warnings.append(f"usd export failed: {exc}")
    return outputs


def main():
    args = parse_args()
    if "install_addon" in args:
        install_addon(args["install_addon"])
        return

    src, out_dir, name = args["src"], args["out_dir"], args["name"]
    warnings = []
    report = {"source_file": src, "ok": False}
    try:
        bpy.ops.wm.read_homefile(use_empty=True)
        ext = import_file(src)
        report["format"] = ext
        report["removed"] = clean_scene()
        report["unit_factor"], report["unit_method"] = normalise(
            ext, args.get("real_height"), args.get("kind"), warnings)
        report["missing_textures"] = relink_and_pack(args.get("search_dir"), warnings)
        report.update(stats())
        report["outputs"] = export_all(out_dir, name, args["usd"], args.get("kind"), warnings)
        report["ok"] = True
    except Exception as exc:  # report every failure instead of crashing the batch
        report["error"] = f"{type(exc).__name__}: {exc}"
    report["warnings"] = warnings
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print(f"[convert] {name}: {'ok' if report['ok'] else report.get('error')}")


main()
