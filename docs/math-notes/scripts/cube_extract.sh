#!/bin/bash
# Pull comparable end-state metrics from each cube-experiment log:
# the last periodic report line (remaining-variables % is the final
# column) and headline statistics.
cd ~/cnc/cube-exp
for f in baseline cube-0 cube-1 cube-2 cube-3 cube-4 cube-5 cube-6 \
         cube-7 cube-8 cube-9 cube-10 cube-11 cube-12 cube-13 cube-14 cube-15; do
  rep=$(grep -E '^c [-{}OiFsu] ' "$f.log" | grep -v '\[' | tail -1)
  props=$(grep -E '^c propagations:' "$f.log" | grep -oE '[0-9]+' | head -1)
  decs=$(grep -E '^c decisions:' "$f.log" | grep -oE '[0-9]+' | head -1)
  printf '%-9s decisions=%-9s propagations=%-12s last_report: %s\n' \
    "$f" "$decs" "$props" "${rep:0:110}"
done
