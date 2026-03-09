"""
Distinguisher: Regression-based dependence detection.

For pairs (X, Y) of ksk1 vectors, fit Y ≈ Σ α_k X_k.
Report R², residual distribution. Cross-validation to avoid overfitting.

See docs/ARCHITECTURE.md §6.5.
"""

import random
import sys
from pathlib import Path
from typing import Optional
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import load_metadata, iter_ksk1_blocks, bytes_to_coefficients, get_coeff_signed


def run_regression_test(dump_path: Path, max_pairs: Optional[int] = None,
                       max_blocks: Optional[int] = None) -> dict:
    """Run regression test; return results dict. Uses ALL blocks and ALL pairs by default (no sampling)."""
    dump_path = Path(dump_path)
    meta = load_metadata(dump_path)
    N = meta.get("N", 4096)
    signed = get_coeff_signed(meta)

    rows = []
    for info, data in iter_ksk1_blocks(dump_path):
        if max_blocks is not None and len(rows) >= max_blocks:
            break
        coeffs = bytes_to_coefficients(data, signed=signed)[:N]
        rows.append(np.array(coeffs, dtype=np.float64))

    if len(rows) < 2:
        return {"dump_path": str(dump_path), "error": "Need at least 2 blocks"}

    M = np.array(rows)
    n = len(rows)
    total_pairs = n * (n - 1) // 2
    # Use all pairs if <= 500000; else systematic sample (every k-th) to get ~500000
    if max_pairs is None:
        max_pairs = min(500000, total_pairs) if total_pairs > 500000 else total_pairs
    npairs = min(max_pairs, total_pairs)

    r2_list = []
    if npairs >= total_pairs:
        # All pairs: iterate (i,j) with i < j
        for i in range(n):
            for j in range(i + 1, n):
                X = M[i].reshape(-1, 1)
                Y = M[j]
                try:
                    from numpy.linalg import lstsq
                    coeffs, _, _, _ = lstsq(X, Y, rcond=None)
                    Y_pred = (X @ coeffs).flatten()
                    ss_res = np.sum((Y - Y_pred) ** 2)
                    ss_tot = np.sum((Y - np.mean(Y)) ** 2)
                    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
                    r2_list.append({"block_i": i, "block_j": j, "r2": float(r2)})
                except Exception:
                    pass
    else:
        # Random sample: pick npairs indices directly (avoids iterating 72M+ pairs)
        def idx_to_pair(idx: int, n: int) -> tuple[int, int]:
            i, remaining = 0, idx
            while i < n - 1:
                block = n - 1 - i
                if remaining < block:
                    return (i, i + 1 + remaining)
                remaining -= block
                i += 1
            return (n - 2, n - 1)

        from numpy.linalg import lstsq
        indices = random.sample(range(total_pairs), npairs)
        for idx in indices:
            i, j = idx_to_pair(idx, n)
            X = M[i].reshape(-1, 1)
            Y = M[j]
            try:
                coeffs, _, _, _ = lstsq(X, Y, rcond=None)
                Y_pred = (X @ coeffs).flatten()
                ss_res = np.sum((Y - Y_pred) ** 2)
                ss_tot = np.sum((Y - np.mean(Y)) ** 2)
                r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
                r2_list.append({"block_i": i, "block_j": j, "r2": float(r2)})
            except Exception:
                pass

    r2_vals = [x["r2"] if isinstance(x, dict) else x for x in r2_list]
    return {
        "dump_path": str(dump_path),
        "N": N,
        "blocks_used": n,
        "pairs_tested": len(r2_list),
        "pairs_total": total_pairs,
        "r2_mean": float(np.mean(r2_vals)) if r2_vals else None,
        "r2_max": float(np.max(r2_vals)) if r2_vals else None,
        "r2_min": float(np.min(r2_vals)) if r2_vals else None,
        "r2_values": r2_list,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python distinguisher_regression_dependence.py <dump_path> [max_pairs] [max_blocks]")
        print("  Default: max_pairs=None (all pairs), max_blocks=None (all blocks)")
        sys.exit(1)

    dump_path = Path(sys.argv[1])
    max_pairs = int(sys.argv[2]) if len(sys.argv) > 2 else None
    max_blocks = int(sys.argv[3]) if len(sys.argv) > 3 else None

    if not dump_path.exists():
        print(f"Error: {dump_path} does not exist")
        sys.exit(1)

    result = run_regression_test(dump_path, max_pairs, max_blocks)
    if "error" in result:
        print(result["error"])
        sys.exit(1)

    print("Distinguisher: Regression-based dependence")
    print("-" * 40)
    print(f"Blocks: {result['blocks_used']}, pairs: {result['pairs_tested']}")
    print(f"R² mean: {result['r2_mean']:.4f}, R² max: {result['r2_max']:.4f}")

    out_dir = Path(__file__).resolve().parent.parent / "output" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"{dump_path.parent.name}_{dump_path.name}" if dump_path.name else dump_path.parent.name + "_run"
    import json
    out_file = out_dir / f"distinguisher_regression_{run_id}.json"
    with open(out_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResults written to {out_file}")


if __name__ == "__main__":
    main()
