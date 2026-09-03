# Clean-room plan: isolated game environments, done properly

Drafted 2026-09-02 after the ad-hoc attempt failed. Goal: reproducible,
genuinely isolated Skyrim environments for (a) verifying dataset packs
against live games, (b) generating save fixtures for parser work,
(c) expanding version/distributor support honestly - each clean room
retires one line of the mod page's "not supported yet" list.

## Why the ad-hoc attempt failed (2026-09-02, lessons locked in)

Profiles and instances (Vortex or MO2) isolate *mod lists*, not the
*game copy*. The daily install is entangled three ways that no profile
switch reaches:

1. A root-folder preloader (`d3dx9_42.dll`, DLL Plugin Loader) force-
   loads every DLL in `Data/SKSE/Plugins` on any launch of the exe.
2. Fifteen SKSE plugin DLLs are physically present and load without
   their data, then crash (observed: OStim.dll null-deref with a clean
   plugin list).
3. Masking the preloader broke the daily setup's launch expectations
   (Community Shaders et al.) - the daily driver and the test rig share
   an engine, so neither can be reconfigured without hurting the other.

**Rule: a clean room is a separate copy of the game.** Never a profile,
never an instance, never a mask over the daily install.

## Architecture

One folder per (distributor, version) under `F:\skyrim-cleanrooms\`:

```
F:\skyrim-cleanrooms\
  steam-1.6.1170\        # game copy (pristine, from steamcmd)
  steam-1.6.1170-mo2\    # portable MO2 instance pointed at it
  ...
```

- **Pristine copies via steamcmd**, never by copying the daily install
  (its Data folder carries hundreds of Vortex-deployed loose files):
  `steamcmd +force_install_dir F:\skyrim-cleanrooms\steam-1.6.1170
  +login <user> +app_update 489830 validate +quit`
  (Owner runs this - interactive Steam login is theirs alone.)
- **Older Steam builds** (1.5.97 and friends) via steamcmd
  `download_depot` with pinned manifest ids; record each manifest id
  here when first used.
- **Per-room MO2 portable instance** provides profile-local saves,
  INIs, and mod list. Over a pristine copy this actually isolates,
  because there is no binary layer underneath to leak through.
- Steam must be running for the exe to start (Steam stub DRM);
  launching the room's exe directly or via its MO2 is fine.
- Budget ~15-20 GB disk per room; rooms are disposable and rebuildable
  from this file.

## Version and distributor matrix

Status: S = supported by Alembic today, U = unsupported/untested,
? = to be determined empirically in the room (save version, form
version, compression, save-directory location).

| Room | Build | Source | Save format | Alembic |
|---|---|---|---|---|
| steam-1.6.1170 | current AE | owned | 12 / LZ4 | S (primary) |
| steam-1.5.97 | pre-AE | depot pin | ? | U |
| gog-1.6.x | GOG offline installer | buy on sale | ? | U |
| epic-1.6.x | Epic | if ever owned | ? | U |
| gamepass | MS Store | if ever owned | ? (different save path) | U |
| vr-1.4.15 | SteamVR | if ever owned | ? | U |
| le-1.9.36 | Legendary | if owned | ? (zlib-era) | U |

Acquisition is phased: build steam-1.6.1170 now (owned); add GOG at
the next sale (offline installers are DRM-free and version-pinnable -
the friendliest distributor for clean rooms); the rest as opportunity
or user demand (a bug report from a Game Pass user is the trigger to
buy Game Pass for a month).

## Protocols

**Fixture generation (the two-save handshake):**
1. Room launches, `coc Riverwood` from the main menu, save -> save 1.
2. `scripts/gen_give_bat.py <save1> <pack...>` reads save 1's plugin
   list, computes runtime form-id prefixes for that exact load order,
   and emits a console batch file granting every ingredient.
3. In-game `bat <file>`, save -> save 2.
4. `scripts/verify_pack_save.py <save2>` parses with packs active and
   asserts the round trip: every granted form resolves to the right
   ingredient, zero pack-attributable unknown forms, counts exact.
   (Both scripts to be written when the first room exists.)

**Parser regression:** each room contributes one minimal canonical
save to `tests/fixtures/local/` (gitignored) plus pinned expectations
in tests, so save-format support never silently regresses.

**Pack verification record:** when a pack passes protocol, note it in
the pack's `_source` with room name and date.

## Standing rules

- The daily install is never modified, masked, or copied from. (The
  2026-09-02 preloader mask was restored the same evening; that class
  of intervention is retired.)
- Rooms never share saves, INIs, or SKSE layers with anything.
- CACO verification is the first customer: room steam-1.6.1170,
  vanilla + CACO 3.0.1 only, the two-save handshake, then the pack's
  `_source` gets its verification line and the DRAFT flag drops.

## Immediate next steps

1. Owner: install steamcmd (or use existing), run the pristine
   download into `F:\skyrim-cleanrooms\steam-1.6.1170`.
2. Claude: write `gen_give_bat.py` + `verify_pack_save.py` while the
   download runs.
3. Room's MO2 portable instance, CACO only, two-save handshake,
   verification, CACO pack graduates on evidence.
