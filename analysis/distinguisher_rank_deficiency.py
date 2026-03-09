"""
Distinguisher: Rank deficiency detection.

Stack ksk_1 (-a) vectors as rows; compute rank over Z_q.
Unusually low rank indicates linear dependence.

See docs/ARCHITECTURE.md §6.3.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import load_metadata, iter_ksk1_blocks, bytes_to_coefficients, get_coeff_signed

# Cap rows per prime for rank test when many blocks (HElib has ~12k blocks).
# Full GE on 2k+ rows is O(rows²×cols) in Python; 500 rows keeps runtime reasonable.
MAX_ROWS_PER_PRIME = 500


def rank_over_field(rows: list, mod: int) -> int:
    """Compute row rank of matrix over Z_mod using Gaussian elimination.
    Uses Python int arithmetic to avoid overflow for large moduli (e.g. 60-bit primes)."""
    if not rows:
        return 0
    # Use list of lists with Python int; reduce each coeff mod q
    M = [[int(c) % mod for c in row] for row in rows]
    nrows, ncols = len(M), len(M[0])
    rank = 0

    for col in range(min(ncols, nrows)):
        pivot_row = None
        for r in range(rank, nrows):
            if M[r][col] % mod != 0:
                pivot_row = r
                break
        if pivot_row is None:
            continue
        M[rank], M[pivot_row] = M[pivot_row], M[rank]
        pivot = M[rank][col] % mod
        inv = pow(pivot, mod - 2, mod)
        # Eliminate column in other rows: M[r] -= (M[r][col]/pivot) * M[rank]
        for r in range(nrows):
            if r != rank and M[r][col] % mod != 0:
                coef = (M[r][col] * inv) % mod
                for j in range(ncols):
                    M[r][j] = (M[r][j] - M[rank][j] * coef) % mod
        rank += 1
        if rank >= nrows:
            break
    return rank


def run_rank_test(dump_path: Path, mod: int = 2**61 - 1) -> dict:
    """Run rank test; return results dict. Per-prime when primes in metadata."""
    dump_path = Path(dump_path)
    meta = load_metadata(dump_path)
    N = meta.get("N", 4096)
    primes = meta.get("primes", [])

    signed = get_coeff_signed(meta)
    by_prime = {}
    for info, data in iter_ksk1_blocks(dump_path):
        coeffs = bytes_to_coefficients(data, signed=signed)[:N]
        p = info.prime
        if p not in by_prime:
            by_prime[p] = []
        by_prime[p].append(coeffs)

    if not by_prime:
        return {"dump_path": str(dump_path), "N": N, "per_prime": {}, "num_rows": 0}

    per_prime = {}
    for p, rows in by_prime.items():
        q = primes[p] if p < len(primes) else mod
        rows_total = len(rows)
        if rows_total > MAX_ROWS_PER_PRIME:
            rows = random.sample(rows, MAX_ROWS_PER_PRIME)
        r = rank_over_field(rows, q)
        nrows = len(rows)
        per_prime[int(p)] = {
            "num_rows": nrows,
            "rows_total": rows_total if rows_total != nrows else None,
            "rank": r,
            "full_rank": r == min(nrows, N),
            "deficit": min(nrows, N) - r,
        }

    return {"dump_path": str(dump_path), "N": N, "per_prime": per_prime}


def main():
    if len(sys.argv) < 2:
        print("Usage: python distinguisher_rank_deficiency.py <dump_path> [modulus]")
        sys.exit(1)

    dump_path = Path(sys.argv[1])
    mod = int(sys.argv[2]) if len(sys.argv) > 2 else 2**61 - 1

    if not dump_path.exists():
        print(f"Error: {dump_path} does not exist")
        sys.exit(1)

    result = run_rank_test(dump_path, mod)
    print("Distinguisher: Rank deficiency")
    print("-" * 40)
    for p, r in result.get("per_prime", {}).items():
        print(f"Prime {p}: rows={r['num_rows']}, rank={r['rank']}, deficit={r['deficit']}")
        if r["deficit"] > 0:
            print("  *** RANK DEFICIENCY ***")

    out_dir = Path(__file__).resolve().parent.parent / "output" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"{dump_path.parent.name}_{dump_path.name}" if dump_path.name else dump_path.parent.name + "_run"
    import json
    out_file = out_dir / f"distinguisher_rank_{run_id}.json"
    with open(out_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResults written to {out_file}")


if __name__ == "__main__":
    main()
