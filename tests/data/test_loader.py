import json, pytest
from pathlib import Path
from alchemy_helper.data.loader import load_dataset, DatasetError

GOOD_EFFECTS = [
    {"id": "e1", "name": "E1", "description": "d", "harmful": False},
    {"id": "e2", "name": "E2", "description": "d", "harmful": True},
    {"id": "e3", "name": "E3", "description": "d", "harmful": False},
    {"id": "e4", "name": "E4", "description": "d", "harmful": False},
]
GOOD_INGREDIENTS = [
    {"id": "a", "name": "A", "plugin": "Skyrim.esm", "form_id": 1,
     "effects": ["e1", "e2", "e3", "e4"]},
]

def write(tmp_path: Path, effects, ingredients) -> Path:
    (tmp_path / "effects.json").write_text(json.dumps(effects))
    (tmp_path / "ingredients.json").write_text(json.dumps(ingredients))
    return tmp_path

def test_loads_valid_dataset(tmp_path):
    ds = load_dataset(write(tmp_path, GOOD_EFFECTS, GOOD_INGREDIENTS))
    assert ds.ingredients["a"].effects == ("e1", "e2", "e3", "e4")
    assert ds.effects["e2"].harmful is True

def test_rejects_wrong_effect_count(tmp_path):
    bad = [dict(GOOD_INGREDIENTS[0], effects=["e1", "e2", "e3"])]
    with pytest.raises(DatasetError, match="a"):
        load_dataset(write(tmp_path, GOOD_EFFECTS, bad))

def test_rejects_unknown_effect_ref(tmp_path):
    bad = [dict(GOOD_INGREDIENTS[0], effects=["e1", "e2", "e3", "nope"])]
    with pytest.raises(DatasetError, match="nope"):
        load_dataset(write(tmp_path, GOOD_EFFECTS, bad))

def test_rejects_duplicate_ids(tmp_path):
    with pytest.raises(DatasetError, match="a"):
        load_dataset(write(tmp_path, GOOD_EFFECTS, GOOD_INGREDIENTS * 2))
