# Implementation Cross-Check Report

This document cross-checks the GaloisProbe project implementation end-to-end: instrumentation, schema, analysis, scripts, and documentation.

**Date:** 2025-03-06  
**Status:** Complete

---

## 1. Instrumentation vs Schema

### 1.1 File Naming

| Component | Schema (`config/schema.json`) | Instrumentation | Status |
|-----------|------------------------------|-----------------|--------|
| Relin block | `block_{l}_prime_{i}_{component}.bin` | `block_{l}_prime_{p}_ksk0.bin` / `ksk1.bin` | ✓ Match |
| Rotation block | `automorphism_{a}/level_{lev}/block_{l}_prime_{i}_{component}.bin` | Same pattern | ✓ Match |

**Note:** Schema `block_metadata.component` enum is `["ksk_0","ksk_1"]` (with underscore); all dump tools write `ksk0`/`ksk1` (no underscore). This is a naming convention difference only—no functional impact. Analysis globs `*_ksk1.bin` and matches actual files.

### 1.2 Directory Layout

- **relin/level_{lev}/** — All three libraries (SEAL, OpenFHE, HElib) write here ✓
- **rotation/automorphism_{a}/level_{lev}/** — All three write here ✓

### 1.3 Metadata

| Field | Schema required | SEAL | OpenFHE | HElib |
|-------|-----------------|------|---------|-------|
| library | ✓ | ✓ | ✓ | ✓ |
| version | ✓ | ✓ | ✓ | ✓ |
| N | ✓ | ✓ | ✓ | ✓ |
| primes | ✓ | ✓ | ✓ | ✓ |
| timestamp | ✓ | ✓ | ✓ | ✓ |
| relin_blocks | optional | ✓ | ✓ | ✓ |
| rotation_count | optional | ✓ | ✓ | ✓ |

### 1.4 Coefficient Types (FIXED)

| Library | Dump tool type | Analysis `get_coeff_signed` | Status |
|---------|----------------|-----------------------------|--------|
| SEAL | `uint64_t` (data()) | False (unsigned) | ✓ |
| OpenFHE | `uint64_t` (ConvertToInt) | **Was True → Fixed to False** | ✓ Fixed |
| HElib | `int64_t` | True (signed) | ✓ |

**Fix applied:** `analysis/utils.py` — `get_coeff_signed()` now returns `True` only for `library == "helib"`. OpenFHE dumps `uint64_t`; treating it as signed would mis-interpret values > 2^63.

---

## 2. Analysis vs Schema

### 2.1 Utils (`analysis/utils.py`)

| Function | Purpose | Schema alignment |
|----------|---------|------------------|
| `load_metadata(dump_path)` | Load metadata.json | Uses `library`, `N`, `primes` ✓ |
| `iter_ksk1_blocks(dump_path, skip_unexpected_size=True)` | Yield (BlockInfo, bytes) per ksk1 | Globs `*_ksk1.bin`, parses `block_{l}_prime_{p}_ksk1` ✓ |
| `bytes_to_coefficients(data, signed)` | Unpack 8-byte coeffs | Uses `get_coeff_signed(meta)` ✓ |
| `hash_coefficients_sha256(coeffs, signed)` | Hash for collision | Pack format matches coeff type ✓ |

**BlockInfo parsing:** Expects filename `block_{l}_prime_{p}_ksk1.bin` → `parts[1]=block`, `parts[3]=prime`. Matches instrumentation output ✓

**Thin blocks (HElib):** When `skip_unexpected_size=True`, blocks where `len(data) != N*8` are skipped. Documented in ARCHITECTURE.md and methodology.md ✓

### 2.2 Distinguishers

| Distinguisher | Input | Output keys | Schema alignment |
|---------------|-------|-------------|------------------|
| collision | ksk1 blocks | blocks_seen, unique_hashes, collision_count | ✓ |
| rank | ksk1 per prime | per_prime.{prime}.deficit | ✓ |
| regression | ksk1 pairs (sampled) | r2_mean, r2_max | ✓ |
| bias | ksk1 per prime | per_prime.{prime}.low_bit_mean, kurtosis | ✓ |
| covariance | ksk1 blocks (sampled) | covariance_frobenius_norm | ✓ |

All distinguishers use `iter_ksk1_blocks`, `bytes_to_coefficients`, `get_coeff_signed` consistently ✓

---

## 3. Scripts

### 3.1 Run Flow

```
run_all_multi_run.py → run_multi_run_suite.py (per lib)
                    → 3 dumps each (seal_run_001..003, openfhe_run_001..003, helib_run_001..003)
run_experiment.py   → 5 distinguishers per dump
export_experiment_results.py → output/csv/results.csv
plot_results.py     → output/figures/fig1_main.png, fig2_bias.png, fig3_controls.png
```

### 3.2 Validation (`scripts/validate_dump.py`)

- Checks `metadata.json` (library, N, primes, timestamp)
- Accepts any block size that is a positive multiple of 8 (HElib variable sizes)
- Requires at least one block with expected size (N×8 bytes)
- Aligns with schema and HElib thin-block behavior ✓

### 3.3 Export (`scripts/export_experiment_results.py`)

- Discovers run IDs from `distinguisher_collision_*.json`
- Merges collision, rank, regression, bias, covariance
- **N inference:** When `meta.N < 100` and `lib == "helib"`, infers N from first `*_ksk1.bin` file size (N = size/8)
- CSV columns match COLUMNS list ✓

### 3.4 Plot (`scripts/plot_results.py`)

- Fig 1: Main results (collision, rank, regression, bias)
- Fig 2: Bias per prime (low_bit_mean, kurtosis)
- Fig 3: Control validation (positive vs fresh, scaled vs fresh)
- Uses first matching control per type (positive, scaled, fresh) from CSV ✓

### 3.5 Aggregate (`scripts/aggregate_multi_run_results.py`)

- Reads distinguisher_*_{run_id}.json for each run
- Aggregates collision, rank, regression, bias, covariance
- Output: `output/results/aggregate_{library}_multi_run.json` ✓

---

## 4. Config and Docs

### 4.1 Library Parameters (`run_multi_run_suite.py`)

| Library | N | m (HElib) | Blocks (typical) |
|---------|---|-----------|------------------|
| SEAL | 4096 | — | 138 |
| OpenFHE | 16384 | — | 336 |
| HElib | 2048 | 4096 (φ(m)=2048) | ~12,000 |

### 4.2 Documentation Alignment

| Doc | Key checks |
|-----|------------|
| README.md | Run commands, fig3_controls, troubleshooting ✓ |
| docs/ARCHITECTURE.md | Params, coefficient types (fixed), variable block sizes ✓ |
| docs/PROJECT_OVERVIEW.md | Block counts, LIBRARY_COMPARISON link ✓ |
| docs/methodology.md | Thin-block note ✓ |
| docs/LIBRARY_COMPARISON.md | N, blocks, scheme per library ✓ |
| tex/main.tex | OpenFHE 336 blocks, HElib m=4096 ✓ |

---

## 5. Fixes Applied This Session

| Issue | Fix |
|-------|-----|
| OpenFHE coefficient type | `get_coeff_signed`: return True only for helib; OpenFHE uses uint64 |
| control_scaled_dump.py | Same bug: was treating OpenFHE as signed; now `signed = (library == "helib")` |
| ARCHITECTURE coefficient table | SEAL, OpenFHE: uint64; HElib: int64 |
| ARCHITECTURE get_coeff_signed doc | "SEAL, OpenFHE→False; HElib→True" (was "others→True") |
| ARCHITECTURE OpenFHE source | "ConvertToInt()"; SEAL: "data()" |
| README Step 2 | Clarified as optional; Step 4 multi-run generates all dumps |
| ARCHITECTURE §7.3 | Note: fig3_controls requires output dir name to contain positive/scaled/fresh |
| run_phase6.bat, run_phase6_reports.py | Removed (Phase 6 optional workflow no longer used) |
| PROJECT_OVERVIEW §6.2 | OpenFHE: uint64 (was int64) |
| LIBRARY_COMPARISON §4 | OpenFHE: uint64_t (was int64_t) |
| OUTPUT_ANALYSIS | Removed run_std/stress refs; fixed control_scaled description |

---

## 6. Known Non-Issues

1. **Schema ksk_0 vs file ksk0:** Schema uses `ksk_0`/`ksk_1`; files use `ksk0`/`ksk1`. Implementation is consistent; schema is reference only.
2. **fig3 multiple fresh dumps:** Uses first matching `control_fresh_*`; multiple fresh runs would need explicit handling if desired.
3. **HElib thin blocks:** Skipped by distinguishers; validator accepts variable sizes and requires at least one full-size block.

---

## 7. Summary

| Area | Status |
|------|--------|
| Instrumentation ↔ Schema | ✓ Aligned (naming convention note) |
| Analysis ↔ Schema | ✓ Aligned |
| Scripts flow | ✓ Correct |
| Config/Docs | ✓ Updated |
| Coefficient types | ✓ Fixed (OpenFHE) |

**Implementation is cross-checked and consistent.**
