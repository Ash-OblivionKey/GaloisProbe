#!/usr/bin/env python3
"""
Control: Deterministic scaled dump (Negative Control B).

Create scaled variant: ksk1_scaled = (P^{-1} * ksk1) mod q.
Expect: rank deficit, high covariance.

See docs/methodology.md §4 (Control Procedures).

Usage: python control_scaled_dump.py <source_dump> <output_dump> [prime_index]
"""

import json
import shutil
import struct
import sys
from pathlib import Path
from datetime import datetime


def main():
    if len(sys.argv) < 3:
        print("Usage: python control_scaled_dump.py <source_dump> <output_dump> [prime_index]")
        sys.exit(1)

    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    prime_idx = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    with open(src / "metadata.json") as f:
        meta = json.load(f)

    N = meta["N"]
    primes = meta.get("primes", [])
    if not primes:
        print("Error: source has no primes in metadata")
        sys.exit(1)
    if prime_idx >= len(primes):
        prime_idx = 0
    q = primes[prime_idx]
    P = 2**61 - 1
    P_inv = pow(P, q - 2, q) if q > 2 else 1

    out.mkdir(parents=True, exist_ok=True)
    (out / "relin" / "level_0").mkdir(parents=True, exist_ok=True)

    # Copy all source relin blocks first
    relin_dir = src / "relin" / "level_0"
    out_relin = out / "relin" / "level_0"
    for f in relin_dir.glob("*.bin"):
        shutil.copy(f, out_relin / f.name)

    # Add scaled block for prime_idx (linear multiple of first block)
    # SEAL and OpenFHE use uint64; HElib uses int64 (see analysis/utils.py get_coeff_signed)
    signed = meta.get("library", "").lower() == "helib"
    fmt = f"<{N}q" if signed else f"<{N}Q"
    scaled_count = 0
    for f in sorted(relin_dir.glob("*_ksk1.bin")):
        parts = f.stem.split("_")
        blk, prm = int(parts[1]), int(parts[3])
        if prm != prime_idx:
            continue
        with open(f, "rb") as fp:
            data = fp.read()
        coeffs = list(struct.unpack(fmt, data))
        scaled = [(c * P_inv) % q for c in coeffs]
        new_blk = meta.get("relin_blocks", 1)
        out_fn = out_relin / f"block_{new_blk}_prime_{prm}_ksk1.bin"
        with open(out_fn, "wb") as fp:
            fp.write(struct.pack(fmt, *scaled))
        scaled_count += 1
        break

    meta["relin_blocks"] = meta.get("relin_blocks", 1) + 1
    meta["timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    meta["_control"] = "deterministic_scaled"
    with open(out / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"Created {out} with {scaled_count} scaled block(s) added")
    print("Run distinguisher_rank_deficiency and distinguisher_covariance_profiling: expect rank deficit, high covariance")


if __name__ == "__main__":
    main()
