@echo off
REM Generate multiple dumps and run distinguisher suite on each.
REM Usage: run_multi_run_suite.bat <library> [num_runs]
REM   library: seal | openfhe | helib
REM   num_runs: default 3

set LIB=%~1
set NUM=%~2
if "%NUM%"=="" set NUM=3

if "%LIB%"=="" (
  echo Usage: run_multi_run_suite.bat ^<library^> [num_runs]
  exit /b 1
)

cd /d "%~dp0.."
python scripts\run_multi_run_suite.py %LIB% %NUM%
