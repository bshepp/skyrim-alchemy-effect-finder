"""Decoding of the two things this app needs out of a save's change
forms: what ingredients the player is carrying, and which of each
ingredient's four effects the player has already discovered.

Nothing on this page is guessable, and the byte layouts are barely
documented in prose anywhere, so the decoding below was derived by
reading two GPL reference implementations for *understanding* (no code
copied from either) and then verifying every field offset against
tests/fixtures/player.ess:

  * cguebert/SkyrimAlchemyHelper, libs/saveParser/Save.cpp -- which
    change-form types carry ingredient data (2018, form version ~74).
  * mdfairch/FallrimTools (ReSaver), src/main/java/resaver/ess/
    ChangeFormACHR.java, ChangeFormInventoryItem.java,
    ChangeFormExtraData(Data).java, ChangeFlagConstantsAchr.java --
    the exact section order of an ACHR change form and the extra-data
    type table.

Both clones live under reference/ (gitignored, read-only).


Change-form type values observed in the fixture
-----------------------------------------------
`ChangeForm.type` is the low 6 bits of the type byte. The fixture's
46855 change forms use 26 distinct values; the two that matter:

    type 1  = ACHR (actor reference). 8420 of them; the player is the
              one with refID type 1 / value 0x14, exactly once.
    type 16 = INGR (ingredient). 31 of them, every one with
              changeFlags == 0x80000000 and exactly 4 bytes of data.

(Others seen, none relevant here: 0 REFR, 6 CELL, 7 INFO, 8 QUST,
9 NPC_, 13 BOOK, 31 FACT, 36 SMQN, 38 LCTN, 39 RELA, 40 PHZD, 43 FLST,
45 LVLI, 48 ENCH, ...)


INGR change form -- where "known effects" live
-----------------------------------------------
An INGR change form exists only once the player has discovered at least
one effect of that ingredient; ingredients with nothing discovered have
no change form at all (this is how the fixture records Bee). Its whole
payload is a single u32 whose low four bits are the discovered slots,
bit i <-> the ingredient's i-th effect in load order -- the same order
the dataset stores effects in:

    data = 4 bytes, u32 little-endian
    bit 0..3 set  =>  effect slot 0..3 discovered

Verified against the two user-reported ground truths in
tests/fixtures/FACTS.md: Wheat's form holds 0x03 = slots {0,1} =
restore-health + fortify-health, and Garlic's holds 0x09 = slots {0,3}
= resist-poison + regenerate-health. Both match the in-game alchemy
menu exactly.

The 0x80000000 change flag is CHANGE_INGREDIENT_USE (bit 31); it is
what marks the u32 as present. Forms without it are skipped rather
than misread.


ACHR change form -- where the inventory lives
----------------------------------------------
The player's carried items are a length-prefixed item array buried
inside the player ACHR change form. The sections before it are all
conditional on `changeFlags`, so the array cannot be found without
walking them; walking them is exact, and the walk is self-checking
(it must consume the change form's data to the last byte).

Flag bits (ChangeFlagConstantsAchr):

    bit 0  CHANGE_FORM_FLAGS                    bit 18 ACTOR_LEVELED_ACTOR
    bit 1  CHANGE_REFR_MOVE                     bit 25 REFR_PROMOTED
    bit 2  CHANGE_REFR_HAVOK_MOVE               bit 26 REFR_EXTRA_ACTIVATING_CHILDREN
    bit 3  CHANGE_REFR_CELL_CHANGED             bit 27 REFR_LEVELED_INVENTORY
    bit 4  CHANGE_REFR_SCALE                    bit 28 REFR_ANIMATION
    bit 5  CHANGE_REFR_INVENTORY                bit 29 REFR_EXTRA_ENCOUNTER_ZONE
    bit 6  CHANGE_REFR_EXTRA_OWNERSHIP          bit 30 REFR_EXTRA_CREATED_ONLY
    bit 7  CHANGE_REFR_BASEOBJECT               bit 31 REFR_EXTRA_GAME_ONLY
    bit 9  ACTOR_EXTRA_PACKAGE_DATA
    bit 11 ACTOR_EXTRA_MERCHANT_CONTAINER
    bit 17 ACTOR_EXTRA_DISMEMBERED_LIMBS

Section order:

    initial data      -- shape picked by refID type + flags, see
                         _read_initial_data
    havok data        -- if HAVOK_MOVE: vsval length + that many bytes
    u32 unknown
    4 bytes unknown
    change form flags -- if CHANGE_FORM_FLAGS: u32 + u16
    base object       -- if REFR_BASEOBJECT: refID (3 bytes)
    scale             -- if REFR_SCALE: f32
    extra data        -- if any of EXTRA_OWNERSHIP, PROMOTED,
                         ACTOR_EXTRA_PACKAGE_DATA, MERCHANT_CONTAINER,
                         DISMEMBERED_LIMBS, ACTIVATING_CHILDREN,
                         ENCOUNTER_ZONE, CREATED_ONLY, GAME_ONLY,
                         LEVELED_ACTOR: an extra-data list (below)
    INVENTORY         -- if INVENTORY or LEVELED_INVENTORY:
                             vsval item_count
                             item_count x inventory entry
    animations        -- if REFR_ANIMATION: vsval length + bytes

Inventory entry (the format the brief asked for):

    refID   3 bytes, big-endian-ish: top 2 bits are the ref type,
            low 22 bits the value (see resolve_ref_id)
    count   i32 little-endian, SIGNED -- change forms store deltas
            against the base object's inventory, so zero and negative
            values occur and mean "carrying none"
    extra   item extra data, usually the single byte 0x00

Actor-level extra-data list (between the fixed fields and inventory):

    vsval count, then `count` entries, each a u8 type followed by a
    type-dependent payload (_EXTRA_FIXED / _EXTRA_VS_ARRAY /
    _EXTRA_STRUCTURED below).

Item extra data (per inventory entry):

    vsval count of STACKS (piles of the item with distinct properties),
    then per stack a vsval count of entries + that many TLV entries as
    above. The stack layer is why a naive "skip N bytes" heuristic
    drifts, and why entry-count vsvals (1..5 encode as bytes 4/8/12/
    16/20) were long mistaken for ReSaver's ExtraExtraData wrapper
    types -- see the note above _skip_item_extra_data.

Verification against tests/fixtures/player.ess (player ACHR, 55511
bytes of data, changeFlags 0xB8000C26 -> MOVE, HAVOK_MOVE, INVENTORY,
LIFESTATE, MERCHANT_CONTAINER, LEVELED_INVENTORY, ANIMATION,
ENCOUNTER_ZONE, GAME_ONLY):

    offset    0  initial data, type 4 (HAVOK_MOVE set, not created,
                 not promoted/cell-changed) = cell refID + 3 pos f32
                 + 3 rot f32                                    27 bytes
    offset   27  havok: vsval 561 + 561 bytes             -> ends 590
    offset  590  u32 unknown, 4 bytes unknown             -> ends 598
                 (CHANGE_FORM_FLAGS / BASEOBJECT / SCALE all clear)
    offset  598  extra data: vsval 2 entries
                   type 136 AliasInstanceArray: vsval 53 x (refID+u32)
                   type 112 EncounterZone: refID          -> ends 976
    offset  976  INVENTORY: vsval 173 items               -> ends 3068
    offset 3068  animations: vsval 15246 + that many bytes
                 (readable ASCII: "BShkbAnimationGraph",
                 "IdleBehavior.hkb/Behavior02", ...)        -> ends 18316
    offset 18316 37195 bytes of actor state this parser does not model
                 (LIFESTATE and the rest of the ACHR-specific data --
                 ReSaver stops here too, reporting the remainder as
                 unparsed). Nothing this app needs lives in it, and it
                 sits *after* the inventory, so it cannot shift it.

Because of that tail, "consumed the change form exactly" is not
available as a correctness check. What is checked instead, and what
makes a misaligned read essentially impossible to mistake for a good
one: the item array must yield exactly its declared item count, every
item's refID must resolve to a form in this save, and every item's
extra-data list must parse with the type table above. A walk starting
at the wrong offset trips one of those within a couple of entries.

Corroboration on the fixture: all 173 items parse, no refID fails to
resolve, and each of the 90 resulting ingredient counts also appears
at an item-aligned offset in an independent brute-force scan of the
change form. The reverse is not true, which is exactly why the scan
approach (what the older SkyrimAlchemyHelper reference does) was
rejected: that scan additionally reports aster-bloom-core, void-
essence, scalon-fin and scrib-jelly, none of which the player carries
-- they are byte coincidences inside neighbouring entries' extra data
and inside the animation blob. 14 of the 173 items carry counts <= 0
(change forms store deltas against the base object); none of those is
an ingredient, and they are dropped.
"""
import struct
from dataclasses import dataclass

