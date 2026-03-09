#!/usr/bin/env python3
"""
Run the full experiment: multi-run key generation, distinguishers, export CSV, figures.

Single entry point. By default: (1) generates 3 dumps per library, (2) runs controls,
(3) runs five distinguishers on all dumps, (4) exports results.csv, (5) generates figures.

Usage: python scripts/run_experiment.py [--no-multi-run] [--no-controls] [--no-export] [--no-clean]
  --no-multi-run: skip multi-run; use existing dumps only (dump/*/run_001, etc.)
  --no-controls: skip control dumps (control_fresh, control_positive, control_scaled)
  --no-export: skip CSV export and figure generation (distinguishers only)
  --no-clean: do not remove old outputs before run (default: clean for fresh results)
"""

import argparse
import subprocess
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
DUMP_BASE = PROJ / "dump"
ANALYSIS = PROJ / "analysis"
SCRIPTS = PROJ / "scripts"
BUILD = PROJ / "instrumentation" / "build"
OUTPUT_RESULTS = PROJ / "output" / "results"
OUTPUT_CSV = PROJ / "output" / "csv"
OUTPUT_FIGURES = PROJ / "output" / "figures"
MULTI_RUN_N = 3

DISTINGUISHERS = [
    "distinguisher_shared_mask_collision.py",
    "distinguisher_rank_deficiency.py",
    "distinguisher_covariance_profiling.py",
    "distinguisher_regression_dependence.py",
    "distinguisher_bias_moments.py",
]


def find_dumps(include_controls: bool) -> list[Path]:
    """Find all dump directories with metadata.json."""
    dumps = []
    for lib in ["seal", "openfhe", "helib"]:
        lib_dir = DUMP_BASE / lib
        if not lib_dir.exists():
            continue
        for run_dir in sorted(lib_dir.iterdir()):
            if run_dir.is_dir() and (run_dir / "metadata.json").exists():
                if not include_controls and "control" in run_dir.name.lower():
                    continue
                dumps.append(run_dir)
    return sorted(dumps)


def has_dump_tools_for_multi_run() -> bool:
    """Return True if at least one dump tool exists for multi-run."""
    for lib in ("seal", "openfhe", "helib"):
        base = BUILD / lib
        for sub in ("", "Release", "Debug"):
            d = base / sub if sub else base
            for name in (f"{lib}_dump_keys.exe", f"{lib}_dump_keys"):
                if (d / name).exists():
                    return True
    return False


def clean_old_outputs() -> None:
    """Remove old CSV, JSON, and figures so each run produces fresh results."""
    count = 0
    if OUTPUT_CSV.exists() and (OUTPUT_CSV / "results.csv").exists():
        (OUTPUT_CSV / "results.csv").unlink()
        count += 1
    if OUTPUT_RESULTS.exists():
        for f in OUTPUT_RESULTS.glob("*.json"):
            f.unlink()
            count += 1
    if OUTPUT_FIGURES.exists():
        for name in ("fig1_main.png", "fig2_bias.png", "fig3_controls.png"):
            p = OUTPUT_FIGURES / name
            if p.exists():
                p.unlink()
                count += 1
    if count > 0:
        print(f"Cleaned {count} old output file(s).")
        print()


def run_distinguisher(cmd: list[str], dump_path: Path) -> bool:
    """Run a single distinguisher. Return True on success."""
    try:
        r = subprocess.run(
            cmd + [str(dump_path)],
            cwd=PROJ,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if r.returncode != 0:
            print(f"  ERROR: {cmd[-1]} on {dump_path.name}: {r.stderr[:200]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT: {cmd[-1]} on {dump_path.name}")
        return False


def main():
    ap = argparse.ArgumentParser(description="Run full experiment: multi-run, distinguishers, export, figures")
    ap.add_argument("--no-multi-run", action="store_true",
                    help="Skip multi-run; use existing dumps only")
    ap.add_argument("--no-controls", action="store_true", help="Skip control dumps")
    ap.add_argument("--no-export", action="store_true", help="Skip CSV export and figure generation")
    ap.add_argument("--no-clean", action="store_true", help="Do not remove old outputs before run")
    args = ap.parse_args()

    if not args.no_clean:
        clean_old_outputs()

    if not args.no_multi_run:
        if not has_dump_tools_for_multi_run():
            print("Dump tools not found. Build instrumentation first, then run this script.")
            print("See README Path B: cmake in instrumentation/build, then run_experiment.py")
            print()
            print("To use existing dumps only (no multi-run), pass --no-multi-run.")
            sys.exit(1)
        else:
            print("Phase 1: Multi-run (3 key generations per library)...")
            r = subprocess.run(
                [sys.executable, str(SCRIPTS / "run_all_multi_run.py"), str(MULTI_RUN_N)],
                cwd=str(PROJ),
            )
            if r.returncode != 0:
                print("Multi-run failed. Run with --no-multi-run to use existing dumps only.")
                sys.exit(r.returncode)
            print()

    print("Phase 2: Distinguishers on all dumps...")

    dumps = find_dumps(include_controls=not args.no_controls)
    if not dumps:
        print("No dumps found. Create dump/seal/run_001, dump/openfhe/run_001, dump/helib/run_001 first.")
        print("See README.md for full pipeline (build + dump).")
        sys.exit(1)

    print("=" * 60)
    print("GaloisProbe Experiment")
    print("=" * 60)
    print(f"Dumps: {[d.relative_to(PROJ) for d in dumps]}")
    print()

    python = "python3" if sys.platform != "win32" else "python"
    ok = 0
    fail = 0

    for dump in dumps:
        rel = dump.relative_to(PROJ)
        print(f"  [{rel}]")
        for dist in DISTINGUISHERS:
            script = ANALYSIS / dist
            if not script.exists():
                print(f"    SKIP {dist} (not found)")
                continue
            cmd = [python, str(script)]
            if run_distinguisher(cmd, dump):
                ok += 1
            else:
                fail += 1
        print()

    if fail > 0:
        print(f"Completed with {fail} failures.")
        sys.exit(1)

    if not args.no_export:
        print("Phase 3: Export and figures...")
        subprocess.run([python, str(SCRIPTS / "export_experiment_results.py")], cwd=PROJ, check=True)
        subprocess.run([python, str(SCRIPTS / "plot_results.py")], cwd=PROJ, check=True)
        print()
        print("Output:")
        print("  output/csv/results.csv (includes p_collision, p_rank)")
        print("  output/results/distinguisher_*.json, aggregate_*_multi_run.json")
        print("  output/figures/fig1_main.png, fig2_bias.png, fig3_controls.png")
    else:
        print("Done. Run export_experiment_results.py and plot_results.py for output.")

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
