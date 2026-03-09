"""
Distinguisher: Shared-mask / collision detection.

For each ksk_1 (-a) block, hash the coefficient vector.
Look for collisions across blocks, key types, levels.

See docs/ARCHITECTURE.md §6.2.
"""

import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import load_metadata, iter_ksk1_blocks, bytes_to_coefficients, hash_coefficients_sha256, get_coeff_signed


def run_collision_test(dump_path: Path, use_sha256: bool = True) -> dict:
    """Run collision test; return results dict. Uses SHA-256 by default (production)."""
    dump_path = Path(dump_path)
    meta = load_metadata(dump_path)
    N = meta.get("N", 4096)
    signed = get_coeff_signed(meta)

    hash_to_blocks = defaultdict(list)
    block_details = []
    block_id = 0

    for info, data in iter_ksk1_blocks(dump_path):
        coeffs = bytes_to_coefficients(data, signed=signed)
        h = hash_coefficients_sha256(coeffs, signed=signed)
        hash_to_blocks[h].append((info.key_type, info.level, info.block, info.prime))
        block_details.append({
            "block_id": block_id,
            "key_type": info.key_type,
            "level": info.level,
            "block": info.block,
            "prime": info.prime,
            "hash_hex": h,
        })
        block_id += 1

    blocks_seen = block_id
    collisions = {h: locs for h, locs in hash_to_blocks.items() if len(locs) > 1}
    num_collisions = sum(len(locs) - 1 for locs in collisions.values())

    return {
        "dump_path": str(dump_path),
        "N": N,
        "hash_function": "SHA-256",
        "blocks_seen": blocks_seen,
        "unique_hashes": len(hash_to_blocks),
        "collision_count": num_collisions,
        "collision_groups": len(collisions),
        "collisions": [
            {"hash": str(h), "locations": locs}
            for h, locs in collisions.items()
        ],
        "block_details": block_details,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python distinguisher_shared_mask_collision.py <dump_path>")
        sys.exit(1)

    dump_path = Path(sys.argv[1])
    if not dump_path.exists():
        print(f"Error: {dump_path} does not exist")
        sys.exit(1)

    result = run_collision_test(dump_path)
    print("Distinguisher: Shared-mask / collision")
    print("-" * 40)
    print(f"Blocks seen:     {result['blocks_seen']}")
    print(f"Unique hashes:   {result['unique_hashes']}")
    print(f"Collision count: {result['collision_count']}")
    print(f"Collision groups: {result['collision_groups']}")

    if result["collision_groups"] > 0:
        print("\n*** COLLISIONS DETECTED ***")
        for c in result["collisions"]:
            print(f"  Hash {c['hash'][:16]}... at: {c['locations']}")
    else:
        print("\nNo collisions (expected for independent masks).")

    out_dir = Path(__file__).resolve().parent.parent / "output" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"{dump_path.parent.name}_{dump_path.name}" if dump_path.name else dump_path.parent.name + "_run"
    out_file = out_dir / f"distinguisher_collision_{run_id}.json"
    import json
    with open(out_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResults written to {out_file}")


if __name__ == "__main__":
    main()
