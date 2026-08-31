"""Exact set-cover MIP for the full-game discovery plan, warm-started.

Pickle is used only for session-local scratch files this same session
wrote (cover.pkl above, mip-result.pkl below) - trusted by construction.
"""
import pickle
import time

import numpy as np
import highspy

SCRATCH = r'C:\Users\Snarf\AppData\Local\Temp\claude\F--video-game-projects-skyrim-alchmey-effect-finder\3dd155bd-a425-4b86-8cbd-4d2229ecf9f5\scratchpad'

with open(SCRATCH + r'\cover.pkl', 'rb') as f:
    data = pickle.load(f)
nrows, covers = data['rows'], data['covers']
ncols = len(covers)
sets = [frozenset(c) for c in covers]

t0 = time.time()
uncovered = set(range(nrows))
chosen = []
while uncovered:
    best, bestn = None, 0
    for j, s in enumerate(sets):
        k = len(s & uncovered)
        if k > bestn:
            best, bestn = j, k
    chosen.append(best)
    uncovered -= sets[best]
print(f'greedy incumbent: {len(chosen)} sets in {time.time()-t0:.0f}s', flush=True)

h = highspy.Highs()
h.setOptionValue('time_limit', 3600.0)
h.setOptionValue('mip_rel_gap', 0.0)
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

print('MIP starting...', flush=True)
t0 = time.time()
h.run()
info = h.getInfo()
status = h.getModelStatus()
print(f'status: {h.modelStatusToString(status)} in {time.time()-t0:.0f}s')
print(f'objective (best solution): {h.getObjectiveValue():.4f}')
print(f'dual bound: {info.mip_dual_bound:.4f}')
print(f'gap: {info.mip_gap:.6f}')

vals = np.array(h.getSolution().col_value)
picked = np.where(vals > 0.5)[0]
print(f'sets in best solution: {len(picked)}')
with open(SCRATCH + r'\mip-result.pkl', 'wb') as f:
    pickle.dump({'picked': picked.tolist(),
                 'objective': h.getObjectiveValue(),
                 'dual_bound': float(info.mip_dual_bound),
                 'status': h.modelStatusToString(status)}, f)
print('result pickled', flush=True)
