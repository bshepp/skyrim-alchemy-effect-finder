# Skyrim Alchemy Effect Finder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A local Python web app that reads a Skyrim SE save, shows which ingredient effects the player has/hasn't discovered, and exposes clean interfaces for a user-written combinatorics module.

**Architecture:** Four hard-bounded modules under one package: `data/` (static JSON dataset + validating loader), `saveparser/` (narrow SE 1.6.x `.ess` reader), `combinatorics/` (USER-OWNED: agents write stubs + tests only, never bodies), `web/` (FastAPI + vanilla-JS frontend). Spec: `docs/superpowers/specs/2026-08-10-alchemy-effect-finder-design.md`.

**Tech Stack:** Python 3.12+, FastAPI, uvicorn, lz4, pytest, httpx (tests). Frontend: hand-written HTML/JS/CSS, no framework, no CDN.

## Global Constraints

- Python `>=3.12`. Runtime deps exactly: `fastapi`, `uvicorn`, `lz4`. Dev deps: `pytest`, `httpx`.
- **Agents NEVER implement `combinatorics/` function bodies.** Stubs raise `NotImplementedError`; the user implements them. Combinatorics tests carry `@pytest.mark.combinatorics` and are excluded from default runs via pytest `addopts`.
- No GPL code may be copied. `reference/SkyrimAlchemyHelper` (gitignored clone) and UESP docs are read-only format references.
- No internet access at runtime; server binds `127.0.0.1` only; frontend loads zero external resources.
- Save support target: SE save **header version 12** exactly; anything else raises `SaveFormatError` whose message includes the observed version numbers. Parse failure must never crash the app — the web layer falls back to manual mode.
- License MIT. Windows paths must tolerate OneDrive-redirected `Documents`.
- All strings in save files decode as `cp1252` with `errors="replace"`.

---

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `LICENSE`, `README.md`,
  `alchemy_helper/__init__.py`, `alchemy_helper/data/__init__.py`,
  `alchemy_helper/saveparser/__init__.py`, `alchemy_helper/combinatorics/__init__.py`,
  `alchemy_helper/web/__init__.py`, `tests/__init__.py`
- Test: `tests/test_scaffold.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: installable package `alchemy_helper` with subpackages `data`, `saveparser`, `combinatorics`, `web`; pytest configured so marker `combinatorics` is excluded by default.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scaffold.py
def test_package_imports():
    import alchemy_helper
    import alchemy_helper.data
    import alchemy_helper.saveparser
    import alchemy_helper.combinatorics
    import alchemy_helper.web
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scaffold.py -v`
Expected: FAIL (`ModuleNotFoundError: alchemy_helper`)

- [ ] **Step 3: Create the scaffold**

`pyproject.toml`:

```toml
[project]
name = "alchemy-helper"
version = "0.1.0"
description = "Skyrim SE alchemy effect finder and discovery planner (local web app)"
requires-python = ">=3.12"
license = { text = "MIT" }
dependencies = ["fastapi>=0.115", "uvicorn>=0.30", "lz4>=4.3"]

[project.optional-dependencies]
dev = ["pytest>=8", "httpx>=0.27"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["alchemy_helper*"]

[tool.pytest.ini_options]
addopts = "-m 'not combinatorics'"
markers = [
  "combinatorics: tests for the user-implemented module (run with: pytest -m combinatorics)",
]
```

`.gitignore`:

```
__pycache__/
*.egg-info/
.pytest_cache/
reference/
.venv/
```

`LICENSE`: standard MIT text, copyright `2026 <user's name — ask if unknown, else "Snarf">`.

`README.md` (stub — Task 13 completes it):

```markdown
# Skyrim Alchemy Effect Finder

Local web app for Skyrim SE alchemy: reads your save, tracks discovered
effects, finds ingredient combos. See docs/superpowers/specs/ for design.

## Setup
    pip install -e .[dev]
    python -m alchemy_helper
```

All five `__init__.py` files: empty.

- [ ] **Step 4: Install and run test to verify it passes**

Run: `pip install -e .[dev]` then `pytest tests/test_scaffold.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: project scaffold (package layout, pytest config, MIT license)"
```

---

### Task 2: Dataset models, loader, validator

**Files:**
- Create: `alchemy_helper/data/models.py`, `alchemy_helper/data/loader.py`
- Test: `tests/data/test_loader.py` (create `tests/data/__init__.py`)

**Interfaces:**
- Consumes: nothing.
- Produces (used by every later task):

```python
# alchemy_helper/data/models.py
from dataclasses import dataclass

@dataclass(frozen=True)
class Effect:
    id: str            # slug, e.g. "fortify-health"
    name: str          # "Fortify Health"
    description: str
    harmful: bool

@dataclass(frozen=True)
class Ingredient:
    id: str                             # slug, e.g. "wheat"
    name: str                           # "Wheat"
    plugin: str                         # e.g. "Skyrim.esm", "ccBGSSSE037-Curios.esl"
    form_id: int                        # object id WITHOUT load-order prefix
                                        #   .esm/.esp: lower 24 bits; .esl: lower 12 bits
    effects: tuple[str, str, str, str]  # effect ids, in-game slot order

# alchemy_helper/data/loader.py
class DatasetError(Exception): ...

@dataclass(frozen=True)
class Dataset:
    effects: dict[str, Effect]          # keyed by id
    ingredients: dict[str, Ingredient]  # keyed by id

def load_dataset(data_dir: Path | None = None) -> Dataset
    # default data_dir = Path(__file__).parent (reads effects.json, ingredients.json)
    # raises DatasetError naming the offending entry on any validation failure
```

