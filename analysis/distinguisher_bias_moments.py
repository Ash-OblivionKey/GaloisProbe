"""
Distinguisher: Bias / moment tests.

Center coefficients in (-q/2, q/2]. Test: low-bit bias (chi-square),
skewness, kurtosis. Cross-prime consistency check.

See docs/ARCHITECTURE.md §6.6.
"""

import sys
from pathlib import Path
from collections import defaultdict
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import load_metadata, iter_ksk1_blocks, bytes_to_coefficients, get_coeff_signed


def center_coeffs(coeffs: list, q: int, signed: bool) -> list:
    """Center in (-q/2, q/2]."""
    out = []
    for c in coeffs:
        v = c % q
        if v > q // 2:
            v -= q
        out.append(v)
    return out


def run_bias_test(dump_path: Path) -> dict:
    """Run bias/moment test; return results dict."""
    dump_path = Path(dump_path)
    meta = load_metadata(dump_path)
    N = meta.get("N", 4096)
    primes = meta.get("primes", [])
    signed = get_coeff_signed(meta)

    by_prime = defaultdict(list)
    for info, data in iter_ksk1_blocks(dump_path):
        coeffs = bytes_to_coefficients(data, signed=signed)[:N]
        q = primes[info.prime] if info.prime < len(primes) else 2**61 - 1
        centered = center_coeffs(coeffs, q, signed)
        by_prime[info.prime].extend(centered)

    results = {}
    for p, vals in by_prime.items():
        arr = np.array(vals)
        low_bits = (arr % 2).astype(int)
        p1 = np.mean(low_bits)
        chi2 = (p1 - 0.5) ** 2 / 0.25 * len(low_bits) if len(low_bits) > 0 else 0
        skew = float(np.cov(np.vstack([arr, arr**2, arr**3]))[0, 2] / (np.std(arr)**3 + 1e-10)) if np.std(arr) > 0 else 0
        kurt = float(np.mean((arr - np.mean(arr))**4) / (np.std(arr)**4 + 1e-10) - 3) if np.std(arr) > 0 else 0
        results[int(p)] = {
            "n_coeffs": len(vals),
            "low_bit_mean": float(p1),
            "chi2_like": float(chi2),
            "skewness": float(skew),
            "kurtosis": float(kurt),
        }

    return {"dump_path": str(dump_path), "N": N, "per_prime": results}


def main():
    if len(sys.argv) < 2:
        print("Usage: python distinguisher_bias_moments.py <dump_path>")
        sys.exit(1)

    dump_path = Path(sys.argv[1])
    if not dump_path.exists():
        print(f"Error: {dump_path} does not exist")
        sys.exit(1)

    result = run_bias_test(dump_path)
    print("Distinguisher: Bias / moment tests")
    print("-" * 40)
    for p, r in result.get("per_prime", {}).items():
        print(f"Prime {p}: low_bit={r['low_bit_mean']:.4f}, skew={r['skewness']:.4f}, kurt={r['kurtosis']:.4f}")

    out_dir = Path(__file__).resolve().parent.parent / "output" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"{dump_path.parent.name}_{dump_path.name}" if dump_path.name else dump_path.parent.name + "_run"
    import json
    out_file = out_dir / f"distinguisher_bias_{run_id}.json"
    with open(out_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResults written to {out_file}")


if __name__ == "__main__":
    main()
