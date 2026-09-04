"""Blender scene builder: greedy-76 vs optimal-70 discovery cascade.

Reads plans-uesp.json (from export_plans.py) and builds two radial
ingredient/effect graphs side by side, every discoverable slot an edge
whose emission ignites at the frame its brew happens. Press play: both
worlds light up together; the optimal side finishes six brews early and
holds, finished, while greedy keeps working.

Usage (from this directory):
    blender --python build_scene.py
or open Blender, load this file in the Scripting tab, Run Script.

Built for Blender 4.x. Emission drives the look - for the glow, add a
Glare node in the compositor (Eevee's legacy bloom toggle is gone) or
render in Cycles. Everything animates via per-object custom property
"lit", read by the shared materials' Object Attribute node.
"""
import json
import math
from pathlib import Path

import bpy

DATA = Path(__file__).resolve().parent / 'plans-uesp.json'

FPS = 24
FRAMES_PER_BREW = 12          # 2 brews per second
START_FRAME = 10
HOLD_FRAMES = 60              # tail after the last greedy brew
SIDE_OFFSET = 14.0            # each ring's center at +/- this on X
FLASH = 2.5                   # ignition overshoot before settling to 1
ING_GLOW = 0.06               # resting glow of ingredient nodes

SIDES = [('greedy', -SIDE_OFFSET, 'GREEDY - 76 BREWS'),
         ('optimal', +SIDE_OFFSET, 'OPTIMAL - 70 BREWS')]


