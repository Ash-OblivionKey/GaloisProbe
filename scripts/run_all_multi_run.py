#!/usr/bin/env python3
"""
Run multi-run suite for all three libraries (SEAL, OpenFHE, HElib).
Generates run_001..run_003 per library, runs distinguishers, produces aggregate_*_multi_run.json.

Usage: python scripts/run_all_multi_run.py [num_runs]
  num_runs: default 3
"""

import subprocess
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
BUILD = PROJ / "instrumentation" / "build"
SUITE = PROJ / "scripts" / "run_multi_run_suite.py"


def get_dump_tool(lib: str) -> Path | None:
    """Return path to dump executable, or None if not found."""
    names = ["seal_dump_keys.exe", "seal_dump_keys", "openfhe_dump_keys.exe", "openfhe_dump_keys", "helib_dump_keys.exe", "helib_dump_keys"]
    lib_names = {"seal": names[:2], "openfhe": names[2:4], "helib": names[4:6]}
    base = BUILD / lib
    for sub in ("", "Release", "Debug"):
        d = base / sub if sub else base
        for name in lib_names.get(lib, []):
            p = d / name
            if p.exists():
                return p
    return None


def main():
    num_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(f"=== Multi-run suite: {num_runs} runs per library ===")
    ran = 0
    for lib in ("seal", "openfhe", "helib"):
        tool = get_dump_tool(lib)
        if not tool:
            print(f"\n--- {lib} --- SKIP (dump tool not found; build instrumentation with {lib.upper()})")
            continue
        print(f"\n--- {lib} ---")
        r = subprocess.run(
            [sys.executable, str(SUITE), lib, str(num_runs)],
            cwd=str(PROJ),
        )
        if r.returncode != 0:
            sys.exit(r.returncode)
        ran += 1
    if ran == 0:
        print("\nNo dump tools found. Build instrumentation first (see README Path B).")
        sys.exit(1)
    print("\n=== Done. Aggregate files in output/results/ ===")
    agg_dir = PROJ / "output" / "results"
    for f in sorted(agg_dir.glob("aggregate_*_multi_run.json")):
        print(f"  {f.name}")


if __name__ == "__main__":
    main()
