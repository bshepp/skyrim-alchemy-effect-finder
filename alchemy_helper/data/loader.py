import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from alchemy_helper.data.models import Effect, Ingredient, Pack


class DatasetError(Exception):
    """Raised when dataset validation fails."""
    pass


@dataclass(frozen=True)
class Dataset:
    effects: dict[str, Effect]          # keyed by id
    ingredients: dict[str, Ingredient]  # keyed by id


PACK_MODES = ("extend", "overhaul")


def load_dataset(data_dir: Path | None = None,
                 packs: Sequence[str] = ()) -> Dataset:
    """Load and validate effects and ingredients from JSON files.

    Args:
        data_dir: Directory containing effects.json and ingredients.json.
                 Defaults to the data package directory.
        packs: Ids of dataset packs (from data_dir/packs/) to merge in,
               applied in the order given. Extend-mode packs may only add
               records; overhaul-mode packs may also replace base records.

    Returns:
        A validated Dataset with effects and ingredients.

    Raises:
        DatasetError: If validation fails, with the offending id mentioned.
    """
    if data_dir is None:
        data_dir = Path(__file__).parent

    # Load JSON files
    effects_text = (data_dir / "effects.json").read_text(encoding="utf-8")
    ingredients_text = (data_dir / "ingredients.json").read_text(encoding="utf-8")

    effects_data = json.loads(effects_text)
    ingredients_data = json.loads(ingredients_text)

    # Build effects dict
    effects_dict: dict[str, Effect] = {}
    seen_effect_ids: set[str] = set()

    for effect_data in effects_data:
        effect_id = effect_data["id"]

        # Check for duplicate effect ids
        if effect_id in seen_effect_ids:
            raise DatasetError(f"Duplicate effect id: {effect_id}")
        seen_effect_ids.add(effect_id)

        effect = Effect(
            id=effect_id,
            name=effect_data["name"],
            description=effect_data["description"],
            harmful=effect_data["harmful"]
        )
        effects_dict[effect_id] = effect

    # Build ingredients dict
    ingredients_dict: dict[str, Ingredient] = {}
    seen_ingredient_ids: set[str] = set()

    for ingredient_data in ingredients_data:
        ingredient_id = ingredient_data["id"]

        # Check for duplicate ingredient ids
        if ingredient_id in seen_ingredient_ids:
            raise DatasetError(f"Duplicate ingredient id: {ingredient_id}")
        seen_ingredient_ids.add(ingredient_id)

        # Validate plugin is non-empty
        plugin = ingredient_data["plugin"]
        if not plugin:
            raise DatasetError(f"Empty plugin for ingredient: {ingredient_id}")

        # Validate form_id >= 0
        form_id = ingredient_data["form_id"]
        if form_id < 0:
            raise DatasetError(f"Negative form_id for ingredient: {ingredient_id}")

        # Validate effects count is exactly 4
        effects_list = ingredient_data["effects"]
        if len(effects_list) != 4:
            raise DatasetError(f"Ingredient {ingredient_id} has {len(effects_list)} effects, expected 4")

        # Validate all effect refs exist
        for effect_id in effects_list:
            if effect_id not in effects_dict:
                raise DatasetError(f"Unknown effect reference: {effect_id}")

        # Create Ingredient with effects as tuple
        ingredient = Ingredient(
            id=ingredient_id,
            name=ingredient_data["name"],
            plugin=plugin,
            form_id=form_id,
            effects=tuple(effects_list)  # type: ignore
        )
        ingredients_dict[ingredient_id] = ingredient

    if packs:
        available = load_packs(data_dir)
        for pack_id in packs:
            if pack_id not in available:
                raise DatasetError(f"Unknown pack: {pack_id}")
            pack = available[pack_id]
            for effect in pack.effects:
                if effect.id in effects_dict:
                    raise DatasetError(
                        f"Pack {pack_id} redefines effect: {effect.id}")
                effects_dict[effect.id] = effect
            for ingredient in pack.ingredients:
                if ingredient.id in ingredients_dict and pack.mode == "extend":
                    raise DatasetError(
                        f"Pack {pack_id} collides with existing ingredient: "
                        f"{ingredient.id}")
                for effect_id in ingredient.effects:
                    if effect_id not in effects_dict:
                        raise DatasetError(
                            f"Unknown effect reference: {effect_id}")
                ingredients_dict[ingredient.id] = ingredient

    return Dataset(effects=effects_dict, ingredients=ingredients_dict)


def load_packs(data_dir: Path | None = None) -> dict[str, Pack]:
    """Load and validate every dataset pack in data_dir/packs/.

    Returns an empty dict if the packs directory does not exist. Effect
    references are NOT resolved here - they are validated against the
    merged effect table when a pack is applied in load_dataset().
    """
    if data_dir is None:
        data_dir = Path(__file__).parent
    packs_dir = data_dir / "packs"
    packs: dict[str, Pack] = {}
    if not packs_dir.is_dir():
        return packs

    for path in sorted(packs_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        pack_id = data["id"]
        if pack_id in packs:
            raise DatasetError(f"Duplicate pack id: {pack_id}")
        if data["mode"] not in PACK_MODES:
            raise DatasetError(
                f"Pack {pack_id} has unknown mode: {data['mode']}")
        plugins = tuple(data["plugins"])
        if not plugins or not all(plugins):
            raise DatasetError(
                f"Pack {pack_id} must list at least one plugin")

        effects = tuple(
            Effect(id=e["id"], name=e["name"],
                   description=e["description"], harmful=e["harmful"])
            for e in data.get("effects", []))

        ingredients = []
        seen_ids: set[str] = set()
        for ing in data["ingredients"]:
            ingredient_id = ing["id"]
            if ingredient_id in seen_ids:
                raise DatasetError(
                    f"Pack {pack_id} duplicates ingredient: {ingredient_id}")
            seen_ids.add(ingredient_id)
            if not ing["plugin"]:
                raise DatasetError(
                    f"Empty plugin for ingredient: {ingredient_id}")
            if ing["form_id"] < 0:
                raise DatasetError(
                    f"Negative form_id for ingredient: {ingredient_id}")
            if len(ing["effects"]) != 4:
                raise DatasetError(
                    f"Ingredient {ingredient_id} has {len(ing['effects'])} "
                    f"effects, expected 4")
            ingredients.append(Ingredient(
                id=ingredient_id, name=ing["name"], plugin=ing["plugin"],
                form_id=ing["form_id"], effects=tuple(ing["effects"])))

        packs[pack_id] = Pack(
            id=pack_id, name=data["name"], plugins=plugins,
            mode=data["mode"], effects=effects,
            ingredients=tuple(ingredients))
    return packs


def packs_for_plugins(packs: Iterable[Pack],
                      plugins: Iterable[str]) -> list[Pack]:
    """The packs a save activates: those whose any plugin appears in the
    save's load order (case-insensitive), sorted by pack id."""
    present = {p.lower() for p in plugins}
    return sorted(
        (pk for pk in packs
         if any(pl.lower() in present for pl in pk.plugins)),
        key=lambda pk: pk.id)
