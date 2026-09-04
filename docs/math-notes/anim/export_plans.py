"""Export the greedy and optimal UESP-112 discovery plans as one JSON
animation timeline for the Blender scene builder (build_scene.py).

Universe: base + DLC minus quest uniques - the same 112-ingredient world
as alchemy-mip-results-uesp.json (448 slots, all coverable). The greedy
plan is recomputed via the app's own planner; the optimal 70-brew plan
is replayed from the stored MIP incumbent, revealing slots under the
same rule the game uses (an effect shared by >= 2 mix members lights
that effect's slot on every member having it).

Output: docs/math-notes/anim/plans-uesp.json
  nodes: [{id, kind: ingredient|effect, name, pos: [x, y]}]
  edges: [{ing, slot, eff}]            # 448 = one per discoverable slot
  plans: {greedy|optimal: [{ings: [...], lit: [edge index, ...]}]}

Run from the repo root: python docs/math-notes/anim/export_plans.py
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from alchemy_helper.combinatorics.core import discovery_plan
from alchemy_helper.data.loader import load_dataset

HERE = Path(__file__).resolve().parent
MIP_RESULTS = HERE.parent / 'data' / 'alchemy-mip-results-uesp.json'
OUT = HERE / 'plans-uesp.json'

PLUGINS = {'Skyrim.esm', 'Update.esm', 'Dawnguard.esm',
           'HearthFires.esm', 'Dragonborn.esm'}
QUEST_UNIQUES = {'berits-ashes', 'jarrin-root'}

ds = load_dataset()
ings = sorted((i for i in ds.ingredients.values()
               if i.plugin in PLUGINS and i.id not in QUEST_UNIQUES),
              key=lambda i: i.id)
assert len(ings) == 112, len(ings)
by_id = {i.id: i for i in ings}
effects = sorted({e for i in ings for e in i.effects})

edges = [{'ing': i.id, 'slot': s, 'eff': e}
         for i in ings for s, e in enumerate(i.effects)]
edge_idx = {(d['ing'], d['slot']): j for j, d in enumerate(edges)}
assert len(edges) == 448


def replay(trios):
    """Reveal slots brew by brew under the game's sharing rule."""
    known: dict[str, set[int]] = defaultdict(set)
    out = []
    for trio in trios:
        shared = defaultdict(list)
        for iid in trio:
            for s, e in enumerate(by_id[iid].effects):
                shared[e].append((iid, s))
        lit = [edge_idx[t] for e, slots in shared.items() if len(slots) >= 2
               for t in slots if t[1] not in known[t[0]]]
        for e, slots in shared.items():
            if len(slots) >= 2:
                for iid, s in slots:
                    known[iid].add(s)
        out.append({'ings': list(trio), 'lit': sorted(lit)})
    total = sum(len(v) for v in known.values())
    return out, total


greedy_brews = discovery_plan(ings, {i.id: 99 for i in ings}, {})
greedy = [{'ings': list(b.ingredient_ids),
           'lit': sorted(edge_idx[t] for t in b.newly_discovered)}
          for b in greedy_brews]
assert sum(len(b['lit']) for b in greedy) == 448

optimal_trios = json.loads(MIP_RESULTS.read_text())[-1]['plan']
optimal, opt_total = replay(optimal_trios)
assert opt_total == 448, f'optimal plan lights only {opt_total} slots'

# Radial layout: effects inner ring, ingredients outer ring. A few
# barycenter sweeps pull connected nodes to similar angles, then each
# ring is re-spaced evenly in sorted-angle order to avoid clumps.
ing_ang = {i.id: 2 * math.pi * k / len(ings) for k, i in enumerate(ings)}
eff_ang = {}


def circular_mean(angles):
    return math.atan2(sum(math.sin(a) for a in angles),
                      sum(math.cos(a) for a in angles))


def respace(ang):
    for rank, key in enumerate(sorted(ang, key=ang.get)):
        ang[key] = 2 * math.pi * rank / len(ang)


eff_ings = defaultdict(list)
for i in ings:
    for e in i.effects:
        eff_ings[e].append(i.id)
for _ in range(4):
    for e in effects:
        eff_ang[e] = circular_mean([ing_ang[iid] for iid in eff_ings[e]])
    respace(eff_ang)
    for i in ings:
        ing_ang[i.id] = circular_mean([eff_ang[e] for e in i.effects])
    respace(ing_ang)

R_ING, R_EFF = 10.0, 4.5
nodes = ([{'id': i.id, 'kind': 'ingredient', 'name': i.name,
           'pos': [R_ING * math.cos(ing_ang[i.id]),
                   R_ING * math.sin(ing_ang[i.id])]} for i in ings]
         + [{'id': e, 'kind': 'effect',
             'name': ds.effects[e].name if e in ds.effects else e,
             'pos': [R_EFF * math.cos(eff_ang[e]),
                     R_EFF * math.sin(eff_ang[e])]} for e in effects])

OUT.write_text(json.dumps(
    {'nodes': nodes, 'edges': edges,
     'plans': {'greedy': greedy, 'optimal': optimal}}))
print(f'greedy {len(greedy)} brews, optimal {len(optimal)} brews, '
      f'{len(nodes)} nodes, {len(edges)} edges -> {OUT.name}')
