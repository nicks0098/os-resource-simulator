#!/usr/bin/env bash
# Live OS resource snapshot (the "real" counterpart of what the simulator models).
set -u
echo "=== Live System Information (Bash) ==="
echo "Host        : $(hostname)"
echo "Kernel      : $(uname -sr)"
echo "CPU cores   : $(nproc 2>/dev/null || echo n/a)"
if [ -r /proc/loadavg ]; then
  read -r l1 l5 l15 _ < /proc/loadavg
  echo "Load average: $l1 (1m)  $l5 (5m)  $l15 (15m)"
fi
if [ -r /proc/meminfo ]; then
  awk '/MemTotal/{t=$2} /MemAvailable/{a=$2} /SwapTotal/{st=$2} /SwapFree/{sf=$2}
       END{printf "Memory      : %.0f MB total, %.0f MB available (%.1f%% used)\n", t/1024, a/1024, (t-a)*100/t;
           printf "Swap        : %.0f MB total, %.0f MB free\n", st/1024, sf/1024}' /proc/meminfo
fi
echo
echo "Disk usage (root filesystem):"
df -h / | awk 'NR==1 || NR==2'
echo
echo "Top 5 processes by memory:"
ps -eo pid,comm,%mem,%cpu --sort=-%mem 2>/dev/null | head -6
echo
echo "Process states:"
ps -eo stat= 2>/dev/null | cut -c1 | sort | uniq -c | awk '{printf "  %-3s %s\n", $2, $1}'
