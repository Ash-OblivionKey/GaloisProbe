# Methodology: Evaluation-Key Correlation Cryptanalysis

This document describes the test procedures, controls, and statistical metrics used in the GaloisProbe project. For system design and schema details, see [ARCHITECTURE.md](ARCHITECTURE.md). For reproduction commands, see [README.md](../README.md).

---

## 1. Attacker View

The adversary is the **untrusted cloud evaluator** who receives public key, relinearization keys, rotation/Galois keys, and derived keys. **No decryption oracle.** CPA setting. The attacker attempts to distinguish real implementations from an ideal RLWE distribution. See [ARCHITECTURE.md](ARCHITECTURE.md) §2 for the full attacker model.

---

## 2. Dump Schema

Dump format is defined in `config/schema.json` and documented in [ARCHITECTURE.md](ARCHITECTURE.md) §4. Summary: `metadata.json` plus `relin/` and `rotation/` directories with `.bin` files (N coefficients × 8 bytes per ksk0/ksk1 block). **Thin blocks:** HElib may produce blocks with fewer than N coefficients (e.g. 32 bytes). These are skipped by distinguishers; only full-size blocks (N×8 bytes) are analyzed, as thin blocks are structurally different and too small for meaningful statistics.

---

## 3. Test Procedures (Distinguishers A–E)

### Test A: Shared-mask / collision

- Hash each ksk₁ block with SHA-256 (coefficient domain)
- Collisions across blocks/key types/levels → possible reuse

### Test B: Rank deficiency

- Stack ksk₁ vectors per prime over Z_q
- Gaussian elimination with modular arithmetic (Python int to avoid overflow)
- Low rank → linear dependence

### Test C: Covariance profiling

- Empirical covariance of coefficient vectors
- Frobenius norm; compare to control baseline

### Test D: Regression

- Fit Y ≈ αX for pairs (X, Y)
- High R² → linear relation

### Test E: Bias / moments

- Center coeffs in (-q/2, q/2]
- Low-bit bias, skewness, kurtosis
- Cross-prime consistency

---

## 4. Control Procedures

| Control | Script | Expectation |
|--------|--------|-------------|
| **Negative A** | `control_fresh_keys.sh` / `.bat` | 3 fresh dumps; no spurious correlation within each run |
| **Negative B** | `control_scaled_dump.py <src> <out> [prime_idx]` | Rank deficit, high covariance |
| **Positive** | `control_reuse_dump.py <src> <out>` | Collision detected, rank deficit |

**Example commands:** See [ARCHITECTURE.md](ARCHITECTURE.md) §7.

---

## 5. Statistical Baselines (Null Hypothesis)

Under the assumption that ksk₁ blocks are **independent and uniformly random** mod q:

| Distinguisher | Null expectation | Interpretation |
|---------------|------------------|----------------|
| **Collision** | 0 collisions; unique_hashes = blocks_seen | Birthday bound: collision probability ≈ n²/(2·2²⁵⁶) for n blocks; negligible for n < 10⁶ |
| **Rank** | Full rank; deficit = 0 | Random vectors over Z_q are linearly independent with overwhelming probability |
| **Regression** | R² ≈ 0 or negative | Independent vectors have no linear relation; R² can be negative when ss_res > ss_tot. **HElib borderline:** HElib uses 500k sampled pairs (vs all pairs for SEAL/OpenFHE) and has many more blocks (12k+), so R² mean may be ≈ 0 rather than ≈ -0.75; both indicate no structure. R² max ~0.01 is negligible. |
| **Bias** | low_bit_mean ≈ 0.5, kurtosis ≈ -1.2 | Uniform mod q: LSB is balanced; excess kurtosis of discrete uniform in (-q/2,q/2] ≈ -1.2 |
| **Covariance** | Frobenius norm within expected range | For independent rows, cov ≈ diagonal (scaled); norm depends on N, block count. Fig1 panel (e) shows log₁₀(cov Frobenius) for comparability across libraries. |

**Observed vs. null:** Our results (collision_count=0, deficit=0, r2_mean<0, low_bit≈0.5, kurtosis≈-1.2) are consistent with the null. Control experiments confirm distinguishers detect structure when present.

---

## 6. Metrics and Correction

### 6.1 p-Values

- **Collision:** p-value for observed collision count vs. null (birthday bound)
- **Rank:** p-value = 0 if deficit > 0, else 1
- **Covariance:** Permutation test vs. control (optional)

### 6.2 Effect Sizes

- Covariance Frobenius norm vs. control baseline
- Normalized rank deficit (deficit / min(rows, N))
- Collision entropy loss (if applicable)

### 6.3 Multiple-Testing Correction

When running many distinguishers (A–E) across primes, regimes, or runs, apply correction to control family-wise error rate:

**Bonferroni:** For k tests, reject at level α if p ≤ α/k. Conservative; controls FWER.

**Benjamini–Hochberg (FDR):** Order p-values p₁ ≤ … ≤ pₖ; find largest j with pⱼ ≤ (j/k)α; reject H₁,…,Hⱼ. Less conservative; controls false discovery rate.

**Recommendation:** Use Bonferroni for small k (≤5) and when strong control is needed; use FDR when exploring many hypotheses. Document the chosen method in each report.

---

## 7. Execution Workflow

**Primary reproduction:** See [README.md](../README.md). Use `python scripts/run_experiment.py` (or `./scripts/run_experiment.sh` / `scripts\run_experiment.bat`) to run all distinguishers on all dumps, export CSV, and generate figures in one step.

**Full pipeline (build + dump + run):** See README.md § Path B. Build instrumentation, run dump tools, validate, then `python scripts/run_experiment.py`.

**Optional steps:**
- **Statistical significance:** P-values (p_collision, p_rank) are computed automatically by `export_experiment_results.py` and included in `output/csv/results.csv`. For per-dump detailed analysis: `python analysis/compute_statistical_significance.py dump/seal/run_001`
- **Skip multi-run:** Use `run_experiment.py --no-multi-run` when dumps already exist and you only want to re-run distinguishers.

---

## 8. Related Documents

| Document | Description |
|----------|-------------|
| [README.md](../README.md) | Reproduction commands, quick start |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, schema, instrumentation, control procedures |
| [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) | Motivation, results, project summary |
| [LIBRARY_COMPARISON.md](LIBRARY_COMPARISON.md) | Side-by-side comparison of SEAL, OpenFHE, HElib |
| [IMPLEMENTATION_CROSSCHECK.md](IMPLEMENTATION_CROSSCHECK.md) | End-to-end implementation cross-check report |
