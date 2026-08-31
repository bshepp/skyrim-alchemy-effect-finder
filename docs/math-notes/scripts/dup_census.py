"""Census of duplicate and near-twin ingredients in both universes."""
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from alchemy_helper.data.loader import load_dataset

ds = load_dataset()
all_ings = list(ds.ingredients.values())
PLUGINS = {'Skyrim.esm', 'Update.esm', 'Dawnguard.esm',
           'HearthFires.esm', 'Dragonborn.esm'}
uesp = [i for i in all_ings
        if i.plugin in PLUGINS and i.id not in {'berits-ashes', 'jarrin-root'}]

for tag, ings in [('uesp-112', uesp), ('full-180', all_ings)]:
    groups = defaultdict(list)
    for i in ings:
        groups[frozenset(i.effects)].append(i.id)
    dups = [v for v in groups.values() if len(v) > 1]
    print(f'{tag}: {len(dups)} exact-duplicate classes')
    for v in dups:
        print('   =', v)
    n3 = [(a.id, b.id) for a, b in combinations(ings, 2)
          if len(set(a.effects) & set(b.effects)) == 3
          and set(a.effects) != set(b.effects)]
    print(f'{tag}: {len(n3)} pairs sharing exactly 3 of 4 effects')
    for p in n3:
        print('   ~', p)
    print()
