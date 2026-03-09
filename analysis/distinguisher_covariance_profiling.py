"""
Distinguisher: Covariance profiling.

Compute empirical covariance across ksk blocks.
Compare to control (fresh / deterministic scaling).

See docs/ARCHITECTURE.md §6.4.
"""

import sys
from pathlib import Path
from typing import Optional
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import load_metadata, iter_ksk1_blocks, bytes_to_coefficients, get_coeff_signed


# Cap blocks for covariance when many (HElib: np.cov on 12k×12k is very slow).
MAX_BLOCKS_COV = 2000


def run_covariance_test(dump_path: Path, max_blocks: Optional[int] = None) -> dict:
    """Run covariance test; return results dict. max_blocks=None uses all blocks (capped at MAX_BLOCKS_COV)."""
    dump_path = Path(dump_path)
    meta = load_metadata(dump_path)
    N = meta.get("N", 4096)

    signed = get_coeff_signed(meta)
    rows = []
    for info, data in iter_ksk1_blocks(dump_path):
        coeffs = bytes_to_coefficients(data, signed=signed)[:N]
        rows.append(coeffs)
        if max_blocks is not None and len(rows) >= max_blocks:
            break
    blocks_total = len(rows)
    if max_blocks is None and len(rows) > MAX_BLOCKS_COV:
        import random
        rows = random.sample(rows, MAX_BLOCKS_COV)

    if len(rows) < 2:
        return {"dump_path": str(dump_path), "blocks_used": len(rows), "error": "Need at least 2 blocks for covariance"}
    M = np.array(rows, dtype=np.float64)
    M_centered = M - M.mean(axis=1, keepdims=True)
    cov = np.cov(M_centered)
    frob = np.linalg.norm(cov, "fro")

    return {
        "dump_path": str(dump_path),
        "blocks_used": len(rows),
        "blocks_total": blocks_total if blocks_total != len(rows) else None,
        "N": N,
        "covariance_frobenius_norm": float(frob),
        "cov_shape": list(cov.shape),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python distinguisher_covariance_profiling.py <dump_path> [max_blocks]")
        sys.exit(1)

    dump_path = Path(sys.argv[1])
    max_blocks = int(sys.argv[2]) if len(sys.argv) > 2 else None

    if not dump_path.exists():
        print(f"Error: {dump_path} does not exist")
        sys.exit(1)

    result = run_covariance_test(dump_path, max_blocks)
    if "error" in result:
        print(result["error"])
        sys.exit(1)

    print("Distinguisher: Covariance profiling")
    print("-" * 40)
    print(f"Blocks used: {result['blocks_used']}")
    print(f"Covariance Frobenius norm: {result['covariance_frobenius_norm']:.4f}")

    out_dir = Path(__file__).resolve().parent.parent / "output" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"{dump_path.parent.name}_{dump_path.name}" if dump_path.name else dump_path.parent.name + "_run"
    import json
    out_file = out_dir / f"distinguisher_covariance_{run_id}.json"
    with open(out_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResults written to {out_file}")


if __name__ == "__main__":
    main()
