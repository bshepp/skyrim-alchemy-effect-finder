"""Dissect the emergent model symmetry: effect-degree skew, then WL
classes on the actual solver model (rows + pruned columns), then decode
what the interchangeable column families are made of."""
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, r'F:\video-game-projects\skyrim-alchmey-effect-finder')
from alchemy_helper.data.loader import load_dataset

ds = load_dataset()
PLUGINS = {'Skyrim.esm', 'Update.esm', 'Dawnguard.esm',
           'HearthFires.esm', 'Dragonborn.esm'}
ings = [i for i in ds.ingredients.values()
        if i.plugin in PLUGINS and i.id not in {'berits-ashes', 'jarrin-root'}]

deg = Counter(e for i in ings for e in i.effects)
hist = Counter(deg.values())
print('effect degree histogram (degree: how many effects have it):')
print('  ', dict(sorted(hist.items())))
top = sorted(deg.items(), key=lambda kv: -kv[1])
print('most common:', [(e, d) for e, d in top[:5]])
print('rarest (deg>=2):', [(e, d) for e, d in top[::-1][:6] if d >= 2])

# build the pruned model exactly as the siege/rung-2 encodings do
rows = {}
row_name = {}
for k, i in enumerate(ings):
    for s, e in enumerate(i.effects):
        if deg[e] >= 2:
            row_name[len(rows)] = (i.id, e)
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
covs = [c for c, _ in kept]
reps = [r for _, r in kept]
print(f'model: {len(rows)} rows x {len(covs)} pruned columns')

# 1-WL on the bipartite model graph
nbr = {}
for j, cov in enumerate(covs):
    nbr[('c', j)] = [('r', r) for r in cov]
for r, js in ((r, js) for r, js in row_to.items()):
    nbr[('r', r)] = [('c', j) for j in js]
color = {v: (0 if v[0] == 'r' else 1) for v in nbr}
rounds = 0
while True:
    sig = {v: (color[v], tuple(sorted(color[u] for u in nbr[v])))
           for v in nbr}
    relabel = {s: c for c, s in enumerate(sorted(set(sig.values())))}
    new = {v: relabel[sig[v]] for v in nbr}
    if len(set(new.values())) == len(set(color.values())):
        break
    color = new
    rounds += 1
ccls = defaultdict(list)
for v, c in color.items():
    if v[0] == 'c':
        ccls[c].append(v[1])
multi = sorted((m for m in ccls.values() if len(m) > 1), key=len,
               reverse=True)
tot = sum(len(m) for m in multi)
print(f'WL stable after {rounds} rounds: {len(ccls)} column classes, '
      f'{len(multi)} ambiguous covering {tot} columns')
print('class sizes:', Counter(len(m) for m in multi))

CLONES = {'ancestor-moth-wing', 'blue-butterfly-wing',
          'chaurus-hunter-antennae', 'chickens-egg', 'hawks-egg',
          'crimson-nirnroot', 'nirnroot', 'dwarven-oil', 'taproot'}
print('\nlargest ambiguous families, decoded:')
for m in multi[:6]:
    effs = Counter()
    ing_involved = set()
    for j in m[:80]:
        for r in covs[j]:
            effs[row_name[r][1]] += 1
        ing_involved.update(reps[j])
    clones = ing_involved & CLONES
    top_effs = [(e, deg[e]) for e, _ in effs.most_common(4)]
    print(f'  size {len(m):>3}: sample trio {reps[m[0]]}')
    print(f'      effects touched (theirs deg): {top_effs}; '
          f'clone members involved: {sorted(clones) if clones else "NONE"}')
