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
import colorsys
import json
import math
import sys
from pathlib import Path

import bpy

DATA = Path(__file__).resolve().parent / 'plans-uesp.json'

# what the spectrum encodes - pass after `--` on the command line:
#   brew        each side divides red->violet by its brew count (default)
#   ingredient  the outer ring is a color wheel; lines wear their
#               ingredient's hue
#   effect      the inner ring is a color wheel; lines wear their
#               effect's hue
_extra = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
MODE = _extra[0] if _extra else 'brew'
VERSION = {'brew': 'v7-eq-brew', 'ingredient': 'v8-eq-ingredients',
           'effect': 'v9-eq-effects'}[MODE]

FPS = 24
FRAMES_PER_BREW = 12          # 2 brews per second
START_FRAME = 10
HOLD_FRAMES = 60              # tail after the last greedy brew
SIDE_OFFSET = 14.0            # each ring's center at +/- this on X
FLASH = 2.5                   # ignition overshoot before settling to 1
ING_GLOW = 0.06               # resting glow of ingredient nodes

# brew ORDER painted into the lines as the full spectrum: each side
# divides red -> violet into exactly its brew count, so brew 1's lines
# are the first color, brew 2's the second, and so on. Both sides share
# the mapping - equal position in the sequence, equal color.
SIDES = [('greedy', -SIDE_OFFSET, 'GREEDY - 76 BREWS', (0.0, 0.83)),
         ('optimal', +SIDE_OFFSET, 'OPTIMAL - 70 BREWS', (0.0, 0.83))]


def brew_color(hue_range, frac):
    hue = hue_range[0] + (hue_range[1] - hue_range[0]) * frac
    return colorsys.hsv_to_rgb(hue % 1.0, 1.0, 1.0)


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


