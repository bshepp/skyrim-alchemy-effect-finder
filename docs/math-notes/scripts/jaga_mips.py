"""Long-run exact set-cover MIPs for the alchemy discovery problem.

Runs the full-game instance then the UESP base+DLC instance, each to
optimality or its time budget, and appends results (including the actual
brew list as ingredient ids) to ~/alchemy-mip-results.json.
"""
import json
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
import highspy

from alchemy_helper.data.loader import load_dataset

RESULTS = Path.home() / 'alchemy-mip-results.json'
THREADS = 84   # leave 4 of 88 for the OS, per house etiquette


def build_instance(ings):
    deg = Counter(e for i in ings for e in i.effects)
    rows = {}
    for k, i in enumerate(ings):
        for s, e in enumerate(i.effects):
            if deg[e] >= 2:
                rows[(k, s)] = len(rows)
    cover = {}   # frozenset(row ids) -> representative trio of ingredient ids
    for combo in combinations(range(len(ings)), 3):
        shared = {}
        for k in combo:
            for s, e in enumerate(ings[k].effects):
                shared.setdefault(e, []).append((k, s))
        cov = [rows[t] for e, slots in shared.items() if len(slots) >= 2
               for t in slots if t in rows]
        if cov:
            cover.setdefault(frozenset(cov), tuple(ings[k].id for k in combo))
    covers = [(sorted(k), rep) for k, rep in cover.items()]
    return len(rows), covers


def solve(name, ings, time_limit):
    t0 = time.time()
    nrows, covers = build_instance(ings)
    sets = [frozenset(c) for c, _ in covers]
    print(f'[{name}] rows={nrows} cols={len(covers)} '
          f'built in {time.time()-t0:.0f}s', flush=True)

    uncovered, chosen = set(range(nrows)), []
    while uncovered:
        j = max(range(len(sets)), key=lambda j: len(sets[j] & uncovered))
        chosen.append(j)
        uncovered -= sets[j]
    print(f'[{name}] greedy incumbent {len(chosen)}', flush=True)

    ncols = len(covers)
    h = highspy.Highs()
    h.setOptionValue('time_limit', float(time_limit))
    h.setOptionValue('mip_rel_gap', 0.0)
    h.setOptionValue('threads', THREADS)
    inf = highspy.kHighsInf
    h.addVars(ncols, np.zeros(ncols), np.ones(ncols))
    h.changeColsCost(ncols, np.arange(ncols, dtype=np.int32), np.ones(ncols))
    rowcols = defaultdict(list)
    for j, (cov, _) in enumerate(covers):
        for r in cov:
            rowcols[r].append(j)
    rstart, rindex = [0], []
    for r in range(nrows):
        rindex.extend(rowcols[r])
        rstart.append(len(rindex))
    h.addRows(nrows, np.ones(nrows), np.full(nrows, inf),
              len(rindex), np.array(rstart[:-1], dtype=np.int32),
              np.array(rindex, dtype=np.int32), np.ones(len(rindex)))
    h.changeColsIntegrality(ncols, np.arange(ncols, dtype=np.int32),
                            np.full(ncols, highspy.HighsVarType.kInteger))
    sol = highspy.HighsSolution()
    chosen_set = set(chosen)
    sol.col_value = [1.0 if j in chosen_set else 0.0 for j in range(ncols)]
    h.setSolution(sol)

    t0 = time.time()
    h.run()
    info = h.getInfo()
    vals = np.array(h.getSolution().col_value)
    picked = [covers[j][1] for j in np.where(vals > 0.5)[0]]
    result = {
        'instance': name,
        'rows': nrows, 'cols': ncols,
        'status': h.modelStatusToString(h.getModelStatus()),
        'best': int(round(h.getObjectiveValue())),
        'dual_bound': float(info.mip_dual_bound),
        'gap': float(info.mip_gap),
        'seconds': round(time.time() - t0, 1),
        'plan': picked,
    }
    print(f'[{name}] {result["status"]}: best {result["best"]}, '
          f'bound {result["dual_bound"]:.2f}, gap {result["gap"]:.4f} '
          f'in {result["seconds"]}s', flush=True)
    existing = json.loads(RESULTS.read_text()) if RESULTS.exists() else []
    existing.append(result)
    RESULTS.write_text(json.dumps(existing, indent=1))


ds = load_dataset()
all_ings = list(ds.ingredients.values())
PLUGINS = {'Skyrim.esm', 'Update.esm', 'Dawnguard.esm',
           'HearthFires.esm', 'Dragonborn.esm'}
uesp = [i for i in all_ings
        if i.plugin in PLUGINS and i.id not in {'berits-ashes', 'jarrin-root'}]

solve('full-game-180', all_ings, 8 * 3600)
solve('uesp-base-dlc-112', uesp, 6 * 3600)
print('ALL DONE', flush=True)
