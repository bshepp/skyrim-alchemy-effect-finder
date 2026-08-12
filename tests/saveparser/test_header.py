import pytest
from pathlib import Path
from alchemy_helper.saveparser.header import parse_header, SaveFormatError

FIXTURE = Path(__file__).parent.parent / "fixtures" / "player.ess"


def test_parses_fixture_header():
    h = parse_header(FIXTURE.read_bytes())
    assert h.version == 12
    assert h.player_name == "Maldric Vane"             # pinned from FACTS.md
    assert h.player_level == 24                        # pinned from FACTS.md
    assert h.compression_type == 2                    # SE 1.6.x uses lz4; if fixture
                                                      # differs, pin observed value


def test_rejects_not_a_save():
    with pytest.raises(SaveFormatError):
        parse_header(b"NOT_A_SAVEGAME" + b"\x00" * 64)


def test_rejects_wrong_version():
    data = bytearray(FIXTURE.read_bytes())
    data[17] = 9   # version u32 starts at offset 17 (13 magic + 4 headerSize)
    with pytest.raises(SaveFormatError, match="9"):
        parse_header(bytes(data))
