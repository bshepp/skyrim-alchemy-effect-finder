"""Emit small UNSAT rung-2 instances for end-to-end certificate validation.

Picks a small universe containing duplicate-ingredient classes (so the
lex-leader clauses are exercised), finds its true optimum with the
independent covering-polynomial engine, and writes the k=OPT-1 CNFs -
which are UNSAT by construction. A kissat DRAT proof of these, checked
by drat-trim, validates the whole certificate pipeline.
"""
import sys
from pathlib import Path

SCRIPTS = Path(r'F:\video-game-projects\skyrim-alchmey-effect-finder'
               r'\docs\math-notes\scripts')
sys.path.insert(0, str(SCRIPTS))

import rung2_encode as R

OUT = Path(__file__).resolve().parent

ds = R.load_dataset()
ids = {i.id: i for i in ds.ingredients.values()}
world = [ids['ancestor-moth-wing'], ids['blue-butterfly-wing'],
         ids['chaurus-hunter-antennae'], ids['chickens-egg'],
         ids['hawks-egg'], ids['nightshade'], ids['deathbell']]

opt = R.exact_opt(world)
print(f'small world: n={len(world)} true optimum={opt} '
      f'(covering-polynomial engine)', flush=True)

for sym, kind in ((False, 'plain'), (True, 'sym')):
    clauses, nv, covs, reps, nr, gens = R.encode(world, opt - 1, sym)
    path = OUT / f'small-k{opt-1}-{kind}.cnf'
    with path.open('w') as f:
        f.write(f'p cnf {nv} {len(clauses)}\n')
        for c in clauses:
            f.write(' '.join(map(str, c)) + ' 0\n')
    print(f'{path.name}: {nv} vars, {len(clauses)} clauses, {nr} rows, '
          f'{len(covs)} cols, {gens} sym generators -> UNSAT expected',
          flush=True)
