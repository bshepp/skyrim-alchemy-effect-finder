import json
from dataclasses import dataclass
from pathlib import Path
from alchemy_helper.data.models import Effect, Ingredient


class DatasetError(Exception):
    """Raised when dataset validation fails."""
    pass


@dataclass(frozen=True)
class Dataset:
    effects: dict[str, Effect]          # keyed by id
    ingredients: dict[str, Ingredient]  # keyed by id


def load_dataset(data_dir: Path | None = None) -> Dataset:
    """Load and validate effects and ingredients from JSON files.

    Args:
        data_dir: Directory containing effects.json and ingredients.json.
                 Defaults to the data package directory.

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

    return Dataset(effects=effects_dict, ingredients=ingredients_dict)
