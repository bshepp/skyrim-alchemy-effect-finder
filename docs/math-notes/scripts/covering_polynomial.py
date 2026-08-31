"""Rung 4, taken to the fence: exact covering polynomials.

The covering polynomial of an instance is P(x) = sum over covering sets S
of x^|S|, where a column is any valid 2- or 3-ingredient mix with nonzero
coverage (NO dedupe, NO dominance - the census counts mixes as distinct
objects). The lowest-degree nonzero term of P is the minimum plan size,
and its coefficient is the census of all optimal plans. One polynomial
contains everything the search campaign fights for.

Method: inclusion-exclusion over row subsets,
    N_k = sum_{U subseteq rows} (-1)^{|U|} C(m_U, k),
where m_U = number of mixes touching no row of U. All m_U at once via a
superset-zeta transform (numpy, O(2^r * r)); the alternating sum grouped
by m-value, then exact big-integer binomials. Cost is 2^r in memory, so
the fence is the reduced row count r:
    r=28 -> 1 GiB, r=30 -> 4 GiB (desktop fence)
    r=34 -> 64 GiB, r=35 -> 128 GiB (jaga fence)

Row reduction (sound, exact): a row whose mix-set contains another row's
mix-set is implied by it and is dropped; duplicate rows keep one
representative. Covers of the reduced instance = covers of the original.

Verification: for the smallest universes the full distribution is checked
against brute-force enumeration over all subsets of mixes.
"""
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from math import comb
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from alchemy_helper.data.loader import load_dataset

ROW_FENCE = 28          # 2^28 int32 = 1 GiB: safe on the desktop
BRUTE_MIX_LIMIT = 20    # brute-force verification up to 2^20 subsets


def sub_universe(pool, n, seed='blue-butterfly-wing'):
    """Deterministic greedy: grow from the seed by most shared effects."""
    chosen = [i for i in pool if i.id == seed]
    rest = sorted((i for i in pool if i.id != seed), key=lambda i: i.id)
    while len(chosen) < n:
        have = {e for i in chosen for e in i.effects}
        best = max(rest, key=lambda i: (sum(e in have for e in i.effects),
                                        [-ord(c) for c in i.id]))
        chosen.append(best)
        rest.remove(best)
    return chosen


def instance(ings):
    """All valid mixes (pairs + trios) with nonzero coverage, un-deduped."""
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
    """Drop rows implied by others (their mix-set contains another's)."""
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
        newcols.append(m)  # keep zero-coverage mixes out of the count
    newcols = [c for c in newcols if c]
    dropped = len(cols) - len(newcols)
    return len(keep), newcols, dropped


def cover_counts(nrows, cols, kmax):
    """N_k for k = 0..kmax via superset-zeta + exact binomials."""
    size = 1 << nrows
    full = size - 1
    f = np.zeros(size, dtype=np.int32)
    for cov in cols:
        f[cov ^ full] += 1
    for b in range(nrows):            # superset-zeta, vectorized per bit
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


def brute_counts(nrows, cols, kmax):
    full = (1 << nrows) - 1
    out = [0] * (kmax + 1)
    for pick in range(1 << len(cols)):
        cov, size, p = 0, 0, pick
        while p:
            j = (p & -p).bit_length() - 1
            cov |= cols[j]
            size += 1
            p &= p - 1
        if cov == full and size <= kmax:
            out[size] += 1
    return out


ds = load_dataset()
PLUGINS = {'Skyrim.esm', 'Update.esm', 'Dawnguard.esm',
           'HearthFires.esm', 'Dragonborn.esm'}
pool = [i for i in ds.ingredients.values()
        if i.plugin in PLUGINS and i.id not in {'berits-ashes', 'jarrin-root'}]

print(f'{"n":>3} {"rows":>5} {"red":>4} {"mixes":>6} {"OPT":>4} '
      f'{"census":>12}  {"next terms":<24} {"secs":>6}')
n = 3
while True:
    ings = sub_universe(pool, n)
    nrows, cols = instance(ings)
    red, rcols, dropped = reduce_rows(nrows, cols)
    if red > ROW_FENCE:
        print(f'{n:>3} {nrows:>5} {red:>4}  -> past the desktop fence '
              f'(2^{red} states); jaga reaches ~35 rows post-siege')
        break
    t0 = time.time()
    counts = cover_counts(red, rcols, kmax=min(len(rcols), red) )
    secs = time.time() - t0
    opt = next((k for k, c in enumerate(counts) if c), None)
    below = all(c == 0 for c in counts[:opt]) if opt is not None else True
    assert below, 'nonzero count below optimum - inclusion-exclusion bug'
    if len(rcols) <= BRUTE_MIX_LIMIT:
        bk = min(len(rcols), red)
        assert brute_counts(red, rcols, bk) == counts[:bk + 1], \
            'brute-force mismatch'
        tag = 'verified brute-force'
    else:
        tag = ''
    nxt = counts[opt + 1:opt + 3] if opt is not None else []
    print(f'{n:>3} {nrows:>5} {red:>4} {len(rcols):>6} {opt:>4} '
          f'{counts[opt]:>12,}  {str(nxt):<24} {secs:>6.1f} {tag}')
    if n == 3:
        terms = [f'{c}x^{k}' for k, c in enumerate(counts) if c]
        print(f'      P(x) for n=3 [{", ".join(i.id for i in ings)}]:')
        print(f'      {" + ".join(terms)}')
    n += 1
