"""
Compute p-values and statistical significance for distinguisher results.
See docs/methodology.md §7 (Phase 5: Statistical Significance).

Usage: python compute_statistical_significance.py <dump_path> [--output <file>]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from distinguisher_shared_mask_collision import run_collision_test
from distinguisher_rank_deficiency import run_rank_test
from distinguisher_covariance_profiling import run_covariance_test


def collision_pvalue(blocks_seen: int, collision_count: int, hash_bits: int = 256) -> float:
    """Approximate p-value for collision count under null (random)."""
    if collision_count == 0:
        return 1.0
    n = blocks_seen
    k = 2 ** hash_bits
    prob_no_collision = 1.0
    for i in range(n):
        prob_no_collision *= (k - i) / k
    return 1 - prob_no_collision


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump_path", type=Path)
    ap.add_argument("--output", "-o", type=Path, default=None)
    args = ap.parse_args()

    if not args.dump_path.exists():
        print(f"Error: {args.dump_path} does not exist")
        sys.exit(1)

    results = {"dump_path": str(args.dump_path), "pvalues": {}}

    r_a = run_collision_test(args.dump_path)
    p_a = collision_pvalue(r_a["blocks_seen"], r_a["collision_count"])
    results["pvalues"]["distinguisher_collision"] = p_a
    results["distinguisher_collision"] = r_a

    r_b = run_rank_test(args.dump_path)
    deficit = sum(v["deficit"] for v in r_b.get("per_prime", {}).values())
    p_b = 0.0 if deficit > 0 else 1.0
    results["pvalues"]["distinguisher_rank"] = p_b
    results["distinguisher_rank"] = r_b

    r_c = run_covariance_test(args.dump_path)
    results["pvalues"]["distinguisher_covariance"] = None
    results["distinguisher_covariance"] = r_c

    out = args.output or Path(__file__).resolve().parent.parent / "output" / "results" / f"statistical_significance_{args.dump_path.name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(results, f, indent=2)

    print("p-values:", results["pvalues"])
    print(f"Written to {out}")


if __name__ == "__main__":
    main()
