"""Greedy + LP + exact MIP on the UESP list's universe (base + official
add-ons, no Creations), with and without the quest-unique ingredients.
Pickle is session-local scratch only - trusted by construction."""
import time
from collections import Counter
from itertools import combinations

import numpy as np
import highspy

from alchemy_helper.data.loader import load_dataset
from alchemy_helper.combinatorics.core import discovery_plan

PLUGINS = {'Skyrim.esm', 'Update.esm', 'Dawnguard.esm',
           'HearthFires.esm', 'Dragonborn.esm'}
QUEST_UNIQUES = {'berits-ashes', 'jarrin-root'}

ds = load_dataset()


def solve(name, ings):
    print(f'=== {name}: {len(ings)} ingredients')
    deg = Counter(e for i in ings for e in i.effects)
    unbrewable = [(i.name, s) for i in ings for s, e in enumerate(i.effects)
                  if deg[e] < 2]
    rows = {}
    for k, i in enumerate(ings):
        for s, e in enumerate(i.effects):
            if deg[e] >= 2:
                rows[(k, s)] = len(rows)
    print(f'  coverable slots: {len(rows)} of {len(ings)*4} '
          f'({len(unbrewable)} unbrewable: {sorted(set(n for n, _ in unbrewable))})')

    plan = discovery_plan(ings, {i.id: 99 for i in ings}, {})
    print(f'  greedy: {len(plan)} brews')

    cover = {}
    for combo in combinations(range(len(ings)), 3):
        shared = {}
        for k in combo:
            for s, e in enumerate(ings[k].effects):
                shared.setdefault(e, []).append((k, s))
        cov = [rows[t] for e, slots in shared.items() if len(slots) >= 2
               for t in slots if t in rows]
        if cov:
            cover[frozenset(cov)] = 1
    covers = [sorted(k) for k in cover]
    print(f'  distinct coverage sets: {len(covers)}')

    sets = [frozenset(c) for c in covers]
    uncovered, chosen = set(range(len(rows))), []
    while uncovered:
        j = max(range(len(sets)), key=lambda j: len(sets[j] & uncovered))
        chosen.append(j)
        uncovered -= sets[j]

    ncols, nrows = len(covers), len(rows)
    h = highspy.Highs()
    h.setOptionValue('output_flag', False)
    h.setOptionValue('time_limit', 1200.0)
    inf = highspy.kHighsInf
    h.addVars(ncols, np.zeros(ncols), np.ones(ncols))
    h.changeColsCost(ncols, np.arange(ncols, dtype=np.int32), np.ones(ncols))
    from collections import defaultdict
    rowcols = defaultdict(list)
    for j, cov in enumerate(covers):
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
    sol.col_value = [1.0 if j in set(chosen) else 0.0 for j in range(ncols)]
    h.setSolution(sol)
    t0 = time.time()
    h.run()
    info = h.getInfo()
    print(f'  MIP: {h.modelStatusToString(h.getModelStatus())} in {time.time()-t0:.0f}s; '
          f'best {h.getObjectiveValue():.0f}, dual bound {info.mip_dual_bound:.2f}, '
          f'gap {info.mip_gap:.4f}', flush=True)


base = [i for i in ds.ingredients.values() if i.plugin in PLUGINS]
solve('base+DLC without quest uniques',
      [i for i in base if i.id not in QUEST_UNIQUES])
solve('base+DLC with quest uniques', base)