Validation rules (each raises `DatasetError` mentioning the bad id): every ingredient has exactly 4 effects; every referenced effect id exists; no duplicate ingredient/effect ids; `plugin` non-empty; `form_id >= 0`.

JSON shapes:

```json
// effects.json                          // ingredients.json
[{"id": "fortify-health",               [{"id": "wheat",
  "name": "Fortify Health",               "name": "Wheat",
  "description": "Health is increased.",  "plugin": "Skyrim.esm",
  "harmful": false}]                      "form_id": 308782,
                                          "effects": ["restore-health", "fortify-health",
                                                      "damage-stamina-regen",
                                                      "lingering-damage-magicka"]}]
```

- [ ] **Step 1: Write the failing tests**

```python
# tests/data/test_loader.py
import json, pytest
from pathlib import Path
from alchemy_helper.data.loader import load_dataset, DatasetError

GOOD_EFFECTS = [
    {"id": "e1", "name": "E1", "description": "d", "harmful": False},
    {"id": "e2", "name": "E2", "description": "d", "harmful": True},
    {"id": "e3", "name": "E3", "description": "d", "harmful": False},
    {"id": "e4", "name": "E4", "description": "d", "harmful": False},
]
GOOD_INGREDIENTS = [
    {"id": "a", "name": "A", "plugin": "Skyrim.esm", "form_id": 1,
     "effects": ["e1", "e2", "e3", "e4"]},
]

def write(tmp_path: Path, effects, ingredients) -> Path:
    (tmp_path / "effects.json").write_text(json.dumps(effects))
    (tmp_path / "ingredients.json").write_text(json.dumps(ingredients))
    return tmp_path

def test_loads_valid_dataset(tmp_path):
    ds = load_dataset(write(tmp_path, GOOD_EFFECTS, GOOD_INGREDIENTS))
    assert ds.ingredients["a"].effects == ("e1", "e2", "e3", "e4")
    assert ds.effects["e2"].harmful is True

def test_rejects_wrong_effect_count(tmp_path):
    bad = [dict(GOOD_INGREDIENTS[0], effects=["e1", "e2", "e3"])]
    with pytest.raises(DatasetError, match="a"):
        load_dataset(write(tmp_path, GOOD_EFFECTS, bad))

def test_rejects_unknown_effect_ref(tmp_path):
    bad = [dict(GOOD_INGREDIENTS[0], effects=["e1", "e2", "e3", "nope"])]
    with pytest.raises(DatasetError, match="nope"):
        load_dataset(write(tmp_path, GOOD_EFFECTS, bad))

def test_rejects_duplicate_ids(tmp_path):
    with pytest.raises(DatasetError, match="a"):
        load_dataset(write(tmp_path, GOOD_EFFECTS, GOOD_INGREDIENTS * 2))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/data -v`
Expected: FAIL (`ModuleNotFoundError` / `ImportError`)

- [ ] **Step 3: Implement models.py and loader.py** exactly per the Produces block (loader: read both JSON files with `json.loads(path.read_text(encoding="utf-8"))`, build frozen dataclasses, run the five validation rules).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/data -v` — Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add alchemy_helper/data tests/data
git commit -m "feat: dataset models and validating loader"
```

---

### Task 3: Compile the real dataset from UESP

**Files:**
- Create: `alchemy_helper/data/effects.json`, `alchemy_helper/data/ingredients.json`
- Test: `tests/data/test_dataset_content.py`

**Interfaces:**
- Consumes: `load_dataset` from Task 2.
- Produces: the shipped dataset — every ingredient in vanilla Skyrim SE + Dawnguard + Hearthfire + Dragonborn + the four free Creations (Fishing, Survival Mode, Saints & Seducers, Rare Curios), with UESP-sourced names, form ids, and slot-ordered effects.

- [ ] **Step 1: Write the golden tests first** (they will fail until the JSON exists)

```python
# tests/data/test_dataset_content.py
from alchemy_helper.data.loader import load_dataset

def test_shipped_dataset_is_valid():
    ds = load_dataset()  # default dir → shipped JSON
    assert len(ds.ingredients) > 100   # vanilla alone has ~63; with DLC+CC well over 100
    assert len(ds.effects) >= 55

def test_wheat_golden():
    ds = load_dataset()
    assert ds.ingredients["wheat"].effects == (
        "restore-health", "fortify-health",
        "damage-stamina-regen", "lingering-damage-magicka")
    assert ds.ingredients["wheat"].plugin == "Skyrim.esm"

def test_giants_toe_golden():
    ds = load_dataset()
    assert ds.ingredients["giants-toe"].effects == (
        "damage-stamina", "fortify-health",
        "fortify-carry-weight", "damage-stamina-regen")

def test_blue_mountain_flower_golden():
    ds = load_dataset()
    assert ds.ingredients["blue-mountain-flower"].effects == (
        "restore-health", "fortify-conjuration",
        "fortify-health", "damage-magicka-regen")

def test_creation_club_plugins_present():
    ds = load_dataset()
    plugins = {i.plugin for i in ds.ingredients.values()}
    assert any("curios" in p.lower() for p in plugins)      # Rare Curios
    assert any(p == "Skyrim.esm" for p in plugins)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/data/test_dataset_content.py -v`
Expected: FAIL (missing effects.json / ingredients.json)

