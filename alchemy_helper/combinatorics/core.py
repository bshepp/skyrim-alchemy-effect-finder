from collections.abc import Sequence, Mapping
from typing import AbstractSet

from alchemy_helper.data.models import Ingredient
from alchemy_helper.combinatorics.types import Combo, EffectResult, PlannedBrew


def combos_for_effect(effect_id: str, ingredients: Sequence[Ingredient],
                      inventory: Mapping[str, int] | None = None) -> list[Combo]:
    """Every 2- or 3-ingredient combination producing effect_id.
    inventory=None → all ingredients; else only ids with count >= 1."""
    raise NotImplementedError


def potion_effects(ingredient_ids: Sequence[str],
                   ingredients: Sequence[Ingredient]) -> list[EffectResult]:
    """Effects of mixing 2-3 ingredients: an effect appears iff >=2 share it.
    Empty list = mix produces nothing (game refuses the brew)."""
    raise NotImplementedError


def discovery_plan(ingredients: Sequence[Ingredient],
                   inventory: Mapping[str, int],
                   known_effects: Mapping[str, AbstractSet[int]]) -> list[PlannedBrew]:
    """Brews discovering EVERY effect reachable from inventory, in as few brews
    as possible (coverage is the hard objective, count the tiebreaker).
    Each brew consumes 1 of each used ingredient; brewing reveals each matched
    effect on every participating ingredient having it."""
    raise NotImplementedError
