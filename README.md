# Alembic - Skyrim Alchemy Effect Finder

A local web app for Skyrim Special Edition alchemy: it reads your save file,
tracks which of the four effects on each ingredient you've discovered in
game, finds ingredient combos for a target effect, and plans brews that
discover everything reachable from your inventory in as few brews as
possible.

Runs entirely on your machine (`127.0.0.1`, no network access) as a small
FastAPI backend serving a static HTML/JS/CSS frontend. No accounts, no
telemetry, nothing leaves your computer.

**Saves are opened read-only, always.** The entire codebase touches save
files at exactly one point – a single `read_bytes()` in
`alchemy_helper/saveparser/api.py` – and parsing operates on that in-memory
copy. The app's only file-write is its own `overrides.json` in
`~/.skyrim_alchemy_helper/`. It cannot modify or corrupt a save.

<!-- screenshot: four-tab UI (Effect Finder / Discovery Tracker / Discovery
     Plan / Best Potions) with a loaded save, goes here -->

## What it does

Four tabs:

- **Effect Finder** – pick an effect, see every 2- or 3-ingredient
  combination that produces it. Toggle between "only ingredients I have"
  and every ingredient in the dataset.
- **Discovery Tracker** – every ingredient with its 4 effect slots, which
  are known vs. unknown, and an overall discovery progress count.
- **Discovery Plan** – a brew plan that discovers every effect reachable
  from your carried ingredients, in as few brews as possible.
- **Best Potions** – every potion craftable from what you carry, ranked by
  how many effects it merges. Effect count is the Phase-1 proxy for potion
  value and alchemy XP (real magnitude/gold math is a Phase 2+ idea).

The dataset covers vanilla Skyrim SE plus Dawnguard, Hearthfire, Dragonborn,
the free Creations (Fishing, Survival Mode, Saints & Seducers, Rare
Curios), and Plague of the Dead's Mort Flesh – 180 ingredients, 60 effects,
built from UESP documentation.

## Setup

