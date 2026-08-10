# Skyrim Alchemy Effect Finder — Design

**Date:** 2026-08-10
**Status:** Approved pending user review
**Decision:** Fresh project (not a fork of cguebert/SkyrimAlchemyHelper)

## Background and prior art

The user previously relied on [SkyrimAlchemyHelper](https://github.com/cguebert/SkyrimAlchemyHelper)
(C++/Qt5, GPL-2.0), which no longer works on modern Skyrim. Evaluation findings:

- Abandoned: last commit December 2018. Open issues confirm it is broken on
  Skyrim Special Edition ("Doesn't work with SSE", 2021) and misses ingredients (2022).
- Safety audit: clean. Source-only, no committed binaries, no network code,
  no process execution, no build-time downloads.
- Its valuable code (binary parsers for plugins/BSA/saves) is exactly the part
  that is out of date; its GUI (Qt5, EOL) and language (C++) do not match this
  project's goals.

**Fork-vs-fresh decision: start fresh.** No code is copied from the old repo, so
this project is not bound by GPL-2.0 and is licensed MIT. The old repo's
`libs/saveParser` may be *read* as a format reference (file-format facts are not
copyrightable), alongside UESP's save-format documentation.

## Goals (Phase 1)

Target game: **Skyrim Special Edition on Steam, current patch (1.6.x)**, vanilla
plus the free Creations offered at first launch (Fishing, Survival Mode,
Saints & Seducers, Rare Curios).

The tool is a **local web app** (Python backend, browser UI, localhost only,
no internet access) that:

1. **Effect finder** — pick an effect, see every 2–3 ingredient combination that
   produces it. Default filter: only ingredients in the player's inventory, with
   a toggle to show all ingredients.
2. **Discovery tracker** — per-ingredient view of the 4 effect slots
   (known vs unknown), with overall progress.
3. **Discovery plan** — compute the smallest set of brews that maximizes newly
   discovered effects from carried ingredients.
4. **Auto-read the save file** — inventory counts and already-discovered effects
   come from the player's actual SE save; no manual bookkeeping required.

The **combinatorics module is written by the user**. Claude scaffolds its
interface and test suite; the user implements the bodies.

### Out of scope (Phase 2+ candidates)

- Other game versions (Legendary Edition, VR, GOG, older SE patches).
- Mod-added ingredients/effects (plugin + BSA parsing).
- Potion value / leveling optimization (magnitude & gold math).
- "Eat an ingredient" as a discovery action in the plan (brews only for now).
- Experimenter-perk awareness.

## Architecture

Python 3.12+, single package, four modules with hard boundaries:

```
alchemy_helper/
├── data/           Static dataset (JSON) + loader/validator
├── saveparser/     SE 1.6.x save reader → inventory + known effects
├── combinatorics/  USER-OWNED logic module (stubs + tests provided)
├── web/            FastAPI app + static frontend (vanilla HTML/JS/CSS)
└── __main__.py     `python -m alchemy_helper` starts server, opens browser
```

**Key boundary:** `combinatorics/` imports nothing from `saveparser/` or `web/`.
It receives plain data (ingredient definitions, inventory, known-effects) and
returns plain data (combos, effect results, planned brews). Pure logic, no I/O.

### data/

- `effects.json`: id, name, description, harmful flag.
- `ingredients.json`: id (source plugin + FormID), display name, source plugin,
  ordered list of exactly 4 effect ids.
- Built from UESP documentation for vanilla + Dawnguard/Hearthfire/Dragonborn +
  the four free Creations.
- Loader validates at startup: every ingredient has exactly 4 effects, every
  effect reference resolves, no duplicate ids.
- Each ingredient records its source plugin so the app can cross-check the
  dataset against the plugin list found in the user's save.

### saveparser/

Deliberately minimal — not a general save editor:

- Parse `.ess` header: game version, save number, character name, plugin list.
- Reject unsupported versions with a clear diagnostic (see Error handling).
- Decompress body (LZ4 for SE 1.6.x saves).
- Extract from change forms: player ingredient inventory (FormID → count) and
  per-ingredient known-effect flags (which of the 4 effects are discovered).
- References: UESP "Save File Format" documentation; cguebert's `saveParser`
  read as a secondary reference (no code copied).
- Auto-detects the saves folder
  (`Documents\My Games\Skyrim Special Edition\Saves`), offers the most recent
  save by default, allows browsing to any `.ess` file.

### combinatorics/ (user-owned)

Claude provides dataclasses, typed stubs raising `NotImplementedError`, and a
test suite. The user implements:

```python
def combos_for_effect(effect_id, ingredients, inventory=None) -> list[Combo]
    # Every 2- or 3-ingredient combination producing this effect.
    # inventory=None → consider all ingredients; otherwise only held ones.

def potion_effects(ingredient_ids, ingredients) -> list[EffectResult]
    # Effects produced by mixing 2–3 given ingredients (shared-effect matching).

def discovery_plan(ingredients, inventory, known_effects) -> list[PlannedBrew]
    # Minimal sequence of brews maximizing newly discovered effects.
    # Each PlannedBrew lists the ingredients used and effects newly revealed.
```

Game rule encoded by tests: a potion produced from 2–3 ingredients carries each
effect shared by at least two of them; brewing reveals each matched effect on
every participating ingredient that has it. Inventory counts limit how many
brews can consume an ingredient.

### web/

- FastAPI + uvicorn, serving a static single-page frontend (no JS framework).
- Endpoints:
  - `GET /api/effects`, `GET /api/ingredients` — dataset.
  - `GET /api/saves` — discovered save files; `POST /api/load-save` — parse one.
  - `GET /api/state` — inventory, known effects, unknown-ingredient list,
    manual overrides merged in.
  - `POST /api/override` — manually set possession/known flags (persisted to a
    local JSON state file).
  - `GET /api/combos?effect=…`, `POST /api/potion`, `GET /api/discovery-plan` —
    thin delegates to the combinatorics module.
- If a combinatorics function raises `NotImplementedError`, the API returns a
  friendly "not implemented yet" payload and the rest of the UI keeps working.
- Reload-save button re-parses the current save on demand.

## Data flow

1. Startup: load + validate dataset; detect saves folder; open browser tab.
2. User picks a save (default: most recent) → parser returns inventory +
   known effects → merged with manual overrides into app state.
3. UI views (effect finder / discovery tracker / discovery plan) call the API;
   the API delegates computation to `combinatorics/`.
4. After more play, one click re-reads the save.

## Error handling

- **Save parse failure** (unsupported version, corrupt file, future patch):
  clear message including the save's reported game version and save format
  number; app falls back to **manual mode** — all features work with hand-ticked
  inventory/known flags. A broken parser degrades the tool, never bricks it.
- **Unknown FormIDs** in the save (e.g. mods added later): collected and shown
  as an "unknown ingredients" list; never a crash. Serves as the early-warning
  signal that the dataset no longer matches the game.
- **Dataset validation errors**: fail at startup with a message naming the
  offending entry.
- **Manual overrides** always win over parsed data and persist across restarts.

## Testing (pytest)

1. **Save parser**: golden tests against a real save file from the user's game,
   committed as a test fixture (requested from the user at build start).
   Asserts known inventory counts and discovered-effect flags.
2. **Dataset**: sanity tests — ingredient/effect counts match UESP, all
   references resolve, exactly 4 effects each.
3. **Combinatorics**: Claude-authored suite the user implements against (TDD):
   golden vanilla facts (e.g. Wheat + Giant's Toe → Fortify Health), symmetry
   and inventory-constraint properties, and a small hand-checked discovery
   scenario with a known-optimal plan.
4. **API**: smoke tests over the FastAPI test client, including the
   manual-mode fallback path.

## Project hygiene

- Git repository initialized in the project folder; MIT `LICENSE`.
- `README.md` with setup (`pip install -e .`, `python -m alchemy_helper`).
- Spec lives at `docs/superpowers/specs/`; implementation plan to follow via
  the writing-plans skill.
