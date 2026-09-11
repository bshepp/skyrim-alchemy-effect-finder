# YouTube upload kit - the cascade library

Prepared 2026-09-06, rewritten 2026-09-10 after the layout correction, per
`F:\utility-projects\publish-all-the-things` (venue: youtube, category:
Research Finding, forms written once here). The user uploads; nothing here
needs a credential. Pre-flight per the venue checklist: review the dormant
account, settle the Infinite Debates channel question.

**Which renders to use.** v13-eq-brew-aligned, v14-eq-ingredients-aligned
and v15-eq-effects-aligned are the corrected barycenter layout; v10-v12
(the constructed wheels) were rendered from explicit layout files and are
unaffected. v2-v9 depict a layout with the two rings a half-turn apart and
should not be published as "barycenter" - though the v7 vs v13 pair makes
the best single frame in the set, because it shows the correction.

## Short form (title + first description line; ~290 chars)

Watching a video game's alchemy learn itself: the fewest potions that
discover every effect is an NP-hard set cover, and these animations show
greedy (76 brews) racing the true optimum (70) - then the same graph
rearranged so its picture has a nearly empty, exactly balanced, or
maximally congested heart.

Title candidate (shorter, for the field): **Watching Skyrim's alchemy
solve itself: greedy vs optimal, animated**

## Long form (description body)

Skyrim's alchemy discovery problem - the fewest brews that reveal every
ingredient effect - is a set-cover instance (NP-hard). These animations
are exact: every line is one discoverable effect slot, lit at the moment
its brew happens, driven by the app's real planner and a MIP-optimal plan.
Greedy needs 76 brews; the optimum is 70; the gap plays out as six brews
of one-sided motion.

The later chapters are about the picture itself, and they include a
correction. The first renders had a dense hairball in the middle, and a
measurement said the inner disc carried nearly four times the ink density
of the ring around it. That number was real, but the layout was wrong: a
one-line bug had left the two rings a half-turn apart, every effect
opposite its own ingredients. The spinoff project that grew out of the
question caught it. On the corrected layout the centre is open (density
ratio 0.47), and the honest question became: over every possible ordering
of the two rings, how empty or how full can the middle be made? The band
is [0.29, 3.86], and three constructed orderings are shown - minimum
congestion (0.34), exact equilibrium (1.00), and maximum (3.73). Every
claim in these videos ships with a script and a witness file, including
the wrong one.

Everything is open and reproducible:
- App + campaign: https://github.com/bshepp/skyrim-alchemy-effect-finder
  (docs/math-notes/ for the ledger, anim/ for this pipeline)
- The congestion geometry spinoff: [chordwheel repo URL when public]
- The mod itself: https://www.nexusmods.com/skyrimspecialedition/mods/189861

Made in collaboration with Claude (Anthropic's AI assistant) under human
direction - the AI wrote the pipelines and renders, the human asked the
questions, chose the constructions, and verified the results. Stated
openly, as always.

## Chapters (compilation cut)

0:00 The race - greedy (amber) vs optimal (ice), 448 effect slots [v13]
0:45 Brew-order spectrum - each side divides red to violet by its count [v13]
1:30 The ingredient wheel - every line wears its source's colour [v14]
2:15 The effect wheel - lines pool into their targets [v15]
3:00 Where the ink lives - the hairball, and the bug behind it [v7 vs v13 frame]
3:45 The min-congestion wheel - the nearly empty heart (0.34) [v10]
4:30 The equilibrium wheel - line and space in exact balance (1.00) [v11]
5:15 The max-congestion wheel - the graph through its own heart (3.73) [v12]

(Timestamps assume ~45s per segment; fix after the edit is cut.)

## Ledger row (draft for LEDGER.md)

| date | project | venue | identity | what went | response |
2026-09-XX | alchemy cascade library | youtube | bshepp (personal) |
compilation video, Research Finding, links to both repos | -

## Open decisions

- Compilation vs singles (recommendation: one compilation; the
  amber/ice classic v13 optionally standalone for the article embed).
- Channel confirmed as the personal account (recommendation given;
  pre-flight review pending).
- chordwheel public repo URL - placeholder above until it exists.
