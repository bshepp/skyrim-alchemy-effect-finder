from pathlib import Path
from fastapi.testclient import TestClient

import alchemy_helper.web.app as app_module
from alchemy_helper.web.app import create_app
from alchemy_helper.combinatorics.types import Combo, PlannedBrew

FIXTURE = Path(__file__).parent.parent / "fixtures" / "player.ess"

def client(tmp_path):
    return TestClient(create_app(overrides_path=tmp_path / "o.json",
                                 saves_dir=tmp_path))

def test_dataset_endpoints(tmp_path):
    c = client(tmp_path)
    assert any(i["id"] == "wheat" for i in c.get("/api/ingredients").json())
    assert any(e["id"] == "fortify-health" for e in c.get("/api/effects").json())

def test_load_real_save(tmp_path):
    c = client(tmp_path)
    r = c.post("/api/load-save", json={"path": str(FIXTURE)}).json()
    assert r["mode"] == "save" and r["error"] is None

def test_bad_save_falls_back_to_manual(tmp_path):
    bad = tmp_path / "bad.ess"; bad.write_bytes(b"garbage" * 10)
    c = client(tmp_path)
    r = c.post("/api/load-save", json={"path": str(bad)}).json()
    assert r["mode"] == "manual" and r["error"]

def test_override_roundtrip(tmp_path):
    c = client(tmp_path)
    r = c.post("/api/override",
               json={"ingredient_id": "wheat", "have": 5,
                     "known_slots": [0, 1]}).json()
    assert r["inventory"]["wheat"] == 5
    assert r["known_effects"]["wheat"] == [0, 1]

def test_combinatorics_not_implemented_is_friendly(tmp_path):
    c = client(tmp_path)
    r = c.get("/api/combos", params={"effect": "fortify-health"})
    assert r.status_code == 200 and r.json()["not_implemented"] is True

def test_discovery_plan_not_implemented_is_friendly(tmp_path):
    c = client(tmp_path)
    r = c.get("/api/discovery-plan")
    assert r.status_code == 200 and r.json()["not_implemented"] is True

def test_potion_not_implemented_is_friendly(tmp_path):
    c = client(tmp_path)
    r = c.post("/api/potion", json={"ingredient_ids": ["wheat", "salt"]})
    assert r.status_code == 200 and r.json()["not_implemented"] is True

def test_combos_serializes_expected_json_shape(tmp_path, monkeypatch):
    """Pins the _jsonable seam the frontend destructures: combo.ingredient_ids
    and combo.effect_ids must survive as plain lists in insertion order,
    before the owner's real combinatorics implementation ever runs."""
    def fake_combos_for_effect(effect_id, ingredients, inventory=None):
        return [Combo(ingredient_ids=("wheat", "salt"),
                      effect_ids=("fortify-health",))]

    monkeypatch.setattr(app_module, "combos_for_effect", fake_combos_for_effect)
    c = client(tmp_path)
    r = c.get("/api/combos", params={"effect": "fortify-health"})
    assert r.status_code == 200
    assert r.json() == {
        "combos": [{"ingredient_ids": ["wheat", "salt"],
                    "effect_ids": ["fortify-health"]}]
    }

def test_discovery_plan_serializes_expected_json_shape(tmp_path, monkeypatch):
    """Pins the _jsonable seam for /api/discovery-plan: newly_discovered
    tuples must survive as [id, slot] pairs."""
    def fake_discovery_plan(ingredients, inventory, known_effects):
        return [PlannedBrew(ingredient_ids=("wheat", "salt"),
                            newly_discovered=(("wheat", 0), ("salt", 2)))]

    monkeypatch.setattr(app_module, "discovery_plan", fake_discovery_plan)
    c = client(tmp_path)
    r = c.get("/api/discovery-plan")
    assert r.status_code == 200
    assert r.json() == {
        "plan": [{"ingredient_ids": ["wheat", "salt"],
                  "newly_discovered": [["wheat", 0], ["salt", 2]]}]
    }

def test_state_save_path_is_null_in_manual_mode(tmp_path):
    c = client(tmp_path)
    r = c.get("/api/state").json()
    assert r["save_path"] is None

def test_state_save_path_set_after_loading_a_save(tmp_path):
    c = client(tmp_path)
    c.post("/api/load-save", json={"path": str(FIXTURE)})
    r = c.get("/api/state").json()
    assert r["save_path"] == str(FIXTURE)

def test_override_partial_update_preserves_known_slots(tmp_path):
    c = client(tmp_path)
    c.post("/api/override",
           json={"ingredient_id": "wheat", "have": 5, "known_slots": [0, 1]})
    r = c.post("/api/override", json={"ingredient_id": "wheat", "have": 9}).json()
    assert r["inventory"]["wheat"] == 9
    assert r["known_effects"]["wheat"] == [0, 1]

def test_override_partial_update_preserves_have(tmp_path):
    c = client(tmp_path)
    c.post("/api/override",
           json={"ingredient_id": "wheat", "have": 5, "known_slots": [0, 1]})
    r = c.post("/api/override",
              json={"ingredient_id": "wheat", "known_slots": [2]}).json()
    assert r["inventory"]["wheat"] == 5
    assert r["known_effects"]["wheat"] == [2]

def test_override_explicit_null_clears(tmp_path):
    c = client(tmp_path)
    c.post("/api/override",
           json={"ingredient_id": "wheat", "have": 5, "known_slots": [0, 1]})
    r = c.post("/api/override",
              json={"ingredient_id": "wheat", "have": None}).json()
    assert "wheat" not in r["inventory"]
    assert r["known_effects"]["wheat"] == [0, 1]

def test_override_unknown_ingredient_is_422(tmp_path):
    c = client(tmp_path)
    r = c.post("/api/override",
               json={"ingredient_id": "totally-not-real", "have": 1})
    assert r.status_code == 422

def test_override_negative_have_is_422(tmp_path):
    c = client(tmp_path)
    r = c.post("/api/override", json={"ingredient_id": "wheat", "have": -5})
    assert r.status_code == 422

def test_override_out_of_range_slot_is_422(tmp_path):
    c = client(tmp_path)
    r = c.post("/api/override",
               json={"ingredient_id": "wheat", "known_slots": [7, 99, -1]})
    assert r.status_code == 422
