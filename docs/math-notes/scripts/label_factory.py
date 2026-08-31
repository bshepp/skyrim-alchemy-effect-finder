"""Lane 3, the label factory: exact-labeled small worlds for ML.

Samples sub-universes of the UESP pool under three growth strategies
(dense, sparse, uniform random), computes EXACT labels with the
covering-polynomial engine - minimum plan size, census of all optimal
plans, the next two coefficients - plus a greedy baseline and its gap,
and appends JSONL records. Every label is exact; the factory is bounded
by the row fence (2^red states per world), which is precisely what makes
the eventual extrapolation experiment honest: models train inside the
fence and are graded just beyond it.

Usage: python label_factory.py [count] [seed]
"""
import json
import random
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from math import comb
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from alchemy_helper.data.loader import load_dataset

OUT = Path(__file__).resolve().parents[1] / 'data' / 'small-worlds-v1.jsonl'
ROW_FENCE = 26
SIZES = range(4, 15)
STRATEGIES = ('dense', 'sparse', 'random')


def instance(ings):
    deg = Counter(e for i in ings for e in i.effects)
    rows = {}
    for k, i in enumerate(ings):
        for s, e in enumerate(i.effects):
            if deg[e] >= 2:
                rows[(k, s)] = len(rows)
    cols = []
    for r in (2, 3):
        for combo in combinations(range(len(ings)), r):
            shared = defaultdict(list)
            for k in combo:
                for s, e in enumerate(ings[k].effects):
                    shared[e].append((k, s))
            cov = 0
            for e, slots in shared.items():
                if len(slots) >= 2:
                    for t in slots:
                        cov |= 1 << rows[t]
            if cov:
                cols.append(cov)
    return len(rows), cols


def reduce_rows(nrows, cols):
    rowcols = defaultdict(set)
    for j, cov in enumerate(cols):
        for r in range(nrows):
            if cov >> r & 1:
                rowcols[r].add(j)
    keep = []
    for r in range(nrows):
        implied = any(rowcols[q] < rowcols[r] or
                      (rowcols[q] == rowcols[r] and q < r)
                      for q in range(nrows) if q != r)
        if not implied:
            keep.append(r)
    remap = {r: i for i, r in enumerate(keep)}
    newcols = []
    for cov in cols:
        m = 0
        for r in keep:
            if cov >> r & 1:
                m |= 1 << remap[r]
        if m:
            newcols.append(m)
    return len(keep), newcols


def cover_counts(nrows, cols, kmax):
    size = 1 << nrows
    full = size - 1
    f = np.zeros(size, dtype=np.int32)
    for cov in cols:
        f[cov ^ full] += 1
    for b in range(nrows):
        v = f.reshape(-1, 2, 1 << b)
        v[:, 0, :] += v[:, 1, :]
    parity = np.zeros(1, dtype=np.int8)
    for _ in range(nrows):
        parity = np.concatenate([parity, parity ^ 1])
    top = int(f.max())
    w_even = np.bincount(f[parity == 0], minlength=top + 1)
    w_odd = np.bincount(f[parity == 1], minlength=top + 1)
    weights = [(m, int(w_even[m]) - int(w_odd[m]))
               for m in range(top + 1) if w_even[m] != w_odd[m]]
    return [sum(w * comb(m, k) for m, w in weights) for k in range(kmax + 1)]


def greedy_size(nrows, cols):
    full = (1 << nrows) - 1
    unc, used = full, 0
    while unc:
        best = max(cols, key=lambda c: bin(c & unc).count('1'))
        unc &= ~best
        used += 1
    return used


def sample_world(pool, n, strategy, rng):
    if strategy == 'random':
        return rng.sample(pool, n)
    chosen = [rng.choice(pool)]
    rest = [i for i in pool if i is not chosen[0]]
    sign = 1 if strategy == 'dense' else -1
    while len(chosen) < n:
        have = {e for i in chosen for e in i.effects}
        rest.sort(key=lambda i: (sign * -sum(e in have for e in i.effects),
                                 i.id))
        pick = rest.pop(0)
        chosen.append(pick)
    return chosen


def main(count, seed):
    ds = load_dataset()
    plugins = {'Skyrim.esm', 'Update.esm', 'Dawnguard.esm',
               'HearthFires.esm', 'Dragonborn.esm'}
    every = list(ds.ingredients.values())
    # Pools are the mod axis: a modded universe (CACO, Apothecary, ...)
    # later becomes one more entry here feeding the same factory, and
    # "train on one pool, test on another" is the distribution-shift
    # experiment.
    pools = {
        'uesp-112': [i for i in every if i.plugin in plugins
                     and i.id not in {'berits-ashes', 'jarrin-root'}],
        'full-180': every,
    }
    rng = random.Random(seed)
    seen = set()
    made = skipped = 0
    t0 = time.time()
    with OUT.open('a', encoding='utf-8') as out:
        while made < count:
            pool_name = rng.choice(sorted(pools))
            pool = pools[pool_name]
            n = rng.choice(SIZES)
            strategy = rng.choice(STRATEGIES)
            ings = sample_world(pool, n, strategy, rng)
            key = frozenset(i.id for i in ings)
            if key in seen:
                continue
            seen.add(key)
            nrows, cols = instance(ings)
            if nrows == 0:
                skipped += 1
                continue
            red, rcols = reduce_rows(nrows, cols)
            if red > ROW_FENCE:
                skipped += 1
                continue
            counts = cover_counts(red, rcols, kmax=min(red, len(rcols)))
            opt = next((k for k, c in enumerate(counts) if c), None)
            if opt is None:
                skipped += 1
                continue
            assert all(c == 0 for c in counts[:opt])
            greedy = greedy_size(red, rcols)
            rec = {'ids': sorted(key), 'n': n, 'pool': pool_name,
                   'strategy': strategy,
                   'rows': nrows, 'reduced_rows': red, 'mixes': len(rcols),
                   'opt': opt, 'census': counts[opt],
                   'coeffs': counts[opt:opt + 3],
                   'greedy': greedy, 'greedy_gap': greedy - opt}
            out.write(json.dumps(rec) + '\n')
            out.flush()
            made += 1
            if made % 50 == 0:
                print(f'{made}/{count} worlds ({skipped} skipped) '
                      f'in {time.time() - t0:.0f}s', flush=True)
    print(f'DONE: {made} worlds, {skipped} skipped, '
          f'{time.time() - t0:.0f}s -> {OUT}', flush=True)


if __name__ == '__main__':
    main(count=int(sys.argv[1]) if len(sys.argv) > 1 else 2000,
         seed=int(sys.argv[2]) if len(sys.argv) > 2 else 20260830)