- [ ] **Step 3: Compile the dataset.** Sources (fetch and read carefully — this is data entry, accuracy is the whole point):
  - `https://en.uesp.net/wiki/Skyrim:Ingredients` — vanilla + DLC table: name, form id, 4 effects in slot order.
  - `https://en.uesp.net/wiki/Skyrim:Alchemy_Effects` — effect names, descriptions, harmful flag (listed as "poison"/negative).
  - Creations: `https://en.uesp.net/wiki/Skyrim:Rare_Curios` and `https://en.uesp.net/wiki/Skyrim:Saints_%26_Seducers` (follow their ingredient links), `https://en.uesp.net/wiki/Skyrim:Fishing` for fish/ingredient items, `https://en.uesp.net/wiki/Skyrim:Survival_Mode` (verify: likely adds no ingredients — if so record that in a comment in this test file). UESP lists CC form ids as `FExxx###` — store only the low 12 bits as `form_id` and the `.esl` plugin file name (also on those pages).
  - Slug rule: lowercase name, spaces→`-`, drop apostrophes (`Giant's Toe` → `giants-toe`).
  - After compiling, update the two count assertions in `test_shipped_dataset_is_valid` to the **exact** counts you shipped, with a comment naming the UESP page totals they were checked against.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/data -v` — Expected: all PASS (loader validation + goldens)

- [ ] **Step 5: Commit**

```bash
git add alchemy_helper/data/*.json tests/data/test_dataset_content.py
git commit -m "feat: ship vanilla+DLC+Creations ingredient/effect dataset from UESP"
```

---

### Task 4: Real save fixture (USER CHECKPOINT — pause and ask)

**Files:**
- Create: `tests/fixtures/player.ess` (copied from user), `tests/fixtures/FACTS.md`

**Interfaces:**
- Consumes: nothing.
- Produces: the golden fixture every saveparser test pins against, plus `FACTS.md` recording ground truth to assert.

- [ ] **Step 1: PAUSE — ask the user for the following** (this task cannot proceed without them):
  1. Copy one recent `.ess` save into `tests/fixtures/player.ess`. Saves live in `Documents\My Games\Skyrim Special Edition\Saves` (check `OneDrive\Documents\...` if not there). Prefer a manual/quicksave made at a spot they remember.
  2. Character name and level as shown in-game for that save.
  3. In-game, open a crafting table or inventory and record: exact carried counts of **three** ingredients they hold (e.g. "Wheat ×7"), and for **two** of those, which effects currently show as discovered (green/named) vs undiscovered.
- [ ] **Step 2: Write `tests/fixtures/FACTS.md`** recording all of the above verbatim, plus the save's file size and date. These numbers get pinned into tests in Tasks 5–8.
- [ ] **Step 3: Commit**

```bash
git add tests/fixtures
git commit -m "test: add real SE save fixture and ground-truth facts"
```

---

### Task 5: Save header parser

**Files:**
- Create: `alchemy_helper/saveparser/reader.py`, `alchemy_helper/saveparser/header.py`
- Test: `tests/saveparser/test_header.py` (create `tests/saveparser/__init__.py`)

**Interfaces:**
- Consumes: fixture from Task 4.
- Produces:

```python
# alchemy_helper/saveparser/reader.py
class Reader:
    def __init__(self, data: bytes, pos: int = 0)
    pos: int
    def u8(self) -> int; def u16(self) -> int; def u32(self) -> int
    def f32(self) -> float; def read(self, n: int) -> bytes
    def wstring(self) -> str   # u16 length + bytes, cp1252, errors="replace"
    # all little-endian; raise SaveFormatError on overrun

# alchemy_helper/saveparser/header.py
class SaveFormatError(Exception): ...   # message is user-facing diagnostic
MAGIC = b"TESV_SAVEGAME"

@dataclass(frozen=True)
class SaveHeader:
    version: int; save_number: int
    player_name: str; player_level: int; player_location: str; game_date: str
    compression_type: int      # 0 none, 1 zlib, 2 lz4
    body_offset: int           # absolute file offset of uncompressedLen field

def parse_header(data: bytes) -> SaveHeader
```

Header layout (UESP "Tes5Mod:Save File Format" — SE): magic (13 bytes) · headerSize u32 · then the header block: version u32 (**must be 12**; else `SaveFormatError` reporting the value) · saveNumber u32 · playerName wstring · playerLevel u32 · playerLocation wstring · gameDate wstring · playerRaceEditorId wstring · playerSex u16 · playerCurExp f32 · playerLvlUpExp f32 · filetime 8 bytes · shotWidth u32 · shotHeight u32 · compressionType u16. After the header block: screenshot = `4 * shotWidth * shotHeight` bytes (SE is RGBA); `body_offset` = position after screenshot. Cross-check consumed header bytes against headerSize; mismatch → `SaveFormatError` naming both numbers.

- [ ] **Step 1: Write the failing tests**

```python
# tests/saveparser/test_header.py
import pytest
from pathlib import Path
from alchemy_helper.saveparser.header import parse_header, SaveFormatError

FIXTURE = Path(__file__).parent.parent / "fixtures" / "player.ess"

def test_parses_fixture_header():
    h = parse_header(FIXTURE.read_bytes())
    assert h.version == 12
    assert h.player_name == "<NAME FROM FACTS.md>"   # pin real value
    assert h.player_level == 0                        # pin real value
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
```

- [ ] **Step 2: Run tests to verify they fail** — `pytest tests/saveparser -v` → ImportError.
- [ ] **Step 3: Implement `Reader` and `parse_header`** per the layout above. Replace the two `<pin>` placeholders in the test with values from `FACTS.md` / observed parse (print the parsed header once, eyeball against FACTS.md, then pin).
- [ ] **Step 4: Run tests to verify they pass** — `pytest tests/saveparser -v` → 3 PASS.
- [ ] **Step 5: Commit**

```bash
git add alchemy_helper/saveparser tests/saveparser
git commit -m "feat: SE save header parser with version/diagnostic guards"
```

---

### Task 6: Body decompression + plugin lists

**Files:**
- Create: `alchemy_helper/saveparser/body.py`
- Test: `tests/saveparser/test_body.py`

**Interfaces:**
- Consumes: `parse_header`, `Reader`, `SaveFormatError`, fixture.
- Produces:

```python
# alchemy_helper/saveparser/body.py
def read_body(data: bytes, header: SaveHeader) -> bytes
    # at header.body_offset: uncompressedLen u32, compressedLen u32, payload.
    # compression_type 2 → lz4.block.decompress(payload, uncompressed_size=uncompressedLen)
    # 1 → zlib.decompress; 0 → raw. Wrong final length → SaveFormatError (both lengths in msg).

@dataclass(frozen=True)
class PluginList:
    form_version: int
    plugins: tuple[str, ...]        # index = load-order slot
    light_plugins: tuple[str, ...]  # ESL slots (FE-prefixed form ids)

def parse_plugins(body: bytes) -> tuple[PluginList, int]
    # returns (plugins, offset_after_plugin_block)
    # body[0]: formVersion u8 · pluginInfoSize u32 · pluginCount u8 · that many wstrings
    # · if cursor < end-of-plugin-block: lightPluginCount u16 · that many wstrings
    # cursor must land exactly on end-of-block; else SaveFormatError naming both offsets.
```

- [ ] **Step 1: Write the failing tests**

```python
# tests/saveparser/test_body.py
from pathlib import Path
from alchemy_helper.saveparser.header import parse_header
from alchemy_helper.saveparser.body import read_body, parse_plugins

FIXTURE = Path(__file__).parent.parent / "fixtures" / "player.ess"

def test_body_decompresses():
    data = FIXTURE.read_bytes()
    body = read_body(data, parse_header(data))
    assert len(body) > 1_000_000   # decompressed SE bodies are multi-MB

def test_plugin_lists():
    data = FIXTURE.read_bytes()
    plugins, _ = parse_plugins(read_body(data, parse_header(data)))
    assert "Skyrim.esm" in plugins.plugins
    assert any(p.lower().startswith("cc") for p in
               plugins.plugins + plugins.light_plugins)  # free Creations present
    # After first successful run, print full lists, cross-check against the
    # user's game (they said: vanilla + free Creations only), then pin exact
    # tuple equality here.
```

- [ ] **Step 2: Run tests to verify they fail** — `pytest tests/saveparser/test_body.py -v` → ImportError.
- [ ] **Step 3: Implement `body.py`.** If `parse_plugins` hits the block-end mismatch on the real fixture, STOP and diff against the reference implementation (`reference/SkyrimAlchemyHelper/libs/saveParser/Save.cpp` — clone per Task 8 Step 3 note — and UESP's page); 1.6.1130+ saves may carry extra fields — locate them empirically, document the finding in a comment, adjust. Then pin the exact plugin tuples in the test.
- [ ] **Step 4: Run tests to verify they pass** — `pytest tests/saveparser -v` → all PASS.
- [ ] **Step 5: Commit**

```bash
git add alchemy_helper/saveparser/body.py tests/saveparser/test_body.py
git commit -m "feat: save body decompression and plugin/light-plugin lists"
```

---

### Task 7: File location table + change-form iterator

**Files:**
- Create: `alchemy_helper/saveparser/changeforms.py`
- Test: `tests/saveparser/test_changeforms.py`

**Interfaces:**
- Consumes: `read_body`, `parse_plugins`, `Reader`, fixture.
- Produces:

```python
# alchemy_helper/saveparser/changeforms.py
@dataclass(frozen=True)
class FileLocationTable:
    form_id_array_count_offset: int; unknown_table_3_offset: int
    global_data_table_1_offset: int; global_data_table_2_offset: int
    change_forms_offset: int; global_data_table_3_offset: int
    global_data_table_1_count: int; global_data_table_2_count: int
    global_data_table_3_count: int; change_form_count: int

def parse_file_location_table(body: bytes, after_plugins: int) -> FileLocationTable
    # 10 u32 fields in the order above, then 15 unused u32s.
    # NOTE: verify empirically whether offsets are relative to body start or
    # need rebasing; validate by checking change_forms_offset lands on a sane
    # first record. Document the finding in a comment.

@dataclass(frozen=True)
class ChangeForm:
    ref_type: int    # top 2 bits of refID: 0=formID-array index, 1=literal form, 2=created
    ref_value: int   # low 22 bits
    flags: int       # changeFlags u32
    type: int        # low 6 bits of type byte
    version: int
    data: bytes      # zlib-inflated when length2 != 0

def iter_change_forms(body: bytes, table: FileLocationTable) -> Iterator[ChangeForm]
    # per record: refID 3 bytes (big-endian: b[0]<<16|b[1]<<8|b[2]) · flags u32 ·
    # typeByte u8 (bits 6-7 select length width: 0→u8, 1→u16, 2→u32) · version u8 ·
    # length1 · length2 · data[length1]; if length2: data = zlib.decompress(data)

def parse_form_id_array(body: bytes, table: FileLocationTable) -> tuple[int, ...]
    # at form_id_array_count_offset: count u32, then count u32 form ids
```

- [ ] **Step 1: Write the failing tests**

```python
# tests/saveparser/test_changeforms.py
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
```

- [ ] **Step 2: Run tests to verify they fail** — ImportError.
- [ ] **Step 3: Implement `changeforms.py`.** The iterator consuming exactly `change_form_count` records with no `Reader` overrun IS the structural proof. If the first record is garbage, the offsets need rebasing — resolve empirically (try body-start-relative first), consult reference `Save.cpp`, document in a comment.
- [ ] **Step 4: Run tests to verify they pass** — `pytest tests/saveparser -v` → all PASS.
- [ ] **Step 5: Commit**

```bash
git add alchemy_helper/saveparser/changeforms.py tests/saveparser/test_changeforms.py
git commit -m "feat: file location table and change-form iterator"
```

---

### Task 8: Extract inventory + known effects → PlayerState

**Files:**
- Create: `alchemy_helper/saveparser/extract.py`, `alchemy_helper/saveparser/api.py`
- Test: `tests/saveparser/test_extract.py`

**Interfaces:**
- Consumes: everything from Tasks 5–7, `Dataset` from Task 2, fixture + `FACTS.md`.
- Produces (the saveparser's ONLY public surface — web layer imports just this):

```python
# alchemy_helper/saveparser/api.py
@dataclass(frozen=True)
class UnknownForm:
    plugin: str; form_id: int

@dataclass(frozen=True)
class PlayerState:
    save_path: str
    character_name: str
    save_number: int
    inventory: dict[str, int]            # ingredient id -> carried count
    known_effects: dict[str, frozenset[int]]  # ingredient id -> known slots (0-3)
    unknown_forms: tuple[UnknownForm, ...]    # INGR-ish forms not in dataset

def parse_save(path: Path, dataset: Dataset) -> PlayerState
    # orchestrates header→body→plugins→changeforms→extract;
    # ANY parsing exception is re-raised as SaveFormatError with diagnostics
    # (save version, form version, step that failed)
```

`extract.py` internals: build a resolver from `PluginList` — a save formID's top byte indexes `plugins` (local id = low 24 bits) unless `0xFE`, where bits 12–23 index `light_plugins` (local id = low 12 bits); map `(plugin, local_id) → ingredient_id` from the dataset. Decode change-form refIDs: ref_type 0 → `form_id_array[value - 1]` (value 0 → form 0), ref_type 1 → value is the formID, ref_type 2 → created (`0xFF000000 | value`, never an ingredient). Then:
1. **Known effects:** change forms whose resolved formID is a dataset ingredient carry ingredient-use data; the known-slots bitmask location within `data` must be ported *by reading* `reference/SkyrimAlchemyHelper/libs/saveParser/Save.cpp` (its ingredient/change-form handling — no code copied, understanding only) and UESP's Change Form docs.
2. **Inventory:** the player change form (ref_type 1, value 0x14) contains the inventory when its `flags` include the inventory change flag; port the entry format (formID + count pairs within the extra/inventory section) the same way.

- [ ] **Step 1: Clone the reference repo (gitignored):**

```bash
git clone --depth 1 https://github.com/cguebert/SkyrimAlchemyHelper reference/SkyrimAlchemyHelper
```

- [ ] **Step 2: Write a throwaway dump script** `scratch_dump.py` (do NOT commit) that prints: distinct change-form `type` values for dataset-ingredient formIDs, hex of the player form's first 200 data bytes, and candidate inventory entries. Iterate against `Save.cpp` + UESP until the three FACTS.md ingredient counts and the two known-effect patterns appear. Record the decoded layout as comments in `extract.py`.
- [ ] **Step 3: Write the failing tests** (pin FACTS.md values):

```python
# tests/saveparser/test_extract.py
from pathlib import Path
from alchemy_helper.data.loader import load_dataset
from alchemy_helper.saveparser.api import parse_save

FIXTURE = Path(__file__).parent.parent / "fixtures" / "player.ess"

def test_player_state_matches_in_game_facts():
    st = parse_save(FIXTURE, load_dataset())
    assert st.character_name == "<FACTS.md name>"
    # Pin the three ingredient counts the user recorded in-game:
    assert st.inventory["<ing-1>"] == 0   # replace with FACTS.md values
    assert st.inventory["<ing-2>"] == 0
    assert st.inventory["<ing-3>"] == 0
    # Pin the two known-effects observations:
    assert st.known_effects["<ing-1>"] == frozenset({0})   # per FACTS.md
    assert st.known_effects["<ing-2>"] == frozenset()      # per FACTS.md

def test_unknown_forms_are_collected_not_fatal():
    st = parse_save(FIXTURE, load_dataset())
    assert isinstance(st.unknown_forms, tuple)  # vanilla+CC game: likely empty —
                                                # pin the observed value
```

- [ ] **Step 4: Run tests to verify they fail**, implement `extract.py` + `api.py`, rerun until PASS: `pytest tests/saveparser -v`
- [ ] **Step 5: Delete `scratch_dump.py`, commit**

```bash
git add alchemy_helper/saveparser tests/saveparser/test_extract.py
git commit -m "feat: extract player inventory and known ingredient effects from save"
```

---

### Task 9: Combinatorics contracts — stubs + user test suite (NO BODIES)

**Files:**
- Create: `alchemy_helper/combinatorics/types.py`, `alchemy_helper/combinatorics/core.py`
- Test: `tests/combinatorics/test_user_module.py` (create `tests/combinatorics/__init__.py`)

**Interfaces:**
- Consumes: `Ingredient` from Task 2.
- Produces (web layer depends on exactly these signatures):

```python
# alchemy_helper/combinatorics/types.py
@dataclass(frozen=True)
class Combo:
    ingredient_ids: tuple[str, ...]   # 2 or 3 ids, sorted
    effect_ids: tuple[str, ...]       # every effect this mix produces, sorted

@dataclass(frozen=True)
class EffectResult:
    effect_id: str
    ingredient_ids: tuple[str, ...]   # the >=2 mix members sharing it, sorted

@dataclass(frozen=True)
class PlannedBrew:
    ingredient_ids: tuple[str, ...]
    newly_discovered: tuple[tuple[str, int], ...]  # (ingredient_id, slot 0-3)

# alchemy_helper/combinatorics/core.py   — USER IMPLEMENTS THE BODIES
def combos_for_effect(effect_id: str, ingredients: Sequence[Ingredient],
                      inventory: Mapping[str, int] | None = None) -> list[Combo]:
    """Every 2- or 3-ingredient combination producing effect_id.
    inventory=None → all ingredients; else only ids with count >= 1."""
    raise NotImplementedError  # ← user's playground; agents must not touch

def potion_effects(ingredient_ids: Sequence[str],
                   ingredients: Sequence[Ingredient]) -> list[EffectResult]:
    """Effects of mixing 2-3 ingredients: an effect appears iff >=2 share it.
    Empty list = mix produces nothing (game refuses the brew)."""
    raise NotImplementedError

def discovery_plan(ingredients: Sequence[Ingredient],
                   inventory: Mapping[str, int],
                   known_effects: Mapping[str, AbstractSet[int]]) -> list[PlannedBrew]:
    """Brews discovering EVERY effect reachable from inventory, in as few brews
    as possible (coverage is the hard objective, count the tiebreaker).
    Each brew consumes 1 of each used ingredient; brewing reveals each matched
    effect on every participating ingredient having it."""
    raise NotImplementedError
```

- [ ] **Step 1: Write types.py and core.py** exactly as above (full docstrings; bodies are single `raise NotImplementedError` statements).
- [ ] **Step 2: Write the user's test suite** — all tests marked, real assertions:

```python
# tests/combinatorics/test_user_module.py
import pytest
from alchemy_helper.data.models import Ingredient
from alchemy_helper.data.loader import load_dataset
from alchemy_helper.combinatorics.core import (
    combos_for_effect, potion_effects, discovery_plan)
from alchemy_helper.combinatorics.types import Combo, EffectResult, PlannedBrew

pytestmark = pytest.mark.combinatorics   # excluded from default runs

def ing(id_, *effects):
    return Ingredient(id=id_, name=id_.upper(), plugin="Test.esp",
                      form_id=0, effects=tuple(effects))

A = ing("a", "e1", "e2", "e3", "e4")
B = ing("b", "e1", "e5", "e6", "e7")
C = ing("c", "e2", "e5", "e8", "e9")
TRIO = [A, B, C]

# --- potion_effects ---
def test_pair_effects():
    [r] = potion_effects(["a", "b"], TRIO)
    assert (r.effect_id, r.ingredient_ids) == ("e1", ("a", "b"))

def test_no_shared_effects_is_empty():
    d = ing("d", "x1", "x2", "x3", "x4")
    assert potion_effects(["a", "d"], TRIO + [d]) == []

def test_trio_produces_three_effects():
    rs = {r.effect_id: r.ingredient_ids for r in potion_effects(["a","b","c"], TRIO)}
    assert rs == {"e1": ("a","b"), "e2": ("a","c"), "e5": ("b","c")}

def test_wheat_plus_giants_toe_real_data():
    ds = load_dataset()
    rs = {r.effect_id for r in
          potion_effects(["wheat", "giants-toe"], list(ds.ingredients.values()))}
    assert rs == {"fortify-health", "damage-stamina-regen"}

# --- combos_for_effect ---
def test_all_combos_for_effect():
    got = {c.ingredient_ids for c in combos_for_effect("e1", TRIO)}
    assert got == {("a", "b"), ("a", "b", "c")}

def test_inventory_filters_combos():
    got = {c.ingredient_ids
           for c in combos_for_effect("e1", TRIO, inventory={"a": 1, "b": 2})}
    assert got == {("a", "b")}

# --- discovery_plan ---
def test_one_trio_brew_beats_three_pairs():
    plan = discovery_plan(TRIO, {"a": 2, "b": 2, "c": 2},
                          {"a": set(), "b": set(), "c": set()})
    assert len(plan) == 1                       # optimal: single a+b+c brew
    assert set(plan[0].ingredient_ids) == {"a", "b", "c"}
    assert set(plan[0].newly_discovered) == {
        ("a", 0), ("b", 0), ("a", 1), ("c", 0), ("b", 1), ("c", 1)}

def test_inventory_limits_plan():
    plan = discovery_plan(TRIO, {"a": 1, "b": 1},
                          {"a": set(), "b": set(), "c": set()})
    assert len(plan) == 1
    assert set(plan[0].ingredient_ids) == {"a", "b"}

def test_nothing_left_to_discover_is_empty_plan():
    known = {"a": {0, 1}, "b": {0, 1}, "c": {0, 1}}
    assert discovery_plan(TRIO, {"a": 5, "b": 5, "c": 5}, known) == []
```

- [ ] **Step 3: Verify default run stays green and marked run fails correctly**

Run: `pytest -v` → combinatorics tests DESELECTED, everything else passes.
Run: `pytest -m combinatorics -v` → all FAIL with `NotImplementedError` (this is the user's TDD starting line).

- [ ] **Step 4: Commit**

```bash
git add alchemy_helper/combinatorics tests/combinatorics
git commit -m "feat: combinatorics contracts + user test suite (bodies user-owned)"
```

---

### Task 10: App state + manual overrides

**Files:**
- Create: `alchemy_helper/state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Consumes: `Dataset` (Task 2), `PlayerState` (Task 8).
- Produces (web layer's model):

```python
# alchemy_helper/state.py
class Overrides:
    def __init__(self, path: Path)          # loads JSON if present, else empty
    have: dict[str, int]                    # ingredient id -> count override
    known: dict[str, set[int]]              # ingredient id -> known-slot override
    def set_have(self, ingredient_id: str, count: int | None) -> None   # None clears
    def set_known(self, ingredient_id: str, slots: set[int] | None) -> None
    def save(self) -> None                  # writes JSON (parents created)

@dataclass
class AppState:
    dataset: Dataset
    player: PlayerState | None              # None → manual mode
    overrides: Overrides
    last_error: str | None                  # diagnostic from a failed parse
    def effective_inventory(self) -> dict[str, int]      # overrides win over player
    def effective_known(self) -> dict[str, frozenset[int]]
    def mode(self) -> str                   # "save" | "manual"
```

Default overrides path: `Path.home() / ".skyrim_alchemy_helper" / "overrides.json"` (constructor arg makes it testable).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_state.py
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
```

- [ ] **Step 2: Run to verify FAIL** (`pytest tests/test_state.py -v`), **Step 3: implement `state.py`**, **Step 4: rerun → 3 PASS**, **Step 5: Commit**

```bash
git add alchemy_helper/state.py tests/test_state.py
git commit -m "feat: app state with save/manual modes and persistent overrides"
```

---

### Task 11: FastAPI endpoints

**Files:**
- Create: `alchemy_helper/web/app.py`, `alchemy_helper/web/saves.py`
- Test: `tests/web/test_api.py` (create `tests/web/__init__.py`)

**Interfaces:**
- Consumes: `AppState`/`Overrides` (Task 10), `parse_save`/`SaveFormatError` (Tasks 5/8), combinatorics stubs (Task 9), `load_dataset` (Task 2).
- Produces:

```python
# alchemy_helper/web/saves.py
def default_saves_dir() -> Path | None
    # try Path.home()/"Documents/My Games/Skyrim Special Edition/Saves"
    # then Path.home()/"OneDrive/Documents/My Games/Skyrim Special Edition/Saves"
    # return first that exists, else None
def list_saves(directory: Path) -> list[dict]   # {"path","name","modified_iso"}, newest first

# alchemy_helper/web/app.py
def create_app(data_dir: Path | None = None,
               overrides_path: Path | None = None,
               saves_dir: Path | None = None) -> FastAPI
```

Endpoints (all JSON; `NOT_IMPL = {"not_implemented": True, "message": "This lives in alchemy_helper/combinatorics/core.py — yours to write! Run: pytest -m combinatorics"}` returned with HTTP 200 whenever a combinatorics call raises `NotImplementedError`):

| Route | Behavior |
|---|---|
| `GET /api/effects` | dataset effects as list of dicts |
| `GET /api/ingredients` | dataset ingredients as list of dicts |
| `GET /api/saves` | `list_saves(saves_dir)` or `[]` |
| `POST /api/load-save` `{path}` | `parse_save`; on success store `PlayerState`, return `/api/state` payload; on `SaveFormatError` store `last_error`, set manual mode, return HTTP 200 `{"mode":"manual","error":"<diagnostic>"}` |
| `GET /api/state` | `{"mode", "character", "error", "inventory", "known_effects", "unknown_forms", "overrides":{"have","known"}}` (known_effects sets → sorted lists) |
| `POST /api/override` `{ingredient_id, have?, known_slots?}` | apply to `Overrides`, `save()`, return new state payload |
| `GET /api/combos?effect=<id>&only_inventory=<bool>` | `combos_for_effect(...)` → `{"combos":[...]}` or `NOT_IMPL` |
| `POST /api/potion` `{ingredient_ids}` | `potion_effects(...)` → `{"effects":[...]}` or `NOT_IMPL` |
| `GET /api/discovery-plan` | `discovery_plan(...)` → `{"plan":[...]}` or `NOT_IMPL` |

Plus `app.mount("/", StaticFiles(directory=web/static, html=True))` LAST (after API routes).

- [ ] **Step 1: Write the failing tests**

```python
# tests/web/test_api.py
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
```

- [ ] **Step 2: Run to verify FAIL**, **Step 3: implement `saves.py` + `app.py`** (create empty `alchemy_helper/web/static/` with a placeholder `index.html` containing `<h1>Alchemy Helper</h1>` so the mount works), **Step 4: rerun → 5 PASS** (`pytest tests/web -v`), **Step 5: Commit**

```bash
git add alchemy_helper/web tests/web
git commit -m "feat: FastAPI endpoints with manual-mode fallback and friendly stubs"
```

---

### Task 12: Frontend + launcher

**Files:**
- Create: `alchemy_helper/web/static/index.html`, `alchemy_helper/web/static/app.js`,
  `alchemy_helper/web/static/style.css`, `alchemy_helper/__main__.py`

**Interfaces:**
- Consumes: every `/api/*` route from Task 11 exactly as specified there.
- Produces: `python -m alchemy_helper [--port N] [--no-browser]` serves the UI at `http://127.0.0.1:8712`.

- [ ] **Step 1: Write `__main__.py`**

```python
import argparse, threading, webbrowser
import uvicorn
from alchemy_helper.web.app import create_app

def main():
    ap = argparse.ArgumentParser(prog="alchemy_helper")
    ap.add_argument("--port", type=int, default=8712)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    if not args.no_browser:
        threading.Timer(
            1.0, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}")).start()
    uvicorn.run(create_app(), host="127.0.0.1", port=args.port)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Build the frontend.** Single page, three tabs + a header bar. No framework, no external fonts/CDN. Structure:
  - **Header:** save picker (`GET /api/saves` dropdown + Load button → `POST /api/load-save`; a "Reload" button re-posts the current path), mode badge ("SAVE: <character>" or "MANUAL MODE" + error tooltip from `state.error`), discovery progress ("N of M effect-slots discovered" computed from `/api/state` + `/api/ingredients`).
  - **Tab 1 — Effect finder:** effect dropdown (from `/api/effects`), checkbox "only ingredients I have" (default ON — this is the spec's toggle), results from `/api/combos` as a list of combos with member names; `not_implemented` payloads render the message in an amber banner.
  - **Tab 2 — Discovery tracker:** table, one row per ingredient (name, count from state, 4 effect cells). Cell shows effect name; class `known` (filled) vs `unknown` (dimmed). Toggle "show ingredients I don't have" (default OFF) filters rows to `inventory > 0`. Clicking a cell or count opens a small inline editor that posts `/api/override` (this is manual mode's editing surface too).
  - **Tab 3 — Discovery plan:** button "Compute plan" → `GET /api/discovery-plan`; renders ordered brew cards (ingredient names + "newly discovers: …"); amber banner when `not_implemented`.
  - `app.js`: one `refreshState()` that re-fetches `/api/state` and re-renders header + current tab; every mutating call ends with `refreshState()`. Keep it plain `fetch` + template literals; ~200 lines is the right ballpark.
  - `style.css`: system font stack, max-width 1100px centered, tab bar, `.known {background:#2f6b2f;color:#fff}` `.unknown {opacity:.35}`, amber banner class, dark-friendly neutral palette.
- [ ] **Step 3: Manual verification checklist** (run `python -m alchemy_helper --no-browser`, open the URL):
  - Save picker lists real saves; loading one flips badge to SAVE and populates counts.
  - Tracker toggle hides/shows un-carried ingredients; a cell edit persists across an app restart (overrides file).
  - Effect finder and plan tabs show the amber "yours to write" banner (stubs not implemented).
  - Loading a garbage file (make one in the saves dir) shows MANUAL MODE badge with the diagnostic, app remains usable.
- [ ] **Step 4: Full test suite still green:** `pytest -v` → PASS (combinatorics deselected).
- [ ] **Step 5: Commit**

```bash
git add alchemy_helper/web/static alchemy_helper/__main__.py
git commit -m "feat: three-tab frontend and python -m launcher"
```

---

### Task 13: README + final verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: everything.
- Produces: the repo's front door, including the user's implementation guide.

- [ ] **Step 1: Write the full README** with sections:
  - What it is + screenshot placeholder comment; Setup (`pip install -e .[dev]`, `python -m alchemy_helper`); pointing the app at a save.
  - **"Writing the combinatorics (that's you!)"**: the three functions in `alchemy_helper/combinatorics/core.py`, their contracts (copy the docstrings), the TDD loop: `pytest -m combinatorics -v` until green; note the app works partially until then (tracker + save reading live; finder/plan show banners).
  - Manual mode & overrides (where the JSON lives); troubleshooting (unsupported save version → the diagnostic, where saves live incl. OneDrive path).
  - Phase 2+ ideas from the spec (other game versions, mod plugin parsing, potion values, eat-to-discover, Experimenter perk).
  - License note: MIT; references UESP docs and cguebert's SkyrimAlchemyHelper (GPL, read as format reference only, no code copied).
- [ ] **Step 2: Full verification:** `pytest -v` (all green, combinatorics deselected), `pytest -m combinatorics -v` (all NotImplementedError-red — expected), `python -m alchemy_helper --no-browser` boots cleanly.
- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: full README with user combinatorics guide"
```

---

## Plan Self-Review (performed at write time)

1. **Spec coverage:** dataset (T2–3), save auto-read incl. plugin cross-check surface (T5–8), effect finder + inventory toggle (T11–12), discovery tracker (T12), discovery plan contract (T9), manual-mode fallback + overrides (T10–11), never-bricks error handling (T5/T8/T11), three test tiers (T3/T8/T9/T11), hygiene (T1/T13). Spec's "dataset cross-check against save plugin list" is satisfied by T6's pinned plugin-list test; no dedicated UI for it (YAGNI — unknown_forms banner covers drift).
2. **Placeholder scan:** `<pin>`-style markers appear only where real-save values must be measured before pinning (Tasks 5, 8) or belong to the user (Task 4) — each has an explicit measure-then-pin step. Save-format unknowns (offset rebasing, ACHR/INGR layouts) get named reference files + empirical verification steps rather than invented offsets — deliberate, since format details must come from the fixture, not from this plan's author.
3. **Type consistency:** `PlayerState.known_effects: dict[str, frozenset[int]]` consumed identically in T10/T11; `Overrides.known: dict[str, set[int]]` (mutable) distinct by design; combinatorics signatures in T9 match T11's calls; `parse_plugins` returns `(PluginList, int)` consumed in T7/T8. Fixed during review: removed a malformed duplicate test from Task 9's suite; `Combo`/`EffectResult`/`PlannedBrew` now imported plainly at the top of the user test file.
