import pytest
from alchemy_helper.data.models import Ingredient
from alchemy_helper.data.loader import load_dataset
from alchemy_helper.combinatorics.core import (
    combos_for_effect, potion_effects, discovery_plan, best_potions)
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
