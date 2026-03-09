# Project Overview: Evaluation-Key Correlation Cryptanalysis

**GaloisProbe** is a research project that investigates whether homomorphic encryption libraries introduce detectable correlation or structure in their evaluation keys. This document provides a complete overview of the project: motivation, what we did, results, and important details.

**Main contribution:** We provide a **rigorous, reproducible methodology and tooling** for correlation cryptanalysis of evaluation keys. The pipeline—instrumentation, dump schema, five distinguishers, and control procedures—can be applied to any HE library that exposes key-switching matrices. Our negative result (no leakage detected in SEAL, OpenFHE, HElib) provides assurance and establishes a baseline for future audits.

---

## 1. What Is This Project?

### 1.1 Homomorphic Encryption in Brief

**Homomorphic encryption (HE)** allows computation on encrypted data without decrypting it. A cloud server can add or multiply encrypted numbers without ever seeing the plaintext. To do this, the server needs **evaluation keys** (also called helper keys):

- **Relinearization keys (RelinKeys):** Convert ciphertexts with quadratic terms (s²) back to linear form (s). Needed after multiplications.
- **Rotation keys (GaloisKeys):** Rotate slots in a ciphertext. Needed for operations like matrix multiplication or data movement.

These keys are **public**—they are sent to the evaluator along with the ciphertexts.

### 1.2 The Research Question

Libraries optimize evaluation keys for performance:

- Generate one key set and derive smaller versions (e.g., by dropping primes)
- Reuse or reorganize internal values
- Precompute scaled variants

**Our question:** Does this optimization introduce **hidden structure** that an attacker could exploit?

Examples of problematic structure:

- **Mask reuse:** Two different keys accidentally share the same random component
- **Linear dependence:** Some key blocks are linear combinations of others
- **Bias:** Coefficients deviate from the expected uniform distribution

If such structure exists, it could indicate a bug, a mismatch with security proofs, or—in the worst case—a path toward leaking information about the secret key.

### 1.3 What We Did

We built a **correlation cryptanalysis** pipeline that:

1. **Extracts** evaluation keys from three major HE libraries (SEAL, OpenFHE, HElib)
2. **Dumps** them into a common format (polynomial coefficients per RNS prime)
3. **Runs five distinguisher tests** (collision, rank, covariance, regression, bias)
4. **Compares** results to what we would expect if keys were ideal and independent

---

## 2. Libraries Tested

| Library | Version | Scheme | Parameters Used |
|---------|---------|--------|-----------------|
| **Microsoft SEAL** | 4.1.2 | CKKS | N=4096, 3 primes (~36 bits each) |
| **OpenFHE** | 1.4.2 | CKKS | N=16384, 8 primes |
| **HElib** | 2.3.0 | BGV | m=4096 (φ(m)=2048), p=3 |

SEAL and OpenFHE use CKKS (approximate arithmetic); HElib uses BGV (exact arithmetic). All three support relinearization and rotation keys.

---

