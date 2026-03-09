#!/usr/bin/env python3
"""
Validate dump schema. See docs/ARCHITECTURE.md §8.

Usage: python validate_dump.py <dump_path>
Exit 0 if valid, 1 if invalid.
"""

import json
import sys
from pathlib import Path

REQUIRED_META = ["library", "version", "N", "primes", "timestamp"]


def validate_dump(dump_path: Path) -> tuple[bool, list[str]]:
    """Return (valid, list of error messages)."""
    errors = []
    base = Path(dump_path)

    if not base.exists():
        return False, [f"Path does not exist: {dump_path}"]

    meta_path = base / "metadata.json"
    if not meta_path.exists():
        return False, ["metadata.json not found"]

    try:
        with open(meta_path) as f:
            meta = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"metadata.json invalid JSON: {e}"]

    for field in REQUIRED_META:
        if field not in meta:
            errors.append(f"metadata.json missing required field: {field}")

    N = meta.get("N")
    if N is not None and (not isinstance(N, int) or N < 1):
        errors.append("metadata.json N must be positive integer")

    primes = meta.get("primes", [])
    if not isinstance(primes, list):
        errors.append("metadata.json primes must be array")

    expected_bin_size = (N or 0) * 8
    has_expected_size = False

    # HElib can produce blocks of different sizes (e.g. 32 bytes for some thin rotation keys).
    # Accept any positive multiple of 8; require at least one block with expected size (N×8).
    def check_bin(f: Path, size: int) -> None:
        nonlocal has_expected_size
        if size <= 0 or size % 8 != 0:
            errors.append(f"{f.relative_to(base)}: invalid size {size} (must be positive multiple of 8)")
        elif expected_bin_size and size == expected_bin_size:
            has_expected_size = True

    relin_dir = base / "relin"
    if relin_dir.exists():
        for level_dir in relin_dir.iterdir():
            if not level_dir.is_dir():
                continue
            for f in level_dir.glob("*.bin"):
                check_bin(f, f.stat().st_size)

    rot_dir = base / "rotation"
    if rot_dir.exists():
        for auto_dir in rot_dir.iterdir():
            if not auto_dir.is_dir():
                continue
            for level_dir in auto_dir.iterdir():
                if not level_dir.is_dir():
                    continue
                for f in level_dir.glob("*.bin"):
                    check_bin(f, f.stat().st_size)

    if not (relin_dir.exists() or rot_dir.exists()):
        errors.append("Neither relin/ nor rotation/ directory found")
    elif expected_bin_size and not has_expected_size:
        errors.append(f"No block has expected size {expected_bin_size} bytes (N×8); dump may be empty or misformed")

    return len(errors) == 0, errors


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_dump.py <dump_path>")
        sys.exit(1)

    dump_path = Path(sys.argv[1])
    valid, errors = validate_dump(dump_path)

    if valid:
        print("OK: dump valid")
        sys.exit(0)
    else:
        for e in errors:
            print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
