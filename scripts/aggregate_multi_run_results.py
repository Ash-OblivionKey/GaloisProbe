#!/usr/bin/env python3
"""
Aggregate distinguisher results across multiple runs.
Reports mean, min, max, and consistency for paper reporting.

Usage: python aggregate_multi_run_results.py <library> [num_runs]
  library: seal | openfhe | helib
  num_runs: default 3

Output: output/results/aggregate_{library}_multi_run.json
"""

import json
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
RESULTS = PROJ / "output" / "results"


def load_json(name: str) -> dict:
    p = RESULTS / name
    if not p.exists():
        return {}
    with open(p) as f:
        return json.load(f)


def aggregate(lib: str, num_runs: int) -> dict:
    agg = {
        "library": lib,
        "num_runs": num_runs,
        "collision": {"blocks_seen": [], "unique_hashes": [], "collision_count": [], "all_zero": True},
        "rank": {"deficits": [], "full_rank_all": True},
        "regression": {"r2_mean": [], "r2_max": []},
        "bias": {"low_bit_mean": [], "kurtosis": []},
        "covariance": {"frobenius_norm": []},
    }

    for i in range(1, num_runs + 1):
        run_id = f"{lib}_run_{i:03d}"
        coll = load_json(f"distinguisher_collision_{run_id}.json")
        rank = load_json(f"distinguisher_rank_{run_id}.json")
        regr = load_json(f"distinguisher_regression_{run_id}.json")
        bias = load_json(f"distinguisher_bias_{run_id}.json")
        cov = load_json(f"distinguisher_covariance_{run_id}.json")

        if coll:
            agg["collision"]["blocks_seen"].append(coll.get("blocks_seen"))
            agg["collision"]["unique_hashes"].append(coll.get("unique_hashes"))
            agg["collision"]["collision_count"].append(coll.get("collision_count", 0))
            if coll.get("collision_count", 0) != 0:
                agg["collision"]["all_zero"] = False

        if rank:
            deficits = [v.get("deficit", 0) for v in rank.get("per_prime", {}).values()]
            agg["rank"]["deficits"].extend(deficits)
            if any(d > 0 for d in deficits):
                agg["rank"]["full_rank_all"] = False

        if regr and regr.get("r2_mean") is not None:
            agg["regression"]["r2_mean"].append(regr["r2_mean"])
            agg["regression"]["r2_max"].append(regr.get("r2_max"))

        if bias:
            for p, v in bias.get("per_prime", {}).items():
                agg["bias"]["low_bit_mean"].append(v.get("low_bit_mean"))
                agg["bias"]["kurtosis"].append(v.get("kurtosis"))

        if cov:
            agg["covariance"]["frobenius_norm"].append(cov.get("covariance_frobenius_norm"))

    # Compute summary stats
    def mean(lst):
        lst = [x for x in lst if x is not None]
        return sum(lst) / len(lst) if lst else None

    def min_max(lst):
        lst = [x for x in lst if x is not None]
        return (min(lst), max(lst)) if lst else (None, None)

    out = {
        "library": lib,
        "num_runs": num_runs,
        "collision": {
            "blocks_seen_mean": mean(agg["collision"]["blocks_seen"]),
            "collision_count_all_zero": agg["collision"]["all_zero"],
            "collision_counts": agg["collision"]["collision_count"],
        },
        "rank": {
            "full_rank_all_runs": agg["rank"]["full_rank_all"],
            "max_deficit_observed": max(agg["rank"]["deficits"]) if agg["rank"]["deficits"] else 0,
        },
        "regression": {
            "r2_mean_avg": mean(agg["regression"]["r2_mean"]),
            "r2_mean_min_max": min_max(agg["regression"]["r2_mean"]),
        },
        "bias": {
            "low_bit_mean_avg": mean(agg["bias"]["low_bit_mean"]),
            "kurtosis_avg": mean(agg["bias"]["kurtosis"]),
        },
        "covariance": {
            "frobenius_norm_mean": mean(agg["covariance"]["frobenius_norm"]),
        },
    }
    return out


def main():
    if len(sys.argv) < 2:
        print("Usage: python aggregate_multi_run_results.py <library> [num_runs]")
        sys.exit(1)
    lib = sys.argv[1]
    num_runs = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    out = aggregate(lib, num_runs)
    out_path = RESULTS / f"aggregate_{lib}_multi_run.json"
    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Written {out_path}")


if __name__ == "__main__":
    main()
