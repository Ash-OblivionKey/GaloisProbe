#!/usr/bin/env python3
"""
Generate multiple dumps and run distinguisher suite on each.
Strengthens confidence by reporting variability across runs.

Usage: python3 run_multi_run_suite.py <library> [num_runs] [--distinguisher-only]
  library: seal | openfhe | helib
  num_runs: default 3
  --distinguisher-only: skip dump generation, run distinguishers on existing dumps only

Example: python3 run_multi_run_suite.py seal 5
Example (existing dumps): python3 run_multi_run_suite.py seal 3 --distinguisher-only
"""

import os
import subprocess
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
BUILD = PROJ / "instrumentation" / "build"
DUMP_BASE = PROJ / "dump"
RESULTS = PROJ / "output" / "results"


def get_dump_tool(lib: str):
    """Return path to dump executable, or None if not found."""
    subdirs = {"seal": "seal", "openfhe": "openfhe", "helib": "helib"}
    names = {
        "seal": ["seal_dump_keys.exe", "seal_dump_keys"],
        "openfhe": ["openfhe_dump_keys.exe", "openfhe_dump_keys"],
        "helib": ["helib_dump_keys.exe", "helib_dump_keys"],
    }
    if lib not in subdirs:
        return None
    base = BUILD / subdirs[lib]
    # Check base, then Release/, Debug/ (Windows/MSVC)
    for sub in ["", "Release", "Debug"]:
        dir_path = base / sub if sub else base
        for name in names[lib]:
            p = dir_path / name
            if p.exists():
                return p
    return None


def existing_run_dirs(lib: str, num_runs: int) -> list:
    """Return list of existing run directories (run_001, run_002, ...)."""
    dump_base = DUMP_BASE / lib
    found = []
    for i in range(1, num_runs + 1):
        run_dir = dump_base / f"run_{i:03d}"
        if (run_dir / "metadata.json").exists():
            found.append(run_dir)
    return found


# Parameters matching the paper's main experiment table (Table 1).
# SEAL: N=4096; OpenFHE: N=16384; HElib: m=4096 (phi(m)=2048).
LIBRARY_PARAMS = {
    "seal": ["--poly_modulus", "4096", "--scheme", "ckks"],
    "openfhe": ["--poly_modulus", "16384", "--scheme", "ckks"],
    "helib": ["--m", "4096", "--p", "3"],
}


def _get_he_roots() -> dict[str, str]:
    """Get HE library roots from env or CMakeCache."""
    roots = {}
    cache = PROJ / "instrumentation" / "build" / "CMakeCache.txt"
    if cache.exists():
        for line in cache.read_text().splitlines():
            for var in ("OPENFHE_ROOT", "HELIB_ROOT", "SEAL_ROOT"):
                if line.startswith(f"{var}:") and "=" in line:
                    val = line.split("=", 1)[1].strip()
                    if val and Path(val).exists():
                        roots[var] = val
    for var in ("OPENFHE_ROOT", "HELIB_ROOT", "SEAL_ROOT"):
        if var not in roots and os.environ.get(var):
            roots[var] = os.environ[var]
    return roots


def _dump_env() -> dict:
    """Build env with PATH including HE library install dirs (for DLL loading on Windows)."""
    env = os.environ.copy()
    roots = _get_he_roots()
    extra = []
    for var, subdirs in [("OPENFHE_ROOT", ["bin", "lib"]), ("HELIB_ROOT", [".", "lib"]), ("SEAL_ROOT", ["lib"])]:
        root = roots.get(var)
        if root:
            for d in subdirs:
                p = Path(root) / d
                if p.exists():
                    extra.append(str(p.resolve()))
    # MinGW runtime (common when built with msys2)
    for mingw in ["C:/msys64/mingw64/bin", "C:/msys64/ucrt64/bin"]:
        if Path(mingw).exists():
            extra.append(mingw)
            break
    if extra:
        env["PATH"] = os.pathsep.join(extra) + os.pathsep + env.get("PATH", "")
    return env


def run_dump(lib: str, run_dir: Path, tool: Path) -> bool:
    """Generate dump. Return True on success."""
    if lib not in LIBRARY_PARAMS:
        return False
    cmd = [str(tool), "--output", str(run_dir)] + LIBRARY_PARAMS[lib]
    r = subprocess.run(cmd, cwd=str(PROJ), capture_output=True, text=True, env=_dump_env())
    if r.returncode != 0 and r.stderr:
        print(f"    stderr: {r.stderr[:300]}")
    return r.returncode == 0


