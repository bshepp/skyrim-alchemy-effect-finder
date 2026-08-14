"""FastAPI application wiring together dataset, save parser, app state and
combinatorics for the alchemy helper web UI.

`create_app` takes every external path as an injectable argument so tests
never touch the real home directory or real Skyrim saves.
"""
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from alchemy_helper.combinatorics.core import (combos_for_effect,
                                                discovery_plan,
                                                potion_effects)
from alchemy_helper.data.loader import load_dataset
from alchemy_helper.saveparser.api import SaveFormatError, parse_save
from alchemy_helper.state import AppState, Overrides
from alchemy_helper.web.saves import default_saves_dir, list_saves

STATIC_DIR = Path(__file__).parent / "static"

class LoadSaveRequest(BaseModel):
    path: str


class OverrideRequest(BaseModel):
    ingredient_id: str
    have: int | None = None
    known_slots: list[int] | None = None


class PotionRequest(BaseModel):
    ingredient_ids: list[str]


def _jsonable(value: Any) -> Any:
    """Recursively convert dataclasses/sets/frozensets/tuples into plain
    JSON-friendly structures. Sets and frozensets become sorted lists."""
    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def create_app(data_dir: Path | None = None,
               overrides_path: Path | None = None,
               saves_dir: Path | None = None) -> FastAPI:
    """Build the FastAPI application.

    Args:
        data_dir: Directory containing effects.json/ingredients.json;
            defaults to the bundled dataset.
        overrides_path: Where manual overrides persist; defaults to
            ``Path.home()/".skyrim_alchemy_helper"/"overrides.json"``.
        saves_dir: Directory to scan for .ess saves; if None, falls back
            to autodetection via `default_saves_dir`.
    """
    if overrides_path is None:
        overrides_path = Path.home() / ".skyrim_alchemy_helper" / "overrides.json"
    if saves_dir is None:
        saves_dir = default_saves_dir()

    dataset = load_dataset(data_dir)
    overrides = Overrides(overrides_path)
    state = AppState(dataset=dataset, player=None, overrides=overrides, last_error=None)

    app = FastAPI(title="Skyrim Alchemy Helper")

    def state_payload() -> dict:
        known_effects = {
            ingredient_id: sorted(slots)
            for ingredient_id, slots in state.effective_known().items()
        }
        return {
            "mode": state.mode(),
            "character": state.player.character_name if state.player else None,
            "error": state.last_error,
            "save_path": state.player.save_path if state.player else None,
            "inventory": state.effective_inventory(),
            "known_effects": known_effects,
            "unknown_forms": [_jsonable(f) for f in state.player.unknown_forms] if state.player else [],
            "overrides": {
                "have": dict(state.overrides.have),
                "known": {k: sorted(v) for k, v in state.overrides.known.items()},
            },
        }

    @app.get("/api/effects")
    def get_effects():
        return [_jsonable(effect) for effect in dataset.effects.values()]

    @app.get("/api/ingredients")
    def get_ingredients():
        return [_jsonable(ingredient) for ingredient in dataset.ingredients.values()]

    @app.get("/api/saves")
    def get_saves():
        if saves_dir is None:
            return []
        return list_saves(saves_dir)

    @app.post("/api/load-save")
    def load_save(req: LoadSaveRequest):
        try:
            player = parse_save(Path(req.path), dataset)
        except SaveFormatError as exc:
            state.player = None
            state.last_error = str(exc)
            return state_payload()
        state.player = player
        state.last_error = None
        return state_payload()

    @app.get("/api/state")
    def get_state():
        return state_payload()

    @app.post("/api/override")
    def post_override(req: OverrideRequest):
        if req.ingredient_id not in dataset.ingredients:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown ingredient id: {req.ingredient_id!r}")

        fields_set = req.model_fields_set

        if "have" in fields_set and req.have is not None and req.have < 0:
            raise HTTPException(
                status_code=422,
                detail=f"have must be >= 0, got {req.have}")

        if "known_slots" in fields_set and req.known_slots is not None:
            bad_slots = [s for s in req.known_slots if not (0 <= s <= 3)]
            if bad_slots:
                raise HTTPException(
                    status_code=422,
                    detail=f"known_slots must be within 0..3, got {bad_slots}")

        # Only touch fields the client actually sent -- omitted fields must
        # leave the sibling override untouched; a field sent as explicit
        # null is a deliberate clear (Overrides treats None as "clear").
        if "have" in fields_set:
            state.overrides.set_have(req.ingredient_id, req.have)

        if "known_slots" in fields_set:
            known = set(req.known_slots) if req.known_slots is not None else None
            state.overrides.set_known(req.ingredient_id, known)

        state.overrides.save()
        return state_payload()

    @app.get("/api/combos")
    def get_combos(effect: str, only_inventory: bool = False):
        inventory = state.effective_inventory() if only_inventory else None
        combos = combos_for_effect(
            effect, list(dataset.ingredients.values()), inventory)
        return {"combos": [_jsonable(combo) for combo in combos]}

    @app.post("/api/potion")
    def post_potion(req: PotionRequest):
        ids = req.ingredient_ids
        if not 2 <= len(ids) <= 3 or len(set(ids)) != len(ids):
            raise HTTPException(422, "a potion mixes 2 or 3 distinct ingredients")
        unknown = sorted(set(ids) - set(dataset.ingredients))
        if unknown:
            raise HTTPException(422, f"unknown ingredient ids: {unknown}")
        effects = potion_effects(ids, list(dataset.ingredients.values()))
        return {"effects": [_jsonable(effect) for effect in effects]}

    @app.get("/api/discovery-plan")
    def get_discovery_plan():
        plan = discovery_plan(
            list(dataset.ingredients.values()),
            state.effective_inventory(),
            state.effective_known(),
        )
        return {"plan": [_jsonable(brew) for brew in plan]}

    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app
