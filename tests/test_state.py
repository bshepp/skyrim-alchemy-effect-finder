from pathlib import Path
from alchemy_helper.state import Overrides, AppState
from alchemy_helper.data.loader import load_dataset
from alchemy_helper.saveparser.api import PlayerState

def player(inv, known):
    return PlayerState(save_path="x", character_name="T", save_number=1,
                       inventory=inv,
                       known_effects={k: frozenset(v) for k, v in known.items()},
                       unknown_forms=())

def test_overrides_win_over_save(tmp_path):
    ov = Overrides(tmp_path / "o.json")
    ov.set_have("wheat", 99); ov.set_known("wheat", {0, 2})
    st = AppState(load_dataset(), player({"wheat": 3}, {"wheat": {1}}), ov, None)
    assert st.effective_inventory()["wheat"] == 99
    assert st.effective_known()["wheat"] == frozenset({0, 2})
    assert st.mode() == "save"

def test_manual_mode_uses_only_overrides(tmp_path):
    ov = Overrides(tmp_path / "o.json"); ov.set_have("wheat", 2)
    st = AppState(load_dataset(), None, ov, "boom")
    assert st.effective_inventory() == {"wheat": 2}
    assert st.mode() == "manual"

def test_overrides_persist_roundtrip(tmp_path):
    p = tmp_path / "o.json"
    ov = Overrides(p); ov.set_have("wheat", 7); ov.set_known("wheat", {3}); ov.save()
    ov2 = Overrides(p)
    assert ov2.have == {"wheat": 7} and ov2.known == {"wheat": {3}}

def test_corrupt_json_nondictionary_toplevel(tmp_path):
    """Non-dict top-level (e.g. array) should degrade to empty."""
    p = tmp_path / "o.json"
    p.write_text("[1, 2, 3]")
    ov = Overrides(p)
    assert ov.have == {} and ov.known == {}

def test_corrupt_json_known_as_list(tmp_path):
    """'known' field as list instead of dict should degrade gracefully."""
    p = tmp_path / "o.json"
    p.write_text('{"have": {"wheat": 5}, "known": [0, 1]}')
    ov = Overrides(p)
    assert ov.have == {"wheat": 5} and ov.known == {}

def test_corrupt_json_have_as_string(tmp_path):
    """'have' field as string instead of dict should degrade gracefully."""
    p = tmp_path / "o.json"
    p.write_text('{"have": "not a dict", "known": {}}')
    ov = Overrides(p)
    assert ov.have == {} and ov.known == {}

def test_non_utf8_bytes(tmp_path):
    """Non-UTF-8 file should degrade to empty, not crash."""
    p = tmp_path / "o.json"
    p.write_bytes(b'\xff\xfe{"have": {"wheat": 5}}')  # UTF-16 BOM
    ov = Overrides(p)
    assert ov.have == {} and ov.known == {}

def test_set_known_coerces_to_set(tmp_path):
    """set_known() should coerce input to set type."""
    ov = Overrides(tmp_path / "o.json")
    # Pass a frozenset (should be coerced to set)
    ov.set_known("wheat", frozenset({1, 2}))
    assert ov.known["wheat"] == {1, 2}
    assert isinstance(ov.known["wheat"], set)
