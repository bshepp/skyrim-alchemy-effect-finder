"""Parser for the Skyrim Special Edition save-file header.

Layout reference: UESP "Tes5Mod:Save File Format" (SE variant):
    magic (13 bytes) -> headerSize u32 -> header block:
        version u32 (must be 12) -> saveNumber u32 -> playerName wstring
        -> playerLevel u32 -> playerLocation wstring -> gameDate wstring
        -> playerRaceEditorId wstring -> playerSex u16 -> playerCurExp f32
        -> playerLvlUpExp f32 -> filetime (8 bytes) -> shotWidth u32
        -> shotHeight u32 -> compressionType u16
    -> screenshot (4 * shotWidth * shotHeight bytes, RGBA on SE)
    -> body (starts with the compressed-body's uncompressedLen field)

Verified against tests/fixtures/player.ess: headerSize=95 matches the
95 bytes actually consumed parsing the header block above, and the
decoded playerName/playerLevel match tests/fixtures/FACTS.md exactly, so
this layout (including the RGBA screenshot size) needs no adjustment.
"""
from dataclasses import dataclass

from alchemy_helper.saveparser.reader import Reader

MAGIC = b"TESV_SAVEGAME"


class SaveFormatError(Exception):
    """Raised when data does not match the expected SE save format.

    Messages are user-facing diagnostics: they name the observed value
    alongside what was expected, so a user can tell what went wrong.
    """


@dataclass(frozen=True)
class SaveHeader:
    version: int
    save_number: int
    player_name: str
    player_level: int
    player_location: str
    game_date: str
    compression_type: int      # 0 none, 1 zlib, 2 lz4
    body_offset: int           # absolute file offset of uncompressedLen field


def parse_header(data: bytes) -> SaveHeader:
    """Parse the fixed-layout header of an SE .ess save file.

    Raises:
        SaveFormatError: magic mismatch, unsupported version, a headerSize
            that doesn't match the bytes actually consumed by the header
            block, or a screenshot that runs past the end of the file.
    """
    observed_magic = data[:len(MAGIC)]
    if observed_magic != MAGIC:
        raise SaveFormatError(
            f"Not a Skyrim SE save file: expected magic {MAGIC!r}, "
            f"observed {observed_magic!r}"
        )

    r = Reader(data, pos=len(MAGIC))
    header_size = r.u32()
    header_block_start = r.pos

    version = r.u32()
    if version != 12:
        raise SaveFormatError(
            f"Unsupported save format version: expected 12, observed {version}"
        )

    save_number = r.u32()
    player_name = r.wstring()
    player_level = r.u32()
    player_location = r.wstring()
    game_date = r.wstring()
    _player_race_editor_id = r.wstring()
    _player_sex = r.u16()
    _player_cur_exp = r.f32()
    _player_lvl_up_exp = r.f32()
    _filetime = r.read(8)
    shot_width = r.u32()
    shot_height = r.u32()
    compression_type = r.u16()

    consumed = r.pos - header_block_start
    if consumed != header_size:
        raise SaveFormatError(
            f"Header size mismatch: file declares headerSize={header_size}, "
            f"but parsing the header block consumed {consumed} byte(s)"
        )

    screenshot_len = 4 * shot_width * shot_height
    body_offset = r.pos + screenshot_len
    if body_offset > len(data):
        raise SaveFormatError(
            f"Screenshot data truncated: need {screenshot_len} byte(s) "
            f"({shot_width}x{shot_height} RGBA) starting at offset {r.pos}, "
            f"but file is only {len(data)} byte(s)"
        )

    return SaveHeader(
        version=version,
        save_number=save_number,
        player_name=player_name,
        player_level=player_level,
        player_location=player_location,
        game_date=game_date,
        compression_type=compression_type,
        body_offset=body_offset,
    )
