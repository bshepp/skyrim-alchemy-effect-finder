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
    CHANGE_INGREDIENT_USE, _skip_extra_data_entry, build_ingredient_lookup,
    decode_form_id, extract_forms, parse_known_effect_slots,
    parse_player_inventory, resolve_ref_id)
from alchemy_helper.saveparser.header import SaveFormatError
from alchemy_helper.saveparser.reader import Reader

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
    # Parser-derived structural pin: this save carries 91 distinct
    # ingredients out of the 180 in the dataset. It was 90 of 179 until
    # 2026-08-27, when Mort Flesh entered the dataset and one item Maldric
    # had been carrying all along (1x, no effects discovered, so no
    # ingredient-use record ever flagged it) became resolvable. A
    # brute-force refID scan of the same change form claims 4 more --
    # (aster-bloom-core, void-essence, scalon-fin, scrib-jelly) are
    # byte coincidences that the structured walk correctly rejects.
    assert len(state.inventory) == 91
    assert state.inventory["mort-flesh"] == 1


def test_known_effects_match_what_the_user_sees_in_the_alchemy_menu(state, dataset):
    # FACTS.md "Known (discovered) effects", reported 2026-08-11:
    #   Wheat: "restore health, fortify health" revealed, other two hidden.
    #   Garlic: "Resist Poison, Regenerate Health" revealed, other two hidden.
    assert state.known_effects["wheat"] == slots(
        dataset, "wheat", "restore-health", "fortify-health")
    assert state.known_effects["garlic"] == slots(
        dataset, "garlic", "resist-poison", "regenerate-health")


def test_bee_has_no_discovered_effects(state):
    # User-confirmed 2026-08-13 against the in-game alchemy view: nothing
    # discovered for Bee (see FACTS.md).
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


def test_modded_ingredient_is_collected_as_unknown_not_fatal(dataset):
    # The degrade-instead-of-crash guarantee, exercised for real: an
    # ingredient-use change form for a form no dataset entry covers
    # (here a fake SomeMod.esp ingredient) must be reported, not raise
    # and not silently vanish. The fixture cannot test this -- it is a
    # vanilla+Creations save where nothing is left over.
    plugins = PluginList(
        form_version=78,
        plugins=("Skyrim.esm", "SomeMod.esp"),
        light_plugins=(),
    )
    # A literal (type 1) refID only holds 22 bits, so it can never carry
    # a plugin index -- which is exactly why forms outside Skyrim.esm go
    # through the form-id array as type 0. This is how a modded
    # ingredient really appears in a save.
    form_id_array = (0x01001234,)            # top byte 0x01 -> SomeMod.esp
    modded = ChangeForm(
        ref_type=0, ref_value=1,             # 1-based index into the array
        flags=CHANGE_INGREDIENT_USE, type=16, version=78,
        data=struct.pack("<I", 0b0101),
    )
    known = ChangeForm(
        ref_type=1, ref_value=0x04B0BA,      # top byte 0x00 -> Skyrim.esm wheat
        flags=CHANGE_INGREDIENT_USE, type=16, version=78,
        data=struct.pack("<I", 0b0011),
    )
    extracted = extract_forms(
        [modded, known, synthetic_player_change_form(items=[])],
        plugins, form_id_array, dataset=dataset)

    assert extracted.unknown_forms == (("SomeMod.esp", 0x1234),)
    # ...and the run continues: the recognised ingredient beside it is
    # still extracted normally.
    assert extracted.known_effects == {"wheat": frozenset({0, 1})}


def test_unknown_form_reaches_the_public_surface_as_unknown_form(dataset):
    plugins = PluginList(
        form_version=78, plugins=("Skyrim.esm", "SomeMod.esp"), light_plugins=())
    modded = ChangeForm(
        ref_type=0, ref_value=1, flags=CHANGE_INGREDIENT_USE,
        type=16, version=78, data=struct.pack("<I", 0b0001))
    extracted = extract_forms(
        [modded, synthetic_player_change_form(items=[])],
        plugins, form_id_array=(0x01001234,), dataset=dataset)
    forms = tuple(UnknownForm(plugin=p, form_id=f)
                  for p, f in extracted.unknown_forms)
    assert forms == (UnknownForm(plugin="SomeMod.esp", form_id=0x1234),)


def test_both_flame_stalk_records_survive_the_lookup(dataset):
    lookup = build_ingredient_lookup(dataset)
    flame_stalks = {
        ingredient_id for (_, _), ingredient_id in lookup.items()
        if ingredient_id.startswith("flame-stalk")
    }
    # Two distinct records keyed by (plugin, local id): neither shadows
    # the other the way a bare form-id key would.
    assert flame_stalks == {"flame-stalk", "flame-stalk-solitude"}


# --- the ACHR walk and the extra-data table, on synthetic bytes -----------
#
# These are the most inferred parts of the parser (the type->size table,
# the wrapper recursion, and the refusal to guess). The fixture exercises
# them only incidentally, and only along the paths this one save happens
# to take, so the safety behaviour is pinned directly here.

CHANGE_REFR_INVENTORY = 1 << 5   # see extract.py's flag table


def vsval(value: int) -> bytes:
    """Encode a vsval the way the save format does (1-byte form only,
    which covers every count these tests use)."""
    assert value < 64
    return bytes([value << 2])


def ref_id(ref_type: int, ref_value: int) -> bytes:
    packed = (ref_type << 22) | ref_value
    return bytes([(packed >> 16) & 0xFF, (packed >> 8) & 0xFF, packed & 0xFF])


