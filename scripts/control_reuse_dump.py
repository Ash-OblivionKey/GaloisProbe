#!/usr/bin/env python3
"""
Control: Intentional reuse (Positive Control).

Create dump with two identical ksk1 blocks.
Expect: collision detected, rank deficit.

See docs/methodology.md §4 (Control Procedures).

Usage: python control_reuse_dump.py <source_dump> <output_dump>
"""

import json
import shutil
import sys
from pathlib import Path
from datetime import datetime


def main():
    if len(sys.argv) < 3:
        print("Usage: python control_reuse_dump.py <source_dump> <output_dump>")
        sys.exit(1)

    src = Path(sys.argv[1])
    out = Path(sys.argv[2])

    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src / "relin", out / "relin", dirs_exist_ok=True)
    if (src / "rotation").exists():
        shutil.copytree(src / "rotation", out / "rotation", dirs_exist_ok=True)

    with open(src / "metadata.json") as f:
        meta = json.load(f)
    meta["timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    meta["_control"] = "positive_intentional_reuse"
    with open(out / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    relin_dir = out / "relin" / "level_0"
    files = list(relin_dir.glob("*_ksk1.bin"))
    # Group by prime index; need two blocks for same prime to get rank deficit
    by_prime = {}
    for f in files:
        parts = f.stem.split("_")
        blk, prm = int(parts[1]), int(parts[3])
        by_prime.setdefault(prm, []).append((blk, f))
    duped = False
    for prm, blk_files in sorted(by_prime.items()):
        if len(blk_files) >= 2:
            _, first = blk_files[0]
            _, second = blk_files[1]
            shutil.copy(first, second)
            print(f"Copied {first.name} to {second.name} (intentional reuse, prime {prm})")
            duped = True
            break
    if not duped:
        print("Error: need at least 2 ksk1 blocks for same prime to duplicate")
        sys.exit(1)
    print(f"Created {out}")
    print("Run distinguisher_shared_mask_collision and distinguisher_rank_deficiency: expect collision, rank deficit")


if __name__ == "__main__":
    main()
