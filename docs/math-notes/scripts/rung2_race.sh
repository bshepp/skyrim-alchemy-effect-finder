#!/bin/bash
# Rung-2 portfolio race: six single-threaded proof engines on k=69.
# UNSAT from any one of them (plus the 70-brew witness) proves OPT=70.
# 96 h timeout each; exit 10 = SAT, 20 = UNSAT, 124 = timeout.
mkdir -p ~/rung2-logs
launch() {
  nohup nice -n 10 timeout 345600 $2 $3 > ~/rung2-logs/$1.log 2>&1 &
  echo "$1 pid $!"
}
launch kissat-sym     "kissat"          ~/rung2-sym.cnf
launch kissat-sym-u   "kissat --unsat"  ~/rung2-sym.cnf
launch kissat-plain   "kissat"          ~/rung2-plain.cnf
launch kissat-plain-u "kissat --unsat"  ~/rung2-plain.cnf
launch cadical-sym    "cadical"         ~/rung2-sym.cnf
launch cadical-plain  "cadical"         ~/rung2-plain.cnf
