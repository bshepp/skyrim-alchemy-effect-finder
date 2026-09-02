# Phase 2 research: what adds or alters alchemy ingredients

Researched 2026-08-29. *Status 2026-09-02:* the dataset-pack mechanism
described in "What this means" is now implemented on the `mod-packs`
branch (extend + overhaul modes, plugin-based activation, The Cause
shipped as the first pack). Priority reordered by the mod page's first
two comments - actual users asked for CACO and Beyond Skyrim by name,
so: CACO, Bruma, then the rest.

Two distinct mechanisms exist in the wild, and Alembic will need both:

- **Adders** - new ingredient records (plugin + form id + 4 effects).
  Exactly what the Mort Flesh addition exercised.
- **Alterers** - the same vanilla records with *remapped effects*. A user
  running one of these needs a replacement dataset, not an extended one.

## Official Creations (Anniversary-era users have these)

UESP's own Alchemy page names the complete set of ingredient-bearing
Creations: Fishing, Rare Curios, Saints & Seducers, Plague of the Dead,
Goblins, The Cause. Alembic covers the first four (Mort Flesh closed
Plague of the Dead). Remaining:

- **The Cause** - resurrects the classic Oblivion Deadlands plants:
  Bloodgrass, Harrada, Spiddal Stick.
- **Goblins** - ingredient details thinly documented; needs a look at the
  plugin itself (or a user's unknown-forms banner) to enumerate.

Both are small (a handful of records) - same shape of work as Mort Flesh.

## Community mods, by reach

- **CACO (Complete Alchemy and Cooking Overhaul)** - the giant, and both
  an adder AND an alterer: 100+ new lore-friendly ingredients (plus 51
  new harvestable creatures) and changed effects on vanilla ingredients.
  A third-party potion-builder web app exists just for CACO
  (dhildebr/caco-potion-builder on GitHub, which also carries Bruma and
  Hunterborn ingredient data in machine-readable form - a possible
  dataset source, licensing to be checked).
- **Apothecary - An Alchemy Overhaul** - the modern popular alternative:
  pure alterer, explicitly adds no ingredients, remaps effects across the
  vanilla set. For Alembic this is a *variant dataset* of the same 180
  records.
- **Beyond Skyrim: Bruma** - adder: dozens of Cyrodiil ingredients
  (Alkanet, Arrowroot, Azra Root, ...). Note the name collision: Bruma
  has its own "Aloe Vera Leaves" distinct from Rare Curios' record -
  our per-(plugin, form id) model handles this the same way it already
  handles the two Flame Stalks.
- **Hunterborn** - adder via harvested animal parts; commonly patched
  into CACO load orders.
- **Requiem** and kin - overhauls that touch alchemy effects as part of
  larger rebalances; alterers of varying depth.

## What this means for Alembic's design

1. The dataset format already keys ingredients by (plugin, form id) and
   the save parser already reads the load order - so mod support is
   *dataset packs plus a selection/merge step*, not an architecture
   change: activate packs whose plugin appears in the save's own list;
   alterer packs replace the vanilla effect tables instead of extending.
2. Priority by user reach: CACO, Apothecary, Bruma, then the two missing
   Creations (cheap wins), then Hunterborn.
3. The unknown-forms banner is organic telemetry: users' reports name the
   exact plugin and form id of whatever we don't cover yet - the Mort
   Flesh workflow, repeated. The bug-report template already asks for it.
4. The phase-42 mathematics scales with these: CACO-sized universes push
   the census to ~20M mixes and make the optimality ladder a genuine
   jaga-class job. (The ladder formulation is ready for that day.)

Sources: UESP Skyrim:Alchemy and The Cause pages, Nexus pages for CACO
(skyrimspecialedition/mods/19924) and Apothecary, Beyond Skyrim wiki
ingredient category, dhildebr/caco-potion-builder.
