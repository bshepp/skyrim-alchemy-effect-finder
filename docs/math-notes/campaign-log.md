# Campaign log: the mathematics of alchemy discovery

The ledger of everything established so far in the post-launch
mathematical campaign (phase 42). Every claim below is dated, names its
instrument, and says where the artifact lives. Prior work by others is
credited in `prior-art.md`.

## The problem

Skyrim's rule: a mix of 2 or 3 distinct ingredients produces exactly the
effects shared by at least two of its members, and brewing reveals each
produced effect on every participant that has it. Discovery is therefore
a covering problem:

- **Rows** are (ingredient, effect-slot) pairs whose effect appears on
  at least two ingredients in the universe (a slot whose effect has no
  partner can never be revealed by any brew).
- **Columns** are mixes; a mix covers the slots it reveals.
- A **discovery plan** is a set of mixes covering every row; the prize
  is the minimum plan size, and eventually the census of all minimum
  plans. This is set cover: NP-hard in general, and concretely hard
  here.

Two universes: **UESP-112** (base + DLC, excluding the unobtainable
Berit's Ashes and Jarrin Root - matches UESP's own accounting) and
**full-180** (everything the app ships, including the free Creations).

## Established results

1. **Census of all mixes** (2026-08-28, local): the full game has
   971,970 valid mixes; by number of effects produced:
   0: 369,690 / 1: 410,922 / 2: 161,002 / 3: 26,794 / 4: 3,527 / 5: 35.
2. **The teaching potion** (2026-08-28): Ancestor Moth Wing + Blue
   Butterfly Wing + Chaurus Hunter Antennae is the unique mix revealing
   12 of 12 participating slots, because the three carry identical
   effect quadruples.
3. **719 of 720** (2026-08-28): Fortify Persuasion appears only on
   Glassfish, so exactly one effect-slot in the full game can never be
   revealed by any brew. Reinterpreted 2026-08-30 (result 11): it is the
   game's only natural *name-effect*.
4. **Minimum ingredient cover = 16** (2026-08-28/29): the fewest
   ingredients whose effects span each universe's effect list is 16 in
   BOTH universes ("sixteen is stubborn"); witness lists computed.
5. **Greedy discovery plans** (2026-08-28, lazy-greedy, exact
   Minoux-style): full-180 in 114 brews, UESP-112 in 76.
6. **Exact MIP corridors** (2026-08-29, HiGHS on jaga, overnight):
   full-180 optimum in **[95, 108]** with an actual 108-brew plan;
   UESP-112 optimum in **[66, 70]** with an actual 70-brew plan. Plans
   and solver metadata: `data/alchemy-mip-results.json`,
   `data/alchemy-mip-results-uesp.json`. Lesson: HiGHS branch-and-bound
   is effectively serial.
7. **The ladder shutout** (2026-08-29/30, `scripts/jaga_ladder.py`,
   CP-SAT fixed-k feasibility probes): all 17 probes (UESP k=66..69,
   full k=95..107) exhausted 12-hour caps at UNKNOWN. Zero information
   in either direction; corridors unchanged.
   `data/alchemy-ladder-results.json`. Lesson: bare BoolOr + cardinality
   probing does not engage at this scale, and the instance's symmetry
   (result 9) is the suspected culprit.
8. **The siege** (2026-08-30 17:57 to 2026-09-01 17:57,
   `scripts/jaga_siege_uesp.py`): CP-SAT optimization mode on the
   unpruned UESP instance (448 rows x 39,612 trio-columns), warm-hinted
   with the 70-brew plan, corridor as hard constraints, fully
   instrumented. Final verdict at the full 48-hour cap: FEASIBLE,
   objective 70, **bound 66.00 - zero movement in 172,803 seconds on
   80 workers**; the dedicated lower-bound subsolvers recorded zero
   improvements. Measured conclusion: CP-SAT cannot move this floor in
   either of its modes; the corridor's remaining gap [67..69] belongs
   to proof-logging engines (symbolic-ladder rung 2). Ceiling
   evidence meanwhile is unanimous: the MIP's 70, two days of LNS, and
   6.3 M iterated-local-search perturbations (`scripts/plan_search.py`)
   all failed to find 69. Working hypothesis: the UESP optimum is
   exactly 70, one UNSAT certificate at k=69 away from a theorem.
