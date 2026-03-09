# Library Comparison: SEAL, OpenFHE, HElib

This document compares the three tested libraries and confirms all parameters and results are correct and consistent across the documentation.

---

## 1. Parameter Summary

| Library | Version | Scheme | N (ring dim) | Parameters | Blocks |
|---------|---------|--------|--------------|------------|--------|
| **SEAL** | 4.1.2 | CKKS | 4096 | poly_modulus 4096, 3 primes | 138 |
| **OpenFHE** | 1.4.2 | CKKS | 16384 | poly_modulus 16384, 8 primes | 336 |
| **HElib** | 2.3.0 | BGV | 2048 (φ(m)) | m=4096, p=3, 6–7 primes | ~12,000 (full-size) |

**Notes:**
- SEAL and OpenFHE use CKKS (approximate arithmetic); HElib uses BGV (exact arithmetic).
- HElib has ~12k full-size blocks (N×8 bytes); ~264 thin blocks (32 bytes) are skipped.
- Block counts are library-specific and determined by key structure (relin + rotation keys).

---

## 2. Dump Tool Commands

| Library | Command |
|---------|---------|
| SEAL | `seal_dump_keys --output dump/seal/run_001 --poly_modulus 4096 --scheme ckks` |
| OpenFHE | `openfhe_dump_keys --output dump/openfhe/run_001 --poly_modulus 16384 --scheme ckks` |
| HElib | `helib_dump_keys --output dump/helib/run_001 --m 4096 --p 3` |

---

## 3. Distinguisher Results (Expected: No Leakage)

| Library | Collision | Rank | Regression (R² mean) | Bias (low-bit) |
|---------|-----------|------|----------------------|----------------|
| SEAL | 0 | 0 | ~-0.75 | ~0.50 |
| OpenFHE | 0 | 0 | ~-0.75 | ~0.50 |
| HElib | 0 | 0 | ~0 (sampled) | ~0.50 |

All three libraries pass all distinguishers. Results are consistent with ideal, independent key material.

---

## 4. Library-Specific Differences

| Aspect | SEAL | OpenFHE | HElib |
|--------|------|---------|-------|
| **Coefficient type** | uint64_t | uint64_t | int64_t |
| **NTT domain** | Yes (typically) | Yes | No |
| **Block size** | Uniform (N×8) | Uniform (N×8) | Mixed (full + thin; thin skipped) |
| **Sampling** | None (all blocks) | None (all blocks) | Regression: 500k pairs; Rank: 500 rows/prime; Cov: 2000 blocks |

**R² distribution:** SEAL and OpenFHE use all pairs → R² mean ≈ -0.75. HElib samples 500k pairs from ~76M → R² mean may be ≈ 0. Both indicate no linear relation; the difference is methodological (sampling), not a security finding.

---

## 5. Documentation Consistency

| Document | SEAL | OpenFHE | HElib |
|----------|------|---------|-------|
| README | N=4096, 138 blocks | N=16384, 336 blocks | m=4096, N=2048 |
| PROJECT_OVERVIEW | ✓ | ✓ | ✓ |
| ARCHITECTURE | ✓ | ✓ | ✓ (variable blocks, sampling) |
| methodology | ✓ | ✓ | ✓ (thin blocks) |
| tex/main.tex | ✓ | ✓ (336 blocks) | ✓ |

---

## 6. Verification Checklist

- [x] All three libraries use correct parameters in `run_multi_run_suite.py`
- [x] README, ARCHITECTURE, PROJECT_OVERVIEW, methodology agree on parameters
- [x] OpenFHE block count corrected to 336 (was 288 in paper)
- [x] HElib variable block sizes and sampling documented
- [x] Validation accepts HElib variable sizes; requires at least one block of expected size
- [x] Controls (positive, scaled, fresh) validate distinguishers

---

## 7. Conclusion

**All three libraries are correctly configured and documented.** The different N values, block counts, and schemes are intentional—each library is tested with representative parameters. The pipeline applies the same five distinguishers to all; the null expectations (0 collisions, full rank, negative R², low-bit ≈ 0.5) are comparable across libraries.