**Easiest:** download `Alembic-<version>.zip` from the
[latest release](https://github.com/bshepp/skyrim-alchemy-effect-finder/releases),
unzip it anywhere, and run `SkyrimAlchemyEffectFinder.exe` inside the
`Alembic` folder – no Python needed. Your browser opens the app
automatically.

**From source:**

```bash
pip install -e .[dev]
python -m alchemy_helper
```

This starts the server on `http://127.0.0.1:8712` and opens it in your
default browser after a second.

Flags:

- `--port <N>` – serve on a different port (default `8712`).
- `--no-browser` – start the server without opening a browser tab (useful
  for scripting, or if you'd rather open the tab yourself).

## Pointing the app at a save

On startup the app looks for your Skyrim SE saves folder at
`Documents\My Games\Skyrim Special Edition\Saves` under your home directory,
falling back to the OneDrive-redirected path
`OneDrive\Documents\My Games\Skyrim Special Edition\Saves` if the first one
doesn't exist. If neither is found, the save picker is simply empty and the
app starts in manual mode (see below).

In the header, pick a save from the dropdown and click **Load**. This reads
your character's inventory (ingredient counts) and which of each
ingredient's 4 effects you've already discovered in the in-game alchemy
menu, and turns the header badge into `SAVE: <character name>`. The
**Reload** button re-parses the same save from disk, for after you've played
more and want fresh numbers without picking the file again.

Only the current Steam release of Skyrim SE is supported (save format
version 12). See **Troubleshooting** below for what happens on anything
else.

## The combinatorics module

The combo-finding and brew-planning logic lives in
`alchemy_helper/combinatorics/core.py`, pinned by the 13 tests in
`tests/combinatorics/test_user_module.py` (select just those with
`pytest -m combinatorics -v`).

Everything derives from Skyrim's brewing rule: a potion mixes 2 or 3
distinct ingredients and produces every effect that at least two of them
share; a mix sharing nothing fails (the game refuses the brew). Brewing a
successful potion reveals, on every participating ingredient, each produced
effect that ingredient has.

- `potion_effects` applies that rule directly to one mix.
- `combos_for_effect` enumerates every 2- or 3-ingredient combination
  producing a target effect: every pair of ingredients having the effect,
  plus each such pair extended by any third ingredient – the third doesn't
  need the effect itself, since the pair still shares it inside the trio.
- `discovery_plan` finds brews until nothing discoverable is left. The
  fewest brews covering every reachable (ingredient, effect-slot) pair is
  set cover (NP-hard), so it's greedy: each round brews the mix revealing
  the most still-unknown slots (ties: fewer ingredients, then
  lexicographic), consuming 1 of each used ingredient from stock.
- `best_potions` enumerates every craftable mix from inventory and ranks
  by effect count (most first; ties: fewer ingredients, then
  lexicographic), returning at most `limit`.

### The contract

Three functions, imported by the web layer with these exact signatures. The
contract lines of their docstrings are the spec – the test suite is written
directly against them:

```python
def combos_for_effect(effect_id: str, ingredients: Sequence[Ingredient],
                      inventory: Mapping[str, int] | None = None) -> list[Combo]:
    """Every 2- or 3-ingredient combination producing effect_id.
    inventory=None → all ingredients; else only ids with count >= 1."""

def potion_effects(ingredient_ids: Sequence[str],
                   ingredients: Sequence[Ingredient]) -> list[EffectResult]:
    """Effects of mixing 2-3 ingredients: an effect appears iff >=2 share it.
    Empty list = mix produces nothing (game refuses the brew)."""

def discovery_plan(ingredients: Sequence[Ingredient],
                   inventory: Mapping[str, int],
                   known_effects: Mapping[str, AbstractSet[int]]) -> list[PlannedBrew]:
    """Brews discovering EVERY effect reachable from inventory, in as few brews
    as possible (coverage is the hard objective, count the tiebreaker).
    Each brew consumes 1 of each used ingredient; brewing reveals each matched
    effect on every participating ingredient having it."""
```

The return types (`Combo`, `EffectResult`, `PlannedBrew`) are plain frozen
dataclasses defined in `alchemy_helper/combinatorics/types.py`:

```python
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
```

`combinatorics/` is deliberately isolated: it imports nothing from
`saveparser/` or `web/`, only `alchemy_helper.data.models.Ingredient` and its
own `types` module. It takes plain data in and returns plain data out – pure
logic, no I/O – so it can be tested with nothing but `pytest` running.

Note that `potion_effects` is exercised by the test suite and reachable via
`POST /api/potion`, but the current frontend doesn't call that endpoint from
either tab – it's there for a future "what does this specific mix do" view.

### Its tests

The 13 tests in `tests/combinatorics/test_user_module.py` cover:

- `potion_effects`: a shared-effect pair, a no-shared-effect pair (must
  return `[]`), a trio producing three distinct shared effects, and a
  real-data check against the shipped dataset (Wheat + Giant's Toe →
  Fortify Health, Damage Stamina Regen).
- `combos_for_effect`: every combo for an effect with `inventory=None`, and
  the same query filtered down by an `inventory` mapping.
- `discovery_plan`: a hand-checked scenario where one 3-ingredient brew
  beats three pairwise brews (coverage-first, brews-as-tiebreaker), the same
  scenario constrained by low inventory counts, and the empty-plan case when
  every discoverable effect is already known.
- `best_potions`: ranking by merged-effect count, inventory filtering,
  exclusion of failed mixes, and the `limit` cap.

## Final verification

Two checks confirm a freshly cloned checkout is in the state this README
describes:

```bash
pytest -v
```
→ **92 passed** – dataset, save parser, app state, web API, and
combinatorics, all green.

```bash
python -m alchemy_helper --no-browser
```
→ boots without error and serves the app at `http://127.0.0.1:8712/`
(`Ctrl+C` to stop). Add `--port <N>` to check a different port.

## Building the standalone app

`powershell -File scripts\build-exe.ps1` (from the repo root) produces
`dist\Alembic-<version>.zip` – a folder build (PyInstaller `--onedir`)
containing `SkyrimAlchemyEffectFinder.exe` beside its libraries, built
from a throwaway venv with only the runtime dependencies. A folder build
is deliberate: single self-extracting exes are what antivirus heuristics
flag, and the folder form of the same app scans clean. It is a console
app: the window it opens shows the server log, and closing it (or
`Ctrl+C`) stops the app.

## Manual mode & overrides

If no save is loaded – no saves folder was found, or no save has been
picked yet, or the loaded save failed to parse (see Troubleshooting) – the
app runs in **manual mode** (shown as a **MANUAL MODE** badge in the
header). Every feature still works; you just hand-tick inventory counts and
known effects yourself instead of them coming from a save.

Whether or not a save is loaded, any manual edits you make are **overrides**
that always win over whatever a loaded save says for that ingredient, and
they persist across restarts to:

```
~/.skyrim_alchemy_helper/overrides.json
```

(i.e. `Path.home() / ".skyrim_alchemy_helper" / "overrides.json"` – on
Windows that's `C:\Users\<you>\.skyrim_alchemy_helper\overrides.json`). It's
plain JSON (`{"have": {...}, "known": {...}}`); delete it or hand-edit it
if you ever want to reset. A corrupted or unreadable file is treated as
empty rather than crashing the app.

## Troubleshooting

**"Unsupported save format version"** – the app only understands SE save
format version 12, which is what the current Steam release of Skyrim SE
writes. If you're on a different game version (Legendary Edition, VR, GOG,
an older SE patch) or the format has changed since this was written, loading
the save shows the parse error verbatim (it names the step that failed and,
where known, the save version and form version observed) and the app falls
back to manual mode instead of crashing – everything is still usable, just
by hand.

**Save picker is empty** – the app couldn't find a saves folder. It checks
`Documents\My Games\Skyrim Special Edition\Saves` and then
`OneDrive\Documents\My Games\Skyrim Special Edition\Saves`, both under your
user home directory. If your saves live somewhere else, manual mode is your
path forward for now (Phase 1 has no "browse for a folder" picker).

**"Unknown ingredients" appear after loading a save** – a change form in
your save referenced an ingredient FormID that isn't in the shipped dataset.
This is expected if you're running mods that add ingredients (the dataset is
vanilla + DLC + free Creations only); it's collected and shown rather than
silently dropped or crashing the parse, and doubles as an early warning that
the dataset may be out of date if it happens on an unmodded save.

## Phase 2+ ideas

Out of scope for this Phase-1 build, listed here as candidates if you come
back to extend it:

- Support for other game versions (Legendary Edition, VR, GOG, older SE
  patches).
- Mod-added ingredients and effects – would need plugin (`.esp`/`.esm`) and
  BSA parsing beyond what the save parser does today.
- Potion value / leveling optimization (magnitude and gold math), not just
  which effects a mix produces.
- "Eat an ingredient" as a discovery action inside the discovery plan
  (brews only, for now).
- Awareness of the Experimenter perk (reveals a second effect on
  ingesting/brewing).

## How it was built

This project was built in collaboration with Claude (Anthropic's AI
assistant) running in Claude Code, under human direction – stated here
plainly because it should be. The human side (bshepp) set the requirements,
supplied and verified all in-game ground truth (inventory counts and
discovered effects checked against the actual alchemy menu), approved the
design, and tested the app against real saves; the AI wrote most of the
code, test-first, with every save-parser claim pinned by tests against a
real save before it was trusted. Commits carry `Co-Authored-By` trailers
marking the AI's hand. The icon art is AI-drawn.

## License and references

This project is [MIT licensed](LICENSE).

No code is copied from any prior-art project. The following were read
purely as *file-format* references while writing the save parser (file
format facts aren't copyrightable; their source was not):

- [UESP's "Tes5Mod:Save File Format" documentation](https://en.uesp.net/wiki/Tes5Mod:Save_File_Format)
  – the primary reference for the `.ess` header/body layout (as cited in the
  module docstrings throughout `alchemy_helper/saveparser/`).
- [FallrimTools / ReSaver](https://github.com/mdfairch/FallrimTools)
  (Apache-2.0) – a Java save-file editor, read as a secondary format
  reference.
- [cguebert/SkyrimAlchemyHelper](https://github.com/cguebert/SkyrimAlchemyHelper)
  (GPL-2.0) – the abandoned C++/Qt tool this project replaces. Its
  `libs/saveParser` was read as a format reference only; **no code from it
  was copied into this project**, which is why this project is free to be
  MIT-licensed rather than bound by GPL-2.0.
