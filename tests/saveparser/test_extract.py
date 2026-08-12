"""Ground-truth tests for save extraction.

The pinned values come from tests/fixtures/FACTS.md -- counts and known
effects the user read out of the running game -- NOT from what this
parser happens to produce. Effect NAMES are mapped to slot indexes
through the shipped dataset's own slot order (never hard-coded
positions), so the pins stay meaningful if the dataset is ever
reordered.
"""
import struct
from pathlib import Path

import pytest

from alchemy_helper.data.loader import load_dataset
from alchemy_helper.saveparser.api import PlayerState, UnknownForm, parse_save
from alchemy_helper.saveparser.body import PluginList
from alchemy_helper.saveparser.changeforms import ChangeForm
from alchemy_helper.saveparser.extract import (
    CHANGE_INGREDIENT_USE, build_ingredient_lookup, decode_form_id,
    parse_known_effect_slots, resolve_ref_id)
from alchemy_helper.saveparser.header import SaveFormatError

FIXTURE = Path(__file__).parent.parent / "fixtures" / "player.ess"


@pytest.fixture(scope="module")
def dataset():
    return load_dataset()


@pytest.fixture(scope="module")
def state(dataset):
    return parse_save(FIXTURE, dataset)


def slots(dataset, ingredient_id: str, *effect_ids: str) -> frozenset[int]:
    """The dataset slot indexes holding the named effects."""
    order = dataset.ingredients[ingredient_id].effects
    return frozenset(order.index(effect_id) for effect_id in effect_ids)


def test_identifies_the_character_and_save(state):
    # FACTS.md: character "Maldric Vane"; save number from the header.
    assert isinstance(state, PlayerState)
    assert state.character_name == "Maldric Vane"
    assert state.save_number == 40
    assert state.save_path == str(FIXTURE)


def test_inventory_matches_the_counts_the_user_read_in_game(state):
    # FACTS.md "In-game inventory counts", reported 2026-08-11.
    assert state.inventory["bee"] == 12
    assert state.inventory["garlic"] == 30
    assert state.inventory["wheat"] == 22


def test_inventory_only_contains_carried_ingredients(state, dataset):
    assert state.inventory, "expected a non-empty inventory"
    assert set(state.inventory) <= set(dataset.ingredients)
    assert all(count > 0 for count in state.inventory.values())
    # Parser-derived structural pin: this save carries 90 distinct
    # ingredients out of the 179 in the dataset. A brute-force refID
    # scan of the same change form claims 94 -- the four extras
    # (aster-bloom-core, void-essence, scalon-fin, scrib-jelly) are
    # byte coincidences that the structured walk correctly rejects.
    assert len(state.inventory) == 90


def test_known_effects_match_what_the_user_sees_in_the_alchemy_menu(state, dataset):
    # FACTS.md "Known (discovered) effects", reported 2026-08-11:
    #   Wheat: "restore health, fortify health" revealed, other two hidden.
    #   Garlic: "Resist Poison, Regenerate Health" revealed, other two hidden.
    assert state.known_effects["wheat"] == slots(
        dataset, "wheat", "restore-health", "fortify-health")
    assert state.known_effects["garlic"] == slots(
        dataset, "garlic", "resist-poison", "regenerate-health")


def test_bee_has_no_discovered_effects(state):
    # NOT user-confirmed. FACTS.md protocol: pin the parser-derived value
    # and present it for confirmation against the in-game alchemy view.
    # The save contains no ingredient-use change form for Bee at all,
    # which is how the game records "nothing discovered yet".
    assert state.known_effects.get("bee", frozenset()) == frozenset()


def test_known_effects_cover_only_discovered_ingredients(state, dataset):
    assert set(state.known_effects) <= set(dataset.ingredients)
    # Parser-derived structural pin: 31 ingredient-use change forms, and
    # every one of them records at least one discovered effect.
    assert len(state.known_effects) == 31
    for ingredient_id, discovered in state.known_effects.items():
        assert discovered, f"{ingredient_id} recorded with no slots"
        assert discovered <= {0, 1, 2, 3}


def test_unknown_forms_are_collected_not_fatal(state):
    # Vanilla + Creations save: every ingredient-use form in it resolves
    # to a dataset ingredient, so nothing is left over. Pinned as the
    # observed value; the type exists so a modded save degrades into a
    # report instead of an exception.
    assert isinstance(state.unknown_forms, tuple)
    assert all(isinstance(form, UnknownForm) for form in state.unknown_forms)
    assert state.unknown_forms == ()


def test_truncated_body_raises_save_format_error_with_diagnostics(tmp_path, dataset):
    # Cut after the header so the version is already known: the
    # diagnostics must carry it plus the failing step.
    truncated = tmp_path / "truncated.ess"
    truncated.write_bytes(FIXTURE.read_bytes()[:1_000_000])
    with pytest.raises(SaveFormatError) as excinfo:
        parse_save(truncated, dataset)
    message = str(excinfo.value)
    assert "save version 12" in message
    assert "truncated.ess" in message
    assert "step" in message.lower()


