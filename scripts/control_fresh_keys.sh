#!/bin/bash
# Control: Fresh keys (Negative Control A).
# Run SEAL dump 3 times. Expect: no collisions between runs.
# See docs/methodology.md §4 (Control Procedures).

DUMP_BASE="$(cd "$(dirname "$0")/.." && pwd)/dump/seal"
EXE="$(cd "$(dirname "$0")/.." && pwd)/instrumentation/build/seal/seal_dump_keys"

if [ ! -x "$EXE" ]; then
  echo "Error: seal_dump_keys not found. Build instrumentation first."
  exit 1
fi

echo "Creating 3 fresh dumps..."
"$EXE" --output "$DUMP_BASE/control_fresh_001" --poly_modulus 4096 --scheme ckks
"$EXE" --output "$DUMP_BASE/control_fresh_002" --poly_modulus 4096 --scheme ckks
"$EXE" --output "$DUMP_BASE/control_fresh_003" --poly_modulus 4096 --scheme ckks

echo ""
echo "Run distinguisher on each - expect 0 collisions within each run."
echo "  python analysis/distinguisher_shared_mask_collision.py dump/seal/control_fresh_001"
echo "  python analysis/distinguisher_shared_mask_collision.py dump/seal/control_fresh_002"
echo "  python analysis/distinguisher_shared_mask_collision.py dump/seal/control_fresh_003"
