@echo off
REM Single entry point: run full experiment (multi-run, distinguishers, export, figures). Use --no-multi-run to skip multi-run.

cd /d "%~dp0.."
python scripts\run_experiment.py %*
