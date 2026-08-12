"""Parser for the file location table and change-form records that make
up the bulk of the SE save body.

Layout reference: UESP "Tes5Mod:Save File Format" for the record shapes
(file location table fields, change-form record fields). The *offset
rebasing* behavior below is an empirical finding, not documented in a
byte-exact way on that page, and was resolved by direct experimentation
against tests/fixtures/player.ess, cross-checked against the read-only
reference clone's libs/saveParser/Save.cpp (cguebert/SkyrimAlchemyHelper,
consulted for understanding only -- no code copied from it).

File location table (fixed layout, immediately after the plugin block --
see body.parse_plugins):
    10 u32 fields, in FileLocationTable field order, followed by 15
    unused u32 fields (100 bytes total).

Offset rebasing -- the empirical finding:
    The six *_offset fields are NOT byte offsets into the decompressed
    `body` buffer directly (tried first, per the brief, as the simplest
    interpretation). Trying that interpretation directly against the
    fixture: iterating change forms from the raw change_forms_offset
    decodes two records that look increasingly implausible (the second
    already has a wildly large flags value) and then blows up on the
    third, demanding a bogus ~32MB length1 -- clear proof the raw value
    is not a `body`-relative offset.

    The reference Save.cpp explains why: it reads these fields from the
    *original* (pre-decompression) file stream and immediately subtracts
    `compressedStart`, the file offset where the compressed body payload
    begins (i.e. this codebase's `header.body_offset`). In other words,
    the game engine writes these offsets as if the decompressed body
    started at that file position, not at 0. So:

        rebased_offset = raw_offset - header.body_offset

    `parse_file_location_table` takes `body_offset` explicitly (the
    caller -- Task 8's parse_save -- has the parsed SaveHeader in hand)
    and uses it as the authoritative rebase constant. As a belt-and-
    suspenders cross-check, the same constant is independently derived
    from a structural fact about the layout -- global_data_table_1 is
    the section that begins immediately after this table, with no gap:

        table_end                = after_plugins + 100
        derived_rebase_constant  = raw_global_data_table_1_offset - table_end

    If the caller-supplied `body_offset` and this derived value disagree,
    that means either the zero-gap assumption doesn't hold for this save
    or `body_offset` is wrong, so a SaveFormatError is raised naming both
    values rather than silently trusting one over the other.

    This was validated against the fixture (throwaway scripts, not
    committed): `body_offset` (245872) matches the zero-gap-derived value
    exactly, and -- the real structural proof -- iterating exactly
    `change_form_count` (46855) change-form records from the rebased
    change_forms_offset consumes them with zero Reader overrun and lands
    the reader at EXACTLY the rebased global_data_table_3_offset (a
    0-byte difference). That exact landing position is asserted by
    `test_change_forms_end_exactly_at_global_data_table_3_offset` in
    tests/saveparser/test_changeforms.py, via `ChangeFormIterator.
    final_position`.
"""
import zlib
from dataclasses import dataclass
from typing import Iterator

from alchemy_helper.saveparser.header import SaveFormatError
from alchemy_helper.saveparser.reader import Reader

_TABLE_UNUSED_FIELDS = 15


@dataclass(frozen=True)
class FileLocationTable:
    form_id_array_count_offset: int
    unknown_table_3_offset: int
    global_data_table_1_offset: int
    global_data_table_2_offset: int
    change_forms_offset: int
    global_data_table_3_offset: int
    global_data_table_1_count: int
    global_data_table_2_count: int
    global_data_table_3_count: int
    change_form_count: int


def parse_file_location_table(
        body: bytes, after_plugins: int, body_offset: int) -> FileLocationTable:
    """Parse the file location table and rebase its offset fields into
    `body`-relative coordinates.

    `body_offset` is `SaveHeader.body_offset` from the same save (the
    file offset of the uncompressedLen field, i.e. 8 bytes before where
    the compressed payload begins) -- see module docstring for why that
    value is the correct rebase constant.

    Raises:
        SaveFormatError: `body_offset` disagrees with the constant
            independently derived from the table's own zero-gap layout
            assumption (names both values), or a rebased offset falls
            outside the bounds of `body` (names the raw value, the
            rebase constant, and the resulting out-of-range offset).
    """
    r = Reader(body, pos=after_plugins)
    raw_form_id_array_count_offset = r.u32()
    raw_unknown_table_3_offset = r.u32()
    raw_global_data_table_1_offset = r.u32()
    raw_global_data_table_2_offset = r.u32()
    raw_change_forms_offset = r.u32()
    raw_global_data_table_3_offset = r.u32()
    global_data_table_1_count = r.u32()
    global_data_table_2_count = r.u32()
    global_data_table_3_count = r.u32()
    change_form_count = r.u32()
    for _ in range(_TABLE_UNUSED_FIELDS):
        r.u32()
    table_end = r.pos

    derived_rebase_constant = raw_global_data_table_1_offset - table_end
    if derived_rebase_constant != body_offset:
        raise SaveFormatError(
            f"File location table rebase constant mismatch: caller-"
            f"supplied body_offset={body_offset}, but the constant "
            f"derived from global_data_table_1 starting immediately "
            f"after this table is {derived_rebase_constant} "
            f"(raw_global_data_table_1_offset={raw_global_data_table_1_offset}, "
            f"table_end={table_end})"
        )
    rebase_constant = body_offset

    def rebase(field_name: str, raw_offset: int) -> int:
        offset = raw_offset - rebase_constant
        if not (0 <= offset <= len(body)):
            raise SaveFormatError(
                f"File location table field {field_name!r} is out of "
                f"range after rebasing: raw={raw_offset}, "
                f"rebase_constant={rebase_constant}, rebased={offset}, "
                f"but body is only {len(body)} byte(s)"
            )
        return offset

    return FileLocationTable(
        form_id_array_count_offset=rebase(
            "form_id_array_count_offset", raw_form_id_array_count_offset),
        unknown_table_3_offset=rebase(
            "unknown_table_3_offset", raw_unknown_table_3_offset),
        global_data_table_1_offset=rebase(
            "global_data_table_1_offset", raw_global_data_table_1_offset),
        global_data_table_2_offset=rebase(
            "global_data_table_2_offset", raw_global_data_table_2_offset),
        change_forms_offset=rebase(
            "change_forms_offset", raw_change_forms_offset),
        global_data_table_3_offset=rebase(
            "global_data_table_3_offset", raw_global_data_table_3_offset),
        global_data_table_1_count=global_data_table_1_count,
        global_data_table_2_count=global_data_table_2_count,
        global_data_table_3_count=global_data_table_3_count,
        change_form_count=change_form_count,
    )


