# v1.2 Nexus material - DRAFT, nothing here is live

Prepared 2026-09-05 (night shift) for the v1.2 release once the Bruma
pack graduates. Blockers before any of this posts: BS_DLC_patch.esp
override check, live-save round-trip verification of the Bruma pack,
and the v1.1.0 file clearing review.

## File upload form - v1.2.0

File name: Alembic 1.2.0. File version: 1.2.0. Description field:

```
Beyond Skyrim: Bruma support - 125 Cyrodiil ingredients (the shared Beyond Skyrim library plus Bruma's local flora) with 21 effects new to Skyrim alchemy, extracted from the mod's plugins and verified against a live save. Auto-activates when the save's load order carries Bruma. Vanilla and CACO behavior unchanged.
```

## Changelog block

```
- Dataset pack: Beyond Skyrim - Bruma. 125 new ingredients across BSAssets.esm and BSHeartland.esm, 21 new effects (Fire Damage, Reflect Spell, Night Eye...). Activates automatically from the save's load order.
- Known quirk, faithfully modelled: Viper's Bugloss's first effect is the vanilla AlchUnknown placeholder - no second ingredient shares it, so it can never be brewed. The three single-effect Mountain Berries are not modelled (the discovery model assumes four-slot ingredients).
```

## Fun stat for the notes

Vanilla + Bruma is a 305-ingredient world: 1,220 effect-slots, 9 of
them unbrewable (Viper's Bugloss's placeholder among them), and the
app's greedy planner discovers all 1,211 reachable ones in 177 brews.

## Comment replies (adapt to the actual threads)

To the Bruma requester:

```
Done - Bruma support just shipped in 1.2.0. All 125 Cyrodiil ingredients (yes, including the unbrewable mystery slot on Viper's Bugloss - that one's the game's own data, not a bug). Thanks for the nudge; it was a fun one to build.
```

To the Apothecary requester:

```
Bruma's out, so Apothecary is up next as promised. It's the same shape of work as the CACO pack, so it should not be a long wait.
```
