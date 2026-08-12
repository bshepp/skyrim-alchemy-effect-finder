from pathlib import Path
from fastapi.testclient import TestClient
from alchemy_helper.web.app import create_app

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