from alchemy_helper.data.loader import Dataset
from alchemy_helper.saveparser.body import PluginList
from alchemy_helper.saveparser.changeforms import ChangeForm
from alchemy_helper.saveparser.header import SaveFormatError
from alchemy_helper.saveparser.reader import Reader

PLAYER_REF_TYPE = 1
PLAYER_REF_VALUE = 0x14
CHANGE_FORM_TYPE_ACHR = 1
CHANGE_FORM_TYPE_INGR = 16

CHANGE_INGREDIENT_USE = 0x80000000

_CHANGE_FORM_FLAGS = 1 << 0
_CHANGE_REFR_MOVE = 1 << 1
_CHANGE_REFR_HAVOK_MOVE = 1 << 2
_CHANGE_REFR_CELL_CHANGED = 1 << 3
_CHANGE_REFR_SCALE = 1 << 4
_CHANGE_REFR_INVENTORY = 1 << 5
_CHANGE_REFR_BASEOBJECT = 1 << 7
_CHANGE_REFR_PROMOTED = 1 << 25
_CHANGE_REFR_LEVELED_INVENTORY = 1 << 27
_CHANGE_REFR_ANIMATION = 1 << 28

# Any of these means an extra-data list sits between the fixed fields
# and the inventory.
_EXTRA_DATA_FLAGS = (
    (1 << 6)    # REFR_EXTRA_OWNERSHIP
    | (1 << 9)  # ACTOR_EXTRA_PACKAGE_DATA
    | (1 << 11)  # ACTOR_EXTRA_MERCHANT_CONTAINER
    | (1 << 17)  # ACTOR_EXTRA_DISMEMBERED_LIMBS
    | (1 << 18)  # ACTOR_LEVELED_ACTOR
    | (1 << 25)  # REFR_PROMOTED
    | (1 << 26)  # REFR_EXTRA_ACTIVATING_CHILDREN
    | (1 << 29)  # REFR_EXTRA_ENCOUNTER_ZONE
    | (1 << 30)  # REFR_EXTRA_CREATED_ONLY
    | (1 << 31)  # REFR_EXTRA_GAME_ONLY
)