@dataclass(frozen=True)
class ChangeForm:
    ref_type: int    # top 2 bits of refID: 0=formID-array index, 1=literal form, 2=created
    ref_value: int   # low 22 bits
    flags: int       # changeFlags u32
    type: int        # low 6 bits of type byte
    version: int
    data: bytes      # zlib-inflated when length2 != 0


class ChangeFormIterator:
    """Iterator over the change-form records in a save body.

    Exposes `final_position` (the underlying Reader's position) so
    callers -- and tests -- can verify the iterator consumed exactly
    the change-form section and landed precisely at the start of the
    next section (global_data_table_3), which is the structural proof
    that the file-location-table offset rebasing is correct. Only
    meaningful once iteration is exhausted.
    """

    def __init__(self, body: bytes, table: FileLocationTable):
        self._reader = Reader(body, pos=table.change_forms_offset)
        self._table = table
        self._index = 0

    def __iter__(self) -> "ChangeFormIterator":
        return self

    def __next__(self) -> ChangeForm:
        if self._index >= self._table.change_form_count:
            raise StopIteration
        form = self._parse_one(self._index)
        self._index += 1
        return form

    @property
    def final_position(self) -> int:
        return self._reader.pos

    def _parse_one(self, i: int) -> ChangeForm:
        r = self._reader
        ref_bytes = r.read(3)
        ref_id = (ref_bytes[0] << 16) | (ref_bytes[1] << 8) | ref_bytes[2]
        ref_type = ref_id >> 22
        ref_value = ref_id & 0x3FFFFF

        flags = r.u32()
        type_byte = r.u8()
        version = r.u8()

        length_width = type_byte >> 6
        if length_width == 0:
            length1, length2 = r.u8(), r.u8()
        elif length_width == 1:
            length1, length2 = r.u16(), r.u16()
        elif length_width == 2:
            length1, length2 = r.u32(), r.u32()
        else:
            raise SaveFormatError(
                f"Change form #{i}: type byte 0x{type_byte:02x} has "
                f"reserved length-width selector 3 (expected 0, 1, or 2)"
            )

        raw_data = r.read(length1)
        if length2:
            data = zlib.decompress(raw_data)
            if len(data) != length2:
                raise SaveFormatError(
                    f"Change form #{i}: declared decompressed length "
                    f"length2={length2}, but inflating produced "
                    f"{len(data)} byte(s)"
                )
        else:
            data = raw_data

        return ChangeForm(
            ref_type=ref_type,
            ref_value=ref_value,
            flags=flags,
            type=type_byte & 0x3F,
            version=version,
            data=data,
        )


def iter_change_forms(body: bytes, table: FileLocationTable) -> Iterator[ChangeForm]:
    """Return an iterator over exactly `table.change_form_count`
    ChangeForm records, in file order, starting at
    `table.change_forms_offset`.

    The returned `ChangeFormIterator` additionally exposes
    `final_position` (the reader's position once exhausted) -- see its
    docstring and the module docstring for why that matters.

    Raises:
        SaveFormatError: a type byte's length-width selector is the
            reserved value 3, or a compressed record's inflated size
            doesn't match its declared length2.
        SaveFormatError (from Reader): any record's declared length1
            would run past the end of `body`.
    """
    return ChangeFormIterator(body, table)


def parse_form_id_array(body: bytes, table: FileLocationTable) -> tuple[int, ...]:
    """Parse the form-id array: a u32 count at
    `table.form_id_array_count_offset`, followed by that many u32 form
    ids.
    """
    r = Reader(body, pos=table.form_id_array_count_offset)
    count = r.u32()
    return tuple(r.u32() for _ in range(count))
