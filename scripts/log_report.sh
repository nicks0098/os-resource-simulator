#!/usr/bin/env bash
# Summarise logs/activity.log (format: time|LEVEL|module|message).
LOG="$(dirname "$0")/../logs/activity.log"
echo "=== Activity Log Summary (Bash) ==="
if [ ! -s "$LOG" ]; then echo "No activity logged yet."; exit 0; fi
echo "Total entries: $(wc -l < "$LOG")"
echo
echo "Entries by level:"
awk -F'|' '{c[$2]++} END{for(k in c) printf "  %-8s %d\n", k, c[k]}' "$LOG" | sort
echo
echo "Entries by module:"
awk -F'|' '{c[$3]++} END{for(k in c) printf "  %-12s %d\n", k, c[k]}' "$LOG" | sort
echo
echo "Last 5 warnings/errors:"
if grep -qE '\|(WARNING|ERROR)\|' "$LOG"; then
  grep -E '\|(WARNING|ERROR)\|' "$LOG" | tail -5 | sed 's/^/  /'
else
  echo "  (none)"
fi
exit 0
