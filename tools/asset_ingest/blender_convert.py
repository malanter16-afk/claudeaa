"""Convert one downloaded asset into normalised .blend/.glb/.fbx (runs inside Blender).

Usage (called by ingest.py, not by hand):
    blender -b --python blender_convert.py -- --src FILE --out-dir DIR --name NAME
                [--search-dir DIR] [--real-height M] [--kind furniture|prop|light|architecture]
                [--usd]
    blender -b --python blender_convert.py -- --src FOLDER --kind material --tile-size M ...
        (texture-only download: PBR material(s) on 1.2 m sample panels)
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
    ".max": [1.0, 0.0254, 0.01, 0.001],  # 3ds Max scenes are often in inches
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


def op_exists(module, name):
    # hasattr() is always True on bpy.ops; only a registered operator has an RNA type.
    try:
        getattr(getattr(bpy.ops, module), name).get_rna_type()
        return True
    except (KeyError, AttributeError):
        return False


def require_op(module, name, fix):
    if not op_exists(module, name):
        raise RuntimeError(f"bpy.ops.{module}.{name} is not available. {fix}")


def ensure_skp_importer():
    if not op_exists("import_scene", "skp"):
        addon_utils.enable(SKP_ADDON, default_set=True)
    require_op("import_scene", "skp",
               "Run `ingest.py setup --skp-zip <pyslapi release zip>` on Windows or macOS "
               "(the SketchUp SDK has no Linux build).")


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
        require_op("wm", "collada_import", "Use Blender 4.5 LTS as the converter (5.x has no Collada).")
        bpy.ops.wm.collada_import(filepath=path)
    elif ext == ".stl":
        bpy.ops.wm.stl_import(filepath=path)
    elif ext == ".ply":
        bpy.ops.wm.ply_import(filepath=path)
    elif ext == ".3ds":
        require_op("import_scene", "max3ds", "Run `ingest.py setup` to install the 3DS extension.")
        bpy.ops.import_scene.max3ds(filepath=path)
    elif ext == ".max":
        require_op("import_scene", "max", "Run `ingest.py setup` to install the MAX extension.")
        bpy.ops.import_scene.max(filepath=path)
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
    if kind in ("architecture", "material"):
        return 1.0, f"kind={kind} (no guess)"
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


# Texture-only downloads (material swatches). First matching slot wins; order matters.
MAP_SLOTS = [
    ("normal", {"normal", "nrm", "nor", "norm", "normalgl", "normaldx"}),
    ("rough", {"roughness", "rough", "rgh"}),
    ("gloss", {"gloss", "glossiness", "glossy"}),
    ("metal", {"metallic", "metalness", "metal"}),
    ("height", {"height", "disp", "displacement", "bump"}),
    ("ao", {"ao", "occlusion", "ambientocclusion"}),
    ("base", {"basecolor", "albedo", "diffuse", "diff", "color", "colour", "col"}),
]
SHORT_SUFFIX = {"n": "normal", "r": "rough", "d": "base", "h": "height"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".exr", ".tga", ".bmp"}
SKIP_WORDS = {"preview", "thumb", "thumbnail", "icon", "render", "logo"}
PANEL_M = 1.2


def map_slot(token):
    for slot, words in MAP_SLOTS:
        if token in words:
            return slot
    return SHORT_SUFFIX.get(token)


def texture_groups(folder):
    """Group images into materials: 'marble_white_rough_2k.jpg' -> group 'marble white', slot 'rough'.
    The map word is the last non-resolution token, so names like 'metal_plate_diffuse' stay correct."""
    groups = {}
    for root, _, files in os.walk(folder):
        for f in files:
            stem, ext = os.path.splitext(f)
            if ext.lower() not in IMAGE_EXTS or f.startswith("._"):
                continue
            toks = "".join(c if c.isalnum() else " " for c in stem.lower()).split()
            if SKIP_WORDS & set(toks):
                continue
            core = [t for t in toks if not (t[:-1].isdigit() and t[-1] == "k") and not t.isdigit()] or toks
            slot = map_slot(core[-1]) if core else None
            key = " ".join(core[:-1] if slot and len(core) > 1 else core) or stem
            groups.setdefault(key, {})[slot or "base"] = os.path.join(root, f)
    return {k: v for k, v in groups.items() if "base" in v or len(v) > 1}


def build_material(name, maps, tile_m):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    coord, mapping = nodes.new("ShaderNodeTexCoord"), nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1 / tile_m,) * 3
    links.new(coord.outputs["UV"], mapping.inputs["Vector"])

    def tex(path, colour):
        node = nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(path, check_existing=True)
        node.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        links.new(mapping.outputs["Vector"], node.inputs["Vector"])
        return node

    if "base" in maps:
        links.new(tex(maps["base"], True).outputs["Color"], bsdf.inputs["Base Color"])
    if "rough" in maps:
        links.new(tex(maps["rough"], False).outputs["Color"], bsdf.inputs["Roughness"])
    elif "gloss" in maps:
        inv = nodes.new("ShaderNodeInvert")
        links.new(tex(maps["gloss"], False).outputs["Color"], inv.inputs["Color"])
        links.new(inv.outputs["Color"], bsdf.inputs["Roughness"])
    if "metal" in maps:
        links.new(tex(maps["metal"], False).outputs["Color"], bsdf.inputs["Metallic"])
    normal_out = None
    if "normal" in maps:
        nmap = nodes.new("ShaderNodeNormalMap")
        links.new(tex(maps["normal"], False).outputs["Color"], nmap.inputs["Color"])
        normal_out = nmap.outputs["Normal"]
    if "height" in maps:
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.2
        links.new(tex(maps["height"], False).outputs["Color"], bump.inputs["Height"])
        if normal_out is not None:
            links.new(normal_out, bump.inputs["Normal"])
        normal_out = bump.outputs["Normal"]
    if normal_out is not None:
        links.new(normal_out, bsdf.inputs["Normal"])
    return mat


def build_material_panels(folder, tile_m, warnings):
    groups = texture_groups(folder)
    if not groups:
        raise RuntimeError("No texture images found for a material.")
    for i, (key, maps) in enumerate(sorted(groups.items())):
        name = key.title()[:60]
        bpy.ops.mesh.primitive_plane_add(size=PANEL_M, location=(i * (PANEL_M + 0.2), 0, PANEL_M / 2),
                                         rotation=(1.5708, 0, 0))
        panel = bpy.context.object
        panel.name = name
        for loop in panel.data.uv_layers.active.data:  # 1 UV unit = 1 m
            loop.uv = loop.uv * PANEL_M
        panel.data.materials.append(build_material(name, maps, tile_m))
        if "base" not in maps:
            warnings.append(f"{name}: no colour map found ({', '.join(sorted(maps))})")
    return [k.title() for k in sorted(groups)]


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
        if args.get("kind") == "material":
            tile = float(args.get("tile_size") or 1.0)
            report["materials_built"] = build_material_panels(src, tile, warnings)
            report["tile_size_m"] = tile
            ext = "material"
        else:
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