_REF_ID_SIZE = 3

# Extra-data entry type -> fixed payload size in bytes. Names are the
# ones ReSaver uses; sizes are the sum of its field reads (refID = 3).
_EXTRA_FIXED = {
    0: 0,      # NULL
    6: 56,     # (unnamed; no ReSaver case) -- observed on the player's
               # actor-level list alongside a TrespassPackage entry.
               # Size derived empirically: six live saves, two list
               # shapes (5- and 6-entry, one shape followed by a type-
               # 152 arrows entry), all align to the same 56-byte
               # payload, holding two refs to the player among unknowns.
               # Graduated by round-trip: the inventory parsed past it
               # matched the in-game pouch item-for-item (2026-09-03).
    22: 0,     # Worn
    23: 0,     # WornLeft
    24: 19,    # PackageStartLocation: refID + 3 f32 + f32
    25: 13,    # Package: refID + refID + u32 + 3 bytes
    26: 3,     # TrespassPackage: refID
    28: 3,     # ReferenceHandle: refID
    29: 0,     # Unknown29
    30: 4,     # LevCreaModifier: u32
    31: 1,     # Ghost: u8
    32: 0,     # Unknown32
    33: 3,     # Ownership: refID
    34: 3,     # Global: refID
    35: 3,     # Rank: refID
    36: 2,     # Count: u16
    37: 4,     # Health: f32
    39: 4,     # TimeLeft: u32
    40: 4,     # Charge: f32
    42: 13,    # Lock: 2 bytes + refID + 2 u32
    43: 28,    # Teleport: 3 f32 + 3 f32 + u8 + refID
    44: 1,     # MapMarker: u8
    46: 5,     # LeveledItem: u32 + u8
    47: 4,     # Scale: f32
    53: 0,     # Unknown53
    56: 3,     # ItemDropper: refID
    61: 0,     # CannotWear
    62: 7,     # ExtraPoison: refID + u32
    69: 3,     # HeadingTarget: refID
    72: 3,     # StartingWorldOrCell: refID
    73: 1,     # HotKey: u8
    77: 1,     # HasNoRumors: u8
    79: 2,     # TerminalState: 2 bytes
    83: 4,     # Unknown83: u32
    84: 1,     # CanTalkToPlayer: u8
    85: 4,     # ObjectHealth: f32
    88: 7,     # ModelSwap: refID + u32
    89: 4,     # Radius: f32
    93: 4,     # ActorCause: u32
    101: 3,    # CombatStyle: refID
    102: 6,    # (unnamed): refID + refID
    104: 3,    # OpenCloseActivateRef: refID
    106: 7,    # Ammo: refID + u32
    112: 3,    # EncounterZone: refID
    133: 3,    # AshPileRef: refID
    135: 12,   # (unnamed): 4 x refID
    142: 3,    # OutfitItem: refID
    146: 3,    # SceneData: refID
    149: 7,    # FromAlias: refID + u32
    150: 1,    # ShouldWear: u8
    155: 5,    # Enchantment: refID + u16
    156: 1,    # Soul: u8
    157: 3,    # ForcedTarget: refID
    159: 6,    # UniqueId: u32 + u16
    160: 4,    # Flags: u32
    161: 88,   # RefrPath: 18 f32 + 4 u32
    164: 3,    # ForcedLandingMarker: refID
    169: 11,   # Interaction: u32 + refID + refID + u8
    176: 8,    # CachedScale: f32 + f32
}

