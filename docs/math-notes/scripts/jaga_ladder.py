"""The feasibility ladder: close both optimality corridors exactly.

For each instance, probe fixed sizes k in parallel with CP-SAT:
SAT(k) lowers the ceiling (and yields a plan); UNSAT(k) raises the floor.
The ladder closes when SAT(k) and UNSAT(k-1) meet.

Columns are dominance-pruned (only maximal coverage sets kept) - valid
for finding the optimal VALUE and a witness plan; the later census of
ALL optimal plans must use the unpruned instance.
"""
import json
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import combinations
from pathlib import Path

from ortools.sat.python import cp_model

from alchemy_helper.data.loader import load_dataset

RESULTS = Path.home() / 'alchemy-ladder-results.json'
PROBE_TIME = 12 * 3600.0


def build_instance(ings):
    deg = Counter(e for i in ings for e in i.effects)
    rows = {}
    for k, i in enumerate(ings):
        for s, e in enumerate(i.effects):
            if deg[e] >= 2:
                rows[(k, s)] = len(rows)
    cover = {}
    for combo in combinations(range(len(ings)), 3):
        shared = {}
        for k in combo:
            for s, e in enumerate(ings[k].effects):
                shared.setdefault(e, []).append((k, s))
        cov = frozenset(rows[t] for e, slots in shared.items() if len(slots) >= 2
                        for t in slots if t in rows)
        if cov:
            cover.setdefault(cov, tuple(ings[k].id for k in combo))
    # dominance pruning: keep only maximal coverage sets
    items = sorted(cover.items(), key=lambda kv: -len(kv[0]))
    kept, row_to_kept = [], defaultdict(list)
    for cov, rep in items:
        rarest = min(cov, key=lambda r: len(row_to_kept[r]))
        if any(cov <= kept[j][0] for j in row_to_kept[rarest]):
            continue
        idx = len(kept)
        kept.append((cov, rep))
        for r in cov:
            row_to_kept[r].append(idx)
    return len(rows), kept


def probe(args):
    tag, k, nrows, covs, workers = args
    model = cp_model.CpModel()
    x = [model.NewBoolVar(f'x{j}') for j in range(len(covs))]
    rowvars = defaultdict(list)
    for j, cov in enumerate(covs):
        for r in cov:
            rowvars[r].append(x[j])
    for r in range(nrows):
        model.AddBoolOr(rowvars[r])
    model.Add(sum(x) <= k)
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = workers
    solver.parameters.max_time_in_seconds = PROBE_TIME
    t0 = time.time()
    status = solver.Solve(model)
    name = solver.StatusName(status)
    picked = ([j for j in range(len(covs)) if solver.Value(x[j])]
              if name in ('OPTIMAL', 'FEASIBLE') else [])
    return {'instance': tag, 'k': k, 'status': name,
            'seconds': round(time.time() - t0, 1), 'picked': picked}


def ladder(tag, ings, ks, workers_per_probe):
    t0 = time.time()
    nrows, kept = build_instance(ings)
    covs = [list(c) for c, _ in kept]
    reps = [r for _, r in kept]
    print(f'[{tag}] rows={nrows} maximal cols={len(covs)} '
          f'built in {time.time()-t0:.0f}s; probing k={ks}', flush=True)
    jobs = [(tag, k, nrows, covs, workers_per_probe) for k in ks]
    with ProcessPoolExecutor(max_workers=len(jobs)) as ex:
        futures = {ex.submit(probe, j): j[1] for j in jobs}
        for fut in as_completed(futures):
            res = fut.result()
            if res['picked']:
                res['plan'] = [reps[j] for j in res['picked']]
            res.pop('picked', None)
            print(f"[{tag}] k={res['k']}: {res['status']} "
                  f"in {res['seconds']}s", flush=True)
            existing = json.loads(RESULTS.read_text()) if RESULTS.exists() else []
            existing.append(res)
            RESULTS.write_text(json.dumps(existing, indent=1))


ds = load_dataset()
all_ings = list(ds.ingredients.values())
PLUGINS = {'Skyrim.esm', 'Update.esm', 'Dawnguard.esm',
           'HearthFires.esm', 'Dragonborn.esm'}
uesp = [i for i in all_ings
        if i.plugin in PLUGINS and i.id not in {'berits-ashes', 'jarrin-root'}]

# UESP corridor [66, 70]: four probes close it completely.
ladder('uesp-base-dlc-112', uesp, [66, 67, 68, 69], workers_per_probe=12)
# Full-game corridor [95, 108]: thirteen probes.
ladder('full-game-180', all_ings, list(range(95, 108)), workers_per_probe=6)
print('LADDER COMPLETE', flush=True)
