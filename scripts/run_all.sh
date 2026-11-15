#!/usr/bin/env bash
# One-command demo: environment check -> tests -> every module -> analysis -> bash reports.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "[1/6] Checking environment"
command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }
python3 -c "import matplotlib" 2>/dev/null || { echo "Installing requirements..."; pip install -r requirements.txt; }
echo "[2/6] Running unit tests"
python3 -m unittest discover -s tests -v 2>&1 | tail -n 5
echo "[3/6] Running simulation modules"
python3 main.py all > outputs/traces/full_run.txt
echo "      trace written to outputs/traces/full_run.txt"
echo "[4/6] Live system information"
python3 main.py sysinfo | tee outputs/traces/system_info.txt
echo "[5/6] Activity log report"
python3 main.py logreport | tee outputs/traces/log_report.txt
echo "[6/6] Done. Charts: outputs/charts/  Tables: outputs/*.csv"