def main():
    args = [a for a in sys.argv[1:] if a not in ("--distinguisher-only", "-d")]
    distinguisher_only = "--distinguisher-only" in sys.argv or "-d" in sys.argv

    if len(args) < 1:
        print("Usage: python3 run_multi_run_suite.py <library> [num_runs] [--distinguisher-only]")
        print("  library: seal | openfhe | helib")
        print("  num_runs: default 3")
        print("  --distinguisher-only: run distinguishers on existing dumps only (no dump generation)")
        sys.exit(1)

    lib = args[0].lower()
    num_runs = int(args[1]) if len(args) > 1 else 3

    if lib not in ("seal", "openfhe", "helib"):
        print("Error: library must be seal, openfhe, or helib")
        sys.exit(1)

    dump_base = DUMP_BASE / lib
    tool = get_dump_tool(lib)

    if distinguisher_only:
        existing = existing_run_dirs(lib, num_runs)
        if not existing:
            print(f"Error: no existing dumps found in {dump_base}/run_001 .. run_{num_runs:03d}")
            print("  Each run needs metadata.json. Generate dumps first or build instrumentation.")
            sys.exit(1)
        print(f"Distinguisher-only mode: using {len(existing)} existing dump(s)")
        run_dirs = existing
        num_runs = len(existing)
    elif not tool:
        existing = existing_run_dirs(lib, num_runs)
        if existing:
            print(f"Note: {lib} dump tool not found. Use --distinguisher-only to run on existing dumps:")
            print(f"  python3 scripts/run_multi_run_suite.py {lib} {len(existing)} --distinguisher-only")
        else:
            print(f"Error: {lib} dump tool not found. Build instrumentation first:")
            print(f"  cd instrumentation/build")
            print(f"  cmake -DSEAL_ROOT=/path/to/SEAL-install ..  # for seal")
            print(f"  cmake -DOPENFHE_ROOT=/path/to/OpenFHE ..    # for openfhe")
            print(f"  cmake -DUSE_HELIB=ON -DHELIB_ROOT=/path/to/HElib ..  # for helib")
            print(f"  make")
        sys.exit(1)
    else:
        run_dirs = []
    dump_base.mkdir(parents=True, exist_ok=True)

    if not distinguisher_only:
        for i in range(1, num_runs + 1):
            run_id = f"run_{i:03d}"
            run_dir = dump_base / run_id
            run_dir.mkdir(parents=True, exist_ok=True)

            print(f"Generating dump {run_id} for {lib}...")
            if not run_dump(lib, run_dir, tool):
                print(f"Error: dump failed for {run_id}")
                sys.exit(1)

            print(f"Validating {run_dir}...")
            r = subprocess.run(
                [sys.executable, str(PROJ / "scripts" / "validate_dump.py"), str(run_dir)],
                cwd=str(PROJ),
                capture_output=True,
                text=True,
            )
            if r.returncode != 0:
                print(f"Validation failed: {r.stderr or r.stdout}")
                sys.exit(1)

            print(f"Running distinguisher suite on {run_dir}...")
            _run_distinguishers(run_dir)
            print()
    else:
        for run_dir in run_dirs:
            print(f"Running distinguisher suite on {run_dir}...")
            _run_distinguishers(run_dir)
            print()

    print(f"Done. Results in {RESULTS}/")
    agg_script = PROJ / "scripts" / "aggregate_multi_run_results.py"
    if agg_script.exists():
        subprocess.run([sys.executable, str(agg_script), lib, str(num_runs)], cwd=str(PROJ))


def _run_distinguishers(run_dir: Path):
    r = subprocess.run(
        [sys.executable, str(PROJ / "analysis" / "distinguisher_shared_mask_collision.py"), str(run_dir)],
        cwd=str(PROJ),
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(f"  Collision distinguisher failed: {r.stderr or r.stdout}")
    for name in ["rank_deficiency", "covariance_profiling", "regression_dependence", "bias_moments"]:
        subprocess.run(
            [sys.executable, str(PROJ / "analysis" / f"distinguisher_{name}.py"), str(run_dir)],
            cwd=str(PROJ),
            capture_output=True,
        )


if __name__ == "__main__":
    main()
