from pathlib import Path
from alchemy_helper.saveparser.header import parse_header
from alchemy_helper.saveparser.body import read_body, parse_plugins
from alchemy_helper.saveparser.changeforms import (
    parse_file_location_table, iter_change_forms, parse_form_id_array)

FIXTURE = Path(__file__).parent.parent / "fixtures" / "player.ess"


def load():
    data = FIXTURE.read_bytes()
    body = read_body(data, parse_header(data))
    _, after = parse_plugins(body)
    return body, parse_file_location_table(body, after)


def test_iterates_every_change_form_without_overrun():
    body, table = load()
    forms = list(iter_change_forms(body, table))
    assert len(forms) == table.change_form_count
    assert table.change_form_count > 1000   # real saves have many thousands


def test_form_id_array_nonempty():
    body, table = load()
    assert len(parse_form_id_array(body, table)) > 100


def test_player_change_form_exists():
    body, table = load()
    # Player reference: refID literal 0x14 (ref_type 1, value 0x14)
    assert any(f.ref_type == 1 and f.ref_value == 0x14
               for f in iter_change_forms(body, table))
