#!/bin/bash
# Overnight staging run for the certified ladder, rung k=66.
#
# Two jobs, deliberately asymmetric:
#
#   plain + DRAT  - the certified attempt. Plain because the sym
#                   variant's lex-leader clauses are satisfiability-
#                   preserving but NOT implied, so a proof of the sym
#                   formula certifies the symmetry-broken problem
#                   rather than the original claim.
#   sym, no proof - an unencumbered scout. Answers "is k=66 refutable
#                   at all, and at what conflict count" without paying
#                   disk for a certificate we could not use anyway.
#
# Disk is the binding constraint (measured ~10.4 KB/conflict), so the
# sampler tracks growth and aborts before the filesystem fills.
set -u
cd ~/ladder

nohup nice -n 5 ~/cnc/kissat/build/kissat \
    rung2-k66-plain.cnf k66-plain.drat > k66-plain.log 2>&1 &
echo "launched k66-plain (certified, DRAT) pid=$!"

nohup nice -n 5 ~/cnc/kissat/build/kissat \
    rung2-k66-sym.cnf > k66-sym.log 2>&1 &
echo "launched k66-sym (scout, no proof) pid=$!"

sleep 2
nohup ./k66_sample.sh > k66-growth.log 2>&1 &
echo "launched sampler pid=$!"
sleep 3
pgrep -af 'kissat rung2-k66'
