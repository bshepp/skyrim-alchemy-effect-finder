"""Emit a medium UNSAT rung-2 instance for check-vs-solve timing.

Takes a sub-universe of the real UESP ingredient list, finds its true
optimum by SAT descent, and writes the UNSAT instance at optimum-1.
Structurally identical to the full k=66 formula but small enough that
drat-trim can actually finish, which is what lets us measure the
check/solve ratio and extrapolate to a real certified run.

Starts the descent from a greedy cover rather than an arbitrary ceiling,
and builds the column set ONCE instead of per rung: the previous version
re-derived every trio at each k and spent half an hour walking down from
40 without ever reaching the interesting range.
"""
import sys
import time
from pathlib import Path

SCRIPTS = Path(r'F:\video-game-projects\skyrim-alchmey-effect-finder'
               r'\docs\math-notes\scripts')
sys.path.insert(0, str(SCRIPTS))

import rung2_encode as R
from pysat.card import CardEnc, EncType

OUT = Path(__file__).resolve().parent
N = int(sys.argv[1]) if len(sys.argv) > 1 else 24

ings = R.uesp_ingredients()[:N]
rows, covs, reps = R.build(ings)
print(f'medium world: n={len(ings)} rows={len(rows)} cols={len(covs)}',
      flush=True)

# Greedy upper bound: repeatedly take the column covering most new rows.
uncovered, greedy = set(range(len(rows))), 0
while uncovered:
    best = max(covs, key=lambda c: len(c & uncovered))
    gain = len(best & uncovered)
    if not gain:
        break
    uncovered -= best
    greedy += 1
print(f'greedy cover = {greedy}', flush=True)


def feasible(k, sym=False):
    clauses, *_ = R.encode(ings, k, sym)
    sat, _ = R.solve_inline(clauses)
    return sat


k, opt = greedy, None
while k >= 1:
    t0 = time.time()
    sat = feasible(k)
    print(f'  k={k}: {"SAT" if sat else "UNSAT"} ({time.time()-t0:.1f}s)',
          flush=True)
    if not sat:
        opt = k + 1
        break
    k -= 1

if opt is None:
    print('descent bottomed out without an UNSAT rung', flush=True)
    sys.exit(1)
print(f'optimum={opt}', flush=True)

for sym, kind in ((False, 'plain'), (True, 'sym')):
    clauses, nv, covs2, reps2, nr, gens = R.encode(ings, opt - 1, sym)
    path = OUT / f'medium-k{opt-1}-{kind}.cnf'
    with path.open('w') as f:
        f.write(f'p cnf {nv} {len(clauses)}\n')
        for c in clauses:
            f.write(' '.join(map(str, c)) + ' 0\n')
    print(f'{path.name}: {nv} vars, {len(clauses)} clauses, {nr} rows, '
          f'{len(covs2)} cols, {gens} sym gens -> UNSAT expected', flush=True)