# Extra-data entry type -> element size of a vsval-counted array.
_EXTRA_VS_ARRAY = {
    27: 4,     # RunOncePacks: u32[]
    52: 8,     # PlayerCrimeList: u64[]
    68: 4,     # FriendHits: f32[]
    136: 7,    # AliasInstanceArray: (refID + u32)[]
    140: 3,    # PromotedRef: refID[]
}

# A historical wrong turn, kept as a warning: bytes 4/8/12/16/20 at the
# head of an item's extra data were once modelled as "wrapper types"
# holding type//4 nested entries (following ReSaver's ExtraExtraData1/2/3
# naming). They are actually vsval-encoded ENTRY COUNTS of an item
# stack -- the vsval encodings of 1..5 are exactly 4/8/12/16/20, so the
# two models are byte-identical up to five entries. A save carrying a
# six-property item (count byte 0x18 = 24, which ReSaver labels
# PackageStartLocation) broke the wrapper reading and exposed the truth;
# see _skip_item_extra_data.


def _skip_text_display_data(r: Reader) -> None:
    """Extra-data type 153, TextDisplayData -- carried by items the
    player has renamed at a grindstone/workbench/enchanter.

    refID + refID + i32, and only when both refIDs are zero and the
    int is -2 does the custom name follow as a wstring. Present in the
    fixture on renamed gear (item 111 of the player's inventory).
    """
    ref1 = r.read(_REF_ID_SIZE)
    ref2 = r.read(_REF_ID_SIZE)
    unknown = _i32(r)
    if not any(ref1) and not any(ref2) and unknown == -2:
        r.wstring()


def _skip_attached_arrows_3d(r: Reader) -> None:
    """Extra-data type 152, AttachedArrows3D -- arrows lodged in an
    actor's body, so it appears on the player mid-combat-heavy sessions.

    vsval count of arrow entries: refID; a nonzero refID adds a u16;
    a u16 other than 0xFFFF adds a u32 + 8 f32. Two u16s trail the
    array. (Layout per ReSaver's ChangeFormExtraDataData.AttachedArrow.)
    """
    count = _vsval(r)
    for _ in range(count):
        ref = r.read(_REF_ID_SIZE)
        if any(ref):
            if r.u16() != 0xFFFF:
                r.read(4 + 32)
    r.read(4)


