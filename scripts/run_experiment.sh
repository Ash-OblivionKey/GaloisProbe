#!/usr/bin/env bash
# Single entry point: run full experiment (multi-run, distinguishers, export, figures). Use --no-multi-run to skip multi-run.

cd "$(dirname "$0")/.."
python3 scripts/run_experiment.py "$@"
