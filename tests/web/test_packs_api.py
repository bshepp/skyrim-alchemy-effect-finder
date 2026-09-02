"""Pack activation through the web layer: the save's own load order
decides which dataset packs apply, and loading re-parses so pack
ingredients resolve instead of appearing as unknown forms."""
from pathlib import Path

from fastapi.testclient import TestClient

import alchemy_helper.web.app as app_module
from alchemy_helper.saveparser.api import PlayerState, UnknownForm
from alchemy_helper.web.app import create_app

FIXTURE = Path(__file__).parent.parent / "fixtures" / "player.ess"

CAUSE_PLUGINS = ("Skyrim.esm", "Update.esm", "ccBGSSSE067-DaedInv.esm")
VANILLA_PLUGINS = ("Skyrim.esm", "Update.esm")


def client(tmp_path):
    return TestClient(create_app(overrides_path=tmp_path / "o.json",
                                 saves_dir=tmp_path))


def fake_cause_save(path, dataset):
    """A save carrying Bloodgrass. Against the base dataset the form is
    unknown; once the-cause is active it resolves - which is exactly the
    two-pass behavior the endpoint must exercise."""
    if "bloodgrass" in dataset.ingredients:
        return PlayerState(
            save_path=str(path), character_name="Mythic Dawn Enjoyer",
            save_number=7, inventory={"bloodgrass": 2, "wheat": 1},
            known_effects={}, unknown_forms=(), plugins=CAUSE_PLUGINS)
    return PlayerState(
        save_path=str(path), character_name="Mythic Dawn Enjoyer",
        save_number=7, inventory={"wheat": 1}, known_effects={},
        unknown_forms=(UnknownForm("ccbgssse067-daedinv.esm", 0x024C13),),
        plugins=CAUSE_PLUGINS)


def fake_vanilla_save(path, dataset):
    return PlayerState(
        save_path=str(path), character_name="Purist",
        save_number=8, inventory={"wheat": 3}, known_effects={},
        unknown_forms=(), plugins=VANILLA_PLUGINS)


def test_pack_activates_and_forms_resolve(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "parse_save", fake_cause_save)
    c = client(tmp_path)
    r = c.post("/api/load-save", json={"path": "whatever.ess"}).json()
    assert r["packs"] == [{"id": "the-cause", "name": "The Cause (Creation)"}]
    assert r["inventory"]["bloodgrass"] == 2
    assert r["unknown_forms"] == []
    assert any(i["id"] == "bloodgrass"
               for i in c.get("/api/ingredients").json())


def test_pack_deactivates_on_vanilla_save(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "parse_save", fake_cause_save)
    c = client(tmp_path)
    c.post("/api/load-save", json={"path": "modded.ess"})
    monkeypatch.setattr(app_module, "parse_save", fake_vanilla_save)
    r = c.post("/api/load-save", json={"path": "vanilla.ess"}).json()
    assert r["packs"] == []
    assert not any(i["id"] == "bloodgrass"
                   for i in c.get("/api/ingredients").json())


def test_real_fixture_save_activates_the_cause(tmp_path):
    """The fixture save comes from an Anniversary Edition game, so The
    Cause's plugin is genuinely in its load order - the pack activates
    on real data (the character just isn't carrying Deadlands flora)."""
    c = client(tmp_path)
    r = c.post("/api/load-save", json={"path": str(FIXTURE)}).json()
    assert r["error"] is None
    assert r["packs"] == [{"id": "the-cause",
                           "name": "The Cause (Creation)"}]
    assert r["unknown_forms"] == []
