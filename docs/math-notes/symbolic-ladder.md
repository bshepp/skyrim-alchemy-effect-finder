# The symbolic ladder

What it would take to *prove* the minimum discovery plan, rather than
merely compute it. Four rungs, in increasing order of rigor and cost.
Written 2026-08-30, while the siege (campaign-log result 8) grinds.

## The asymmetry that motivates all of this

The claim "70 brews suffice" already has a tiny checkable certificate:
the plan itself (`data/alchemy-mip-results-uesp.json`), verifiable by
simulating 70 brews. The claim "65 brews do not suffice" quantifies over
every 65-subset of 39,612 mixes and has no such object - that is the
NP vs co-NP asymmetry in game clothing. We hold the easy half of a
symbolic proof; the ladder is about the hard half: a checkable
certificate for the floor.

## Rung 1 - exact rational LP certificate (days; buyable now)

The floor of 66 currently rests on floating-point LP (HiGHS). Upgrade:
solve the LP relaxation in exact rational arithmetic (Sage, or SoPlex
exact mode) and keep the **dual solution** - a rational weighting of the
448 slots such that no mix collects more than 1 unit of weight, yet the
total weight exceeds 65. Human-legible floor proof: each brew pays for
at most one unit; the world owes more than 65 units; 65 brews cannot
settle the debt. Hand-checkable arithmetic; no solver trusted.

## Rung 2 - proof-logging solvers (the modern standard; this is round 3)

SAT solvers (kissat, CaDiCaL) emit DRAT/LRAT proof traces of UNSAT;
pseudo-Boolean solvers (RoundingSat) emit VeriPB certificates, which can
also certify symmetry breaking as sound proof steps rather than trusted
preprocessing. The computation and the proof become the same act: close
k=66 with proof logging on, and the answer arrives holding its own
certificate, checkable by an independently verified checker (cake_lpr
and kin). Costs: the same solve times plus disk for the proof (the
famous precedents ran 200 TB for Pythagorean triples and 2 PB for Schur
five; ours may be far smaller) plus checking time comparable to solving.
Plan if the siege stalls: RoundingSat first (cardinality is native), the
four duplicate classes broken by explicit canonical-order constraints,
BreakID for the emergent remainder, kissat + totalizer as the fallback.

## Rung 3 - a kernel-checked theorem (weeks; the crown jewel)

Formalize in Lean 4: define the mixing rule and the ingredient dataset,
prove once that the CNF encoding is faithful to the game, then import
the solver's LRAT certificate through the verified checker
infrastructure that already exists (the `bv_decide` LRAT path). End
state: `minDiscoveryPlan uesp = 70` as a theorem checked by a proof
kernel, trusting no solver and no floating point. Most of the labor is
the encoding-faithfulness proof. Dovetails with the planned Lean
formalization of the lazy-greedy exactness theorem.

## Rung 4 - the covering polynomial (beautiful; bounded; taken to the fence)

The purest reading: the answer is a *coefficient*. For an instance with
row set R and mix list C, the covering polynomial is

    P(x) = sum over covering sets S of x^|S|
         = sum over U subseteq R of (-1)^|U| (1+x)^(m_U)

where m_U counts mixes touching no row of U. The lowest-degree nonzero
term's degree is the minimum plan size; its coefficient is the census of
all optimal plans. One polynomial contains the whole campaign.

Cost is 2^|R|: for the real UESP instance (448 rows) that is ~10^134
terms - more than the atoms in the observable universe, before Buchberger
even clears its throat. The rung cannot be completed. It can be climbed
to the fence.

**The fence, measured** (2026-08-30, `scripts/covering_polynomial.py`:
superset-zeta transform over row subsets, sound row reduction, exact
big-integer binomials, brute-force verified at the small end).
Sub-universes grown greedily from Blue Butterfly Wing; `red` is rows
after reduction; census = number of distinct optimal plans:

| n ingredients | rows | red | mixes | OPT | census | next coefficients |
|---|---|---|---|---|---|---|
| 3 | 12 | 3 | 4 | 1 | 1 | 6, 4 |
| 4 | 14 | 4 | 10 | 2 | 15 | 88, 194 |
| 5 | 17 | 5 | 17 | 2 | 3 | 144, 1115 |
| 6 | 21 | 6 | 29 | 3 | 57 | 2,803, 33,707 |
| 7 | 27 | 9 | 47 | 4 | 117 | 9,887, 264,969 |
| 8 | 30 | 16 | 75 | 5 | 1,080 | 160,647, 8,550,624 |
| 9 | 32 | 18 | 109 | 5 | 594 | 187,635, 19,447,360 |
| 10 | 36 | 22 | 152 | 5 | 2 | 3,329, 1,498,901 |
| 11 | 39 | 26 | 206 | 6 | 526 | 546,306, 185,393,714 |
| 12 | 43 | 34 | - | - | past the desktop fence (2^34) | - |

For the wing triple alone (n=3), the full polynomial is

    P(x) = x + 6x^2 + 4x^3

and the lone x term **is the teaching potion** - the unique one-brew
cover of that universe, sitting in a symbolic object as the coefficient
1. Note also n=10: a sub-universe whose optimum is achieved by exactly
**two** plans - near-uniqueness appears in the wild.

Memory sets the fence: 2^28 states = 1 GiB (desktop, n=11), 2^34 = 64
GiB and 2^35 = 128 GiB (jaga, post-siege, expected n~13-14). Next fence
pushes if wanted: connected-component factoring of P (products of
component polynomials), and uint16 states. Beyond that, the census at
full scale belongs to projected model counting (#SAT), which trades the
polynomial for a number and the certificate for weaker assurances.

Pairs note: columns here are all valid pairs AND trios, un-deduped,
because the census counts mixes as distinct objects. (The search-side
instances prune pairs and duplicates - sound for the optimum's value,
never for the census.)
