@echo off
REM Run multi-run suite for all three libraries (SEAL, OpenFHE, HElib).
REM Generates run_001..run_003 per library, runs distinguishers, produces aggregate_*_multi_run.json.
REM
REM Usage: scripts\run_all_multi_run.bat [num_runs]
REM   num_runs: default 3

set NUM=%1
if "%NUM%"=="" set NUM=3

cd /d "%~dp0\.."

echo === Multi-run suite: %NUM% runs per library ===
for %%L in (seal openfhe helib) do (
  echo.
  echo --- %%L ---
  python scripts\run_multi_run_suite.py %%L %NUM% || exit /b 1
)

echo.
echo === Done. Aggregate files in output\results\ ===
dir output\results\aggregate_*_multi_run.json 2>nul || echo No aggregate files (run may have failed)
