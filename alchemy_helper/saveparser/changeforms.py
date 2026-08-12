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
    started at that file position, not at 0.

    `parse_file_location_table` only receives (body, after_plugins), not
    the header, so `header.body_offset` isn't available here to replay
    that exact subtraction. Instead the equivalent constant is derived
    self-consistently: global_data_table_1 is the section that begins
    immediately after this table (no gap), so:

        table_end        = after_plugins + 100
        rebase_constant   = raw_global_data_table_1_offset - table_end
        rebased_offset    = raw_offset - rebase_constant

    This was cross-validated against the fixture two ways:
      - rebase_constant computed this way equals header.body_offset
        exactly (245872 for the fixture).
      - Using the rebased change_forms_offset, iterating exactly
        change_form_count (46855 for the fixture) change-form records
        consumes them with zero Reader overrun, and the reader ends up
        at EXACTLY the (identically rebased) global_data_table_3_offset
        -- a 0-byte difference. That is the structural proof this
        rebasing is correct, per the task's empirical-honesty rule.
    (Verified with a throwaway script, never committed.)
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


def parse_file_location_table(body: bytes, after_plugins: int) -> FileLocationTable:
    """Parse the file location table and rebase its offset fields into
    `body`-relative coordinates (see module docstring for why rebasing
    is necessary and how the rebase constant is derived).

    Raises:
        SaveFormatError: a rebased offset falls outside the bounds of
            `body`, naming the raw value, the derived rebase constant,
            and the resulting out-of-range offset.
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

    rebase_constant = raw_global_data_table_1_offset - table_end

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


def iter_change_forms(body: bytes, table: FileLocationTable) -> Iterator[ChangeForm]:
    """Yield exactly `table.change_form_count` ChangeForm records, in
    file order, starting at `table.change_forms_offset`.

    Raises:
        SaveFormatError: a type byte's length-width selector is the
            reserved value 3, or a compressed record's inflated size
            doesn't match its declared length2.
        SaveFormatError (from Reader): any record's declared length1
            would run past the end of `body`.
    """
    r = Reader(body, pos=table.change_forms_offset)
    for i in range(table.change_form_count):
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

        yield ChangeForm(
            ref_type=ref_type,
            ref_value=ref_value,
            flags=flags,
            type=type_byte & 0x3F,
            version=version,
            data=data,
        )


def parse_form_id_array(body: bytes, table: FileLocationTable) -> tuple[int, ...]:
    """Parse the form-id array: a u32 count at
    `table.form_id_array_count_offset`, followed by that many u32 form
    ids.
    """
    r = Reader(body, pos=table.form_id_array_count_offset)
    count = r.u32()
    return tuple(r.u32() for _ in range(count))
