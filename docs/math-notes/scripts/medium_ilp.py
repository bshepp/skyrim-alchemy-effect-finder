"""Solve the medium world's optimum as an ILP instead of by SAT descent.

The descent (make_medium.py) re-encodes and re-solves from scratch at every
rung: k=20 in 24 s, k=19 in 252 s, k=18 in 12.4 h, k=17 still unresolved after
a day. This asks whether the instance is actually hard or the method was
wrong, by handing the same 88-row / 457-column set cover to HiGHS as a
straight minimisation.
"""
import sys
import time
from pathlib import Path

SCRIPTS = Path(r'F:\video-game-projects\skyrim-alchmey-effect-finder'
               r'\docs\math-notes\scripts')
sys.path.insert(0, str(SCRIPTS))

import numpy as np
import highspy

import rung2_encode as R

N = int(sys.argv[1]) if len(sys.argv) > 1 else 26

ings = R.uesp_ingredients()[:N]
rows, covs, reps = R.build(ings)
nr, nc = len(rows), len(covs)
print(f'world n={N}: {nr} rows, {nc} pruned columns', flush=True)

h = highspy.Highs()
h.setOptionValue('output_flag', False)

inf = highspy.kHighsInf
# One binary per column, minimise the count.
for _ in range(nc):
    h.addVar(0.0, 1.0)
    h.changeColIntegrality(h.getNumCol() - 1, highspy.HighsVarType.kInteger)
h.changeColsCost(nc, np.arange(nc, dtype=np.int32),
                 np.ones(nc, dtype=np.float64))

# One covering constraint per row: sum of columns containing it >= 1.
row_cols = {r: [] for r in range(nr)}
for j, c in enumerate(covs):
    for r in c:
        row_cols[r].append(j)
for r in range(nr):
    idx = np.array(row_cols[r], dtype=np.int32)
    val = np.ones(len(idx), dtype=np.float64)
    h.addRow(1.0, inf, len(idx), idx, val)

print(f'ILP: {h.getNumCol()} binaries, {h.getNumRow()} constraints',
      flush=True)

t0 = time.time()
h.run()
dt = time.time() - t0

status = h.getModelStatus()
info = h.getInfo()
obj = h.getObjectiveValue()
print(f'status={h.modelStatusToString(status)}  time={dt:.2f}s')
print(f'OPTIMUM = {round(obj)}   (bound {info.mip_dual_bound:g}, '
      f'gap {info.mip_gap:.3g}, nodes {info.mip_node_count})')

sol = h.getSolution()
chosen = [j for j in range(nc) if sol.col_value[j] > 0.5]
covered = set().union(*(covs[j] for j in chosen)) if chosen else set()
print(f'witness: {len(chosen)} columns covering {len(covered)}/{nr} rows '
      f'-> {"VALID" if len(covered) == nr else "INVALID"}')
