# Nexus mod page copy

Prepared 2026-08-26 for the Skyrim Special Edition → Utilities category,
posted from the `ohnomomo` account. The summary is the short form; the
description is the long form in Nexus BBCode. Update the SHA-256 whenever
the exe is rebuilt.

If the upload form asks about AI-generated content, answer honestly: yes –
AI-assisted code and AI-drawn icon art, human-directed and verified (also
disclosed in the description's Credits and the repo README).

Screenshots: upload in the numbered order in `docs/screenshots/` –
Discovery Plan leads (it becomes the page thumbnail), then Best Potions,
Discovery Tracker, Effect Finder, and the header strip.

## Name

Alembic - Skyrim Alchemy Effect Finder

## Summary (short form)

Reads your save and shows what to brew: every combo for any effect, which
ingredient effects you haven't discovered yet, the fewest brews to learn them
all, and the most valuable potions you can make right now. Runs locally,
never touches your save.

## Description (BBCode)

```
[size=4][b]Your alchemy table already knows what you should brew. Now you can too.[/b][/size]

Pick a save, click Load, and the app reads your ingredient inventory and – the part nothing else does – [b]which of each ingredient's four effects you have already discovered in your game[/b], straight from the save file. No spreadsheets, no manual ticking, no wiki tab.

[size=3][b]What you get[/b][/size]

[list]
[*][b]Effect Finder[/b] – pick any effect (Paralysis, Fortify Enchanting, whatever you're farming) and see every 2- or 3-ingredient combination that produces it, filtered to what you're actually carrying if you want.
[*][b]Discovery Tracker[/b] – all 180 ingredients (vanilla + DLC + the free Creations + Plague of the Dead's Mort Flesh), showing exactly which effect slots you've discovered and which are still ???. Editable by hand if you want to plan ahead.
[*][b]Discovery Plan[/b] – the clever one: the [i]fewest brews[/i] that will discover [i]every effect[/i] reachable from the ingredients in your bag. Brew down the list at any alchemy table and watch the ??? disappear.
[*][b]Best Potions[/b] – every potion you can craft right now, ranked by how many effects it merges. More merged effects = more gold and more alchemy XP. This is the "what do I brew to level up and get rich" button.
[/list]

[size=3][b]How to use it[/b][/size]

Download [b]SkyrimAlchemyEffectFinder.exe[/b], run it, and it opens in your browser (it's a tiny local web app). Your newest save is pre-selected – click Load and go. When you've played more, hit Reload for fresh numbers.

[size=3][b]Safe by construction[/b][/size]

[list]
[*][b]Read-only.[/b] It opens your save, reads it, and never writes a byte. It cannot corrupt a save – it doesn't have the code to write one. That's checkable, not marketing: the source contains exactly one call that touches a save file (a read), and the app's only file-write is its own settings file in its own folder.
[*][b]Local-only.[/b] Serves only your own machine (127.0.0.1). No internet, no accounts, no telemetry – nothing leaves your PC.
[*][b]Open source (MIT).[/b] Full source at [url=https://github.com/bshepp/skyrim-alchemy-effect-finder]github.com/bshepp/skyrim-alchemy-effect-finder[/url] – read it, build it yourself with one script, or grab the exe from the GitHub release.
[*]SHA-256 of the exe: [code]931649ed899595e5434cb22a6efe316309c1620fcf1309a179ba97fc4f401360[/code]
[/list]

[b]About antivirus warnings:[/b] the exe is built with PyInstaller, which some antivirus tools flag on general principle (single-file Python apps all look alike to them). If yours complains: the source is public, the build script is in the repo, and the checksum above lets you verify the download. Or run it from source with Python – the README shows how.

[size=3][b]Requirements and limits[/b][/size]

[list]
[*]Skyrim Special Edition, current Steam release (save format 12). Covers vanilla + Dawnguard, Hearthfire, Dragonborn + the free Creations (Fishing, Survival Mode, Saints & Seducers, Rare Curios) + Plague of the Dead's Mort Flesh.
[*]Not supported yet: Legendary Edition, VR, GOG, and ingredients added by mods or other paid Creations – those show up in an "unknown ingredients" notice instead of breaking anything. If a save can't be read at all, the app tells you why and drops to manual mode – every feature still works, you just enter counts yourself.
[*]No plugin, no SKSE, no load order impact – it's a separate program, not a mod in your game.
[/list]

[size=3][b]Credits[/b][/size]

Successor in spirit to cguebert's SkyrimAlchemyHelper, which served this niche for years before the game outgrew it. Ingredient data built from UESP's documentation. Bug reports are welcome in the comments, but [url=https://github.com/bshepp/skyrim-alchemy-effect-finder/issues]GitHub Issues[/url] get seen fastest – a save file that fails to parse is the most useful bug report of all.

Built in collaboration with Claude (Anthropic's AI assistant) under human direction, stated openly: the AI wrote most of the code and drew the icon; the human set the requirements, verified the save parsing against real saves and the in-game alchemy menu, and tested everything you see in the screenshots. The commit history carries co-author trailers.
```