def inventory_item(ref_type: int, ref_value: int, count: int,
                   extra: bytes = b"") -> bytes:
    """refID + signed i32 count + extra-data list."""
    extra_list = vsval(1) + extra if extra else vsval(0)
    return ref_id(ref_type, ref_value) + struct.pack("<i", count) + extra_list


def synthetic_player_change_form(items: list[bytes], flags: int | None = None,
                                 body: bytes | None = None) -> ChangeForm:
    """A minimal player ACHR: INVENTORY only, so the walk reads 8 bytes
    of unknowns and then the item array (no initial data, no havok, no
    extra data, no animations).
    """
    if body is None:
        body = b"\x00" * 8 + vsval(len(items)) + b"".join(items)
    return ChangeForm(
        ref_type=1, ref_value=0x14,
        flags=CHANGE_REFR_INVENTORY if flags is None else flags,
        type=1, version=78, data=body,
    )


def test_inventory_entries_decode_as_ref_id_signed_count_and_extras():
    form = synthetic_player_change_form(items=[
        inventory_item(1, 0x04B0BA, 22),
        # An entry carrying extras: wrapper type 20 holding five nested
        # entries -- UniqueId(6), ReferenceHandle(3), HotKey(1),
        # Charge(4), Worn(0) -- exactly the shape the fixture's
        # hotkeyed enchanted item uses.
        inventory_item(1, 0x0341A0, 1, extra=bytes([20])
                       + bytes([159]) + b"\x01\x02\x03\x04\x05\x06"
                       + bytes([28]) + b"\x00\x00\x00"
                       + bytes([73]) + b"\x07"
                       + bytes([40]) + b"\x00\x00\x80\x3f"
                       + bytes([22])),
        inventory_item(1, 0x034D22, 30),
        inventory_item(1, 0x000000F, -4),   # deltas can be negative
    ])
    assert parse_player_inventory(form, form_id_array=()) == [
        (0x04B0BA, 22), (0x0341A0, 1), (0x034D22, 30), (0x00000F, -4)]


def test_wrapper_extra_type_consumes_exactly_its_nested_entries():
    # Type 20 wraps five entries; the walk must land on the sentinel
    # immediately after them and not one byte to either side.
    nested = (bytes([159]) + b"\x01\x02\x03\x04\x05\x06"   # UniqueId, 6
              + bytes([28]) + b"\x00\x00\x00"              # ReferenceHandle, 3
              + bytes([73]) + b"\x07"                      # HotKey, 1
              + bytes([40]) + b"\x00\x00\x80\x3f"          # Charge, 4
              + bytes([22]))                               # Worn, 0
    data = bytes([20]) + nested + b"SENTINEL"
    reader = Reader(data)
    _skip_extra_data_entry(reader)
    assert reader.pos == 1 + len(nested)
    assert data[reader.pos:] == b"SENTINEL"


def test_nested_wrapper_types_recurse():
    # 4/8/12 wrap 1/2/3 entries; a wrapper inside a wrapper still lands
    # exactly, which is what keeps the item walk aligned.
    inner = bytes([4]) + bytes([28]) + b"\x00\x00\x00"     # wrapper-of-1
    data = bytes([8]) + inner + bytes([36]) + b"\x02\x00" + b"END"
    reader = Reader(data)
    _skip_extra_data_entry(reader)
    assert data[reader.pos:] == b"END"


def test_unmodelled_extra_type_raises_naming_the_type():
    # Type 45 (LeveledCreature) is a structure this parser deliberately
    # does not model. It must say so and stop, never skip a guessed
    # number of bytes and carry on misaligned.
    reader = Reader(bytes([45]) + b"\x00" * 32)
    with pytest.raises(SaveFormatError) as excinfo:
        _skip_extra_data_entry(reader)
    message = str(excinfo.value)
    assert "45" in message
    assert "extra-data" in message.lower()


def test_garbage_inventory_raises_instead_of_guessing():
    # INVENTORY flag set but the bytes are nonsense: the walk must
    # refuse rather than return a plausible-looking inventory.
    form = synthetic_player_change_form(
        items=[], body=b"\x00" * 8 + vsval(20) + b"\xff" * 200)
    with pytest.raises(SaveFormatError) as excinfo:
        parse_player_inventory(form, form_id_array=())
    message = str(excinfo.value)
    assert "inventory item 0 of 20" in message


def test_truncated_inventory_raises_instead_of_returning_a_short_list():
    # Declares more items than there are bytes for.
    form = synthetic_player_change_form(
        items=[], body=b"\x00" * 8 + vsval(9) + inventory_item(1, 0x04B0BA, 22))
    with pytest.raises(SaveFormatError) as excinfo:
        parse_player_inventory(form, form_id_array=())
    assert "inventory item 1 of 9" in str(excinfo.value)


def test_malformed_player_change_form_fails_the_whole_parse(dataset):
    # And the failure propagates out of extract_forms rather than
    # yielding a PlayerState with a fabricated inventory.
    plugins = PluginList(form_version=78, plugins=("Skyrim.esm",), light_plugins=())
    broken = synthetic_player_change_form(
        items=[], body=b"\x00" * 8 + vsval(20) + b"\xff" * 200)
    with pytest.raises(SaveFormatError):
        extract_forms([broken], plugins, form_id_array=(), dataset=dataset)


def test_missing_player_change_form_is_reported(dataset):
    plugins = PluginList(form_version=78, plugins=("Skyrim.esm",), light_plugins=())
    with pytest.raises(SaveFormatError) as excinfo:
        extract_forms([], plugins, form_id_array=(), dataset=dataset)
    assert "0x14" in str(excinfo.value)
