# Project Architecture: Evaluation-Key Correlation Cryptanalysis

This document describes the architecture of the GaloisProbe research project: its components, data flow, schema, and design decisions.

---

## 1. Overview

### 1.1 Purpose

The project detects **implementation-induced correlation or structure** in homomorphic encryption evaluation keys (RelinKeys, GaloisKeys/RotationKeys). The goal is to determine whether real libraries (SEAL, OpenFHE, HElib) introduce detectable patterns that deviate from the ideal RLWE distribution—e.g., mask reuse, linear dependence, or bias.

### 1.2 High-Level Pipeline

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Instrumentation │     │      Dump       │     │    Analysis     │
│  (C++ per lib)   │────▶│  (binary + JSON) │────▶│  (Python A–E)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                         │                         │
   seal_dump_keys            dump/seal/run_001         distinguisher_*.py
   openfhe_dump_keys         dump/openfhe/run_001      output/results/*.json
   helib_dump_keys           dump/helib/run_001
```

1. **Instrumentation**: C++ executables that generate keys and dump their internal representation to a common schema.
2. **Dump**: Directory tree with `metadata.json` and `.bin` files (polynomial coefficients per RNS prime).
3. **Analysis**: Python distinguishers (A–E) that consume dumps and produce JSON results.

---

## 2. Attacker Model

### 2.1 Adversary

The adversary is the **untrusted cloud evaluator** who receives:

- Public key
- Relinearization keys (s² → s)
- Rotation/Galois keys (π(s) → s)
- Any derived or level-specific keys

**No decryption oracle.** CPA setting.

### 2.2 Threat

The adversary observes evaluation-key artifacts and attempts to:

1. **Distinguish** real implementations from an ideal distribution (RLWE-consistent, no implementation-induced reuse or bias).
2. **Detect** structure such as:
   - Shared masks (same random `a` across blocks)
   - Linear dependence among ksk₁ vectors
   - Covariance patterns
   - Low-bit or moment bias

### 2.3 Ideal vs. Real

| Ideal | Real (potential deviation) |
|-------|----------------------------|
| Each ksk₁ block uses fresh randomness | Mask reuse across blocks |
| ksk₁ vectors linearly independent | Rank deficiency |
| Covariance ≈ identity (scaled) | Structured covariance |
| Coefficients uniform mod q | Low-bit bias, skew, kurtosis |

---

## 3. Directory Structure

```
GaloisProbe/
├── config/
│   ├── schema.json              # JSON schema for dumps
│   ├── parameters.json          # Parameter regimes (N, log_q, primes_bits)
│   └── experiment_configuration.json  # Locked experiment config (paths, library versions)
├── instrumentation/
│   ├── CMakeLists.txt            # Top-level; conditionally includes seal, openfhe, helib
│   ├── seal/
│   │   ├── CMakeLists.txt
│   │   └── dump_keys.cpp
│   ├── openfhe/
│   │   ├── CMakeLists.txt
│   │   └── dump_keys.cpp
│   └── helib/
│       ├── CMakeLists.txt
│       └── dump_keys.cpp
├── analysis/
│   ├── utils.py                  # load_metadata, iter_ksk1_blocks, bytes_to_coefficients
│   ├── distinguisher_shared_mask_collision.py   # Test A
│   ├── distinguisher_rank_deficiency.py         # Test B
│   ├── distinguisher_covariance_profiling.py    # Test C
│   ├── distinguisher_regression_dependence.py   # Test D
│   ├── distinguisher_bias_moments.py            # Test E
│   └── compute_statistical_significance.py     # p-values for collision, rank, covariance
├── dump/
│   ├── seal/run_001/             # Per-library, per-run dumps
│   ├── openfhe/run_001/
│   └── helib/run_001/
├── output/
│   ├── results/                  # distinguisher_*_{lib}_run_001.json, aggregate_*.json
│   ├── csv/                      # results.csv (summary table)
│   ├── figures/                  # fig1_main.png, fig2_bias.png, fig3_controls.png
│   ├── logs/                     # Control run logs (optional)
│   └── reports/                  # Optional experiment reports
├── scripts/
│   ├── run_experiment.py / .sh / .bat  # Single entry point: multi-run (default), distinguishers, export, figures; --no-multi-run to skip
│   ├── run_all_multi_run.py / .sh / .bat  # Internal: called by run_experiment
│   ├── run_multi_run_suite.py / .sh / .bat  # Internal: called by run_all_multi_run
│   ├── aggregate_multi_run_results.py  # Internal: called by run_multi_run_suite
│   ├── control_fresh_keys.sh / .bat   # Negative control A: 3 fresh dumps
│   ├── control_scaled_dump.py     # Negative control B: scaled variant
│   ├── control_reuse_dump.py      # Positive control: intentional duplicate
│   ├── export_experiment_results.py  # CSV from JSON results
│   └── plot_results.py               # Generate figures from CSV
├── tex/
│   ├── main.tex                  # Paper (LLNCS format)
│   └── references.bib            # Bibliography
└── docs/
    ├── ARCHITECTURE.md
    ├── PROJECT_OVERVIEW.md
    └── methodology.md
```

---

## 4. Dump Schema

### 4.1 Schema Definition

Defined in `config/schema.json`. The dump is a directory with:

- **metadata.json** (required)
- **relin/** — Relinearization keys
- **rotation/** — Rotation/Galois keys

### 4.2 metadata.json

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `library` | string | ✓ | `"seal"` \| `"openfhe"` \| `"helib"` |
| `version` | string | ✓ | Library version (e.g. `"4.1.2"`) |
| `N` | integer | ✓ | Polynomial ring dimension (coefficients per polynomial) |
| `primes` | array[int] | ✓ | RNS prime moduli (q₀, q₁, …) |
| `timestamp` | string | ✓ | ISO 8601 (e.g. `"2026-02-17T12:53:19"`) |
| `relin_blocks` | integer | | Number of relin key blocks |
| `rotation_count` | integer | | Number of rotation keys |
| `in_ntt_domain` | boolean | | Coefficients in NTT form |

### 4.3 File Layout

**Relin keys:**
```
relin/level_{lev}/block_{l}_prime_{p}_ksk0.bin
relin/level_{lev}/block_{l}_prime_{p}_ksk1.bin
```

**Rotation keys:**
```
rotation/automorphism_{a}/level_{lev}/block_{l}_prime_{p}_ksk0.bin
rotation/automorphism_{a}/level_{lev}/block_{l}_prime_{p}_ksk1.bin
```

### 4.4 Block Semantics

Each key-switching matrix row is a polynomial. In RNS, each polynomial is stored per prime:

- **ksk0** (b): The “public” row; encrypts the key material.
- **ksk1** (a): The “mask” row; should be uniformly random per block.

Distinguishers focus on **ksk1** because:
- ksk0 is derived from the secret; structure there is expected.
- ksk1 should be independent random; any structure indicates implementation issues.

### 4.5 Binary Format

- **SEAL, OpenFHE**: `uint64_t` (unsigned), little-endian
- **HElib**: `int64_t` (signed), little-endian

Each `.bin` file: `N` coefficients × 8 bytes = `8*N` bytes.

**HElib variable block sizes:** HElib produces some blocks with fewer than N coefficients (e.g. 32 bytes for thin rotation keys). The schema expects uniform size; in practice we accept variable sizes and **only full-size blocks** (N×8 bytes) are used by the distinguishers. Thin blocks are skipped because they are structurally different and too small for meaningful statistical analysis (collision, rank, regression, bias, covariance).

**Sampling for large dumps (HElib):** When block count is large, distinguishers cap for runtime: regression samples 500k pairs (random); rank uses 500 rows per prime (random sample); covariance uses 2000 blocks (random sample). Results remain statistically meaningful.

---

## 5. Instrumentation (C++ Dump Tools)

### 5.1 Design

Each library has a standalone `dump_keys` executable that:

1. Initializes the library with fixed parameters
2. Generates a secret key and evaluation keys (RelinKeys, GaloisKeys/RotationKeys)
3. Extracts polynomial coefficients from the key structures
4. Writes `metadata.json` and `.bin` files to the output directory

### 5.2 SEAL (seal_dump_keys)

- **Library**: Microsoft SEAL 4.1.x
- **Parameters**: `poly_modulus` (default 4096), `scheme` (ckks|bfv)
- **Windows/MinGW**: Build SEAL with `-DSEAL_USE_ALIGNED_ALLOC=OFF` (see README Adding SEAL). Instrumentation links zlib, zstd, bcrypt explicitly.
- **Key structures**: `RelinKeys`, `GaloisKeys`
- **Layout**: Ciphertext = 2 polynomials (ct[0], ct[1]); each polynomial has `coeff_mod_size` RNS limbs
- **Coefficient type**: `uint64_t`

**Usage:**
```bash
seal_dump_keys --output dump/seal/run_001 --poly_modulus 4096 --scheme ckks
```

### 5.3 OpenFHE (openfhe_dump_keys)

- **Library**: OpenFHE 1.4.x
- **Parameters**: `poly_modulus`, `scheme`
- **Key structures**: `EvalKey` (RelinKeys, GaloisKeys)
- **Layout**: `DCRTPoly` with `GetAllElements()` per RNS prime
- **Coefficient type**: `uint64_t` (from `ConvertToInt()`)

**Usage:**
```bash
openfhe_dump_keys --output dump/openfhe/run_001 --poly_modulus 16384 --scheme ckks
```

### 5.4 HElib (helib_dump_keys)

- **Library**: HElib 2.3.x
- **Parameters**: `m` (cyclotomic index), `p` (plaintext modulus), `r` (Hensel lifting)
- **Key structures**: `SecKey.keySWlist()` → `KeySwitch` matrices
- **Layout**: `KeySwitch` has `b[]` (DoubleCRT) and `prgSeed`; `a` row regenerated from seed
- **Relin vs rotation**: Relin = `from_s==2 && from_x==1`; else rotation
- **Coefficient type**: `int64_t` (NTL::ZZX → long)
- **Constraint**: `p` must not divide `m` (e.g. m=4096 → p=3, not 2)
- **Variable block sizes:** Some rotation keys use a "thin" representation (4 coefficients instead of 2048). These blocks are skipped by the analysis; only full-size blocks (N×8 bytes) are used by distinguishers.

**Usage:**
```bash
helib_dump_keys --output dump/helib/run_001 --m 4096 --p 3
# For production BGV: --m 4096 --p 3 (p=2 invalid when m is power of 2)
```

### 5.5 Library-Specific Notes

| Library | N source | in_ntt_domain |
|---------|----------|----------------|
| SEAL | poly_modulus_degree | true (typically) |
| OpenFHE | ring dimension | true |
| HElib | getPhiM() (φ(m)) | false |

---

## 6. Analysis (Distinguishers)

### 6.1 Shared Utilities (analysis/utils.py)

| Function | Purpose |
|----------|---------|
| `load_metadata(dump_path)` | Load and return metadata.json |
| `iter_ksk1_blocks(dump_path)` | Yield `(BlockInfo, bytes)` for each ksk1 block |
| `bytes_to_coefficients(data, signed)` | Unpack bytes to list of int64/uint64 |
| `get_coeff_signed(meta)` | SEAL, OpenFHE→False (uint64); HElib→True (int64) |
| `hash_coefficients_sha256(coeffs, signed)` | SHA-256 of coefficient vector |

### 6.2 Test A: Shared-Mask / Collision

**Script:** `distinguisher_shared_mask_collision.py`

**Logic:**
- Hash each ksk1 block with SHA-256
- Count collisions across blocks, key types, levels
- Collisions → possible mask reuse

**Output:** `blocks_seen`, `unique_hashes`, `collision_count`, `collision_groups`, `collisions`

**Expected (no leakage):** `collision_count: 0`, `unique_hashes == blocks_seen`

### 6.3 Test B: Rank Deficiency

**Script:** `distinguisher_rank_deficiency.py`

**Logic:**
- Group ksk1 blocks by prime index
- Stack vectors as rows; compute rank over Z_q (Gaussian elimination)
- Low rank → linear dependence

**Output:** `per_prime`: `num_rows`, `rank`, `full_rank`, `deficit`

**Expected (no leakage):** `deficit: 0`, `full_rank: true` for all primes

### 6.4 Test C: Covariance Profiling

**Script:** `distinguisher_covariance_profiling.py`

**Logic:**
- Build matrix M (rows = blocks, cols = N)
- Compute empirical covariance; report Frobenius norm
- Compare to control baseline (fresh vs. scaled)

**Output:** `blocks_used`, `covariance_frobenius_norm`, `cov_shape`

**Expected:** Norm within expected range; large deviation vs. control → structure

### 6.5 Test D: Regression Dependence

**Script:** `distinguisher_regression_dependence.py`

**Logic:**
- Sample pairs (X, Y) of ksk1 vectors
- Fit Y ≈ αX; compute R²
- High R² → linear relation

**Output:** `blocks_used`, `pairs_tested`, `r2_mean`, `r2_max`

**Expected (no leakage):** `r2_mean` negative or near zero

### 6.6 Test E: Bias / Moment Tests

**Script:** `distinguisher_bias_moments.py`

**Logic:**
- Center coefficients in (-q/2, q/2]
- Compute low-bit mean (expect 0.5), skewness, kurtosis
- Cross-prime consistency

**Output:** `per_prime`: `n_coeffs`, `low_bit_mean`, `chi2_like`, `skewness`, `kurtosis`

**Expected (no leakage):** `low_bit_mean ≈ 0.5`, `kurtosis ≈ -1.2`

### 6.7 Statistical Significance

**Script:** `compute_statistical_significance.py`

**Logic:**
- Runs collision, rank, and covariance tests
- Computes p-values for collision (birthday bound) and rank (0 if deficit > 0, else 1)
- Writes `output/results/statistical_significance_{run_id}.json`

**Usage:** `python analysis/compute_statistical_significance.py dump/seal/run_001 [--output <file>]`

---

## 7. Control Procedures

### 7.1 Negative Control A: Fresh Keys

**Scripts:** `control_fresh_keys.sh` / `control_fresh_keys.bat`

- Generate 3 independent dumps (different keygen runs) into `dump/seal/control_fresh_001`, `control_fresh_002`, `control_fresh_003`
- Expect: no spurious correlation within each run

```bash
./scripts/control_fresh_keys.sh
# Then run full experiment (includes control dumps by default):
python scripts/run_experiment.py
```

### 7.2 Negative Control B: Deterministic Scaled

**Script:** `control_scaled_dump.py`

- Create ksk1_scaled = (P⁻¹ × ksk1) mod q (linear multiple of existing block)
- Expect: rank deficit, high covariance

```bash
python scripts/control_scaled_dump.py dump/seal/run_001 dump/seal/control_scaled_001 [prime_index]
```

### 7.3 Positive Control: Intentional Duplicate

**Script:** `control_reuse_dump.py`

- Copy a ksk1 block to create a duplicate in the same dump
- Expect: collision, rank deficit

```bash
python scripts/control_reuse_dump.py dump/seal/run_001 dump/seal/control_positive_001
```

*For fig3_controls to pick up controls, the output directory name must contain `positive`, `scaled`, or `fresh` (e.g. `control_positive_001`, `control_scaled_001`, `control_fresh_001`).*

### 7.4 Multi-Run (Variance Across Key Generations)

**Built into run_experiment.** By default, run_experiment generates 3 key dumps per library, runs distinguishers, and produces `output/results/aggregate_{seal,openfhe,helib}_multi_run.json`. Parameters: SEAL N=4096, OpenFHE N=16384, HElib m=4096 (φ(m)=2048). Use `--no-multi-run` to skip when dumps already exist. If only some dump tools are built, multi-run runs for the available libraries only.

---

## 8. Validation

**Script:** `scripts/validate_dump.py`

**Checks:**
- `metadata.json` exists and is valid JSON
- Required fields present: `library`, `version`, `N`, `primes`, `timestamp`
- `N` positive integer
- Each `.bin` file: expected `N * 8` bytes; HElib may have variable sizes (see §4.5). At least one block must match expected size.
- At least one of `relin/` or `rotation/` exists

**Usage:** `python scripts/validate_dump.py dump/seal/run_001`

---

## 9. Data Flow Detail

```
                    ┌──────────────────────────────────────────┐
                    │           Instrumentation                 │
                    │  (SEAL / OpenFHE / HElib key generation)  │
                    └──────────────────┬───────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Dump Directory                                                           │
│  dump/{lib}/run_001/                                                      │
│  ├── metadata.json     { library, version, N, primes, ... }               │
│  ├── relin/level_0/    block_L_prime_P_ksk0.bin, block_L_prime_P_ksk1.bin │
│  └── rotation/automorphism_A/level_0/  ...                                │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────────────────┐
                    │  utils.iter_ksk1_blocks()                │
                    │  Yields (BlockInfo, raw_bytes) per ksk1  │
                    └──────────────────┬───────────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         │                             │                             │
         ▼                             ▼                             ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  Collision      │         │  Rank           │         │  Covariance      │
│  Hash each      │         │  Stack rows,     │         │  M @ M^T,        │
│  block          │         │  Gaussian elim.  │         │  Frobenius norm  │
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         └───────────────────────────┼───────────────────────────┘
                                     │
                                     ▼
                    ┌──────────────────────────────────────────┐
                    │  output/results/                         │
                    │  distinguisher_{A,B,C,D,E}_{lib}_run.json│
                    └──────────────────────────────────────────┘
```

---

## 10. Result Naming

Results use `run_id = f"{dump_path.parent.name}_{dump_path.name}"` so that:

- `dump/seal/run_001` → `distinguisher_collision_seal_run_001.json`
- `dump/openfhe/run_001` → `distinguisher_collision_openfhe_run_001.json`
- `dump/helib/run_001` → `distinguisher_collision_helib_run_001.json`

This prevents overwriting when running the suite on multiple libraries.

---

## 11. Configuration

### 11.1 parameters.json

Defines parameter regimes and library metadata:

- **regimes:** `standards_aligned` (N=4096, 128-bit), `optimization_stress` (N=32768)
- **libraries:** Version and URL for SEAL, HElib
- **dump:** Domain, NTT flag, subset strategy (max_primes, max_levels, max_rotations)

### 11.2 experiment_configuration.json

Locked experiment config (update when starting a new experiment):

- **libraries:** Per-library version, path, enabled flag
- **parameters:** regime, N, scheme, poly_modulus
- **paths:** dump_base, output_base, logs_dir, results_dir, reports_dir

---

## 12. Multi-Run and Reporting

### 12.1 run_multi_run_suite

**Script:** `run_multi_run_suite.py` (invoked via `.sh` or `.bat`)

- Generates `num_runs` dumps per library (default 3)
- Runs distinguisher suite on each
- Use `--distinguisher-only` to skip dump generation when dumps already exist

```bash
./scripts/run_multi_run_suite.sh seal 5
python scripts/run_multi_run_suite.py openfhe 3 --distinguisher-only
```

### 12.2 aggregate_multi_run_results

**Script:** `aggregate_multi_run_results.py`

- Aggregates results across runs: mean, min, max, consistency
- Output: `output/results/aggregate_{library}_multi_run.json`

### 12.3 CSV Export and Plotting

**Script:** `export_experiment_results.py`

- Reads all `distinguisher_*.json` from `output/results/`
- Writes **one CSV**: `results.csv` (12 columns: library, version, run_id, N, blocks, collision_count, unique_hashes, rank_deficit, r2_mean, r2_max, low_bit_mean, cov_frobenius)
- One row per run—paper-ready summary table

**Script:** `plot_results.py`

- Reads from `output/csv/results.csv` and `output/results/*.json`
- Generates **3 figures**: `fig1_main.png` (2×2 main results), `fig2_bias.png` (bias per prime), `fig3_controls.png` (control validation; placeholder if no control dumps)

**Usage:** Run automatically by `run_experiment.py`, or manually:
```bash
python scripts/export_experiment_results.py
python scripts/plot_results.py
```

---

## 13. Extensibility

### Adding a New Library

1. Add `instrumentation/newlib/dump_keys.cpp` that writes to the schema
2. Add `instrumentation/newlib/CMakeLists.txt`
3. Add `newlib` to `instrumentation/CMakeLists.txt`
4. Update `config/schema.json` `library` enum if needed
5. Update `utils.get_coeff_signed()` if coefficient type differs

### Adding a New Distinguisher

1. Add `analysis/distinguisher_foo.py`
2. Use `utils.load_metadata`, `iter_ksk1_blocks`, `bytes_to_coefficients`
3. Write JSON to `output/results/distinguisher_foo_{run_id}.json`
4. Add to `scripts/run_experiment.py` (DISTINGUISHERS list) and `run_multi_run_suite.py`
5. Optionally add to `compute_statistical_significance.py` if p-value computation applies
