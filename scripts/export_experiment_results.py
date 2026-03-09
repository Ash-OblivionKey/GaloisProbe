#!/usr/bin/env python3
"""
Export experiment results to a single summary CSV (15 columns, one row per run).

Output: output/csv/results.csv
Columns: library, version, scheme, run_id, N, blocks, collision_count, unique_hashes,
         rank_deficit, r2_mean, r2_max, low_bit_mean, cov_frobenius, p_collision, p_rank

Usage: python scripts/export_experiment_results.py [results_dir]
"""

import csv
import json
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
RESULTS = PROJ / "output" / "results"
CSV_DIR = PROJ / "output" / "csv"
OUTPUT_FILE = CSV_DIR / "results.csv"

COLUMNS = [
    "library", "version", "scheme", "run_id", "N", "blocks",
    "collision_count", "unique_hashes", "rank_deficit",
    "r2_mean", "r2_max", "low_bit_mean", "cov_frobenius",
    "p_collision", "p_rank",
]


def collision_pvalue(blocks_seen: int, collision_count: int, hash_bits: int = 256) -> float:
    """P-value for collision count under null (random). See methodology §6.1."""
    if collision_count == 0:
        return 1.0
    k = 2**hash_bits
    prob_no_collision = 1.0
    for i in range(blocks_seen):
        prob_no_collision *= (k - i) / k
    return 1 - prob_no_collision


def get_metadata(dump_path: str) -> dict:
    """Load metadata.json from dump path if it exists."""
    p = Path(dump_path.replace("\\", "/"))
    if not p.is_absolute():
        p = PROJ / p
    meta_path = p / "metadata.json"
    if meta_path.exists():
        with open(meta_path) as f:
            return json.load(f)
    return {}


def infer_n_from_dump(dump_path: Path) -> int | None:
    """Infer N from first .bin file size (N = size/8) when metadata N is wrong."""
    for f in dump_path.rglob("*_ksk1.bin"):
        size = f.stat().st_size
        if size > 0 and size % 8 == 0:
            return size // 8
    return None


def sort_run_ids(run_ids: list[str]) -> list[str]:
    """Main runs first (seal, openfhe, helib), then run_std/stress, then controls."""
    lib_order = {"seal": 0, "openfhe": 1, "helib": 2}

    def key(r: str):
        lib = r.split("_")[0] if "_" in r else r
        if r in ("seal_run_001", "openfhe_run_001", "helib_run_001"):
            return (0, lib_order.get(lib, 9), r)
        if "run_std" in r or "run_stress" in r:
            return (1, lib_order.get(lib, 9), r)
        if "control" in r.lower():
            return (2, r)
        return (1, lib_order.get(lib, 9), r)
    return sorted(run_ids, key=key)


def fmt_num(val, decimals: int = 4):
    """Format number: round floats, scientific for large values."""
    if val == "" or val is None:
        return ""
    try:
        v = float(val)
        if abs(v) >= 1e15 or (0 < abs(v) < 1e-6 and v != 0):
            return f"{v:.2e}"
        return round(v, decimals) if decimals else int(v)
    except (TypeError, ValueError):
        return val


def main():
    results_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else RESULTS
    if not results_dir.exists():
        results_dir = RESULTS

    run_ids = []
    for f in results_dir.glob("distinguisher_collision_*.json"):
        stem = f.stem.replace("distinguisher_collision_", "")
        if stem and stem not in run_ids:
            run_ids.append(stem)

    run_ids = sort_run_ids(run_ids)
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    rows = []

    for run_id in run_ids:
        lib = run_id.split("_")[0] if "_" in run_id else run_id
        scheme = "BGV" if lib == "helib" else "CKKS"
        row = {"library": lib, "version": "", "scheme": scheme, "run_id": run_id,
               "N": "", "blocks": "", "collision_count": "", "unique_hashes": "",
               "rank_deficit": "", "r2_mean": "", "r2_max": "", "low_bit_mean": "",
               "cov_frobenius": "", "p_collision": "", "p_rank": ""}

        dump_path_str = ""

        # Collision
        cf = results_dir / f"distinguisher_collision_{run_id}.json"
        if cf.exists():
            with open(cf) as fp:
                c = json.load(fp)
            row["blocks"] = c.get("blocks_seen", "")
            row["collision_count"] = c.get("collision_count", "")
            row["unique_hashes"] = c.get("unique_hashes", "")
            row["N"] = c.get("N", "")
            dump_path_str = c.get("dump_path", "")
            if dump_path_str:
                meta = get_metadata(dump_path_str)
                row["version"] = meta.get("version", "")
                if meta.get("library"):
                    row["library"] = meta["library"]
                    scheme = "BGV" if meta["library"] == "helib" else "CKKS"
                    row["scheme"] = scheme
                # Fix N if metadata has wrong value (e.g. helib N=4 when should be 2048)
                meta_n = meta.get("N")
                if meta_n is not None and meta_n < 100 and lib == "helib":
                    p = Path(dump_path_str.replace("\\", "/"))
                    if not p.is_absolute():
                        p = PROJ / p
                    inferred = infer_n_from_dump(p)
                    if inferred and inferred > 100:
                        row["N"] = inferred

        # Rank
        rf = results_dir / f"distinguisher_rank_{run_id}.json"
        if rf.exists():
            with open(rf) as fp:
                r = json.load(fp)
            deficits = [int(v.get("deficit", 0) or 0) for v in r.get("per_prime", {}).values()]
            row["rank_deficit"] = max(deficits) if deficits else 0

        # Regression
        regf = results_dir / f"distinguisher_regression_{run_id}.json"
        if regf.exists():
            with open(regf) as fp:
                reg = json.load(fp)
            r2m = reg.get("r2_mean", "")
            r2x = reg.get("r2_max", "")
            row["r2_mean"] = fmt_num(r2m, 4) if r2m != "" else ""
            row["r2_max"] = fmt_num(r2x, 4) if r2x != "" else ""

        # Bias
        bf = results_dir / f"distinguisher_bias_{run_id}.json"
        if bf.exists():
            with open(bf) as fp:
                b = json.load(fp)
            lbs = [float(v.get("low_bit_mean")) for v in b.get("per_prime", {}).values()
                   if v.get("low_bit_mean") is not None]
            row["low_bit_mean"] = round(sum(lbs) / len(lbs), 4) if lbs else ""

        # Covariance (format large numbers)
        covf = results_dir / f"distinguisher_covariance_{run_id}.json"
        if covf.exists():
            with open(covf) as fp:
                cov = json.load(fp)
            row["cov_frobenius"] = fmt_num(cov.get("covariance_frobenius_norm", ""))

        # Statistical significance (p-values)
        blocks_seen = int(row.get("blocks") or 0)
        collision_count = int(row.get("collision_count") or 0)
        rank_deficit = int(row.get("rank_deficit") or 0)
        row["p_collision"] = round(collision_pvalue(blocks_seen, collision_count), 6) if blocks_seen else ""
        row["p_rank"] = 0.0 if rank_deficit > 0 else 1.0

        rows.append(row)

    if not rows:
        print("No data to export. Run distinguisher suite first.")
        return

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as fp:
        w = csv.DictWriter(fp, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"Done. {len(rows)} rows -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
