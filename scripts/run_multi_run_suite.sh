#!/usr/bin/env bash
# Generate multiple dumps and run distinguisher suite on each.
# Usage: run_multi_run_suite.sh <library> [num_runs]
#   library: seal | openfhe | helib
#   num_runs: default 3

LIB="$1"
NUM="${2:-3}"

if [ -z "$LIB" ]; then
  echo "Usage: run_multi_run_suite.sh <library> [num_runs]"
  exit 1
fi

cd "$(dirname "$0")/.."
python3 scripts/run_multi_run_suite.py "$LIB" "$NUM"
