from dataclasses import dataclass


@dataclass(frozen=True)
class Combo:
    ingredient_ids: tuple[str, ...]   # 2 or 3 ids, sorted
    effect_ids: tuple[str, ...]       # every effect this mix produces, sorted


@dataclass(frozen=True)
class EffectResult:
    effect_id: str
    ingredient_ids: tuple[str, ...]   # the >=2 mix members sharing it, sorted


@dataclass(frozen=True)
class PlannedBrew:
    ingredient_ids: tuple[str, ...]
    newly_discovered: tuple[tuple[str, int], ...]  # (ingredient_id, slot 0-3)
