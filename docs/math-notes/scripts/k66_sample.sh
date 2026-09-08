#!/bin/bash
# Sample proof growth and guard the disk every 5 minutes.
#
# IMPORTANT: the guard watches the HOST drive (C:, via /mnt/c), not the
# WSL filesystem. ~/ladder lives on the ext4 root, which is a virtual
# disk (ext4.vhdx) stored on C:. From inside WSL that root reports its
# LOGICAL size (~1 TB) no matter how full the host is, so a guest-side
# guard reads ~700 GB free right up until the host system drive fills.
# Verified 2026-09-07: df on /mnt/c agrees with PowerShell to within 1 GB.
set -u
cd ~/ladder
MIN_HOST_GB=${MIN_HOST_GB:-100}

host_free_gb() { df -BG --output=avail /mnt/c | tail -1 | tr -dc 0-9; }

while true; do
  ts=$(date '+%Y-%m-%dT%H:%M:%S')
  for v in plain sym; do
    sz=$(stat -c %s "k66-$v.drat" 2>/dev/null || echo 0)
    line=$(grep -E '^c [-a-zA-Z] [0-9]' "k66-$v.log" 2>/dev/null | tail -1)
    cf=$(echo "$line" | awk '{print $10}')
    rem=$(echo "$line" | awk '{print $NF}')
    verdict=$(grep -m1 '^s ' "k66-$v.log" 2>/dev/null)
    alive=no
    pgrep -f "kissat rung2-k66-$v.cnf" > /dev/null && alive=yes
    echo "$ts $v alive=$alive bytes=$sz conflicts=${cf:-0} remaining=${rem:-?} ${verdict:-}"
  done
  host=$(host_free_gb)
  echo "$ts host_C_avail_gb=${host:-?}"
  if [ "${host:-0}" -lt "$MIN_HOST_GB" ]; then
    echo "$ts ABORT: host C: below ${MIN_HOST_GB}G, stopping k66 runs"
    for p in $(pgrep -f 'kissat rung2-k66'); do kill "$p"; done
    break
  fi
  if ! pgrep -f 'kissat rung2-k66' > /dev/null; then
    echo "$ts all k66 runs finished; sampler exiting"
    break
  fi
  sleep 300
done
