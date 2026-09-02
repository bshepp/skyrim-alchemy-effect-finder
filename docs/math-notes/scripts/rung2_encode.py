"""Rung 2 encoder: the k=69 question as pure CNF.

Encodes "does a discovery plan of at most k mixes exist?" for the
UESP-112 universe as DIMACS CNF: one variable per dominance-pruned trio
column, one covering clause per slot row, a totalizer for the
cardinality bound, and (in the sym variant) lex-leader clauses breaking
the duplicate-ingredient symmetries. UNSAT at k=69 plus the known
70-brew witness proves the optimum is exactly 70.

Soundness notes:
- Pairs are dominated by trios and identical-coverage trios collapse,
  so pruned maximal trio columns decide feasibility-at-k exactly.
- Lex-leader clauses X <=lex sigma(X), one per transposition generator
  of the duplicate-class symmetry group, preserve the lex-least member
  of every solution orbit.

Modes:
  selftest  - validate the whole chain on small worlds against the
              exact covering-polynomial engine (SAT at OPT with a
              verified decoded witness, UNSAT at OPT-1, both variants).
  encode    - emit rung2-plain.cnf, rung2-sym.cnf, rung2-vars.json.
"""
import json
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from math import comb
from pathlib import Path

sys.path.insert(0, str(Path.home() / 'alembic'))
from alchemy_helper.data.loader import load_dataset

from pysat.card import CardEnc, EncType
from pysat.solvers import Cadical153

K = 69
OUTDIR = Path.home()


def build(ings):
    """Rows, pruned maximal columns (frozensets), representative trios."""
    deg = Counter(e for i in ings for e in i.effects)
    rows = {}
    for k, i in enumerate(ings):
        for s, e in enumerate(i.effects):
            if deg[e] >= 2:
                rows[(k, s)] = len(rows)
    cover = {}
    for combo in combinations(range(len(ings)), 3):
        shared = defaultdict(list)
        for k in combo:
            for s, e in enumerate(ings[k].effects):
                shared[e].append((k, s))
        cov = frozenset(rows[t] for e, sl in shared.items() if len(sl) >= 2
                        for t in sl if t in rows)
        if cov:
            cover.setdefault(cov, tuple(ings[k].id for k in combo))
    items = sorted(cover.items(), key=lambda kv: -len(kv[0]))
    kept, row_to = [], defaultdict(list)
    for cov, rep in items:
        rare = min(cov, key=lambda r: len(row_to[r]))
        if any(cov <= kept[j][0] for j in row_to[rare]):
            continue
        idx = len(kept)
        kept.append((cov, rep))
        for r in cov:
            row_to[r].append(idx)
    return rows, [c for c, _ in kept], [r for _, r in kept]


def dup_transpositions(ings):
    """Adjacent transpositions (a, b) generating each duplicate class."""
    groups = defaultdict(list)
    for i in ings:
        groups[frozenset(i.effects)].append(i)
    gens = []
    for members in groups.values():
        members.sort(key=lambda i: i.id)
        for a, b in zip(members, members[1:]):
            gens.append((a, b))
    return gens


def column_permutation(rows, covs, ings, a, b):
    """The involution on columns induced by swapping clones a and b."""
    ka = next(k for k, i in enumerate(ings) if i.id == a.id)
    kb = next(k for k, i in enumerate(ings) if i.id == b.id)
    rowswap = {}
    for sa, e in enumerate(a.effects):
        sb = b.effects.index(e)
        ra, rb = rows.get((ka, sa)), rows.get((kb, sb))
        if ra is not None and rb is not None:
            rowswap[ra], rowswap[rb] = rb, ra
    index = {c: j for j, c in enumerate(covs)}
    perm = []
    for c in covs:
        img = frozenset(rowswap.get(r, r) for r in c)
        j = index.get(img)
        if j is None:
            return None  # symmetry broken by pruning; skip this generator
        perm.append(j)
    return perm


def lex_clauses(perm, nvars, next_aux):
    """X <=lex sigma(X) for an involution, pair-compressed encoding."""
    pairs = sorted(i for i in range(len(perm)) if i < perm[i])
    clauses = []
    prev = None
    for t, i in enumerate(pairs):
        j = perm[i]
        xi, xj = i + 1, j + 1
        if prev is None:
            clauses.append([-xi, xj])
        else:
            clauses.append([-prev, -xi, xj])
        if t < len(pairs) - 1:
            e = next_aux
            next_aux += 1
            if prev is None:
                clauses.append([-xi, -xj, e])
                clauses.append([xi, xj, e])
            else:
                clauses.append([-prev, -xi, -xj, e])
                clauses.append([-prev, xi, xj, e])
            prev = e
    return clauses, next_aux