9. **Model symmetry** (2026-08-30, from the siege's own presolve log):
   54 symmetry generators; 3,256 orbits on 7,640 variables, orbit sizes
   50, 12, then many 6s; an 800x2 orbitope detected and exploited.
   *Resolved 2026-09-01* (`scripts/orbit_probe.py`): WL refinement on
   the clean model (448 rows x 37,872 pruned columns) finds 3,149
   interchangeable-column families covering 7,346 columns - within ~3%
   of CP-SAT's counts - and every family decodes as a *product of
   duplicate-ingredient classes* (sizes 2, 3, 4, 6, and one 12 =
   wings x eggs x nirnroots). The covering problem's symmetry group is
   exactly the clone-product group of result 11, order 48. The size-50
   orbit and the surplus generators were artifacts of CP-SAT's internal
   encoding graph (119K nodes of literal/constraint machinery), not of
   the problem. Also measured: effect degrees in UESP-112 span 4..21
   with NO degree-2 or degree-3 effects, so neither frequency tail
   creates symmetry - exact duplication is the entire story.
10. **Duplicate-ingredient census** (2026-08-30,
    `scripts/dup_census.py`): ingredients with identical effect sets.
    UESP-112 has four classes (nine ingredients): the wing triple;
    Chicken's Egg = Hawk's Egg; Crimson Nirnroot = Nirnroot; Dwarven
    Oil = Taproot. Full-180 adds Bone Meal = Berit's Ashes, Human
    Heart = Mort Flesh, Elytra Ichor = Green Butterfly Wing, and the
    two Flame Stalks. Near-twins (3 of 4 effects shared): 8 pairs in
    UESP, 20 in full.
11. **The naming probe** (2026-08-30, `scripts/wl_probe.py`): anonymous
    color refinement (1-WL) on the label-stripped ingredient-effect
    graph stabilizes in 4 rounds and distinguishes 107 of 112 UESP
    ingredients - failing exactly on the duplicate classes. Sandwich
    argument (refinement classes are unions of orbits; duplicate swaps
    are automorphisms; clones have identical neighborhoods) gives the
    graph's automorphism group exactly: S3 x S2 x S2 x S2, order 48.
    Individualization: 5 pins fully name the UESP universe, 9 the full
    game (the determining number). The full game has exactly one
    degree-1 effect - Fortify Persuasion - i.e. the game shipped one
    ingredient whose fourth effect is functionally its own name, and
    that is precisely why one slot of 720 is unbrewable.
12. **Covering polynomials** (2026-08-30,
    `scripts/covering_polynomial.py`): exact P(x) = sum of x^|S| over
    covering sets S (mixes un-deduped - this is the census object) for
    greedily-grown sub-universes, by inclusion-exclusion via superset-
    zeta transform, brute-force verified on the small end. For the wing
    triple alone, P(x) = x + 6x^2 + 4x^3 - the lone x term is the
    teaching potion. Fence data in `symbolic-ladder.md`: a desktop
    reaches 11 ingredients; jaga should reach ~13-14.
13. **The hairball is the hardness** (2026-09-05, `anim/` density
    measurement): in the radial layout (ingredients R=10, effects
    R=4.5, barycenter-untangled), the disc inside the effects ring
    carries 4.74x the annulus's ink density, area-compensated; 422 of
    448 edges penetrate it. With equal-area rings (effects at
    R/sqrt 2) the ratio is still 3.61x, with 78% of total line length
    inside. No circular ordering can empty the center: each
    ingredient's four effects scatter across the effect space, and
    that expansion is the same property that defeats LP rounding and
    starves CDCL of exploitable structure at k=69. CORRECTED same day:
    the claim "no circular ordering can empty the center" was
    conjecture from expansion intuition, and a 60k-swap hill-climb
    over ring permutations (scripts/congestion_extremes.py) falsified
    it - at the equal-area radius the ordering band is [0.43, 3.76]
    (barycenter sits at 3.61; supremum 4 = all-diameters), so the
    center CAN be emptied and equality (ratio 1) is crossable by
    ordering alone. What survives: (a) for the FIXED barycenter
    ordering, a radius sweep shows the ratio falls monotonically to a
    2.55 floor (closed form in the merged limit: 4*sum sin(gap/2) /
    sum 1/sin(gap/2)) and never reaches 1 - the impossibility was
    ordering-conditional; (b) the dataset's true invariant is the
    achievable BAND, not any single layout's ratio. The hairball was
    the heuristic's hardness, not (proven to be) the graph's. Open:
    render the min-congestion ordering; does min-achievable congestion
    across the 2,015 labeled small worlds predict their hardness?

14. **Cube-and-conquer does not bite at k=69** (2026-09-06, staged on
    the desktop, racers untouched): two routes tested and retired.
    treengeling (12 threads, 20h) spent 74% of its time
    re-simplifying the 2.65M-var formula, froze at 23 tree nodes,
    and completed less total search than one racer thread does alone.
    Manual cubes over the top-4 coverage variables (16 cubes + a
    baseline, 20k-conflict kissat probes each): remaining-variable
    percentages 48-53% across cubes vs 52% baseline, with matching
    propagation and decision profiles - conditioning on the strongest
    covers leaves subproblems as hard as the whole. Consistent with
    the flat LP floor: the instance shows no exploitable seam from
    this direction either. The racer portfolio remains the strongest
    known attack and runs on.

15. **The certified ladder, and the checkability horizon** (2026-09-07/08,
    staged on the desktop; jaga's racers untouched). Premise: the race
    attacks k=69, the *hardest* UNSAT rung in the family, sitting one
    step below the flip to SAT. The corridor's floor of 66 is an LP
    bound that was never tested directly, so k=66..68 are open, each
    strictly easier to refute, and each one that falls tightens the
    corridor from below. `rung2_encode.py` now takes the bound on the
    command line (commit da85d4a; selftest unchanged, 13 worlds).
    **Certificate pipeline built and validated end to end** on both
    machines: kissat -> binary DRAT -> drat-trim, cadical -> DRAT ->
    drat-trim, and cadical -> LRAT -> lrat-check, all returning
    VERIFIED on small worlds carrying live seqcounter cardinality and
    lex-leader clauses. Trap recorded: cadical writes LRAT in binary by
    default and lrat-check reads only text, failing as "Last line
    checked = 0 / NOT VERIFIED" with exit 0.
    **Only the plain encoding can certify the claim.** The sym variant's
    lex-leader clauses are satisfiability-preserving but not implied, so
    a verified refutation of rung2-sym.cnf certifies the symmetry-broken
    formula and leaves an unmachine-checked step in front of the actual
    conclusion. This costs nothing: after 149 h the plain and sym racers
    are indistinguishable (26%/26% cadical, 33%/33% kissat), so the
    order-48 clone group buys no measurable search advantage at 2.65 M
    variables.
    **Measured costs of proof logging** (identical 20,002-conflict
    budgets on the full formula): 261.3 s without a proof vs 276.6 s
    with, i.e. **~6% wall-time overhead**, far cheaper than assumed. The
    expense is disk: **8,406 bytes per conflict** over a full 5h 24m run
    (marginal windows 4.9-8.7 KB), about 4.3 MB/s sustained.
    **The binding constraint is neither time nor disk but memory.**
    drat-trim verifies backward, reconstructing unit propagations in
    reverse, which effectively wants the whole proof resident. A 10 M
    conflict run produced an **84 GB** proof, already past the desktop's
    48 GB and straining jaga's 251 GB. Disk can be bought; this cannot.
    The structural fix is to emit **LRAT**, whose resolution hints make
    checking a forward, single-pass, bounded-memory operation, at the
    cost of a larger file. Recorded because it reframes the campaign's
    stopping rule: a rung is certifiable only if it refutes within a
    conflict budget whose proof we can still check.
    **Negative result on the ladder's premise.** Same solver, same
    encoding, three rungs of cardinality slack: kissat on rung2-sym at
    k=69 plateaus at 33% remaining variables; at k=66 it reaches 29% and
    stops there too, holding that figure from 1.6 M conflicts through
    **25.4 M** with no verdict. The easier rung is markedly faster
    (516 conflicts/sec vs 77 on the same hardware at k=69) but lands on
    the same structural floor. Lower rungs are so far easier only in
    throughput, not in kind. Artifact kept with provenance:
    `F:\_shared-resources\sat-proofs\k66-plain-2026-09-08\` (84 GB
    partial DRAT + its CNF + solver log; incomplete, proves nothing on
    its own, but DRAT proofs concatenate so it could still form the
    front half of a real certificate).
    **Phase transition in miniature**, from the by-product instrument
    (`make_medium.py`, 26-ingredient sub-universe, 88 rows, 457 pruned
    columns): descending from a greedy cover of 20, k=20 solves SAT in
    **24.4 s**, k=19 in **251.9 s**, and k=18 in **44,773 s (12.4 h)**
    - escalation factors of **10.3x then 177.7x** for one rung each.
    Difficulty explodes approaching the optimum from above, which is the
    same geometry that makes k=69 the worst possible rung to have
    attacked and the clearest independent argument for working from the
    bottom. *Updated 2026-09-08 09:2x: k=18 resolved SAT after the entry
    above was written (it had been recorded as unresolved at 11 h); the
    descent moved on to k=17.* The consequence is sharper than the
    curve: this world's optimum is only known to be **at most 18**, and
    projecting the observed ratios puts k=17 somewhere between 5 days
    and 3 months. **A 26-ingredient sub-universe therefore cannot have
    its optimum determined by SAT descent** - on an instance with 88
    rows and 457 columns, against the real problem's 448 and 37,872.
    That is the campaign's whole difficulty reproduced in a toy, and it
    is the strongest evidence yet that the corridor [66, 70] is not
    closing by search.

## Open questions

- Close the corridors: exact optima for both universes (siege running;
  round 3 = proof-logging pseudo-Boolean/SAT per `symbolic-ladder.md`).
- The census of ALL optimal plans (requires the unpruned pairs+trios
  instance; covering-polynomial method at small scale, projected model
  counting at full scale).
- Interpret the 54 generators; explain the size-50 emergent orbit.
- Does any rung of the corridor refute inside a *checkable* budget? Result
  15 makes this the operative question: an uncertified UNSAT is a claim,
  not a theorem, and at ~8.4 KB of DRAT per conflict the certificate
  outgrows available memory long before the search concludes. Cheapest
  test is a no-proof scout per rung to find the refutation length first,
  then re-run in LRAT only where the number says the proof can be
  checked.
- The essay's door II (the descent) awaits the corridor verdicts.

## Where things live

- `scripts/` - every campaign instrument, archived as run.
- `data/` - solver results pulled home from the compute box, including
  the actual 108- and 70-brew plans.
- The interactive essay draft (five doors, one cliff) is a private
  Claude artifact of the project owner; it is deliberately not in this
  public repo.
- Compute-box operational history lives in the operator's machine
  cookbook, not here.
- The congestion-geometry line of inquiry (result 13 and its
  correction) spun off 2026-09-05 into its own project - working name
  chordwheel, local sibling directory - taking the ordering
  optimization, synthetic finite-material world families, and the
  congestion-vs-hardness question with it. Its HANDOFF.md points back
  here; data crossings cite commits.
