"""Dataset packs: mod-added ingredients as data, not code.

A pack is a JSON file in data/packs/ carrying new ingredient records
(extend mode - Creations, Bruma, Hunterborn) or a mix of replaced and
new records (overhaul mode - CACO, Apothecary). Packs are activated by
the plugins present in the save's own load order.
"""
import json

import pytest

from alchemy_helper.data.loader import (
    DatasetError,
    load_dataset,
    load_packs,
    packs_for_plugins,
)

BASE_EFFECTS = [
    {"id": "restore-health", "name": "Restore Health",
     "description": "Heals.", "harmful": False},
    {"id": "damage-magicka", "name": "Damage Magicka",
     "description": "Hurts.", "harmful": True},
    {"id": "resist-frost", "name": "Resist Frost",
     "description": "Warms.", "harmful": False},
    {"id": "invisibility", "name": "Invisibility",
     "description": "Hides.", "harmful": False},
]
BASE_INGREDIENTS = [
    {"id": "wheat", "name": "Wheat", "plugin": "Skyrim.esm", "form_id": 1,
     "effects": ["restore-health", "damage-magicka", "resist-frost",
                 "invisibility"]},
    {"id": "garlic", "name": "Garlic", "plugin": "Skyrim.esm", "form_id": 2,
     "effects": ["resist-frost", "invisibility", "restore-health",
                 "damage-magicka"]},
]


def write_base(data_dir):
    (data_dir / "effects.json").write_text(json.dumps(BASE_EFFECTS))
    (data_dir / "ingredients.json").write_text(json.dumps(BASE_INGREDIENTS))


def write_pack(data_dir, filename, pack):
    packs_dir = data_dir / "packs"
    packs_dir.mkdir(exist_ok=True)
    (packs_dir / filename).write_text(json.dumps(pack))


EXTEND_PACK = {
    "id": "test-cause", "name": "The Test Cause",
    "plugins": ["ccTEST001-Cause.esl"], "mode": "extend",
    "effects": [{"id": "burden", "name": "Burden",
                 "description": "Weighs.", "harmful": True}],
    "ingredients": [
        {"id": "bloodgrass", "name": "Bloodgrass",
         "plugin": "ccTEST001-Cause.esl", "form_id": 2049,
         "effects": ["burden", "restore-health", "resist-frost",
                     "invisibility"]},
    ],
}
OVERHAUL_PACK = {
    "id": "test-overhaul", "name": "Test Overhaul",
    "plugins": ["TestOverhaul.esp", "TestOverhaul_Patch.esp"],
    "mode": "overhaul",
    "effects": [],
    "ingredients": [
        {"id": "wheat", "name": "Wheat", "plugin": "Skyrim.esm",
         "form_id": 1,
         "effects": ["damage-magicka", "restore-health", "invisibility",
                     "resist-frost"]},
        {"id": "chaurus-jelly", "name": "Chaurus Jelly",
         "plugin": "TestOverhaul.esp", "form_id": 77,
         "effects": ["restore-health", "damage-magicka", "resist-frost",
                     "invisibility"]},
    ],
}


def test_no_packs_is_unchanged(tmp_path):
    write_base(tmp_path)
    write_pack(tmp_path, "extend.json", EXTEND_PACK)
    ds = load_dataset(tmp_path)
    assert set(ds.ingredients) == {"wheat", "garlic"}
    assert set(ds.effects) == {e["id"] for e in BASE_EFFECTS}


def test_extend_pack_adds(tmp_path):
    write_base(tmp_path)
    write_pack(tmp_path, "extend.json", EXTEND_PACK)
    ds = load_dataset(tmp_path, packs=["test-cause"])
    assert "bloodgrass" in ds.ingredients
    assert "burden" in ds.effects
    assert ds.ingredients["bloodgrass"].plugin == "ccTEST001-Cause.esl"
    assert set(ds.ingredients) == {"wheat", "garlic", "bloodgrass"}


def test_extend_collision_errors(tmp_path):
    write_base(tmp_path)
    clash = dict(EXTEND_PACK, ingredients=[
        dict(EXTEND_PACK["ingredients"][0], id="wheat")])
    write_pack(tmp_path, "extend.json", clash)
    with pytest.raises(DatasetError, match="wheat"):
        load_dataset(tmp_path, packs=["test-cause"])


def test_overhaul_replaces_and_adds(tmp_path):
    write_base(tmp_path)
    write_pack(tmp_path, "overhaul.json", OVERHAUL_PACK)
    ds = load_dataset(tmp_path, packs=["test-overhaul"])
    assert ds.ingredients["wheat"].effects[0] == "damage-magicka"
    assert "chaurus-jelly" in ds.ingredients
    assert set(ds.ingredients) == {"wheat", "garlic", "chaurus-jelly"}


def test_unknown_pack_errors(tmp_path):
    write_base(tmp_path)
    with pytest.raises(DatasetError, match="no-such-pack"):
        load_dataset(tmp_path, packs=["no-such-pack"])


def test_bad_effect_ref_errors(tmp_path):
    write_base(tmp_path)
    broken = dict(EXTEND_PACK, ingredients=[
        dict(EXTEND_PACK["ingredients"][0],
             effects=["nope", "restore-health", "resist-frost",
                      "invisibility"])])
    write_pack(tmp_path, "extend.json", broken)
    with pytest.raises(DatasetError, match="nope"):
        load_dataset(tmp_path, packs=["test-cause"])


