"""Render a neutral studio preview for each normalised .blend (runs inside Blender).

    blender -b --python render_thumb.py -- jobs.json
jobs.json: [{"id", "blend", "out", "size"}]. Cycles on CPU, 3/4 view, auto-framed.
"""
import json
import math
import sys

import bpy
from mathutils import Vector


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
    az, el = math.radians(35), math.radians(20)
    fov = 2 * math.atan(cam_data.sensor_width / (2 * cam_data.lens))
    dist = radius / math.sin(fov / 2) * 1.08
    cam.location = centre + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * dist
    cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
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
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "AgX"
    scene.render.image_settings.file_format = "PNG"


def main():
    jobs = json.load(open(sys.argv[sys.argv.index("--") + 1]))
    failed = 0
    for job in jobs:
        try:
            bpy.ops.wm.open_mainfile(filepath=job["blend"])
            scene = bpy.context.scene
            meshes = [o for o in scene.objects if o.type == "MESH"]
            lo, hi = bbox(meshes)
            studio(scene, lo, hi, job["size"])
            scene.render.filepath = job["out"]
            bpy.ops.render.render(write_still=True)
            print(f"[thumb] {job['id']}")
        except Exception as exc:  # keep going; report at the end
            failed += 1
            print(f"[thumb] FAILED {job['id']}: {exc}")
    if failed:
        sys.exit(1)


main()
