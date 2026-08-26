"""The combinatorics behind the app: what a mix produces, and what to brew next.

Skyrim's brewing rule, which everything here derives from: a potion is made
from 2 or 3 distinct ingredients, and it produces every effect that at least
two of them share. A mix sharing nothing fails (the game refuses the brew).
Brewing a successful potion reveals, on every participating ingredient, each
produced effect that ingredient has.
"""
import heapq
from collections.abc import Sequence, Mapping
from itertools import combinations
from typing import AbstractSet

from alchemy_helper.data.models import Ingredient
from alchemy_helper.combinatorics.types import Combo, EffectResult, PlannedBrew


def _produced(mix: Sequence[Ingredient]) -> list[EffectResult]:
    """Effects a mix of distinct ingredients produces: those shared by >= 2."""
    sharers: dict[str, list[str]] = {}
    for ingredient in mix:
        for effect_id in ingredient.effects:
            sharers.setdefault(effect_id, []).append(ingredient.id)
    return [EffectResult(effect_id=effect_id, ingredient_ids=tuple(sorted(ids)))
            for effect_id, ids in sorted(sharers.items()) if len(ids) >= 2]


def combos_for_effect(effect_id: str, ingredients: Sequence[Ingredient],
                      inventory: Mapping[str, int] | None = None) -> list[Combo]:
    """Every 2- or 3-ingredient combination producing effect_id.
    inventory=None → all ingredients; else only ids with count >= 1."""
    pool = {i.id: i for i in ingredients
            if inventory is None or inventory.get(i.id, 0) >= 1}
    # A combo produces the effect iff it contains two ingredients having it,
    # so every valid combo is a having-pair, or a having-pair plus any third.
    havers = sorted(i.id for i in pool.values() if effect_id in i.effects)
    haver_pairs = list(combinations(havers, 2))
    combo_ids = set(haver_pairs)
    for pair in haver_pairs:
        for third in pool:
            if third not in pair:
                combo_ids.add(tuple(sorted((*pair, third))))
    return [Combo(ingredient_ids=ids,
                  effect_ids=tuple(r.effect_id
                                   for r in _produced([pool[i] for i in ids])))
            for ids in sorted(combo_ids, key=lambda ids: (len(ids), ids))]


def potion_effects(ingredient_ids: Sequence[str],
                   ingredients: Sequence[Ingredient]) -> list[EffectResult]:
    """Effects of mixing 2-3 ingredients: an effect appears iff >=2 share it.
    Empty list = mix produces nothing (game refuses the brew)."""
    by_id = {i.id: i for i in ingredients}
    return _produced([by_id[iid] for iid in ingredient_ids])


def best_potions(ingredients: Sequence[Ingredient],
                 inventory: Mapping[str, int],
                 limit: int = 50) -> list[Combo]:
    """Craftable 2-3 ingredient mixes from inventory (count >= 1), ranked by
    how many effects each produces — the Phase-1 proxy for potion worth and
    alchemy XP (real magnitude/gold math is a Phase 2+ idea). Ties: fewer
    ingredients, then lexicographic. Failed mixes are excluded; at most
    `limit` are returned."""
    pool = {i.id: i for i in ingredients if inventory.get(i.id, 0) >= 1}
    ranked = []
    for size in (2, 3):
        for ids in combinations(sorted(pool), size):
            effect_ids = tuple(r.effect_id
                               for r in _produced([pool[i] for i in ids]))
            if effect_ids:
                ranked.append(Combo(ingredient_ids=ids, effect_ids=effect_ids))
    ranked.sort(key=lambda c: (-len(c.effect_ids), len(c.ingredient_ids),
                               c.ingredient_ids))
    return ranked[:limit]


def discovery_plan(ingredients: Sequence[Ingredient],
                   inventory: Mapping[str, int],
                   known_effects: Mapping[str, AbstractSet[int]]) -> list[PlannedBrew]:
    """Brews discovering EVERY effect reachable from inventory, in as few brews
    as possible (coverage is the hard objective, count the tiebreaker).
    Each brew consumes 1 of each used ingredient; brewing reveals each matched
    effect on every participating ingredient having it.

    Greedy: each round brews the mix revealing the most still-unknown slots
    (ties: fewer ingredients, then lexicographic), until no mix reveals
    anything. Optimal brew count is set cover (NP-hard); greedy's larger
    reveals-per-brew is exactly what makes it also stop before wasting the
    stock a rarer reveal still needs.

    Lazy evaluation: a mix's reveal count only ever DECREASES as knowledge
    grows and stock shrinks, so scores cached in a heap are upper bounds.
    Pop the best, re-score it; unchanged means it is still the exact global
    best (keys are unique — they end in the ids tuple), so one full scan up
    front replaces a full re-scan per brew.
    """
    by_id = {i.id: i for i in ingredients}
    stock = {iid: n for iid, n in inventory.items() if iid in by_id and n >= 1}
    known = {iid: set(known_effects.get(iid, ())) for iid in stock}

    def reveals(ids: tuple[str, ...]) -> list[tuple[str, int]]:
        return [(iid, by_id[iid].effects.index(r.effect_id))
                for r in _produced([by_id[i] for i in ids])
                for iid in r.ingredient_ids
                if by_id[iid].effects.index(r.effect_id) not in known[iid]]

    avail = sorted(stock)
    heap = []
    for size in (2, 3):
        for ids in combinations(avail, size):
            newly = reveals(ids)
            if newly:
                heap.append(((-len(newly), len(ids), ids), ids))
    heapq.heapify(heap)

    plan = []
    while heap:
        cached_key, ids = heapq.heappop(heap)
        if any(stock[iid] < 1 for iid in ids):
            continue                      # stock never refills: gone for good
        newly = reveals(ids)
        if not newly:
            continue                      # reveal counts never grow back
        fresh_key = (-len(newly), len(ids), ids)
        if fresh_key != cached_key:
            heapq.heappush(heap, (fresh_key, ids))
            continue
        plan.append(PlannedBrew(ingredient_ids=ids,
                                newly_discovered=tuple(sorted(newly))))
        for iid, slot in newly:
            known[iid].add(slot)
        for iid in ids:
            stock[iid] -= 1
    return plan
