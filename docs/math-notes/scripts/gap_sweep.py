"""Where does the LP gap open up?

The full UESP-112 instance has an LP/dual bound of 66 against a best known
plan of 70: a gap of 4 that neither HiGHS nor CP-SAT could close. The
26-ingredient sub-universe has NO gap at all (HiGHS: optimum 18, bound 18,
one node, 0.04 s).

So the toy does not reproduce the real instance's hardness. This sweeps
sub-universe size to find where the LP relaxation stops being tight, which
is the scale at which the campaign's actual difficulty is born.
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

SIZES = [int(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 \
    else [26, 35, 45, 55, 65, 75, 90, 112]
TIME_LIMIT = float(sys.argv[2]) if len(sys.argv) > 2 else 120.0

ALL = R.uesp_ingredients()
inf = highspy.kHighsInf


def build_model(covs, nr, integral):
    h = highspy.Highs()
    h.setOptionValue('output_flag', False)
    h.setOptionValue('time_limit', TIME_LIMIT)
    nc = len(covs)
    for _ in range(nc):
        h.addVar(0.0, 1.0)
    if integral:
        for j in range(nc):
            h.changeColIntegrality(j, highspy.HighsVarType.kInteger)
    h.changeColsCost(nc, np.arange(nc, dtype=np.int32),
                     np.ones(nc, dtype=np.float64))
    row_cols = {r: [] for r in range(nr)}
    for j, c in enumerate(covs):
        for r in c:
            row_cols[r].append(j)
    for r in range(nr):
        idx = np.array(row_cols[r], dtype=np.int32)
        h.addRow(1.0, inf, len(idx), idx,
                 np.ones(len(idx), dtype=np.float64))
    return h


print(f'{"n":>4} {"rows":>5} {"cols":>7} {"LP":>8} {"ILP":>6} {"bound":>7} '
      f'{"gap":>6} {"nodes":>8} {"secs":>8}  status', flush=True)

for n in SIZES:
    ings = ALL[:n]
    rows, covs, reps = R.build(ings)
    nr, nc = len(rows), len(covs)

    lp = build_model(covs, nr, integral=False)
    lp.run()
    lp_val = lp.getObjectiveValue()

    m = build_model(covs, nr, integral=True)
    t0 = time.time()
    m.run()
    dt = time.time() - t0
    st = m.modelStatusToString(m.getModelStatus())
    info = m.getInfo()
    obj = m.getObjectiveValue()
    bound = info.mip_dual_bound
    print(f'{n:>4} {nr:>5} {nc:>7} {lp_val:>8.2f} {round(obj):>6} '
          f'{bound:>7.2f} {round(obj)-bound:>6.2f} {info.mip_node_count:>8} '
          f'{dt:>8.2f}  {st}', flush=True)
