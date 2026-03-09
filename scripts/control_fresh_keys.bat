@echo off
REM Control: Fresh keys (Negative Control A).
REM Run SEAL dump 3 times. Expect: no collisions between runs.
REM See docs/methodology.md §4 (Control Procedures).

set DUMP_BASE=%~dp0..\dump\seal
set EXE=%~dp0..\instrumentation\build\seal\Release\seal_dump_keys.exe
if not exist "%EXE%" set EXE=%~dp0..\instrumentation\build\seal\seal_dump_keys.exe
if not exist "%EXE%" (
  echo Error: seal_dump_keys not found. Build instrumentation first.
  exit /b 1
)

echo Creating 3 fresh dumps...
"%EXE%" --output "%DUMP_BASE%\control_fresh_001" --poly_modulus 4096 --scheme ckks
"%EXE%" --output "%DUMP_BASE%\control_fresh_002" --poly_modulus 4096 --scheme ckks
"%EXE%" --output "%DUMP_BASE%\control_fresh_003" --poly_modulus 4096 --scheme ckks

echo.
echo Run distinguisher on each - expect 0 collisions within each run.
echo   python analysis\distinguisher_shared_mask_collision.py ..\dump\seal\control_fresh_001
echo   python analysis\distinguisher_shared_mask_collision.py ..\dump\seal\control_fresh_002
echo   python analysis\distinguisher_shared_mask_collision.py ..\dump\seal\control_fresh_003
