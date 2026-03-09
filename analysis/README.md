# Analysis: Distinguisher Suite

Implements distinguishers A–E. See [docs/methodology.md](../docs/methodology.md) for test procedures.

## Setup

From project root: `pip install -r analysis/requirements.txt`

## Main Entry Point

From project root, run the full experiment (one script):

```bash
python scripts/run_experiment.py
```

Or `./scripts/run_experiment.sh` (Linux/macOS) / `scripts\run_experiment.bat` (Windows). By default: multi-run (3 dumps per library), five distinguishers, export CSV, figures. Use `--no-multi-run` if dumps already exist.

## Distinguishers

| Script | Test | Description |
|--------|------|-------------|
| `distinguisher_shared_mask_collision.py` | A. Shared-mask / collision | Hash ksk₁ blocks; detect collisions |
| `distinguisher_rank_deficiency.py` | B. Rank deficiency | Stack ksk₁ vectors; compute rank |
| `distinguisher_covariance_profiling.py` | C. Covariance profiling | Empirical covariance across keys |
| `distinguisher_regression_dependence.py` | D. Regression dependence | Linear fit Y ≈ Σ α_k X_k |
| `distinguisher_bias_moments.py` | E. Bias / moment tests | Low-bit, skewness, kurtosis |

## Running a Single Distinguisher

From project root:

```bash
python analysis/distinguisher_shared_mask_collision.py dump/seal/run_001
```

## Statistical Significance (Optional)

```bash
python analysis/compute_statistical_significance.py dump/seal/run_001
```

## Output

Results: `output/results/*.json`, `output/results/aggregate_*_multi_run.json`, `output/csv/results.csv`, `output/figures/`.