# Extra-data types whose payload is not a fixed size or a flat array.
_EXTRA_STRUCTURED = {152: _skip_attached_arrows_3d,
                     153: _skip_text_display_data}


def _vsval(r: Reader) -> int:
    """Variable-size value: the low 2 bits of the first byte give the
    width (0 -> 1 byte, 1 -> 2, 2 -> 3); the value is the whole
    little-endian field shifted right by 2.
    """
    first = r.data[r.pos] if r.pos < len(r.data) else None
    if first is None:
        raise SaveFormatError(
            f"Unexpected end of change-form data reading a vsval at "
            f"offset {r.pos} of {len(r.data)}"
        )
    width = first & 0x3
    if width == 0:
        return r.u8() >> 2
    if width == 1:
        return r.u16() >> 2
    if width == 2:
        raw = r.read(3)
        return (raw[0] | (raw[1] << 8) | (raw[2] << 16)) >> 2
    raise SaveFormatError(
        f"Invalid vsval at offset {r.pos}: width selector 3 is reserved "
        f"(first byte 0x{first:02x})"
    )


def _i32(r: Reader) -> int:
    return struct.unpack("<i", r.read(4))[0]


def _read_ref_id(r: Reader) -> tuple[int, int]:
    """Read a 3-byte refID, returning (ref_type, ref_value)."""
    raw = r.read(_REF_ID_SIZE)
    packed = (raw[0] << 16) | (raw[1] << 8) | raw[2]
    return packed >> 22, packed & 0x3FFFFF


def resolve_ref_id(ref_type: int, ref_value: int,
                   form_id_array: tuple[int, ...]) -> int | None:
    """Turn a change-form refID into a formID.

    ref_type 0 indexes `form_id_array` 1-based (value 0 means form 0);
    ref_type 1 is already a formID; ref_type 2 is a run-time created
    form (0xFF000000 | value), which can never be a dataset ingredient.

    Returns None when the refID cannot be resolved (an array index past
    the end of the form-id array), so callers can skip it instead of
    inventing a form.
    """
    if ref_type == 0:
        if ref_value == 0:
            return 0
        if ref_value > len(form_id_array):
            return None
        return form_id_array[ref_value - 1]
    if ref_type == 1:
        return ref_value
    if ref_type == 2:
        return 0xFF000000 | ref_value
    return None


def decode_form_id(form_id: int, plugins: PluginList) -> tuple[str, int] | None:
    """Split a formID into (plugin filename, local id) using this
    save's load order.

    Top byte 0xFE marks a light plugin: bits 12-23 index
    `light_plugins` and the local id is the low 12 bits. Top byte 0xFF
    is a run-time created form and belongs to no plugin. Otherwise the
    top byte indexes `plugins` and the local id is the low 24 bits.

    Returns None for created forms and for indexes this save's load
    order doesn't have.
    """
    top = form_id >> 24
    if top == 0xFF:
        return None
    if top == 0xFE:
        index = (form_id >> 12) & 0xFFF
        if index >= len(plugins.light_plugins):
            return None
        return plugins.light_plugins[index], form_id & 0xFFF
    if top >= len(plugins.plugins):
        return None
    return plugins.plugins[top], form_id & 0xFFFFFF


def build_ingredient_lookup(dataset: Dataset) -> dict[tuple[str, int], str]:
    """(lowercased plugin filename, local form id) -> ingredient id.

    Keying on the plugin name rather than a load-order index is what
    lets the two Flame Stalk records (Skyrim.esm vs the Saints &
    Seducers plugin) coexist without either shadowing the other.
    """
    return {
        (ingredient.plugin.lower(), ingredient.form_id): ingredient.id
        for ingredient in dataset.ingredients.values()
    }