## 3. Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Phase 1: Instrumentation (C++)                                          │
│  Build seal_dump_keys, openfhe_dump_keys, helib_dump_keys                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Phase 2: Key Generation & Dump                                          │
│  Run each tool → dump/{seal,openfhe,helib}/run_001/                     │
│  Output: metadata.json + .bin files (coefficients per prime)              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Phase 3: Validation                                                     │
│  python scripts/validate_dump.py dump/seal/run_001                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Phase 4: Distinguisher Suite (Python)                                   │
│  Run 5 tests (A–E) on each dump → output/results/*.json                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. The Five Distinguishers

We run five tests on the **ksk₁** (mask) components of each key block. The ksk₁ should be uniformly random; any structure is suspicious.

| Test | Name | What It Detects | Ideal Result |
|------|------|-----------------|--------------|
| **A** | Shared-mask / collision | Same mask used in multiple blocks | 0 collisions |
| **B** | Rank deficiency | Linear dependence among blocks | Full rank, deficit 0 |
| **C** | Covariance profiling | Correlations between blocks | Norm within expected range |
| **D** | Regression dependence | Linear relation Y ≈ αX between blocks | R² near 0 or negative |
| **E** | Bias / moments | Non-uniform coefficients (low-bit, skew, kurtosis) | low_bit ≈ 0.5, kurt ≈ -1.2 |

---

## 5. Results Summary

### 5.1 Main Finding

**No correlation leakage was detected** in any of the three libraries. All distinguishers reported results consistent with ideal, independent key material.

### 5.2 Per-Library Results

| Library | Blocks | Collisions | Rank Deficit | R² Mean | Low-Bit Mean |
|---------|--------|------------|--------------|---------|--------------|
| SEAL | 138 | 0 | 0 | ~-0.75 | ~0.50 |
| OpenFHE | 336 | 0 | 0 | ~-0.75 | ~0.50 |
| HElib | varies | 0 | 0 | negative | ~0.50 |

- **Collision:** Zero collisions in all libraries; each ksk₁ block has a unique hash.
- **Rank:** Full rank for all primes; no linear dependence.
- **Regression:** Negative R² indicates poor linear fit; no detectable linear relations.
- **Bias:** Low-bit mean near 0.5 and kurtosis near -1.2; consistent with uniform distribution.

### 5.3 Control Validation

We validated that the distinguishers work correctly:

- **Positive control:** Intentional duplicate block → collision and rank deficit detected ✓
- **Negative control (scaled):** Deterministic linear multiple → rank deficit, high covariance ✓
- **Negative control (fresh):** Three independent dumps → no spurious correlation ✓

---

## 6. What We Built

### 6.1 Instrumentation (C++)

Three standalone executables, one per library:

- **seal_dump_keys:** Extracts RelinKeys and GaloisKeys from SEAL 4.1.x
- **openfhe_dump_keys:** Extracts RelinKeys and GaloisKeys from OpenFHE 1.4.x
- **helib_dump_keys:** Extracts relin and rotation keys from HElib 2.3.x (BGV)

Each tool generates keys with fixed parameters and writes polynomial coefficients to a common schema.

### 6.2 Dump Schema

A dump is a directory with:

- **metadata.json:** Library, version, N (ring dimension), primes, block counts, timestamp
- **relin/level_X/:** Relinearization key blocks (block_L_prime_P_ksk0.bin, ksk1.bin)
- **rotation/automorphism_A/level_X/:** Rotation key blocks

Each `.bin` file: N coefficients × 8 bytes (little-endian). SEAL and OpenFHE use uint64; HElib uses int64 (signed).

### 6.3 Analysis (Python)

- **utils.py:** Load metadata, iterate over ksk₁ blocks, convert bytes to coefficients
- **Five distinguisher scripts:** Each reads a dump and writes JSON results
- **compute_statistical_significance.py:** Compute p-values for collision, rank, covariance
- **validate_dump.py:** Schema validation
- **Control scripts:** Generate positive/negative control dumps

### 6.4 Scripts

- **run_experiment.py / .sh / .bat:** Single entry point. By default: multi-run (3 dumps per library), distinguishers, export, figures. Use `--no-multi-run` to skip multi-run when dumps already exist. See [README.md](../README.md).
- **run_all_multi_run.py** (internal): Called by run_experiment for multi-run; generates `run_001`–`run_003` per library and `aggregate_*_multi_run.json`.
- **control_fresh_keys.sh / .bat, control_scaled_dump.py, control_reuse_dump.py:** Control experiments. See [ARCHITECTURE.md](ARCHITECTURE.md) §7.

---

## 7. Important Technical Details

### 7.1 Why ksk₁?

Each key-switching matrix has two rows:

- **ksk₀ (b):** Encrypts the key material; derived from the secret. Structure here is expected.
- **ksk₁ (a):** The "mask"; should be uniformly random. Structure here indicates implementation issues.

We focus on ksk₁ because it is the component that must be independent across blocks.

### 7.2 RNS (Residue Number System)

Coefficients are stored per prime modulus. Each polynomial is split into limbs, one per prime. The distinguishers operate per prime where relevant (e.g., rank test stacks blocks by prime index).

### 7.3 Library-Specific Notes

**SEAL:** Coefficients are typically in NTT (Number Theoretic Transform) form. Our analysis treats them as raw coefficients; the distinguishers still detect structure.

**OpenFHE:** Uses DCRTPoly; we extract coefficients per RNS limb.

**HElib:** Uses DoubleCRT. The ksk₁ row is regenerated from a PRG seed; we dump the regenerated coefficients. Relin keys identified by from_s=2, from_x=1.

### 7.4 HElib Parameter Constraint

HElib requires the plaintext modulus `p` to **not divide** the cyclotomic index `m`. For m=4096 (power of 2), p=2 is invalid. We use p=3.

---

## 8. Project Structure

```
GaloisProbe/
├── config/
│   ├── schema.json             # Dump schema definition
│   ├── parameters.json         # Parameter regimes (N, log_q, primes_bits)
│   └── experiment_configuration.json  # Locked experiment config
├── instrumentation/            # C++ dump tools
│   ├── seal/dump_keys.cpp
│   ├── openfhe/dump_keys.cpp
│   └── helib/dump_keys.cpp
├── analysis/                   # Python distinguishers
│   ├── utils.py
│   ├── distinguisher_shared_mask_collision.py
│   ├── distinguisher_rank_deficiency.py
│   ├── distinguisher_covariance_profiling.py
│   ├── distinguisher_regression_dependence.py
│   ├── distinguisher_bias_moments.py
│   └── compute_statistical_significance.py
├── dump/                       # Raw dumps (per library, per run)
├── output/
│   ├── results/                # JSON results, aggregate_*_multi_run.json
│   ├── csv/                    # results.csv (summary table)
│   ├── figures/                # fig1_main.png, fig2_bias.png, fig3_controls.png
│   ├── logs/                   # Control run logs (optional)
│   └── reports/                # Optional experiment reports
├── scripts/                    # Validation, run_experiment, run_all_multi_run, controls
├── tex/                        # Paper (main.tex, references.bib)
├── docs/                       # Architecture, methodology, this overview
└── README.md                   # Reproduction instructions
```

---

## 9. Reproducibility

All reproduction steps are in the main [README.md](../README.md). Summary:

- **One script:** Run `python scripts/run_experiment.py` (or `./scripts/run_experiment.sh` / `scripts\run_experiment.bat`). By default it runs multi-run (3 dumps per library), distinguishers, export, and figures.
- **Existing dumps:** Use `--no-multi-run` to skip multi-run and only re-run distinguishers on existing dumps.
- **Full pipeline:** Build instrumentation, then run `python scripts/run_experiment.py`.

Results: `output/csv/results.csv`, `output/figures/fig1_main.png`, `fig2_bias.png`, `fig3_controls.png`. Raw JSON in `output/results/`. Multi-run aggregates in `output/results/aggregate_*_multi_run.json`.

---

## 10. Limitations and Caveats

- **Sample size:** run_experiment runs **3 key generations per library** by default. This is a modest sample; statistical power for detecting rare or subtle structure is limited. Fig2 aggregates across these 3 runs (mean ± std). Use `--no-multi-run` to skip when dumps already exist. For stronger conclusions, increase the number of runs.
- **Parameters:** We use default or standard parameters. Different parameter sets could behave differently.
- **Scope:** We test evaluation keys only. We do not analyze ciphertexts, plaintexts, or other components.

---

## 11. Related Work

- **HE implementation security:** Prior work on homomorphic encryption has focused on side-channel attacks (timing, power) on key generation or encryption, and on correctness/security of the underlying schemes. We are not aware of prior systematic correlation analysis of evaluation-key *implementations* across multiple libraries.
- **RLWE/LWE cryptanalysis:** Distinguishing attacks on RLWE assume access to many samples; our setting is different—we observe a fixed set of evaluation-key blocks and test for implementation-induced structure (reuse, dependence, bias) rather than solving RLWE.
- **Key-switching security:** The key-switching procedure is well-studied theoretically; we test whether *implementations* deviate from the ideal by reusing randomness or introducing bias.

---

## 12. Conclusion

GaloisProbe provides a **rigorous, reproducible pipeline** for testing evaluation keys from SEAL, OpenFHE, and HElib. We found **no evidence of correlation leakage** in any of the three libraries. The distinguishers are validated by control experiments. The methodology and tooling are the main contribution; the codebase, schema, and documentation support future extensions (e.g., additional libraries, parameters, or tests).

---

## 13. Related Documents

| Document | Description |
|----------|-------------|
| [README.md](../README.md) | Quick start and reproduction steps |
| [ARCHITECTURE.md](ARCHITECTURE.md) | In-depth system architecture |
| [methodology.md](methodology.md) | Test procedures and statistical metrics |
| [LIBRARY_COMPARISON.md](LIBRARY_COMPARISON.md) | Side-by-side comparison of SEAL, OpenFHE, HElib |
| [IMPLEMENTATION_CROSSCHECK.md](IMPLEMENTATION_CROSSCHECK.md) | End-to-end implementation cross-check report |
| [config/schema.json](../config/schema.json) | Dump schema definition |