def test_truncation_inside_the_header_still_names_the_failing_step(tmp_path, dataset):
    truncated = tmp_path / "stub.ess"
    truncated.write_bytes(FIXTURE.read_bytes()[:200_000])
    with pytest.raises(SaveFormatError) as excinfo:
        parse_save(truncated, dataset)
    message = str(excinfo.value)
    assert "parsing the header" in message
    assert "save version unknown" in message


def test_garbage_file_raises_save_format_error(tmp_path, dataset):
    junk = tmp_path / "junk.ess"
    junk.write_bytes(b"not a skyrim save at all" * 100)
    with pytest.raises(SaveFormatError):
        parse_save(junk, dataset)


def test_missing_file_raises_save_format_error(tmp_path, dataset):
    with pytest.raises(SaveFormatError) as excinfo:
        parse_save(tmp_path / "nope.ess", dataset)
    assert "nope.ess" in str(excinfo.value)


# --- the bit-level rules, exercised without the fixture -------------------

def test_ref_ids_resolve_by_type():
    array = (0x0A00_0001, 0x0B00_0002, 0x0C00_0003)
    # type 0 indexes the form id array, 1-based; 0 means form 0.
    assert resolve_ref_id(0, 1, array) == 0x0A000001
    assert resolve_ref_id(0, 3, array) == 0x0C000003
    assert resolve_ref_id(0, 0, array) == 0
    assert resolve_ref_id(0, 4, array) is None      # past the end
    # type 1 is the formID itself, type 2 is a created form.
    assert resolve_ref_id(1, 0x14, array) == 0x14
    assert resolve_ref_id(2, 0x1234, array) == 0xFF001234
    assert resolve_ref_id(3, 1, array) is None


def test_form_ids_split_on_the_plugin_index_rules():
    plugins = PluginList(
        form_version=78,
        plugins=("Skyrim.esm", "Update.esm", "Dawnguard.esm"),
        light_plugins=("ccOne.esl", "ccTwo.esl"),
    )
    # Normal plugin: top byte indexes plugins, low 24 bits are local.
    assert decode_form_id(0x0004B0BA, plugins) == ("Skyrim.esm", 0x4B0BA)
    assert decode_form_id(0x02001234, plugins) == ("Dawnguard.esm", 0x1234)
    # Light plugin: 0xFE prefix, bits 12-23 index, low 12 bits local.
    assert decode_form_id(0xFE000ABC, plugins) == ("ccOne.esl", 0xABC)
    assert decode_form_id(0xFE0017FF, plugins) == ("ccTwo.esl", 0x7FF)
    # Created forms and out-of-range indexes belong to no plugin.
    assert decode_form_id(0xFF000123, plugins) is None
    assert decode_form_id(0x09000001, plugins) is None
    assert decode_form_id(0xFE009000, plugins) is None


@pytest.mark.parametrize("mask, expected", [
    (0b0000, frozenset()),
    (0b0001, frozenset({0})),
    (0b1001, frozenset({0, 3})),      # Garlic in the fixture
    (0b0011, frozenset({0, 1})),      # Wheat in the fixture
    (0b1111, frozenset({0, 1, 2, 3})),
    (0xFFFF_FFF0, frozenset()),       # bits above slot 3 are not effects
])
def test_known_effect_slots_come_from_the_low_four_bits(mask, expected):
    form = ChangeForm(ref_type=1, ref_value=0x4B0BA, flags=CHANGE_INGREDIENT_USE,
                      type=16, version=78, data=struct.pack("<I", mask))
    assert parse_known_effect_slots(form) == expected


def test_ingredient_forms_without_the_use_flag_are_ignored():
    form = ChangeForm(ref_type=1, ref_value=0x4B0BA, flags=0,
                      type=16, version=78, data=struct.pack("<I", 0b11))
    assert parse_known_effect_slots(form) is None
    wrong_size = ChangeForm(ref_type=1, ref_value=0x4B0BA,
                            flags=CHANGE_INGREDIENT_USE, type=16, version=78,
                            data=b"\x03\x00")
    assert parse_known_effect_slots(wrong_size) is None


def test_both_flame_stalk_records_survive_the_lookup(dataset):
    lookup = build_ingredient_lookup(dataset)
    flame_stalks = {
        ingredient_id for (_, _), ingredient_id in lookup.items()
        if ingredient_id.startswith("flame-stalk")
    }
    # Two distinct records keyed by (plugin, local id): neither shadows
    # the other the way a bare form-id key would.
    assert flame_stalks == {"flame-stalk", "flame-stalk-solitude"}
