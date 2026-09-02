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
   Since orbit sizes divide group order and 50 does not divide 48 (see
   result 11), some model symmetry is *emergent*: not induced by any
   relabeling of ingredients. Interpreting the generators is open.
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

## Open questions

- Close the corridors: exact optima for both universes (siege running;
  round 3 = proof-logging pseudo-Boolean/SAT per `symbolic-ladder.md`).
- The census of ALL optimal plans (requires the unpruned pairs+trios
  instance; covering-polynomial method at small scale, projected model
  counting at full scale).
- Interpret the 54 generators; explain the size-50 emergent orbit.
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