def test_pack_effect_redefinition_errors(tmp_path):
    write_base(tmp_path)
    clash = dict(EXTEND_PACK, effects=[
        {"id": "restore-health", "name": "Restore Health",
         "description": "Again.", "harmful": False}])
    write_pack(tmp_path, "extend.json", clash)
    with pytest.raises(DatasetError, match="restore-health"):
        load_dataset(tmp_path, packs=["test-cause"])


def test_wrong_effect_count_errors(tmp_path):
    write_base(tmp_path)
    short = dict(EXTEND_PACK, ingredients=[
        dict(EXTEND_PACK["ingredients"][0],
             effects=["restore-health", "resist-frost", "invisibility"])])
    write_pack(tmp_path, "extend.json", short)
    with pytest.raises(DatasetError, match="bloodgrass"):
        load_packs(tmp_path)


def test_load_packs_missing_dir_is_empty(tmp_path):
    write_base(tmp_path)
    assert load_packs(tmp_path) == {}


def test_real_the_cause_pack():
    """The shipped pack: three Deadlands plants, real UESP data."""
    base = load_dataset()
    ds = load_dataset(packs=["the-cause"])
    assert len(ds.ingredients) == len(base.ingredients) + 3
    blood = ds.ingredients["bloodgrass"]
    assert blood.plugin == "ccbgssse067-daedinv.esm"
    assert blood.form_id == 0x024C13
    assert blood.effects == ("invisibility", "resist-poison", "slow",
                             "fortify-health")
    assert ds.ingredients["harrada"].form_id == 0x024C11
    assert ds.ingredients["spiddal-stick"].form_id == 0x024C15
    packs = load_packs()
    active = packs_for_plugins(
        packs.values(),
        ["Skyrim.esm", "Update.esm", "ccBGSSSE067-DaedInv.esm"])
    assert [p.id for p in active] == ["the-cause"]


def test_real_caco_pack():
    """The extracted CACO 3.0.1 pack: overhaul mode at full scale."""
    ds = load_dataset(packs=["caco"])
    assert len(ds.ingredients) == 358
    assert len(ds.effects) == 74
    # CACO remaps wheat's third and fourth effects
    assert ds.ingredients["wheat"].effects == (
        "restore-health", "fortify-health", "damage-magicka-regen",
        "damage-stamina-regen")
    # records injected into vanilla masters keep the master's identity
    assert ds.ingredients["argonian-scales"].plugin == "Update.esm"
    packs = load_packs()
    active = packs_for_plugins(
        packs.values(),
        ["Skyrim.esm", "complete alchemy & cooking overhaul.esp"])
    assert [p.id for p in active] == ["caco"]


def test_real_bruma_pack():
    """The extracted Beyond Skyrim: Bruma pack: extend mode, merged from
    BSAssets.esm (92 shared ingredients) + BSHeartland.esm (33 local
    ones; the three single-effect Mountain Berries are deliberately not
    modelled)."""
    ds = load_dataset(packs=["bruma"])
    assert len(ds.ingredients) == 305          # 180 vanilla + 125
    assert len(ds.effects) == 81               # 60 vanilla + 21 new
    # pure extension: no vanilla record may change
    base = load_dataset()
    for iid, ing in base.ingredients.items():
        assert ds.ingredients[iid].effects == ing.effects
    # a Cyrodiil classic carries a genuinely new effect
    assert "fire-damage" in {e for i in ds.ingredients.values()
                             for e in i.effects if i.plugin == "BSAssets.esm"}
    # Viper's Bugloss slot 1 is vanilla's AlchUnknown placeholder -
    # degree 1, so it can never be brewed; kept because it is what the
    # game data really says (verify in-game by eating one)
    assert ds.ingredients["viper-s-bugloss"].effects[0] == "unknown"
    packs = load_packs()
    active = packs_for_plugins(
        packs.values(), ["Skyrim.esm", "BSAssets.esm", "BSHeartland.esm"])
    assert [p.id for p in active] == ["bruma"]


def test_caco_and_the_cause_together():
    ds = load_dataset(packs=["caco", "the-cause"])
    assert len(ds.ingredients) == 361
    assert ds.ingredients["bloodgrass"].effects[0] == "invisibility"
    assert ds.ingredients["garlic"].effects == (
        "resist-disease", "regenerate-stamina", "regenerate-health",
        "regenerate-magicka")


def test_packs_for_plugins_matches_case_insensitively(tmp_path):
    write_base(tmp_path)
    write_pack(tmp_path, "extend.json", EXTEND_PACK)
    write_pack(tmp_path, "overhaul.json", OVERHAUL_PACK)
    packs = load_packs(tmp_path)
    save_plugins = ["Skyrim.esm", "Update.esm", "CCTEST001-CAUSE.ESL"]
    active = packs_for_plugins(packs.values(), save_plugins)
    assert [p.id for p in active] == ["test-cause"]
    both = packs_for_plugins(
        packs.values(), save_plugins + ["testoverhaul_patch.esp"])
    assert [p.id for p in both] == ["test-cause", "test-overhaul"]
    assert packs_for_plugins(packs.values(), ["Skyrim.esm"]) == []