def parse_known_effect_slots(change_form: ChangeForm) -> frozenset[int] | None:
    """The discovered-effect slots recorded by an INGR change form.

    Returns None when this form carries no ingredient-use payload (the
    flag is clear or the payload isn't the expected 4 bytes), so the
    caller can ignore it rather than guess.
    """
    if not change_form.flags & CHANGE_INGREDIENT_USE:
        return None
    if len(change_form.data) != 4:
        return None
    mask = struct.unpack("<I", change_form.data)[0]
    return frozenset(slot for slot in range(4) if mask & (1 << slot))


def _skip_extra_data_entry(r: Reader) -> None:
    entry_type = r.u8()
    if entry_type in _EXTRA_FIXED:
        r.read(_EXTRA_FIXED[entry_type])
    elif entry_type in _EXTRA_VS_ARRAY:
        count = _vsval(r)
        r.read(count * _EXTRA_VS_ARRAY[entry_type])
    elif entry_type in _EXTRA_STRUCTURED:
        _EXTRA_STRUCTURED[entry_type](r)
    else:
        raise SaveFormatError(
            f"Unsupported extra-data type {entry_type} at offset "
            f"{r.pos - 1} of the player change form; this parser knows "
            f"the fixed-size and array types but not this one, so the "
            f"rest of the inventory cannot be located safely"
        )


def _skip_extra_data(r: Reader) -> None:
    count = _vsval(r)
    if count > 1024:
        raise SaveFormatError(
            f"Implausible extra-data entry count {count} at offset "
            f"{r.pos}; the change form is not laid out as expected"
        )
    for _ in range(count):
        _skip_extra_data_entry(r)


def _skip_item_extra_data(r: Reader) -> None:
    """An inventory item's extra data: a vsval count of stacks (piles of
    the item with distinct properties), then per stack a vsval count of
    TLV entries followed by the entries themselves.

    Distinct from the actor-level list above, which is a flat vsval +
    TLV entries with no stack layer.
    """
    stacks = _vsval(r)
    if stacks > 1024:
        raise SaveFormatError(
            f"Implausible item stack count {stacks} at offset {r.pos}; "
            f"the item array is not laid out as expected"
        )
    for _ in range(stacks):
        entries = _vsval(r)
        if entries > 1024:
            raise SaveFormatError(
                f"Implausible stack entry count {entries} at offset "
                f"{r.pos}; the item array is not laid out as expected"
            )
        for _ in range(entries):
            _skip_extra_data_entry(r)


def _read_initial_data(r: Reader, initial_type: int) -> None:
    if initial_type == 4:
        r.read(_REF_ID_SIZE + 24)          # cell + 3 pos f32 + 3 rot f32
    elif initial_type == 5:
        r.read(_REF_ID_SIZE + 24 + 1 + _REF_ID_SIZE)
    elif initial_type == 6:
        r.read(_REF_ID_SIZE + 24 + _REF_ID_SIZE + 4)
    elif initial_type != 0:
        raise SaveFormatError(
            f"Unsupported ACHR initial-data type {initial_type}"
        )


