# GaloisProbe

A reproducible pipeline to detect implementation-induced correlation in homomorphic encryption evaluation keys (RelinKeys, GaloisKeys) across **Microsoft SEAL**, **OpenFHE**, and **HElib**.

**Result:** No correlation leakage found in any of the three libraries.

---

## Table of Contents

- [Quick Start](#quick-start)
- [What to Run When](#what-to-run-when)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Reproduction](#reproduction)
- [Output](#output)
- [Interpreting Results](#interpreting-results)
- [Troubleshooting](#troubleshooting)
- [Further Reading](#further-reading)

---


## Quick Start

**One command** — from the project root, after [Setup](#setup) and building dump tools ([Path B](#path-b-full-pipeline-build--run)):

```bash
python scripts/run_experiment.py
```

**Linux/macOS:** Use `python3` if `python` points to Python 2. **Windows:** Use `python` (or `scripts\run_experiment.bat`).

This runs multi-run (3 key generations per library), distinguishers, export CSV, and figures. **Dump tools must be built first**; otherwise the script exits. Use `--no-multi-run` only when you already have dumps (e.g. from a [release](https://github.com/Ash-OblivionKey/GaloisProbe/releases)).

---

## What to Run When

| You have | Run this | What happens |
|----------|----------|--------------|
| **Built dump tools** (SEAL, OpenFHE, HElib) | `python scripts/run_experiment.py` | Full run: multi-run (3 dumps per lib), distinguishers, CSV, figures |
| **Dumps only** (e.g. from release, no build) | `python scripts/run_experiment.py --no-multi-run` | Uses existing dumps, runs distinguishers, exports CSV, figures |
| **Nothing** | Follow [Path B](#path-b-full-pipeline-build--run) | Build first, then run experiment |

**Rule:** Get everything you need (build dump tools) first, then run the experiment. Use `--no-multi-run` only when you already have dumps and do not need to generate new ones.

**Optional flags:**

| Flag | Use when |
|------|----------|
| `--no-multi-run` | Force skip multi-run; use existing dumps only |
| `--no-controls` | Skip control dumps (control_fresh, control_positive, control_scaled) |
| `--no-clean` | Keep old outputs; do not remove before run |
| `--no-export` | Run distinguishers only; skip CSV and figures |

---

## Prerequisites

| Requirement | Needed for |
|-------------|------------|
| **Python ≥ 3.8** | Always (distinguishers, export, figures) |
| **numpy, scipy, scikit-learn, matplotlib** | `pip install -r analysis/requirements.txt` |
| **CMake ≥ 3.14, C++17** | Only for building dump tools |
| **SEAL 4.1.x, OpenFHE 1.4.x, HElib 2.3.x** | Only for generating key dumps. See [HE Libraries](#he-libraries-clone--build) below. |

---

## Setup

All commands from the **project root** (directory containing this README).

### 1. Python dependencies

```bash
pip install -r analysis/requirements.txt
```

This installs numpy, scipy, scikit-learn, matplotlib. **That's all you need** for the Python analysis (distinguishers, export, figures). For Path B you also need the HE libraries and dump tools.

### 2. Virtual environment (optional)

Use a venv if you prefer isolated dependencies or hit `externally-managed-environment` errors:

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r analysis/requirements.txt
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r analysis/requirements.txt
```

---

## Reproduction

**What's in this repository:** The clone includes source code, scripts, config, and documentation only. The `dump/` and `output/` directories are **not** included—they are generated when you run the experiment. To reproduce the full results, either generate dumps (Path B) or obtain them from a [release](https://github.com/Ash-OblivionKey/GaloisProbe/releases) (Path A).

**Reproduction checklist (Path B — full pipeline):**

1. Clone GaloisProbe: `git clone https://github.com/Ash-OblivionKey/GaloisProbe.git && cd GaloisProbe`
2. [Setup](#setup): Install Python dependencies (`pip install -r analysis/requirements.txt`)
3. [HE Libraries](#he-libraries-clone--build): Clone, build, and install SEAL, OpenFHE, HElib (or a subset)
4. [Step 1](#step-1-build-dump-tools): Build dump tools (`instrumentation/build/`)
5. [Step 4](#step-4-run-experiment): Run `python scripts/run_experiment.py`

---

### Path A: Run Experiment with Existing Dumps

**Prerequisites:** [Setup](#setup) (Python dependencies) — no HE libraries or dump tools needed.

If you have dumps (e.g. from a [release](https://github.com/Ash-OblivionKey/GaloisProbe/releases)), extract or place them under `dump/seal/`, `dump/openfhe/`, `dump/helib/` with the expected structure (e.g. `dump/seal/run_001/`, `dump/seal/run_002/`, each containing `metadata.json` and key blocks). You need at least one dump per library you want to analyze. Then:

**Linux / macOS:**
```bash
python3 scripts/run_experiment.py --no-multi-run
```

**Windows:**
```powershell
python scripts/run_experiment.py --no-multi-run
```

Or: `scripts\run_experiment.bat --no-multi-run` (Windows), `./scripts/run_experiment.sh --no-multi-run` (Linux/macOS).

**Output:** `output/csv/results.csv`, `output/results/*.json`, `output/figures/fig1_main.png`, `output/figures/fig2_bias.png`, `output/figures/fig3_controls.png`.

---

### Path B: Full Pipeline (build + generate dumps + run)

Use when you have no dumps and want to generate them from the HE libraries.

#### HE Libraries: Clone & Build

Clone and build each library separately. Install to a prefix (e.g. `SEAL-install`, `OpenFHE-install`) and point CMake at the **install** directory, not the source.

| Library | GitHub | Clone command |
|---------|--------|----------------|
| **SEAL** | [microsoft/SEAL](https://github.com/microsoft/SEAL) | `git clone https://github.com/microsoft/SEAL.git` |
| **OpenFHE** | [openfheorg/openfhe-development](https://github.com/openfheorg/openfhe-development) | `git clone https://github.com/openfheorg/openfhe-development.git` |
| **HElib** | [homenc/HElib](https://github.com/homenc/HElib) | `git clone https://github.com/homenc/HElib.git` |

**After cloning, for each library** (run from the directory where you cloned it):

1. **Checkout the version** (for compatibility use SEAL 4.1.x, OpenFHE 1.4.x, HElib 2.3.x):
   ```bash
   # From SEAL/ directory:
   git checkout v4.1.1
   # From openfhe-development/ directory:
   git checkout v1.4.2
   # From HElib/ directory:
   git checkout v2.3.0
   ```

2. **Build and install** (replace `/path/to/X-install` with your chosen install prefix; e.g. `$HOME/SEAL-install`):
   ```bash
   # SEAL
   cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/path/to/SEAL-install
   cmake --build build && cmake --install build

   # OpenFHE
   mkdir build && cd build
   cmake -DCMAKE_INSTALL_PREFIX=/path/to/OpenFHE-install ..
   make -j4 && make install

   # HElib (use PACKAGE_BUILD to bundle NTL/GMP)
   mkdir build && cd build
   cmake -DPACKAGE_BUILD=ON -DCMAKE_INSTALL_PREFIX=/path/to/HElib-install ..
   make -j4 && make install
   ```

3. **Note the install path** — use it for `SEAL_ROOT`, `OPENFHE_ROOT`, `HELIB_ROOT` in [Step 1](#step-1-build-dump-tools) below.

See each library's [SEAL](https://github.com/microsoft/SEAL#building) | [OpenFHE](https://openfhe-development.readthedocs.io/en/latest/sphinx_rsts/intro/installation/installation.html) | [HElib](https://github.com/homenc/HElib/blob/master/INSTALL.md) docs for platform-specific details (Windows, macOS, etc.).

---

#### Step 1: Build dump tools

**Linux / macOS:**
```bash
rm -rf instrumentation/build
mkdir -p instrumentation/build && cd instrumentation/build
cmake -G "Unix Makefiles" \
  -DSEAL_ROOT="/path/to/SEAL-install" \
  -DOPENFHE_ROOT="/path/to/OpenFHE-install" \
  -DUSE_HELIB=ON -DHELIB_ROOT="/path/to/HElib-install" \
  ..
make
cd ../..
```

**Windows (PowerShell):**
```powershell
if (Test-Path instrumentation\build) { Remove-Item -Recurse -Force instrumentation\build }
mkdir instrumentation\build
cd instrumentation\build
cmake -G "Visual Studio 17 2022" -A x64 `
  -DSEAL_ROOT="C:\path\to\SEAL-install" `
  -DOPENFHE_ROOT="C:\path\to\OpenFHE-install" `
  -DUSE_HELIB=ON -DHELIB_ROOT="C:\path\to\HElib-install" `
  ..
cmake --build . --config Release
cd ..\..
```

Replace `/path/to/X-install` with your actual install paths. Omit `-DSEAL_ROOT`, `-DOPENFHE_ROOT`, or `-DHELIB_ROOT` if that library is not installed (you can run with a subset).

##### Adding SEAL (full multi-run for all three libraries)

If you built instrumentation without SEAL and want to add it later:

**Two folders:** `SEAL` = source (for building); `SEAL-install` = install prefix (for `SEAL_ROOT`). Point `SEAL_ROOT` at the **install** prefix, not the source.

1. **Build and install SEAL 4.1** ([microsoft/SEAL](https://github.com/microsoft/SEAL) — `git clone https://github.com/microsoft/SEAL.git`):

   **Windows (Visual Studio):**
   ```powershell
   cd path\to\SEAL
   cmake -S . -B build -G "Visual Studio 17 2022" -A x64
   cmake --build build --config Release
   cmake --install build   # Run as Administrator; installs to C:\Program Files (x86)\SEAL\
   ```

   **Windows (MSYS2/MinGW):** Use Ninja from MSYS2 MinGW64 shell. Add `-DSEAL_USE_ALIGNED_ALLOC=OFF` (required: `aligned_alloc` unavailable on MinGW/Windows):
   ```powershell
   # From MSYS2 MinGW64 shell:
   cd /c/path/to/SEAL
   cmake -G Ninja -B build-mingw -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="/c/path/to/GaloisProbe/SEAL-install" -DSEAL_USE_ALIGNED_ALLOC=OFF ..
   ninja -C build-mingw
   cmake --install build-mingw
   ```

   **Linux / macOS:**
   ```bash
   cd path/to/SEAL
   cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/usr/local
   cmake --build build
   sudo cmake --install build
   ```

2. **Reconfigure and rebuild instrumentation:**
   Set `SEAL_ROOT` to the **install** prefix (e.g. `SEAL-install` in project root, or `C:\Program Files (x86)\SEAL`).

   **Windows:**
   ```powershell
   cd instrumentation\build
   cmake -DSEAL_ROOT="C:\Program Files (x86)\SEAL" ..
   # Or, if SEAL-install is in project root: cmake -DSEAL_ROOT="..\..\SEAL-install" ..
   cmake --build . --config Release
   cd ..\..
   ```

   **Linux / macOS:**
   ```bash
   cd instrumentation/build
   cmake -DSEAL_ROOT=/usr/local ..
   make
   cd ../..
   ```

3. **Run the full experiment:**
   ```bash
   python scripts/run_experiment.py
   ```

**Note:** Use the same toolchain for SEAL and instrumentation (e.g. both VS or both MinGW).

#### Step 2: Generate dumps (optional)

*Step 4 runs multi-run, which generates run_001–run_003 per library automatically. Use Step 2 only to verify dump tools work before the full run.*

**Linux / macOS:**
```bash
mkdir -p dump/seal/run_001 dump/openfhe/run_001 dump/helib/run_001

./instrumentation/build/seal/seal_dump_keys --output dump/seal/run_001 --poly_modulus 4096 --scheme ckks
./instrumentation/build/openfhe/openfhe_dump_keys --output dump/openfhe/run_001 --poly_modulus 16384 --scheme ckks
./instrumentation/build/helib/helib_dump_keys --output dump/helib/run_001 --m 4096 --p 3
```

**Windows:** Use `instrumentation\build\seal\seal_dump_keys.exe` (MinGW) or `instrumentation\build\seal\Release\seal_dump_keys.exe` (MSVC). Same for openfhe and helib.

#### Step 3: Validate (optional)

```bash
python scripts/validate_dump.py dump/seal/run_001
python scripts/validate_dump.py dump/openfhe/run_001
python scripts/validate_dump.py dump/helib/run_001
```

#### Step 4: Run experiment

From the **project root** (directory containing this README):

```bash
python scripts/run_experiment.py
```

This runs multi-run (3 dumps per library), distinguishers, export, and figures.

---

## Output

`python scripts/run_experiment.py` produces:

| Path | Description |
|------|-------------|
| `output/csv/results.csv` | Summary table: library, version, scheme, run_id, N, blocks, collision_count, rank_deficit, r2_mean, low_bit_mean, cov_frobenius |
| `output/results/distinguisher_*.json` | Per-dump distinguisher results (collision, rank, regression, bias, covariance) |
| `output/results/aggregate_*_multi_run.json` | Multi-run aggregates (only when multi-run ran) |
| `output/figures/fig1_main.png` | Main results (collision, rank, regression, bias) |
| `output/figures/fig2_bias.png` | Bias per RNS prime |
| `output/figures/fig3_controls.png` | Control validation (always generated; placeholder if no control dumps) |

### Re-export and regenerate figures

Without re-running distinguishers:

```bash
python scripts/export_experiment_results.py
python scripts/plot_results.py
```

---

## Interpreting Results

When no leakage is present, the distinguishers report:

| Distinguisher | Expected |
|---------------|----------|
| Collision | `collision_count: 0` |
| Rank | `deficit: 0` |
| Regression | `r2_mean` negative |
| Bias | `low_bit_mean` ≈ 0.5 |

See `docs/methodology.md` for detailed test procedures and statistical metrics.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `bash\r: No such file or directory` | Fix line endings: `sed -i.bak 's/\r$//' scripts/*.sh && rm -f scripts/*.bak` (Linux/macOS) |
| CMake path mismatch | Remove `instrumentation/build` and reconfigure |
| `SEAL: skipped` | Optional. Add `-DSEAL_ROOT=/path/to/SEAL-install` to build SEAL; omit to run with OpenFHE/HElib only. See [Adding SEAL](#adding-seal-full-multi-run-for-all-three-libraries). |
| `OpenFHE not found` | Provide `-DOPENFHE_ROOT=/path` |
| `HElib: disabled` | Add `-DUSE_HELIB=ON -DHELIB_ROOT=/path/to/HElib-install` (install prefix, not source) |
| HElib: `Modulus pp divides mm` | For m=4096, use `--p 3` (p=2 is invalid) |
| `externally-managed-environment` (pip) | Your system restricts global pip. Use a venv: see [Setup §2](#2-virtual-environment-optional). |
| `python3` not found (Windows) | Use `python` instead |
| Dump tools not found | Script exits. Build instrumentation (Path B) first. Use `--no-multi-run` only if you have existing dumps. |
| How to add SEAL later | See [Adding SEAL](#adding-seal-full-multi-run-for-all-three-libraries) under Path B. |
| WinError 4551 / "Application Control policy blocked" | Windows Smart App Control blocks new executables. Turn off Smart App Control (App & browser control) or add an exclusion for the GaloisProbe project folder. |

---

## Further Reading

| Document | Description |
|----------|-------------|
| `docs/PROJECT_OVERVIEW.md` | Motivation, research question, results summary |
| `docs/ARCHITECTURE.md` | System design, schema, instrumentation, controls |
| `docs/methodology.md` | Test procedures, statistical baselines, metrics |
| `docs/LIBRARY_COMPARISON.md` | Side-by-side comparison of SEAL, OpenFHE, HElib |
| `docs/IMPLEMENTATION_CROSSCHECK.md` | End-to-end implementation cross-check report |
