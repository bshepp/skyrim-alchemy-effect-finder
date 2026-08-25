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

def test_combos_endpoint_returns_real_combos(tmp_path):
    c = client(tmp_path)
    r = c.get("/api/combos", params={"effect": "fortify-health"})
    assert r.status_code == 200
    combos = r.json()["combos"]
    assert combos
    assert all("fortify-health" in combo["effect_ids"] for combo in combos)

def test_potion_endpoint_returns_real_effects(tmp_path):
    c = client(tmp_path)
    r = c.post("/api/potion", json={"ingredient_ids": ["wheat", "giants-toe"]})
    assert r.status_code == 200
    assert {e["effect_id"] for e in r.json()["effects"]} == {
        "fortify-health", "damage-stamina-regen"}

def test_discovery_plan_endpoint_returns_real_plan(tmp_path):
    c = client(tmp_path)
    c.post("/api/override", json={"ingredient_id": "wheat", "have": 5})
    c.post("/api/override", json={"ingredient_id": "giants-toe", "have": 5})
    r = c.get("/api/discovery-plan")
    assert r.status_code == 200
    plan = r.json()["plan"]
    # wheat and giant's toe share two effects; one brew reveals both on both.
    assert len(plan) == 1
    assert plan[0]["ingredient_ids"] == ["giants-toe", "wheat"]
    assert len(plan[0]["newly_discovered"]) == 4

def test_best_potions_endpoint_ranks_by_effect_count(tmp_path):
    c = client(tmp_path)
    for iid in ("wheat", "giants-toe", "blue-mountain-flower"):
        c.post("/api/override", json={"ingredient_id": iid, "have": 5})
    r = c.get("/api/best-potions")
    assert r.status_code == 200
    potions = r.json()["potions"]
    assert len(potions) == 4          # the trio + all three pairs share effects
    assert potions[0]["ingredient_ids"] == [
        "blue-mountain-flower", "giants-toe", "wheat"]
    assert potions[0]["effect_ids"] == [
        "damage-stamina-regen", "fortify-health", "restore-health"]
    counts = [len(p["effect_ids"]) for p in potions]
    assert counts == sorted(counts, reverse=True)

def test_best_potions_bad_limit_is_422(tmp_path):
    c = client(tmp_path)
    assert c.get("/api/best-potions", params={"limit": 0}).status_code == 422
    assert c.get("/api/best-potions", params={"limit": 9999}).status_code == 422

def test_potion_unknown_ingredient_is_422(tmp_path):
    c = client(tmp_path)
    r = c.post("/api/potion", json={"ingredient_ids": ["wheat", "not-real"]})
    assert r.status_code == 422

def test_potion_wrong_ingredient_count_is_422(tmp_path):
    c = client(tmp_path)
    for ids in (["wheat"], ["wheat", "garlic", "bee", "giants-toe"],
                ["wheat", "wheat"]):
        assert c.post("/api/potion",
                      json={"ingredient_ids": ids}).status_code == 422

def test_combos_serializes_expected_json_shape(tmp_path, monkeypatch):
    """Pins the _jsonable seam the frontend destructures: combo.ingredient_ids
    and combo.effect_ids must survive as plain lists in insertion order,
    independent of the real combinatorics implementation."""
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
