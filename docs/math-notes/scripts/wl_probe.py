"""Names as a probe: anonymous color refinement (1-WL) on the alchemy
bipartite graph, then individualization - pin names one at a time and
watch identity cascade back through the structure.

Question 1: with all labels stripped, how many ingredients does the
sharing structure alone distinguish?
Question 2: how many pins (individualizations) until everything is named?
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from alchemy_helper.data.loader import load_dataset


def refine(ings, pins=()):
    """Anonymous 1-WL to stability. Returns (ingredient classes, rounds)."""
    nbr = {}
    eff_members = defaultdict(list)
    for i in ings:
        nbr[('i', i.id)] = [('e', e) for e in i.effects]
        for e in i.effects:
            eff_members[e].append(('i', i.id))
    for e, members in eff_members.items():
        nbr[('e', e)] = members
    color = {v: (0 if v[0] == 'i' else 1) for v in nbr}
    for n, ing_id in enumerate(pins):
        color[('i', ing_id)] = 2 + n
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
    classes = defaultdict(list)
    for v, c in color.items():
        if v[0] == 'i':
            classes[c].append(v[1])
    return sorted((sorted(m) for m in classes.values()),
                  key=lambda m: (-len(m), m)), rounds


def probe(tag, ings):
    n_eff = len({e for i in ings for e in i.effects})
    deg = defaultdict(int)
    for i in ings:
        for e in i.effects:
            deg[e] += 1
    pendants = sorted(e for e, d in deg.items() if d == 1)
    classes, rounds = refine(ings)
    multi = [m for m in classes if len(m) > 1]
    print(f'== {tag}: {len(ings)} ingredients, {n_eff} effects ==')
    print(f'natural name-effects (appear on exactly one ingredient): '
          f'{pendants if pendants else "none"}')
    print(f'anonymous refinement stabilized in {rounds} rounds: '
          f'{len(classes)} classes ({len(multi)} still ambiguous)')
    for m in multi:
        print('   ?', m)
    pins = []
    while True:
        classes, _ = refine(ings, pins)
        multi = [m for m in classes if len(m) > 1]
        if not multi:
            break
        target = multi[0][0]  # first member of the largest ambiguous class
        pins.append(target)
        print(f'   pin #{len(pins)}: {target} '
              f'(was in class of {len(multi[0])})')
    print(f'fully named after {len(pins)} pins\n')


ds = load_dataset()
all_ings = list(ds.ingredients.values())
PLUGINS = {'Skyrim.esm', 'Update.esm', 'Dawnguard.esm',
           'HearthFires.esm', 'Dragonborn.esm'}
uesp = [i for i in all_ings
        if i.plugin in PLUGINS and i.id not in {'berits-ashes', 'jarrin-root'}]

probe('uesp-112', uesp)
probe('full-180', all_ings)
