# YouTube upload kit - the cascade library

Prepared 2026-09-06 per `F:\utility-projects\publish-all-the-things`
(venue: youtube, category: Research Finding, forms written once here).
The user uploads; nothing here needs a credential. Pre-flight per the
venue checklist: review the dormant account, settle the Infinite
Debates channel question.

## Short form (title + first description line; ~290 chars)

Watching a video game's alchemy learn itself: the fewest potions that
discover every effect is an NP-hard set cover, and these animations
show greedy (76 brews) racing the true optimum (70) - then the same
graph rearranged so its picture has a provably empty, balanced, or
maximally congested heart.

Title candidate (shorter, for the field): **Watching Skyrim's alchemy
solve itself: greedy vs optimal, animated**

## Long form (description body)

Skyrim's alchemy discovery problem - the fewest brews that reveal
every ingredient effect - is a set-cover instance (NP-hard). These
animations are exact: every line is one discoverable effect slot, lit
at the moment its brew happens, driven by the app's real planner and
a MIP-optimal plan. Greedy needs 76 brews; the optimum is 70; the gap
plays out as six brews of one-sided motion.

The later chapters are about the picture itself: measuring ink
density inside vs outside the effects ring, the conjecture that the
graph's expansion forbids emptying the center, its same-day
falsification by a 60,000-swap hill-climb, and three constructed
orderings - minimum congestion (0.344), exact equilibrium (1.000),
and maximum (3.734). Proof by construction, Euclid-style: every claim
in these videos ships with a script and a witness file.

Everything is open and reproducible:
- App + campaign: https://github.com/bshepp/skyrim-alchemy-effect-finder
  (docs/math-notes/ for the ledger, anim/ for this pipeline)
- The congestion geometry spinoff: [chordwheel repo URL when public]
- The mod itself: https://www.nexusmods.com/skyrimspecialedition/mods/189861

Made in collaboration with Claude (Anthropic's AI assistant) under
human direction - the AI wrote the pipelines and renders, the human
asked the questions, chose the constructions, and verified the
results. Stated openly, as always.

## Chapters (compilation cut)

0:00 The race - greedy (amber) vs optimal (ice), 448 effect slots
0:45 Brew-order spectrum - each side divides red to violet by its count
1:30 The ingredient wheel - every line wears its source's color
2:15 The effect wheel - lines pool into their targets
3:00 Equal-area rings - measuring where the ink lives
3:45 The min-congestion wheel - the falsifying witness (0.344)
4:30 The equilibrium wheel - line and space in exact balance (1.000)
5:15 The max-congestion wheel - the graph through its own heart (3.734)

(Timestamps assume ~45s per segment; fix after the edit is cut.)

## Ledger row (draft for LEDGER.md)

| date | project | venue | identity | what went | response |
2026-09-XX | alchemy cascade library | youtube | bshepp (personal) |
compilation video, Research Finding, links to both repos | -

## Open decisions

- Compilation vs singles (recommendation: one compilation; the
  amber/ice classic optionally standalone for the article embed).
- Channel confirmed as the personal account (recommendation given;
  pre-flight review pending).
- chordwheel public repo URL - placeholder above until it exists.
