#!/bin/bash
# Cube-decomposition experiment: does fixing the top-S cover variables
# make the k=69 subproblems measurably easier for kissat?
# Baseline + all 2^S cubes, fixed conflict budget each, 6-way parallel.
set -u
cd ~/cnc
S=4
BUDGET=20000
EXP=~/cnc/cube-exp
mkdir -p "$EXP"
BASE=rung2-sym.cnf

# header: bump clause count by S for the appended units
read _ _ NV NC < <(head -1 "$BASE")

gen_cube() {  # $1 = cube index (bit i of $1 = sign of var i+1)
  local idx=$1 out="$EXP/cube-$1.cnf"
  { printf 'p cnf %d %d\n' "$NV" $((NC + S))
    tail -n +2 "$BASE"
    for ((i = 0; i < S; i++)); do
      if (( (idx >> i) & 1 )); then printf '%d 0\n' $((i + 1))
      else printf '%d 0\n' $((-(i + 1))); fi
    done
  } > "$out"
}

run_one() {  # $1 = label, $2 = cnf path
  ./kissat/build/kissat --conflicts=$BUDGET "$2" > "$EXP/$1.log" 2>&1
  local rc=$?
  local verdict="UNKNOWN"
  grep -q '^s SATISFIABLE' "$EXP/$1.log" && verdict="SAT"
  grep -q '^s UNSATISFIABLE' "$EXP/$1.log" && verdict="UNSAT"
  local line
  line=$(grep -E '^c (-|\{|\})' "$EXP/$1.log" | tail -1)
  local secs confl
  secs=$(grep -Ei 'process-time' "$EXP/$1.log" | grep -oE '[0-9]+\.[0-9]+' | tail -1)
  confl=$(grep -Ei '^c conflicts:' "$EXP/$1.log" | grep -oE '[0-9]+' | head -1)
  echo "$1 verdict=$verdict conflicts=$confl secs=$secs lastreport=[$line]"
}

echo "=== generating $((1 << S)) cubes over vars 1..$S"
for ((c = 0; c < (1 << S); c++)); do gen_cube "$c"; done

echo "=== baseline"
run_one baseline "$BASE"

echo "=== cubes (6-way parallel)"
for ((c = 0; c < (1 << S); c++)); do
  ( run_one "cube-$c" "$EXP/cube-$c.cnf" ) &
  while (( $(jobs -r | wc -l) >= 6 )); do wait -n; done
done
wait
echo "=== all runs complete"
