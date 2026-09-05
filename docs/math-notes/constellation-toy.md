# The constellation toy - a grabbable alchemy graph

Status: designed 2026-09-05, not yet built. Queued behind the alchemy
cliff article (2026-09-08). An evening of work for the 2D standalone.

## The idea

An interactive force-directed graph of the alchemy data: grab a node,
drag it, and the rest of the web rearranges around it live. Where the
cascade animation (`anim/`) shows the data's *history* - brew order,
greedy vs optimal - this shows its *structure*, through the hands.

## Three views, one engine

The bipartite ingredients + effects graph is the true data; the other
two views are projections computed from it, so a single physics engine
with a mode switch serves all three:

1. **Both** - ingredients and effects as distinct node kinds, one edge
   per ingredient effect-slot (the animation's graph, now tactile).
2. **Ingredients** - ingredients linked when they share an effect,
   weight = number shared. The "what brews with what" web.
3. **Effects** - effects linked when they co-occur on an ingredient.
   Effect communities (poisons cluster, restoratives cluster).

## Physics as proof

Two behaviors fall out of the simulation for free and are the whole
reason this is worth building:

- **Clones find each other.** Ingredients with identical effect-sets
  (the generators of the problem's order-48 automorphism group - see
  campaign-log result 9) have identical connections, hence identical
  equilibria. Drag one clone away, release, and it glides back onto
  its twin. The orbit theorem as a physical sensation.
- **Unbrewables dangle.** Degree-1 slots (Viper's Bugloss's AlchUnknown
  placeholder in the Bruma world) hang visibly loose at the rim.

## Architecture

- Single self-contained HTML file, d3-force, no build system - same
  discipline as the app's static/ frontend. A small export script
  (like `anim/export_plans.py`) emits nodes/edges JSON per world
  (UESP-112, full-180, and any pack world: Bruma-305, CACO-358).
- 2D first: legible, article-embeddable, 60fps at every world size.
  3D (three.js force-graph) is a later mode toggle, not the base.
- Standard drag semantics: pinned while held, released on drop.

## The long game: Constellation View in Alembic

The end-state is an app tab. Alembic already knows the save's
discovery state, so the constellation can render discovered slots lit
and undiscovered dark, rearrange as you drag, and update as you brew -
the Discovery Tracker's table, reborn as a sky. The standalone toy is
the risk-free prototype; it graduates to the app only if it earns it
(per the usual rule: play first, ship what survives).

## Open questions for build night

- Edge rendering at 448+ edges while dragging: plain lines are fine at
  112; test at 358 before promising CACO.
- Duplicate-clone overlap: exact overlap hides one node - tiny jitter
  force or a shared halo when distance < epsilon?
- Discovery overlay in the standalone: fake it with a slider (brew k of
  the plan timeline) before wiring real save state in the app.