def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.curves):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def lit_material(name, color, floor=0.0):
    """Emission = floor + color * "lit" (per-object custom property)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    emit = nt.nodes.new('ShaderNodeEmission')
    emit.inputs['Color'].default_value = (*color, 1.0)
    attr = nt.nodes.new('ShaderNodeAttribute')
    attr.attribute_type = 'OBJECT'
    attr.attribute_name = 'lit'
    add = nt.nodes.new('ShaderNodeMath')
    add.operation = 'ADD'
    add.inputs[1].default_value = floor
    nt.links.new(attr.outputs['Fac'], add.inputs[0])
    nt.links.new(add.outputs['Value'], emit.inputs['Strength'])
    nt.links.new(emit.outputs['Emission'], out.inputs['Surface'])
    return mat


def key_lit(obj, frame, value):
    obj['lit'] = float(value)
    obj.keyframe_insert('["lit"]', frame=frame)


def ignite(obj, frame):
    key_lit(obj, frame - 1, obj.get('lit', 0.0))
    key_lit(obj, frame, FLASH)
    key_lit(obj, frame + 6, 1.0)


def pulse(obj, frame, base):
    key_lit(obj, frame - 1, base)
    key_lit(obj, frame, FLASH)
    key_lit(obj, frame + 5, base)


def unit_cylinder():
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=1.0, depth=1.0)
    obj = bpy.context.object
    mesh = obj.data
    bpy.data.objects.remove(obj)
    return mesh


def unit_sphere(subdiv):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=1.0)
    obj = bpy.context.object
    mesh = obj.data
    bpy.data.objects.remove(obj)
    return mesh


def place_edge(obj, a, b, radius):
    """Stretch a unit-Z cylinder between points a and b (3D)."""
    ax, ay, az = a
    bx, by, bz = b
    dx, dy, dz = bx - ax, by - ay, bz - az
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    obj.location = ((ax + bx) / 2, (ay + by) / 2, (az + bz) / 2)
    obj.rotation_mode = 'QUATERNION'
    # rotate +Z onto the edge direction
    ux, uy, uz = dx / length, dy / length, dz / length
    w = 1.0 + uz
    if w < 1e-6:                       # antiparallel: flip around X
        obj.rotation_quaternion = (0.0, 1.0, 0.0, 0.0)
    else:
        qx, qy = -uy, ux
        n = math.sqrt(w * w + qx * qx + qy * qy)
        obj.rotation_quaternion = (w / n, qx / n, qy / n, 0.0)
    obj.scale = (radius, radius, length)


def build():
    data = json.loads(DATA.read_text())
    scene = bpy.context.scene
    scene.render.fps = FPS
    clean_scene()

    mat_edge = lit_material('edge', (1.0, 0.72, 0.25), floor=0.015)
    mat_ing = lit_material('ingredient', (0.55, 0.8, 1.0), floor=0.0)
    mat_eff = lit_material('effect', (1.0, 0.95, 0.7), floor=0.01)
    mat_text = lit_material('label', (0.85, 0.85, 0.9), floor=1.0)

    cyl = unit_cylinder()
    cyl.materials.append(mat_edge)
    sph_ing = unit_sphere(2)
    sph_ing.materials.append(mat_ing)
    sph_eff = unit_sphere(2)
    sph_eff.materials.append(mat_eff)

    pos = {n['id']: n['pos'] for n in data['nodes']}
    kind = {n['id']: n['kind'] for n in data['nodes']}
    last_frame = START_FRAME

    for plan_key, cx, label in SIDES:
        col = bpy.data.collections.new(plan_key)
        scene.collection.children.link(col)

        def at(node_id):
            x, y = pos[node_id]
            return (x + cx, y, 0.0)

        node_objs = {}
        for nid in pos:
            mesh = sph_ing if kind[nid] == 'ingredient' else sph_eff
            r = 0.12 if kind[nid] == 'ingredient' else 0.22
            obj = bpy.data.objects.new(f'{plan_key}:{nid}', mesh)
            obj.location = at(nid)
            obj.scale = (r, r, r)
            base = ING_GLOW if kind[nid] == 'ingredient' else 0.0
            key_lit(obj, 0, base)
            col.objects.link(obj)
            node_objs[nid] = obj

        edge_objs = []
        for j, e in enumerate(data['edges']):
            obj = bpy.data.objects.new(f'{plan_key}:e{j}', cyl)
            place_edge(obj, at(e['ing']), at(e['eff']), 0.018)
            key_lit(obj, 0, 0.0)
            col.objects.link(obj)
            edge_objs.append(obj)

        eff_degree = {}
        eff_lit_count = {}
        for e in data['edges']:
            eff_degree[e['eff']] = eff_degree.get(e['eff'], 0) + 1

        for k, brew in enumerate(data['plans'][plan_key]):
            frame = START_FRAME + k * FRAMES_PER_BREW
            last_frame = max(last_frame, frame)
            for iid in brew['ings']:
                pulse(node_objs[iid], frame, ING_GLOW)
            for j in brew['lit']:
                ignite(edge_objs[j], frame)
                eff = data['edges'][j]['eff']
                eff_lit_count[eff] = eff_lit_count.get(eff, 0) + 1
                obj = node_objs[eff]
                frac = eff_lit_count[eff] / eff_degree[eff]
                key_lit(obj, frame - 1, obj.get('lit', 0.0))
                key_lit(obj, frame, frac * 1.5)

        text_curve = bpy.data.curves.new(f'{plan_key}-label', type='FONT')
        text_curve.body = label
        text_curve.align_x = 'CENTER'
        text_curve.size = 1.1
        text_curve.materials.append(mat_text)
        text_obj = bpy.data.objects.new(f'{plan_key}:label', text_curve)
        text_obj.location = (cx, -12.3, 0.0)
        col.objects.link(text_obj)

    scene.frame_start = 1
    scene.frame_end = last_frame + FRAMES_PER_BREW + HOLD_FRAMES

    bpy.ops.object.camera_add(location=(0, -1.5, 46), rotation=(0, 0, 0))
    cam = bpy.context.object
    cam.data.lens = 32
    scene.camera = cam

    world = bpy.data.worlds.get('World') or bpy.data.worlds.new('World')
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    if bg:
        bg.inputs['Color'].default_value = (0.004, 0.005, 0.008, 1.0)
        bg.inputs['Strength'].default_value = 1.0

    print(f'scene built: {scene.frame_end} frames '
          f'({scene.frame_end / FPS:.0f}s at {FPS}fps)')


build()
