"""Lane 1, the ceiling attack: iterated local search for a 69-brew plan.

Attacks the UESP-112 ceiling directly: start from the exact 70-brew MIP
plan, repeatedly destroy a few brews and greedily repair, accept
non-worsening plans, log every improvement. A found 69-plan shrinks the
corridor from above with a millisecond-checkable witness - no proof
claimed, none needed for a ceiling. This lane can only ever lower the
ceiling; the floor belongs to proof systems (see symbolic-ladder.md).

Usage: python plan_search.py [seconds] [workers]
Improvements land in data/plan-search-best.json the moment they exist.
"""
import json
import os
import random
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from multiprocessing import Process
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from alchemy_helper.data.loader import load_dataset

DATA = Path(__file__).resolve().parents[1] / 'data'
START = DATA / 'alchemy-mip-results-uesp.json'
BEST = DATA / 'plan-search-best.json'


def build():
    ds = load_dataset()
    plugins = {'Skyrim.esm', 'Update.esm', 'Dawnguard.esm',
               'HearthFires.esm', 'Dragonborn.esm'}
    ings = [i for i in ds.ingredients.values()
            if i.plugin in plugins
            and i.id not in {'berits-ashes', 'jarrin-root'}]
    deg = Counter(e for i in ings for e in i.effects)
    rows = {}
    for k, i in enumerate(ings):
        for s, e in enumerate(i.effects):
            if deg[e] >= 2:
                rows[(k, s)] = len(rows)

    def coverage(ks):
        shared = defaultdict(list)
        for k in ks:
            for s, e in enumerate(ings[k].effects):
                shared[e].append((k, s))
        cov = 0
        for e, slots in shared.items():
            if len(slots) >= 2:
                for t in slots:
                    cov |= 1 << rows[t]
        return cov

    cover = {}
    for combo in combinations(range(len(ings)), 3):
        cov = coverage(combo)
        if cov:
            cover.setdefault(cov, tuple(ings[k].id for k in combo))
    covs = list(cover)
    reps = [cover[c] for c in covs]
    cov_idx = {c: j for j, c in enumerate(covs)}
    idx_of = {i.id: k for k, i in enumerate(ings)}
    plan = json.loads(START.read_text())[-1]['plan']
    start = [cov_idx[coverage([idx_of[t] for t in trio])] for trio in plan]
    full = (1 << len(rows)) - 1
    return covs, reps, start, full


def repair(plan_set, covs, full, rng):
    unc = full
    for j in plan_set:
        unc &= ~covs[j]
    while unc:
        best_j, best_gain = -1, 0
        for j, c in enumerate(covs):
            g = (c & unc).bit_count()
            if g > best_gain or (g == best_gain and g and rng.random() < .1):
                best_j, best_gain = j, g
        plan_set.add(best_j)
        unc &= ~covs[best_j]
    return plan_set


def announce(size, plan_ids, wid, note):
    tmp = BEST.with_suffix('.tmp')
    tmp.write_text(json.dumps(
        {'size': size, 'worker': wid, 'time': time.strftime('%F %T'),
         'plan': plan_ids}, indent=1))
    os.replace(tmp, BEST)
    print(f'[w{wid}] {note}: {size} brews', flush=True)


def worker(wid, seconds, seed):
    covs, reps, start, full = build()
    rng = random.Random(seed)
    best = set(start)
    cur = set(best)
    t0 = time.time()
    iters = 0
    while time.time() - t0 < seconds:
        iters += 1
        trial = set(cur)
        for j in rng.sample(sorted(trial), rng.randint(2, 4)):
            trial.discard(j)
        trial = repair(trial, covs, full, rng)
        if len(trial) <= len(cur):
            cur = trial
        if len(cur) < len(best):
            best = set(cur)
            announce(len(best), [list(reps[j]) for j in sorted(best)],
                     wid, 'IMPROVED')
        if iters % 500 == 0:
            print(f'[w{wid}] {iters} iters, best {len(best)}, '
                  f'{time.time() - t0:.0f}s', flush=True)
            cur = set(best)  # restart the walk from the incumbent
    print(f'[w{wid}] done: {iters} iters, best {len(best)}', flush=True)


if __name__ == '__main__':
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 6 * 3600
    nworkers = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    procs = [Process(target=worker, args=(w, seconds, 20260830 + w))
             for w in range(nworkers)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    print('CEILING ATTACK COMPLETE', flush=True)
