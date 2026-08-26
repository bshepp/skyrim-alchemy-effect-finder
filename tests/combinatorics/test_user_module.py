import random
from itertools import combinations

import pytest
from alchemy_helper.data.models import Ingredient
from alchemy_helper.data.loader import load_dataset
from alchemy_helper.combinatorics.core import (
    combos_for_effect, potion_effects, discovery_plan, best_potions, _produced)
from alchemy_helper.combinatorics.types import Combo, EffectResult, PlannedBrew

pytestmark = pytest.mark.combinatorics   # select just these: pytest -m combinatorics

def ing(id_, *effects):
    return Ingredient(id=id_, name=id_.upper(), plugin="Test.esp",
                      form_id=0, effects=tuple(effects))

A = ing("a", "e1", "e2", "e3", "e4")
B = ing("b", "e1", "e5", "e6", "e7")
C = ing("c", "e2", "e5", "e8", "e9")
TRIO = [A, B, C]

# --- potion_effects ---
def test_pair_effects():
    [r] = potion_effects(["a", "b"], TRIO)
    assert (r.effect_id, r.ingredient_ids) == ("e1", ("a", "b"))

def test_no_shared_effects_is_empty():
    d = ing("d", "x1", "x2", "x3", "x4")
    assert potion_effects(["a", "d"], TRIO + [d]) == []

def test_trio_produces_three_effects():
    rs = {r.effect_id: r.ingredient_ids for r in potion_effects(["a","b","c"], TRIO)}
    assert rs == {"e1": ("a","b"), "e2": ("a","c"), "e5": ("b","c")}

def test_wheat_plus_giants_toe_real_data():
    ds = load_dataset()
    rs = {r.effect_id for r in
          potion_effects(["wheat", "giants-toe"], list(ds.ingredients.values()))}
    assert rs == {"fortify-health", "damage-stamina-regen"}

# --- combos_for_effect ---
def test_all_combos_for_effect():
    got = {c.ingredient_ids for c in combos_for_effect("e1", TRIO)}
    assert got == {("a", "b"), ("a", "b", "c")}

def test_inventory_filters_combos():
    got = {c.ingredient_ids
           for c in combos_for_effect("e1", TRIO, inventory={"a": 1, "b": 2})}
    assert got == {("a", "b")}

# --- discovery_plan ---
def test_one_trio_brew_beats_three_pairs():
    plan = discovery_plan(TRIO, {"a": 2, "b": 2, "c": 2},
                          {"a": set(), "b": set(), "c": set()})
    assert len(plan) == 1                       # optimal: single a+b+c brew
    assert set(plan[0].ingredient_ids) == {"a", "b", "c"}
    assert set(plan[0].newly_discovered) == {
        ("a", 0), ("b", 0), ("a", 1), ("c", 0), ("b", 1), ("c", 1)}

def test_inventory_limits_plan():
    plan = discovery_plan(TRIO, {"a": 1, "b": 1},
                          {"a": set(), "b": set(), "c": set()})
    assert len(plan) == 1
    assert set(plan[0].ingredient_ids) == {"a", "b"}

def test_nothing_left_to_discover_is_empty_plan():
    known = {"a": {0, 1}, "b": {0, 1}, "c": {0, 1}}
    assert discovery_plan(TRIO, {"a": 5, "b": 5, "c": 5}, known) == []

def _naive_plan(ingredients, inventory, known_effects):
    """Reference implementation: full re-scan of every mix each round.
    discovery_plan must always produce exactly this output, however it
    gets there internally."""
    by_id = {i.id: i for i in ingredients}
    stock = {iid: n for iid, n in inventory.items() if iid in by_id and n >= 1}
    known = {iid: set(known_effects.get(iid, ())) for iid in stock}

    def reveals(ids):
        return [(iid, by_id[iid].effects.index(r.effect_id))
                for r in _produced([by_id[i] for i in ids])
                for iid in r.ingredient_ids
                if by_id[iid].effects.index(r.effect_id) not in known[iid]]

    plan = []
    while True:
        avail = sorted(iid for iid, n in stock.items() if n >= 1)
        best = None
        for size in (2, 3):
            for ids in combinations(avail, size):
                newly = reveals(ids)
                if newly and (best is None
                              or (-len(newly), len(ids), ids) < best[0]):
                    best = ((-len(newly), len(ids), ids), ids, newly)
        if best is None:
            return plan
        _, ids, newly = best
        plan.append(PlannedBrew(ingredient_ids=ids,
                                newly_discovered=tuple(sorted(newly))))
        for iid, slot in newly:
            known[iid].add(slot)
        for iid in ids:
            stock[iid] -= 1


def test_discovery_plan_matches_naive_reference_on_generated_scenarios():
    rng = random.Random(42)
    effect_pool = [f"e{i}" for i in range(12)]
    for _ in range(5):
        ings = [ing(f"i{k}", *rng.sample(effect_pool, 4)) for k in range(15)]
        inventory = {i.id: rng.randint(1, 3)
                     for i in ings if rng.random() < 0.8}
        known = {i.id: set(rng.sample(range(4), rng.randint(0, 2)))
                 for i in ings}
        assert (discovery_plan(ings, inventory, known)
                == _naive_plan(ings, inventory, known))


# --- best_potions ---
def test_best_potions_ranks_by_effect_count():
    pots = best_potions(TRIO, {"a": 1, "b": 1, "c": 1})
    assert pots[0].ingredient_ids == ("a", "b", "c")     # 3 merged effects
    assert pots[0].effect_ids == ("e1", "e2", "e5")
    # then the three 1-effect pairs; failed mixes never appear
    assert {p.ingredient_ids for p in pots[1:]} == {("a","b"), ("a","c"), ("b","c")}

def test_best_potions_only_uses_carried_ingredients():
    pots = best_potions(TRIO, {"a": 1, "b": 1})
    assert {p.ingredient_ids for p in pots} == {("a", "b")}

def test_best_potions_excludes_failed_mixes():
    d = ing("d", "x1", "x2", "x3", "x4")
    assert best_potions(TRIO + [d], {"a": 1, "d": 1}) == []

def test_best_potions_respects_limit():
    pots = best_potions(TRIO, {"a": 1, "b": 1, "c": 1}, limit=2)
    assert len(pots) == 2
    assert pots[0].ingredient_ids == ("a", "b", "c")
