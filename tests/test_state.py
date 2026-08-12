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
