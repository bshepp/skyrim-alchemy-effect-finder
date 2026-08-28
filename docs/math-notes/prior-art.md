# Prior art: the shoulders we stand on

Collected 2026-08-28 during the phase-42 exploration of the discovery
problem's mathematics. Anything we prove is a footnote to fifteen years of
community work; every result below predates ours and gets cited wherever
our numbers are shown.

## The direct predecessors

- **The UESP editors** - [Skyrim:Alchemy](https://en.uesp.net/wiki/Skyrim:Alchemy)
  carries a hand-curated list, "Base Game and Official Add-On Ingredients
  (73 Potions, 218 Ingredients)", that reveals all four effects of every
  ingredient up through the Hearthfire add-on. No optimality claim, no
  Creations coverage - but it is the community's standing answer to "how
  few brews teach you everything", built by hand, and the benchmark our
  restricted-universe computation measures against. The same page records
  a kindred exact result: the minimum *ingredient set* covering all
  effects is 16 ingredients (1,715 optimal sets) - a different problem
  (effect coverage, not discovery coverage), and real computation by
  community hands.
- **timoffex, [skyrim-alchemy](https://github.com/timoffex/skyrim-alchemy)** -
  a discovery assistant that frames the problem as set cover and pursues
  an information-gain heuristic. Its README contains the sentence that
  our MIP answers directly: "trying to math it out directly like this is
  just too hard, even with computer assistance and a math degree." An
  honest surrender is also a contribution: it marked where the frontier
  was.
- **Blake Rayvid, [skyrim-alchemy-optimizer](https://github.com/brayvid/skyrim-alchemy-optimizer)** -
  integer linear programming applied to Skyrim alchemy before us, for the
  dual problem (maximum potion value from an inventory rather than
  minimum brews to knowledge).
- **cguebert, [SkyrimAlchemyHelper](https://github.com/cguebert/SkyrimAlchemyHelper)** -
  the tool whose save-reading idea inspired Alembic itself; the reason
  any of this exists.

## Adjacent census work

- UESP's count of **21,974 distinct and efficient recipes** at release
  (order-insensitive, every ingredient contributing an effect) - a cousin
  of our 971,970-mix census under a stricter counting rule.
- The UESP talk pages' per-ingredient scheme: at most **eight potions**
  against a fixed tester set identify any single ingredient's four
  effects.

## What was NOT found anywhere (2026-08-28 search)

No published computation of a provably minimal brew count for full
discovery, on any ingredient universe - not for base game, base+DLC, or
Anniversary content. The searches: web (multiple phrasings), GitHub,
UESP main and talk pages, Medium/data-science blogs. Absence of evidence
noted honestly: we claim "first we could find", never "first".
