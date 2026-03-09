#!/usr/bin/env bash
# Run multi-run suite for all three libraries (SEAL, OpenFHE, HElib).
# Generates run_001..run_003 per library, runs distinguishers, produces aggregate_*_multi_run.json.
#
# Usage: ./scripts/run_all_multi_run.sh [num_runs]
#   num_runs: default 3

NUM="${1:-3}"
cd "$(dirname "$0")/.."

echo "=== Multi-run suite: $NUM runs per library ==="
for lib in seal openfhe helib; do
  echo ""
  echo "--- $lib ---"
  python3 scripts/run_multi_run_suite.py "$lib" "$NUM" || exit 1
done

echo ""
echo "=== Done. Aggregate files in output/results/ ==="
ls -la output/results/aggregate_*_multi_run.json 2>/dev/null || echo "No aggregate files (run may have failed)"
