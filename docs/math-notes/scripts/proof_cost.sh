#!/bin/bash
# Measure the cost of DRAT proof logging on a full-size rung-2 formula:
# identical conflict budgets with and without a proof file, reporting
# process time and proof bytes per conflict.
set -u
CNF=${1:-$HOME/cnc/rung2-sym.cnf}
BUDGET=${2:-20000}
cd ~/ladder

echo "=== formula: $CNF"
head -1 "$CNF"

run() {  # $1 label, $2 proof-path-or-empty
  local t0 t1
  t0=$(date +%s.%N)
  if [[ -n "$2" ]]; then
    ~/cnc/kissat/build/kissat --conflicts=$BUDGET "$CNF" "$2" > "$1.log" 2>&1
  else
    ~/cnc/kissat/build/kissat --conflicts=$BUDGET "$CNF" > "$1.log" 2>&1
  fi
  t1=$(date +%s.%N)
  local wall proc confl bytes
  wall=$(echo "$t1 - $t0" | bc)
  proc=$(grep -E '^c process-time:' "$1.log" | grep -oE '[0-9]+\.[0-9]+' | tail -1)
  confl=$(grep -E '^c conflicts:' "$1.log" | grep -oE '[0-9]+' | head -1)
  bytes=0; [[ -n "$2" ]] && bytes=$(stat -c %s "$2")
  printf '%-10s wall=%8.1fs process=%8ss conflicts=%-8s proof_bytes=%-14s bytes/conflict=%s\n' \
    "$1" "$wall" "$proc" "$confl" "$bytes" \
    "$(echo "scale=1; $bytes / $confl" | bc 2>/dev/null)"
}

run noproof ""
run withproof "$HOME/ladder/cost.drat"
rm -f "$HOME/ladder/cost.drat"
echo "=== done"
