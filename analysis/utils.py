"""
Utilities for evaluation-key dump loading and analysis.
See docs/ARCHITECTURE.md §6.
"""

import json
import struct
from pathlib import Path
from typing import Iterator, Tuple, Optional
from dataclasses import dataclass


@dataclass
class BlockInfo:
    """Metadata for a single KSK block."""
    key_type: str       # "relin" | "rotation"
    level: int
    block: int
    prime: int
    component: str     # "ksk_0" | "ksk_1"
    automorphism: Optional[int] = None


def load_metadata(dump_path: Path) -> dict:
    """Load metadata.json from dump directory."""
    p = Path(dump_path) / "metadata.json"
    if not p.exists():
        raise FileNotFoundError(f"metadata.json not found in {dump_path}")
    with open(p) as f:
        return json.load(f)


def iter_ksk1_blocks(dump_path: Path, skip_unexpected_size: bool = True) -> Iterator[Tuple[BlockInfo, bytes]]:
    """
    Iterate over all ksk_1 (-a) blocks in the dump.
    Yields (BlockInfo, raw_bytes) for each block.
    If skip_unexpected_size is True (default), skips blocks where len(data) != N*8.
    This handles HElib dumps with variable block sizes (e.g. thin rotation keys).
    """
    base = Path(dump_path)
    meta = load_metadata(base)
    N = meta.get("N", 4096)
    expected_size = N * 8

    def _iter_relin():
        relin_dir = base / "relin"
        if relin_dir.exists():
            for level_dir in sorted(relin_dir.iterdir()):
                if not level_dir.is_dir():
                    continue
                lev = int(level_dir.name.split("_")[-1])
                for f in sorted(level_dir.glob("*_ksk1.bin")):
                    parts = f.stem.split("_")
                    blk = int(parts[1])
                    prm = int(parts[3])
                    with open(f, "rb") as fp:
                        data = fp.read()
                    if skip_unexpected_size and len(data) != expected_size:
                        continue
                    yield BlockInfo("relin", lev, blk, prm, "ksk_1"), data

    def _iter_rotation():
        rot_dir = base / "rotation"
        if rot_dir.exists():
            for auto_dir in sorted(rot_dir.iterdir()):
                if not auto_dir.is_dir():
                    continue
                auto_idx = int(auto_dir.name.split("_")[-1])
                for level_dir in sorted(auto_dir.iterdir()):
                    if not level_dir.is_dir():
                        continue
                    lev = int(level_dir.name.split("_")[-1])
                    for f in level_dir.glob("*_ksk1.bin"):
                        parts = f.stem.split("_")
                        blk = int(parts[1])
                        prm = int(parts[3])
                        with open(f, "rb") as fp:
                            data = fp.read()
                        if skip_unexpected_size and len(data) != expected_size:
                            continue
                        yield BlockInfo("rotation", lev, blk, prm, "ksk_1",
                                       automorphism=auto_idx), data

    yield from _iter_relin()
    yield from _iter_rotation()


def bytes_to_coefficients(data: bytes, signed: bool = True) -> list:
    """Convert raw bytes to list of coefficients (int64 or uint64)."""
    n = len(data) // 8
    if signed:
        return list(struct.unpack(f"<{n}q", data))
    return list(struct.unpack(f"<{n}Q", data))


def get_coeff_signed(meta: dict) -> bool:
    """SEAL and OpenFHE use uint64 (unsigned); HElib uses int64 (signed)."""
    return meta.get("library", "").lower() == "helib"


def hash_coefficients(coeffs: list, mod: int = 2**32) -> int:
    """Simple hash (legacy). Prefer hash_coefficients_sha256 for production."""
    h = 0
    for c in coeffs:
        h = (h * 31 + (c % mod)) % (2**64)
    return h


def hash_coefficients_sha256(coeffs: list, signed: bool = True) -> str:
    """SHA-256 hash of coefficient vector for collision detection. Production use."""
    import hashlib
    n = len(coeffs) * 8
    fmt = f"<{len(coeffs)}q" if signed else f"<{len(coeffs)}Q"
    data = struct.pack(fmt, *coeffs)
    return hashlib.sha256(data).hexdigest()
