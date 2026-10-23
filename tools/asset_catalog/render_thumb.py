"""Render studio previews and measure real colours for each normalised .blend (runs inside Blender).

    blender -b --python render_thumb.py -- jobs.json
jobs.json: [{"id", "blend", "out", "size", "views": ["hero", "front", "side", "detail"]}]

Writes <out> (the hero 3/4 view), views/<name>.png next to it for the other views, and
views/palette.json: the asset's own surface colours (material base colour or texture average,
weighted by surface area), independent of the studio lighting.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

# name: (azimuth°, elevation°, distance factor, aim height as fraction of bbox height)
VIEWS = {
    "hero": (35, 20, 1.08, 0.5),
    "front": (0, 5, 1.05, 0.5),
    "side": (90, 5, 1.05, 0.5),
    "detail": (25, 25, 0.38, 0.75),  # close-up of the upper part: material and finish
}


def bbox(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def studio(scene, lo, hi, size):
    centre, radius = (lo + hi) / 2, max((hi - lo).length / 2, 0.05)
    cam_data = bpy.data.cameras.new("ThumbCam")
    cam_data.lens = 50
    cam = bpy.data.objects.new("ThumbCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    for name, loc, energy, size_m in (("Key", (-1.5, -2, 2.5), 400, 2.0), ("Fill", (2.5, -1, 1.2), 120, 3.0),
                                      ("Rim", (0.5, 2.5, 2.0), 200, 1.5)):
        light = bpy.data.lights.new(name, "AREA")
        light.energy = energy * max(radius, 0.3) ** 2
        light.size = size_m * max(radius, 0.3)
        obj = bpy.data.objects.new(name, light)
        obj.location = centre + Vector(loc) * max(radius, 0.3) * 2
        obj.rotation_euler = (centre - obj.location).to_track_quat("-Z", "Y").to_euler()
        scene.collection.objects.link(obj)

    bpy.ops.mesh.primitive_plane_add(size=max(radius, 0.3) * 40, location=(centre.x, centre.y, lo.z))
    floor_mat = bpy.data.materials.new("ThumbFloor")
    floor_mat.use_nodes = True
    floor_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1)
    bpy.context.object.data.materials.append(floor_mat)

    world = bpy.data.worlds.new("ThumbWorld")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.75, 0.75, 0.75, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    scene.world = world

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "AgX"
    scene.render.image_settings.file_format = "PNG"
    return cam, cam_data, centre, radius


def aim(cam, cam_data, lo, hi, radius, view):
    az, el, dist_f, aim_h = VIEWS[view]
    az, el = math.radians(az), math.radians(el)
    target = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z + (hi.z - lo.z) * aim_h))
    fov = 2 * math.atan(cam_data.sensor_width / (2 * cam_data.lens))
    dist = radius / math.sin(fov / 2) * dist_f
    cam.location = target + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * dist
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()


def image_colours(img, k=3):
    """Main colours of a texture as [(rgb, fraction)], via a small k-means on a 32x32 copy.
    Textures often pack several materials (e.g. leather + metal), so one average would mislead."""
    small = img.copy()
    try:
        small.scale(32, 32)
        px = list(small.pixels)
    finally:
        bpy.data.images.remove(small)
    pts = [tuple(px[i:i + 3]) for i in range(0, len(px), 4)]
    if not pts:
        return []
    centres = [pts[int(i * (len(pts) - 1) / max(k - 1, 1))] for i in range(k)]
    for _ in range(8):
        groups = [[] for _ in centres]
        for p in pts:
            j = min(range(len(centres)), key=lambda c: sum((a - b) ** 2 for a, b in zip(p, centres[c])))
            groups[j].append(p)
        centres = [tuple(sum(c) / len(g) for c in zip(*g)) if g else centres[j] for j, g in enumerate(groups)]
    out = [(list(c), len(g) / len(pts)) for c, g in zip(centres, groups) if g]
    return sorted(out, key=lambda cg: -cg[1])


def base_colours(mat):
    """[(linear rgb, fraction)] for a material's base colour: flat value or texture clusters."""
    if not mat:
        return []
    if not mat.use_nodes:
        return [(list(mat.diffuse_color[:3]), 1.0)]
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if not bsdf:
        return []
    sock = bsdf.inputs["Base Color"]
    if sock.is_linked:
        node = sock.links[0].from_node
        while node.type != "TEX_IMAGE" and any(i.is_linked for i in node.inputs):
            node = next(i for i in node.inputs if i.is_linked).links[0].from_node  # walk back
        if node.type == "TEX_IMAGE" and node.image and node.image.size[0] > 0:
            return image_colours(node.image)
    return [(list(sock.default_value[:3]), 1.0)]


def palette(meshes):
    """Surface colours weighted by area: [{"hex", "share", "material"}], largest first."""
    areas = {}
    for obj in meshes:
        scale = obj.matrix_world.to_scale()
        k = abs(scale.x * scale.y * scale.z) ** (2 / 3)
        for poly in obj.data.polygons:
            slot = obj.material_slots[poly.material_index].material if obj.material_slots else None
            areas[slot] = areas.get(slot, 0.0) + poly.area * k
    total = sum(areas.values()) or 1.0
    out = []
    for mat, area in areas.items():
        for rgb, frac in base_colours(mat):
            share = area / total * frac  # texture clusters: share of texture pixels, approximately
            if share < 0.03:
                continue
            srgb = [max(0.0, min(1.0, c)) ** (1 / 2.2) for c in rgb]  # linear -> display, approx.
            out.append({"hex": "#" + "".join(f"{round(c * 255):02X}" for c in srgb),
                        "share": round(share, 3), "material": mat.name if mat else "(none)"})
    return sorted(out, key=lambda c: -c["share"])[:6]


def main():
    jobs = json.load(open(sys.argv[sys.argv.index("--") + 1]))
    failed = 0
    for job in jobs:
        try:
            bpy.ops.wm.open_mainfile(filepath=job["blend"])
            scene = bpy.context.scene
            meshes = [o for o in scene.objects if o.type == "MESH"]
            views_dir = os.path.join(os.path.dirname(job["out"]), "views")
            os.makedirs(views_dir, exist_ok=True)
            with open(os.path.join(views_dir, "palette.json"), "w") as f:
                json.dump(palette(meshes), f, indent=1)
            lo, hi = bbox(meshes)
            cam, cam_data, _, radius = studio(scene, lo, hi, job["size"])
            for view in job.get("views") or ["hero"]:
                hero = view == "hero"
                aim(cam, cam_data, lo, hi, radius, view)
                scene.cycles.samples = 32 if hero else 24
                px = job["size"] if hero else max(256, job["size"] * 3 // 4)
                scene.render.resolution_x = scene.render.resolution_y = px
                scene.render.filepath = job["out"] if hero else os.path.join(views_dir, f"{view}.png")
                bpy.ops.render.render(write_still=True)
            print(f"[thumb] {job['id']}")
        except Exception as exc:  # keep going; report at the end
            failed += 1
            print(f"[thumb] FAILED {job['id']}: {exc}")
    if failed:
        sys.exit(1)


main()