def edge_material(name, floor=0.015):
    """Emission color from per-object "col", strength from "lit" - one
    material serves many objects; each carries its own hue."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    emit = nt.nodes.new('ShaderNodeEmission')
    col = nt.nodes.new('ShaderNodeAttribute')
    col.attribute_type = 'OBJECT'
    col.attribute_name = 'col'
    lit = nt.nodes.new('ShaderNodeAttribute')
    lit.attribute_type = 'OBJECT'
    lit.attribute_name = 'lit'
    add = nt.nodes.new('ShaderNodeMath')
    add.operation = 'ADD'
    add.inputs[1].default_value = floor
    nt.links.new(col.outputs['Color'], emit.inputs['Color'])
    nt.links.new(lit.outputs['Fac'], add.inputs[0])
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

    mat_text = lit_material('label', (0.85, 0.85, 0.9), floor=1.0)

    base_cyl = unit_cylinder()
    sph_ing = unit_sphere(2)
    sph_ing.materials.append(edge_material('ingredient', floor=0.0))
    base_sph_eff = unit_sphere(2)

    pos = {n['id']: n['pos'] for n in data['nodes']}
    kind = {n['id']: n['kind'] for n in data['nodes']}
    last_frame = START_FRAME

    def ring_hue(node_id):
        """Position on the ring as a full color wheel - a line's color
        points back at its source node."""
        x, y = pos[node_id]
        return colorsys.hsv_to_rgb((math.atan2(y, x) / math.tau) % 1.0,
                                   1.0, 1.0)

    for plan_key, cx, label, hue_range in SIDES:
        cyl = base_cyl.copy()
        cyl.materials.append(edge_material(f'edge-{plan_key}'))
        sph_eff = base_sph_eff.copy()
        sph_eff.materials.append(
            edge_material(f'effect-{plan_key}', floor=0.01))

        plan = data['plans'][plan_key]
        brew_frac = {}
        for k, brew in enumerate(plan):
            for j in brew['lit']:
                brew_frac[j] = k / max(1, len(plan) - 1)
        col = bpy.data.collections.new(plan_key)
        scene.collection.children.link(col)

        def at(node_id):
            x, y = pos[node_id]
            return (x + cx, y, 0.0)

        # colored-mode source dots glow bright enough to read their hue
        # from frame one; everything else keeps the dim defaults
        ing_base = 0.6 if MODE == 'ingredient' else ING_GLOW
        eff_base = 0.4 if MODE == 'effect' else 0.0

        node_objs = {}
        for nid in pos:
            is_ing = kind[nid] == 'ingredient'
            mesh = sph_ing if is_ing else sph_eff
            r = 0.12 if is_ing else 0.22
            obj = bpy.data.objects.new(f'{plan_key}:{nid}', mesh)
            obj.location = at(nid)
            obj.scale = (r, r, r)
            base = ing_base if is_ing else eff_base
            key_lit(obj, 0, base)
            if MODE == 'ingredient' and is_ing:
                obj['col'] = list(ring_hue(nid))
            elif MODE == 'effect' and not is_ing:
                obj['col'] = list(ring_hue(nid))
            else:
                obj['col'] = [1.0, 1.0, 1.0] if is_ing else [0.9, 0.9, 0.95]
            col.objects.link(obj)
            node_objs[nid] = obj

        edge_objs = []
        for j, e in enumerate(data['edges']):
            obj = bpy.data.objects.new(f'{plan_key}:e{j}', cyl)
            place_edge(obj, at(e['ing']), at(e['eff']), 0.018)
            key_lit(obj, 0, 0.0)
            if MODE == 'ingredient':
                obj['col'] = list(ring_hue(e['ing']))
            elif MODE == 'effect':
                obj['col'] = list(ring_hue(e['eff']))
            else:
                obj['col'] = list(brew_color(hue_range,
                                             brew_frac.get(j, 0.0)))
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
                pulse(node_objs[iid], frame, ing_base)
            for j in brew['lit']:
                ignite(edge_objs[j], frame)
                eff = data['edges'][j]['eff']
                eff_lit_count[eff] = eff_lit_count.get(eff, 0) + 1
                obj = node_objs[eff]
                frac = eff_lit_count[eff] / eff_degree[eff]
                key_lit(obj, frame - 1, obj.get('lit', 0.0))
                key_lit(obj, frame, eff_base + frac * (1.5 - eff_base))

        # the finish: a hard specular flash across the whole web, then
        # one slow settling breath - completion you can feel
        done = START_FRAME + (len(plan) - 1) * FRAMES_PER_BREW + 8
        for obj in edge_objs:
            key_lit(obj, done, 1.0)
            key_lit(obj, done + 2, 3.4)
            key_lit(obj, done + 8, 0.85)
            key_lit(obj, done + 24, 1.0)

        done_curve = bpy.data.curves.new(f'{plan_key}-done', type='FONT')
        done_curve.body = 'DONE'
        done_curve.align_x = 'CENTER'
        done_curve.size = 0.9
        done_curve.materials.append(mat_text)
        done_obj = bpy.data.objects.new(f'{plan_key}:done', done_curve)
        done_obj.location = (cx, -15.4, 0.0)
        col.objects.link(done_obj)
        key_lit(done_obj, done + 1, 3.0)
        key_lit(done_obj, done + 12, 1.0)
        for prop in ('hide_render', 'hide_viewport'):
            setattr(done_obj, prop, True)
            done_obj.keyframe_insert(prop, frame=0)
            setattr(done_obj, prop, False)
            done_obj.keyframe_insert(prop, frame=done + 1)

        text_curve = bpy.data.curves.new(f'{plan_key}-label', type='FONT')
        text_curve.body = label
        text_curve.align_x = 'CENTER'
        text_curve.size = 1.1
        text_curve.materials.append(mat_text)
        text_obj = bpy.data.objects.new(f'{plan_key}:label', text_curve)
        text_obj.location = (cx, -12.3, 0.0)
        col.objects.link(text_obj)

        # brew counter: one text object per count, visibility-keyed so
        # the number ticks up with each brew and freezes when done
        total = len(plan)
        for k in range(total):
            frame = START_FRAME + k * FRAMES_PER_BREW
            nxt = (START_FRAME + (k + 1) * FRAMES_PER_BREW
                   if k + 1 < total else None)
            tc = bpy.data.curves.new(f'{plan_key}-n{k}', type='FONT')
            tc.body = f'{k + 1} of {total}'
            tc.align_x = 'CENTER'
            tc.size = 0.85
            tc.materials.append(mat_text)
            to = bpy.data.objects.new(f'{plan_key}:n{k}', tc)
            to.location = (cx, -14.0, 0.0)
            col.objects.link(to)
            for prop in ('hide_render', 'hide_viewport'):
                setattr(to, prop, True)
                to.keyframe_insert(prop, frame=0)
                setattr(to, prop, False)
                to.keyframe_insert(prop, frame=frame)
                if nxt is not None:
                    setattr(to, prop, True)
                    to.keyframe_insert(prop, frame=nxt)

    scene.frame_start = 1
    scene.frame_end = last_frame + FRAMES_PER_BREW + HOLD_FRAMES

    bpy.ops.object.camera_add(location=(0, -1.5, 52.5), rotation=(0, 0, 0))
    cam = bpy.context.object
    cam.data.lens = 32
    scene.camera = cam
    # one slow breath inward; the END must still hold both full rings
    # (half-width at distance z is z*18/32; the rings span +/-24.6)
    cam.keyframe_insert('location', frame=1)
    cam.location = (0, -1.5, 46.5)
    cam.keyframe_insert('location', frame=scene.frame_end)

    legend = bpy.data.curves.new('legend', type='FONT')
    legend.body = {
        'brew': ('outer dots: ingredients   ·   inner dots: effects   ·   '
                 'each line: one ingredient effect, colored by brew '
                 'order - red first, violet last'),
        'ingredient': ('outer dots: ingredients, colored by ring position   '
                       '·   inner dots: effects   ·   each line wears its '
                       "ingredient's color"),
        'effect': ('outer dots: ingredients   ·   inner dots: effects, '
                   'colored by ring position   ·   each line wears its '
                   "effect's color"),
    }[MODE]
    legend.align_x = 'CENTER'
    legend.size = 0.55
    legend.materials.append(lit_material('legend', (0.6, 0.62, 0.68),
                                         floor=0.8))
    legend_obj = bpy.data.objects.new('legend', legend)
    legend_obj.location = (0, 12.6, 0.0)
    scene.collection.objects.link(legend_obj)

    # bloom via compositor glare - Blender 5.0 style: a compositor node
    # GROUP assigned to the scene, ending in a NodeGroupOutput (the old
    # scene.node_tree / Composite node are gone). Tolerate API drift -
    # the render is correct without it, just drier.
    try:
        scene.render.use_compositing = True
        ng = bpy.data.node_groups.new('cascade-glare', 'CompositorNodeTree')
        ng.interface.new_socket('Image', in_out='OUTPUT',
                                socket_type='NodeSocketColor')
        rl = ng.nodes.new('CompositorNodeRLayers')
        glare = ng.nodes.new('CompositorNodeGlare')
        # 5.0 exposes glare options as input sockets, Type as a menu
        for name, value in (('Type', 'Bloom'), ('Threshold', 0.8),
                            ('Strength', 0.35), ('Size', 7)):
            try:
                glare.inputs[name].default_value = value
            except (KeyError, TypeError) as exc:
                print(f'glare input {name!r} left at default: {exc}')
        out = ng.nodes.new('NodeGroupOutput')
        ng.links.new(rl.outputs['Image'], glare.inputs['Image'])
        ng.links.new(glare.outputs['Image'], out.inputs['Image'])
        scene.compositing_node_group = ng
    except Exception as exc:                       # noqa: BLE001
        print(f'compositor glare skipped: {exc}')

    # output: H.264 MP4, ready for `blender -b --python ... -a`
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.image_settings.media_type = 'VIDEO'
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'HIGH'
    scene.render.filepath = str(DATA.parent / 'render' / f'cascade-{VERSION}-')

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
