"""Round two, the siege: CP-SAT optimization mode on the UESP universe.

The ladder's fixed-k feasibility probes never engaged (17/17 UNKNOWN at
full 12 h caps), so this run deletes the feasibility burden entirely:
minimize plan size directly, warm-hinted with the known 70-brew MIP plan,
with the proven corridor [66, 70] baked in as constraints. Unpruned
instance - every distinct coverage set kept - which is also the instance
the eventual all-optimal-plans census needs.

Fully instrumented this time: every CP-SAT search line lands in
~/alchemy-siege-uesp.log, every incumbent is announced and saved to
~/alchemy-siege-uesp-results.json the moment it exists.
"""
import json
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from ortools.sat.python import cp_model

from alchemy_helper.data.loader import load_dataset

LOG = Path.home() / 'alchemy-siege-uesp.log'
RESULTS = Path.home() / 'alchemy-siege-uesp-results.json'
HINT = Path.home() / 'alchemy-mip-results-uesp.json'
WALL = 48 * 3600.0
LB_KNOWN, UB_KNOWN = 66, 70


def log(msg):
    line = f'{time.strftime("%m-%d %H:%M:%S")} {str(msg).rstrip()}'
    with LOG.open('a') as f:
        f.write(line + '\n')


def save(entry):
    data = json.loads(RESULTS.read_text()) if RESULTS.exists() else []
    data.append(entry)
    RESULTS.write_text(json.dumps(data, indent=1))


def coverage(rows, ings, ks):
    shared = {}
    for k in ks:
        for s, e in enumerate(ings[k].effects):
            shared.setdefault(e, []).append((k, s))
    return frozenset(rows[t] for e, slots in shared.items() if len(slots) >= 2
                     for t in slots if t in rows)


def build_unpruned(ings):
    deg = Counter(e for i in ings for e in i.effects)
    rows = {}
    for k, i in enumerate(ings):
        for s, e in enumerate(i.effects):
            if deg[e] >= 2:
                rows[(k, s)] = len(rows)
    cover = {}
    for combo in combinations(range(len(ings)), 3):
        cov = coverage(rows, ings, combo)
        if cov:
            cover.setdefault(cov, tuple(ings[k].id for k in combo))
    return rows, cover


ds = load_dataset()
PLUGINS = {'Skyrim.esm', 'Update.esm', 'Dawnguard.esm',
           'HearthFires.esm', 'Dragonborn.esm'}
ings = [i for i in ds.ingredients.values()
        if i.plugin in PLUGINS and i.id not in {'berits-ashes', 'jarrin-root'}]

t0 = time.time()
rows, cover = build_unpruned(ings)
covs = list(cover)
reps = [cover[c] for c in covs]
cov_idx = {c: j for j, c in enumerate(covs)}
nrows = len(rows)
log(f'instance: {nrows} rows x {len(covs)} cols (unpruned) '
    f'built in {time.time() - t0:.0f}s')

# map the 70-brew MIP plan onto column indices for the warm hint
idx_of = {i.id: k for k, i in enumerate(ings)}
plan = json.loads(HINT.read_text())[-1]['plan']
hint = {cov_idx[coverage(rows, ings, [idx_of[t] for t in trio])]
        for trio in plan}
log(f'hint mapped: {len(hint)} distinct columns from the 70-brew plan')

model = cp_model.CpModel()
x = [model.NewBoolVar(f'x{j}') for j in range(len(covs))]
rowvars = defaultdict(list)
for j, cov in enumerate(covs):
    for r in cov:
        rowvars[r].append(x[j])
for r in range(nrows):
    model.AddBoolOr(rowvars[r])
size = sum(x)
model.Minimize(size)
model.Add(size >= LB_KNOWN)
model.Add(size <= UB_KNOWN)
for j, v in enumerate(x):
    model.AddHint(v, 1 if j in hint else 0)


class Incumbent(cp_model.CpSolverSolutionCallback):
    def __init__(self):
        super().__init__()
        self.t0 = time.time()

    def on_solution_callback(self):
        obj = int(self.ObjectiveValue())
        bnd = self.BestObjectiveBound()
        secs = round(time.time() - self.t0, 1)
        log(f'*** incumbent {obj} (bound {bnd:.2f}) at {secs}s')
        save({'instance': 'uesp-base-dlc-112', 'phase': 'incumbent',
              'objective': obj, 'bound': bnd, 'seconds': secs,
              'plan': [list(reps[j]) for j, v in enumerate(x)
                       if self.Value(v)]})


solver = cp_model.CpSolver()
solver.parameters.num_search_workers = 80
solver.parameters.max_time_in_seconds = WALL
solver.parameters.log_search_progress = True
solver.log_callback = log

log(f'siege begins: minimize over [{LB_KNOWN}, {UB_KNOWN}], '
    f'80 workers, {WALL / 3600:.0f}h cap')
status = solver.Solve(model, Incumbent())
name = solver.StatusName(status)
obj = (int(solver.ObjectiveValue())
       if name in ('OPTIMAL', 'FEASIBLE') else None)
log(f'SIEGE OVER: {name} objective={obj} '
    f'bound={solver.BestObjectiveBound():.2f} '
    f'after {solver.WallTime():.0f}s')
save({'instance': 'uesp-base-dlc-112', 'phase': 'final', 'status': name,
      'objective': obj, 'bound': solver.BestObjectiveBound(),
      'seconds': round(solver.WallTime(), 1)})
