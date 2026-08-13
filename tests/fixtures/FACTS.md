# Ground truth for tests/fixtures/player.ess

Recorded 2026-08-11 from the user's game (Skyrim SE on Steam, vanilla + free
Creations: Fishing, Survival Mode, Saints & Seducers, Rare Curios).

## Source save

- Original file: `Quicksave0_B30AD84E_0_4D616C647269632056616E65_0EEJSSE001House_011054_20260810221438_24_1.ess`
  (newest save in `Documents\My Games\Skyrim Special Edition\Saves` at copy time)
- Size: 5,315,996 bytes; game timestamp in filename: 2026-08-10 22:14:38
- Character (decoded from filename hex `4D616C647269632056616E65`): **Maldric Vane**
- Level (from filename field before `_1.ess`): **24**
- Location at save: a player home (`0EEJSSE001House` — Creation content cell id)

The character name and level above are decoded from the game's own filename
encoding; the header parser (Task 5) must reproduce them, which cross-checks
both the parser and this decoding at once.

## In-game inventory counts (reported by the user, 2026-08-11)

| Ingredient | Carried count |
| ---------- | ------------- |
| Bee        | 12            |
| Garlic     | 30            |
| Wheat      | 22            |

These are the pinned assertions for Task 8's `parse_save` inventory test.

## Known (discovered) effects (reported by the user, 2026-08-11)

- **Wheat**: "restore health, fortify health" revealed; other two hidden.
- **Garlic**: "Resist Poison, Regenerate Health" revealed; other two hidden.
- **Bee**: nothing discovered — all four effects hidden. Parser-derived first
  (the save has no ingredient-use change form for Bee), then confirmed by the
  user against the in-game alchemy view on 2026-08-13.

Task 8 must map these effect NAMES to slot indexes via the shipped dataset's
slot order (do not assume slot positions independently of the dataset).