def parse_player_inventory(change_form: ChangeForm,
                           form_id_array: tuple[int, ...]) -> list[tuple[int, int]]:
    """Walk the player's ACHR change form and return its inventory as
    [(form_id, count), ...] in file order.

    Counts are the raw signed values; entries with count <= 0 are kept
    here and filtered by the caller, so the item total still matches
    what the save declared.

    Raises:
        SaveFormatError: the change form does not match the documented
            ACHR layout -- a section runs off the end, an extra-data
            type isn't in the table, or an item's refID doesn't resolve
            to a form in this save. Each of those means the item array
            was probably read from the wrong offset, so the inventory
            is rejected rather than reported.
    """
    flags = change_form.flags
    r = Reader(change_form.data)

    if change_form.ref_type == 2:
        initial_type = 5
    elif flags & (_CHANGE_REFR_PROMOTED | _CHANGE_REFR_CELL_CHANGED):
        initial_type = 6
    elif flags & (_CHANGE_REFR_HAVOK_MOVE | _CHANGE_REFR_MOVE):
        initial_type = 4
    else:
        initial_type = 0

    _read_initial_data(r, initial_type)

    if flags & _CHANGE_REFR_HAVOK_MOVE:
        r.read(_vsval(r))
    r.u32()      # unknown
    r.read(4)    # unknown
    if flags & _CHANGE_FORM_FLAGS:
        r.u32()
        r.u16()
    if flags & _CHANGE_REFR_BASEOBJECT:
        r.read(_REF_ID_SIZE)
    if flags & _CHANGE_REFR_SCALE:
        r.f32()
    if flags & _EXTRA_DATA_FLAGS:
        _skip_extra_data(r)

    items: list[tuple[int, int]] = []
    if flags & (_CHANGE_REFR_INVENTORY | _CHANGE_REFR_LEVELED_INVENTORY):
        item_count = _vsval(r)
        for index in range(item_count):
            offset = r.pos
            try:
                ref_type, ref_value = _read_ref_id(r)
                count = _i32(r)
                form_id = resolve_ref_id(ref_type, ref_value, form_id_array)
                if form_id is None:
                    raise SaveFormatError(
                        f"refID (type {ref_type}, value {ref_value}) does "
                        f"not resolve to a form in this save"
                    )
                _skip_item_extra_data(r)
            except SaveFormatError as exc:
                raise SaveFormatError(
                    f"Failed reading inventory item {index} of "
                    f"{item_count} at offset {offset} of the player "
                    f"change form: {exc}"
                ) from exc
            items.append((form_id, count))

    if flags & _CHANGE_REFR_ANIMATION:
        # Bounds-checked but not modelled: a length that doesn't fit is
        # the clearest signal that the sections above were misread.
        r.read(_vsval(r))

    # The remaining bytes are ACHR actor state this parser does not
    # model; see the module docstring for why that is safe here.
    return items


@dataclass(frozen=True)
class ExtractedForms:
    """Raw extraction results, before they become a PlayerState."""
    inventory: dict[str, int]                 # ingredient id -> count
    known_effects: dict[str, frozenset[int]]  # ingredient id -> slots
    unknown_forms: tuple[tuple[str, int], ...]  # (plugin, local id)


def extract_forms(change_forms, plugins: PluginList,
                  form_id_array: tuple[int, ...],
                  dataset: Dataset) -> ExtractedForms:
    """Pull the inventory and known effects out of an iterable of
    change forms in a single pass.

    Raises:
        SaveFormatError: no player change form was found, or the player
            change form did not match the documented ACHR layout.
    """
    lookup = build_ingredient_lookup(dataset)
    known_effects: dict[str, frozenset[int]] = {}
    unknown: list[tuple[str, int]] = []
    player_form: ChangeForm | None = None

    def to_ingredient(form_id: int) -> tuple[str | None, tuple[str, int] | None]:
        decoded = decode_form_id(form_id, plugins)
        if decoded is None:
            return None, None
        plugin, local_id = decoded
        return lookup.get((plugin.lower(), local_id)), (plugin, local_id)

    for change_form in change_forms:
        if (change_form.ref_type == PLAYER_REF_TYPE
                and change_form.ref_value == PLAYER_REF_VALUE
                and change_form.type == CHANGE_FORM_TYPE_ACHR):
            player_form = change_form
            continue
        if change_form.type != CHANGE_FORM_TYPE_INGR:
            continue
        slots = parse_known_effect_slots(change_form)
        if slots is None:
            continue
        form_id = resolve_ref_id(
            change_form.ref_type, change_form.ref_value, form_id_array)
        if form_id is None:
            continue
        ingredient_id, decoded = to_ingredient(form_id)
        if ingredient_id is None:
            if decoded is not None:
                unknown.append(decoded)
            continue
        if slots:
            known_effects[ingredient_id] = slots

    if player_form is None:
        raise SaveFormatError(
            "No player change form in this save: expected exactly one "
            "change form with refID type 1 / value 0x14 and type 1 (ACHR)"
        )

    inventory: dict[str, int] = {}
    for form_id, count in parse_player_inventory(player_form, form_id_array):
        if count <= 0:
            continue
        ingredient_id, _ = to_ingredient(form_id)
        if ingredient_id is None:
            continue
        inventory[ingredient_id] = inventory.get(ingredient_id, 0) + count

    return ExtractedForms(
        inventory=inventory,
        known_effects=known_effects,
        unknown_forms=tuple(unknown),
    )
