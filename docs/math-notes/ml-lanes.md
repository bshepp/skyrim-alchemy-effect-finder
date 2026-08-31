# The three ML lanes

Set up 2026-08-30, ordered by who grades whom: **the factory grades the
scout, and both feed the apprentice.** Lane 3 produces exact ground
truth, which calibrates lane 1 and trains lane 2; lane 1 needs no ML and
attacks the live corridor immediately; lane 2 consumes the dataset last.

The standing constraint on all three: ML lives entirely on the NP side
of the asymmetry in `symbolic-ladder.md`. A model can *find* plans
(checkable witnesses that lower the ceiling); no model can ever prove a
floor. ML proposes; proof systems dispose.

## Lane 3 - the label factory (`scripts/label_factory.py`)

Samples small worlds from the ingredient pools under three growth
strategies (dense, sparse, uniform), computes EXACT labels via the
covering-polynomial engine - minimum plan size, census of all optimal
plans, next coefficients - plus a greedy baseline and its gap. Output:
`data/small-worlds-v1.jsonl`, one world per line.

Design notes:

- **The fence is the point.** Worlds are gated by reduced-row count
  (2^26 states), which is what makes the extrapolation experiment
  honest: train inside the fence, grade one rung beyond it (jaga can
  compute truth to ~35 rows), then ask the falsifiable question - does
  learned structure extrapolate across scale?
- **Pools are the mod axis.** Records carry a `pool` field (`uesp-112`,
  `full-180` today). A modded universe - CACO, Apothecary's remapped
  vanilla - later becomes one more pool feeding the same factory, and
  "train on Bethesda's design, test on CACO's design" becomes a
  distribution-shift experiment. Modded pools stay small dense graphs
  (CACO roughly doubles the pool; sharing stays dense), so every
  instrument here scales as-is.
- The `greedy_gap` label is a study in itself: on which worlds is
  greedy exactly optimal, and what structure predicts the gap?

## Lane 1 - the ceiling attack (`scripts/plan_search.py`)

Iterated local search on the real UESP-112 instance: start from the
exact 70-brew MIP plan, destroy 2-4 brews, greedily repair, accept
non-worsening, log improvements to `data/plan-search-best.json` the
moment they exist. A found 69-plan shrinks the corridor from above with
a millisecond-checkable witness. Calibration plan: run the same searcher
on factory worlds where the optimum is known, measuring how often ILS
finds true optima - lane 3 grading lane 1.

## Lane 2 - the apprentice (design; build after v1 data exists)

A graph network over the bipartite world graph (ingredient-slot rows,
mix columns), trained on factory labels. Two tasks, in order:

1. **Graph-level: predict the optimum** (and the census's order of
   magnitude). The extrapolation experiment proper.
2. **Column-level: predict participation marginals** - for each mix,
   the probability it appears in a uniformly random optimal plan. Exact
   marginal labels are computable with the same zeta engine (force a
   column in, count covers of the residual); v2 of the factory.

The expressivity ceiling is already measured: message-passing GNNs are
exactly as strong as 1-WL (the GIN theorem), and our naming probe
(`scripts/wl_probe.py`) IS 1-WL on this universe - so a standard GNN
provably cannot distinguish the duplicate-ingredient classes, and the
fix (random node features = individualization) is the naming probe's
pins. Solver symmetry, WL classes, and GNN expressivity are one
structure in three costumes; any lane-2 writeup should say so.

## Status

- 2026-08-30 ~23:20: factory v1 launched (2,000 worlds, both pools);
  ceiling attack launched (4 workers, 6 h). Siege (campaign-log
  result 8) concurrently holding bound 66 on jaga.
- Publishing note: the dataset is plausible nerd bait (exact set-cover
  instances with exact optima and censuses, from a game people love).
  If it ever goes to Hugging Face, that is a publish-registry decision
  with its own venue file and an explicit AI-involvement disclosure -
  not a phase-42 reflex. Phase 42 ships nothing by default.
