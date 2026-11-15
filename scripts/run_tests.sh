#!/usr/bin/env bash
# Run all test cases and save the evidence to outputs/traces/test_results.txt
cd "$(dirname "$0")/.."
mkdir -p outputs/traces
python3 -m unittest discover -s tests -v 2>&1 | tee outputs/traces/test_results.txt
exit "${PIPESTATUS[0]}"
