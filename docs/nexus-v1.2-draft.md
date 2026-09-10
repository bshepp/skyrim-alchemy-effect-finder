# v1.2 Nexus material - DRAFT, nothing here is live

Prepared 2026-09-05, rewritten 2026-09-10 now that BOTH community-requested
packs have passed the two-save handshake on live saves
(scripts/gen_give_bat.py + scripts/verify_pack_save.py). Remaining blocker
before any of this posts: the v1.1.0 file clearing Nexus review (every exe
upload is quarantined and reviewed; approval is per file).

## File upload form - v1.2.0

File name: Alembic 1.2.0. File version: 1.2.0. Description field (255 max):

```
Beyond Skyrim: Bruma and Apothecary support. Bruma adds 125 Cyrodiil ingredients with 21 new effects; Apothecary remaps 71 vanilla ingredients and adds 5 effects. Both auto-activate from the save's load order and were verified against live saves.
```

## Changelog block

```
- Dataset pack: Beyond Skyrim - Bruma. 125 new ingredients across BSAssets.esm and BSHeartland.esm, 21 new effects (Fire Damage, Reflect Spell, Night Eye...). Activates automatically from the save's load order.
- Dataset pack: Apothecary - An Alchemy Overhaul. 71 vanilla ingredients get Apothecary's remapped effects, 5 new effects (Become Ethereal, Fortify Alchemy, Fortify Speed, Muffle, Water Walking), plus the extra Salt Pile the mod injects. Overhaul mode: takes precedence over vanilla when Apothecary.esp is loaded.
- Both packs verified in-game: every ingredient granted by console round-tripped through the save parser to the correct record, with no unknown forms.
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
Done - Apothecary support is in 1.2.0 alongside Bruma. All 71 remapped ingredients and the five new effects, verified by loading a real Apothecary save and eating a Falmer Ear to watch Water Walking show up. Thanks for asking; it made the pair a natural release.
```
