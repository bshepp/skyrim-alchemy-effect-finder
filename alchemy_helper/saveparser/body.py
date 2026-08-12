"""Decompression of the SE save body, and the plugin/light-plugin lists
that begin it.

Layout reference: UESP "Tes5Mod:Save File Format".

Body decompression (starts at header.body_offset):
    uncompressedLen u32 -> compressedLen u32 -> payload (compressedLen bytes)
    compressionType (from the header) selects how payload decodes to a
    buffer of exactly uncompressedLen bytes:
        0 -> stored raw (payload IS the body, no decompression)
        1 -> zlib
        2 -> LZ4 block format (used by SE 1.6.x, incl. the 1.6.1130+ fixture)

Plugin block (first bytes of the decompressed body):
    formVersion u8 -> pluginInfoSize u32 -> pluginCount u8 -> that many
    wstrings -> lightPluginCount u16 -> that many wstrings.

Verified against tests/fixtures/player.ess (SE 1.6.1130+, formVersion=78):
pluginInfoSize=2112, and after reading pluginCount(=15) + 15 plugin
wstrings + lightPluginCount(=65) + 65 light-plugin wstrings, the cursor
lands at exactly offset 5 + 2112 = 2117 (diff 0 from the declared
plugin-block end). 1.6.1130+ saves were flagged as a version that might
carry extra fields beyond this documented layout, but for this fixture
the plugin block matches it exactly with no leftover/undocumented bytes
-- confirmed with a throwaway hexdump/parse script (not committed)
rather than assumed. parse_plugins() below still raises SaveFormatError
if a future save's cursor lands short of or past plugin_block_end,
rather than silently skipping bytes.
"""
import zlib
from dataclasses import dataclass

import lz4.block

from alchemy_helper.saveparser.header import SaveFormatError, SaveHeader
from alchemy_helper.saveparser.reader import Reader


def read_body(data: bytes, header: SaveHeader) -> bytes:
    """Decompress the save body starting at header.body_offset.

    Raises:
        SaveFormatError: an unsupported compression_type, or a decompressed
            length that doesn't match the declared uncompressedLen.
    """
    r = Reader(data, pos=header.body_offset)
    uncompressed_len = r.u32()
    compressed_len = r.u32()
    payload = r.read(compressed_len)

    if header.compression_type == 0:
        body = payload
    elif header.compression_type == 1:
        body = zlib.decompress(payload)
    elif header.compression_type == 2:
        body = lz4.block.decompress(payload, uncompressed_size=uncompressed_len)
    else:
        raise SaveFormatError(
            f"Unsupported body compression type: expected 0 (none), 1 "
            f"(zlib), or 2 (lz4), observed {header.compression_type}"
        )

    if len(body) != uncompressed_len:
        raise SaveFormatError(
            f"Decompressed body length mismatch: file declares "
            f"uncompressedLen={uncompressed_len}, but decompression "
            f"produced {len(body)} byte(s)"
        )

    return body


@dataclass(frozen=True)
class PluginList:
    form_version: int
    plugins: tuple[str, ...]        # index = load-order slot
    light_plugins: tuple[str, ...]  # ESL slots (FE-prefixed form ids)


def parse_plugins(body: bytes) -> tuple[PluginList, int]:
    """Parse the plugin/light-plugin lists at the start of the save body.

    Returns:
        (plugins, offset_after_plugin_block)

    Raises:
        SaveFormatError: the cursor doesn't land exactly on the declared
            end of the plugin block after reading pluginCount/lightPlugin-
            Count wstrings, naming both the expected and observed offsets.
    """
    r = Reader(body, pos=0)
    form_version = r.u8()
    plugin_info_size = r.u32()
    plugin_block_start = r.pos
    plugin_block_end = plugin_block_start + plugin_info_size

    plugin_count = r.u8()
    plugins = tuple(r.wstring() for _ in range(plugin_count))

    light_plugins: tuple[str, ...] = ()
    if r.pos < plugin_block_end:
        light_count = r.u16()
        light_plugins = tuple(r.wstring() for _ in range(light_count))

    if r.pos != plugin_block_end:
        raise SaveFormatError(
            f"Plugin block size mismatch: file declares pluginInfoSize "
            f"ending at offset {plugin_block_end}, but parsing plugins "
            f"and light plugins left the cursor at offset {r.pos}"
        )

    plugin_list = PluginList(
        form_version=form_version,
        plugins=plugins,
        light_plugins=light_plugins,
    )
    return plugin_list, r.pos