def encode(ings, k, sym):
    rows, covs, reps = build(ings)
    n = len(covs)
    rowvars = defaultdict(list)
    for j, cov in enumerate(covs):
        for r in cov:
            rowvars[r].append(j + 1)
    clauses = [rowvars[r] for r in range(len(rows))]
    aux = n + 1
    gens_used = 0
    if sym:
        for a, b in dup_transpositions(ings):
            perm = column_permutation(rows, covs, ings, a, b)
            if perm:
                cl, aux = lex_clauses(perm, n, aux)
                clauses.extend(cl)
                gens_used += 1
    card = CardEnc.atmost(lits=list(range(1, n + 1)), bound=k,
                          encoding=EncType.seqcounter, top_id=aux - 1)
    clauses.extend(card.clauses)
    nv = max(aux - 1, card.nv)
    return clauses, nv, covs, reps, len(rows), gens_used


def solve_inline(clauses):
    with Cadical153(bootstrap_with=clauses) as s:
        sat = s.solve()
        return sat, (s.get_model() if sat else None)


def exact_opt(ings):
    """Independent truth: covering polynomial over ALL pairs+trios."""
    import numpy as np
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
            for e, sl in shared.items():
                if len(sl) >= 2:
                    for t in sl:
                        cov |= 1 << rows[t]
            if cov:
                cols.append(cov)
    nr = len(rows)
    if nr == 0 or nr > 24:
        return None
    size = 1 << nr
    f = np.zeros(size, dtype=np.int32)
    full = size - 1
    for cov in cols:
        f[cov ^ full] += 1
    for b in range(nr):
        v = f.reshape(-1, 2, 1 << b)
        v[:, 0, :] += v[:, 1, :]
    par = np.zeros(1, dtype=np.int8)
    for _ in range(nr):
        par = np.concatenate([par, par ^ 1])
    top = int(f.max())
    we = np.bincount(f[par == 0], minlength=top + 1)
    wo = np.bincount(f[par == 1], minlength=top + 1)
    ws = [(m, int(we[m]) - int(wo[m])) for m in range(top + 1)
          if we[m] != wo[m]]
    for k in range(1, nr + 1):
        if sum(w * comb(m, k) for m, w in ws):
            return k
    return None


def selftest():
    import random
    ds = load_dataset()
    pool = list(ds.ingredients.values())
    rng = random.Random(20260901)
    ids = {i.id: i for i in pool}
    worlds = []
    # crafted worlds containing duplicate classes, to exercise lex code
    worlds.append([ids['ancestor-moth-wing'], ids['blue-butterfly-wing'],
                   ids['chaurus-hunter-antennae'], ids['chickens-egg'],
                   ids['hawks-egg'], ids['nightshade'], ids['deathbell']])
    worlds.append([ids['crimson-nirnroot'], ids['nirnroot'],
                   ids['dwarven-oil'], ids['taproot'], ids['glow-dust'],
                   ids['fire-salts'], ids['moon-sugar'], ids['elves-ear']])
    while len(worlds) < 14:
        worlds.append(rng.sample(pool, rng.randint(5, 9)))
    passed = 0
    for w, ings in enumerate(worlds):
        opt = exact_opt(ings)
        if opt is None:
            continue
        for sym in (False, True):
            cl, nv, covs, reps, nr, g = encode(ings, opt, sym)
            sat, model = solve_inline(cl)
            assert sat, f'world {w} sym={sym}: SAT expected at k={opt}'
            chosen = [j for j in range(len(covs)) if model[j] > 0]
            covered = set().union(*(covs[j] for j in chosen)) if chosen else set()
            assert len(chosen) <= opt and len(covered) == nr, \
                f'world {w} sym={sym}: witness invalid'
            if opt > 1:
                cl, *_ = encode(ings, opt - 1, sym)
                sat, _ = solve_inline(cl)
                assert not sat, f'world {w} sym={sym}: UNSAT expected at {opt-1}'
        passed += 1
        print(f'world {w}: n={len(ings)} opt={opt} gens={g} OK', flush=True)
    print(f'SELFTEST PASSED on {passed} worlds', flush=True)


def emit():
    ds = load_dataset()
    plugins = {'Skyrim.esm', 'Update.esm', 'Dawnguard.esm',
               'HearthFires.esm', 'Dragonborn.esm'}
    ings = [i for i in ds.ingredients.values()
            if i.plugin in plugins
            and i.id not in {'berits-ashes', 'jarrin-root'}]
    for sym, name in ((False, 'rung2-plain.cnf'), (True, 'rung2-sym.cnf')):
        t0 = time.time()
        clauses, nv, covs, reps, nr, gens = encode(ings, K, sym)
        path = OUTDIR / name
        with path.open('w') as f:
            f.write(f'p cnf {nv} {len(clauses)}\n')
            for c in clauses:
                f.write(' '.join(map(str, c)) + ' 0\n')
        print(f'{name}: {nv} vars, {len(clauses)} clauses, '
              f'{nr} rows, {len(covs)} cols, {gens} sym generators, '
              f'{time.time()-t0:.0f}s, {path.stat().st_size/1e6:.0f} MB',
              flush=True)
        if not sym:
            (OUTDIR / 'rung2-vars.json').write_text(json.dumps(
                {'k': K, 'columns': [list(r) for r in reps]}))


if __name__ == '__main__':
    if sys.argv[1:] == ['selftest']:
        selftest()
    elif sys.argv[1:] == ['encode']:
        emit()
    else:
        print('usage: rung2_encode.py selftest|encode')
