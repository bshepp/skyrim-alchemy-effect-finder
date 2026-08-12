"""Sequential little-endian byte reader for Skyrim SE save files."""
import struct


class Reader:
    """Reads primitive values out of an in-memory buffer, left to right.

    All multi-byte values are little-endian, matching the SE save format.
    Any read that would run past the end of the buffer raises
    SaveFormatError (imported lazily from .header to avoid a circular
    import, since header.py imports Reader from this module).
    """

    def __init__(self, data: bytes, pos: int = 0):
        self.data = data
        self.pos = pos

    def _take(self, n: int) -> bytes:
        end = self.pos + n
        if end > len(self.data):
            from alchemy_helper.saveparser.header import SaveFormatError
            raise SaveFormatError(
                f"Unexpected end of save data: need {n} byte(s) at offset "
                f"{self.pos}, but only {len(self.data) - self.pos} byte(s) "
                f"remain (buffer is {len(self.data)} byte(s) total)"
            )
        chunk = self.data[self.pos:end]
        self.pos = end
        return chunk

    def read(self, n: int) -> bytes:
        return self._take(n)

    def u8(self) -> int:
        return self._take(1)[0]

    def u16(self) -> int:
        return struct.unpack("<H", self._take(2))[0]

    def u32(self) -> int:
        return struct.unpack("<I", self._take(4))[0]

    def f32(self) -> float:
        return struct.unpack("<f", self._take(4))[0]

    def wstring(self) -> str:
        """A u16 length prefix followed by that many cp1252 bytes."""
        length = self.u16()
        raw = self._take(length)
        return raw.decode("cp1252", errors="replace")
