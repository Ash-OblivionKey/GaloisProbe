#!/usr/bin/env python3
"""
Generate 3 publication-ready figures from experiment results.

Fig 1: Main results (2×3 grid: collision, rank, regression, bias, covariance)
Fig 2: Bias per prime (low-bit mean, kurtosis across RNS primes)
Fig 3: Control validation (distinguishers detect structure when present)

Reads: output/csv/results.csv, output/results/distinguisher_*.json
Output: output/figures/fig1_main.png, fig2_bias.png, fig3_controls.png

Usage: python scripts/plot_results.py [--csv-dir] [--output-dir]
"""

import argparse
import csv
import json
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
CSV_DIR = PROJ / "output" / "csv"
RESULTS_DIR = PROJ / "output" / "results"
FIGURES_DIR = PROJ / "output" / "figures"

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    print("Error: matplotlib required. Run: pip install matplotlib")
    sys.exit(1)

# Publication style: clean, readable, no overlap
plt.rcParams.update({
    "font.size": 10,
    "axes.labelsize": 10,
    "axes.titlesize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "font.family": "sans-serif",
})

# Library colors (colorblind-friendly)
LIB_COLORS = {"seal": "#0173b2", "openfhe": "#de8f05", "helib": "#029e73"}


def load_results_csv(csv_dir: Path) -> list:
    path = csv_dir / "results.csv"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_bias_per_prime(results_dir: Path) -> list:
    """Load per-prime bias data from JSON for Fig 2."""
    rows = []
    for f in results_dir.glob("distinguisher_bias_*.json"):
        run_id = f.stem.replace("distinguisher_bias_", "")
        with open(f) as fp:
            d = json.load(fp)
        lib = run_id.split("_")[0] if "_" in run_id else run_id
        for prime_idx, v in d.get("per_prime", {}).items():
            rows.append({
                "run_id": run_id,
                "library": lib,
                "prime_index": int(prime_idx),
                "low_bit_mean": float(v.get("low_bit_mean", 0.5)),
                "kurtosis": float(v.get("kurtosis", -1.2)),
            })
    return rows


def _bar_or_marker(ax, x, vals, colors, w=0.6):
    """Draw bars; for zero values use a visible marker instead of invisible bar."""
    ymax = max(max(vals) * 1.2 if max(vals) > 0 else 0.5, 0.15)
    for i, (xi, v) in enumerate(zip(x, vals)):
        c = colors[i] if i < len(colors) else "#333333"
        if v == 0:
            ax.plot(xi, 0, "o", color=c, markersize=10, zorder=3)
            ax.text(xi, 0.03 * ymax, "0", ha="center", va="bottom", fontsize=9, color=c)
        else:
            ax.bar(xi, v, w, color=c, edgecolor="none", zorder=2)


def _parse_cov(val):
    """Parse cov_frobenius from CSV (may be scientific notation)."""
    if not val or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def fig1_main_results(csv_dir: Path, out_dir: Path):
    """2×3 grid: collision, rank, regression, bias, covariance across libraries."""
    rows = load_results_csv(csv_dir)
    if not rows:
        print("  (fig1_main.png skipped: no data)")
        return
    main = [r for r in rows if r["run_id"] in ("seal_run_001", "seal_run_stress_001", "openfhe_run_001", "helib_run_001")]
    if not main:
        main = rows[:6]
    def _label(run_id):
        if run_id == "seal_run_001": return "SEAL"
        if run_id == "seal_run_stress_001": return "SEAL (stress)"
        if run_id == "openfhe_run_001": return "OpenFHE"
        if run_id == "helib_run_001": return "HElib"
        return run_id.replace("_run_001", "").replace("_", " ").title()
    labels = [_label(r["run_id"]) for r in main]
    colors = [LIB_COLORS.get(r["library"].lower(), "#333333") for r in main]
    x = np.arange(len(main))
    w = 0.55

    fig, axes = plt.subplots(2, 3, figsize=(11, 6), constrained_layout=True)

    ax = axes[0, 0]
    vals = [int(r.get("collision_count", 0) or 0) for r in main]
    _bar_or_marker(ax, x, vals, colors, w)
    ax.axhline(0, color="#888", linestyle="-", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9, rotation=15, ha="right")
    ax.set_ylabel("Collisions")
    ax.set_title("(a) Collision (expect 0)")
    ax.set_ylim(-0.05, max(max(vals) * 1.2 if max(vals) > 0 else 0.5, 0.15))

    ax = axes[0, 1]
    vals = [int(r.get("rank_deficit", 0) or 0) for r in main]
    _bar_or_marker(ax, x, vals, colors, w)
    ax.axhline(0, color="#888", linestyle="-", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9, rotation=15, ha="right")
    ax.set_ylabel("Rank deficit")
    ax.set_title("(b) Rank (expect 0)")
    ax.set_ylim(-0.05, max(max(vals) * 1.2 if max(vals) > 0 else 0.5, 0.15))

    ax = axes[0, 2]
    vals = [float(r.get("r2_mean", 0) or 0) for r in main]
    # Use marker for zero values (e.g. HElib) so bar at y=0 is visible against dashed reference line
    ymax = max(max(vals) * 1.2 if max(vals) > 0 else 0.5, 0.15)
    ymin = min(min(vals) * 1.2 if min(vals) < 0 else -0.8, -0.05)
    for i, (xi, v) in enumerate(zip(x, vals)):
        c = colors[i] if i < len(colors) else "#333333"
        if v == 0:
            ax.plot(xi, 0, "o", color=c, markersize=10, zorder=3)
            ax.text(xi, 0.03 * (ymax - ymin) + ymin, "0", ha="center", va="bottom", fontsize=9, color=c)
        else:
            ax.bar(xi, v, w, color=c, edgecolor="none", zorder=2)
    ax.axhline(0, color="#888", linestyle="--", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9, rotation=15, ha="right")
    ax.set_ylabel("R² mean")
    ax.set_title("(c) Regression (expect ≤ 0)")
    ax.set_ylim(ymin, ymax)

    ax = axes[1, 0]
    vals = [float(r.get("low_bit_mean", 0.5) or 0.5) for r in main]
    ax.bar(x, vals, w, color=colors, edgecolor="none")
    ax.axhline(0.5, color="#888", linestyle="--", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9, rotation=15, ha="right")
    ax.set_ylabel("Low-bit mean")
    ax.set_title("(d) Bias (expect 0.5)")
    ax.set_ylim(0.45, 0.55)

    ax = axes[1, 1]
    cov_vals = [_parse_cov(r.get("cov_frobenius", "")) for r in main]
    valid = [(i, v) for i, v in enumerate(cov_vals) if v is not None and v > 0]
    if valid:
        idx, vals = zip(*valid)
        x_cov = np.array([x[i] for i in idx])
        colors_cov = [colors[i] for i in idx]
        log_vals = np.log10(np.array(vals))
        bars = ax.bar(x_cov, log_vals, w, color=colors_cov, edgecolor="none")
        ax.set_ylabel("log₁₀(cov Frobenius)")
        ax.set_title("(e) Covariance")
    else:
        ax.text(0.5, 0.5, "No covariance data", ha="center", va="center", fontsize=9, color="#666", transform=ax.transAxes)
        ax.set_title("(e) Covariance")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9, rotation=15, ha="right")

    ax = axes[1, 2]
    ax.axis("off")

    fig.savefig(out_dir / "fig1_main.png", dpi=300, bbox_inches="tight", pad_inches=0.15)
    plt.close()
    print("  fig1_main.png")


def _aggregate_bias_by_prime(rows: list) -> dict:
    """Aggregate per-prime bias across runs: (lib, prime_idx) -> {mean, std}."""
    from collections import defaultdict
    agg = defaultdict(lambda: defaultdict(list))
    main_run_suffixes = ("_run_001", "_run_002", "_run_003")
    for r in rows:
        run_id = r.get("run_id", "")
        if "control" in run_id.lower() or "stress" in run_id or "std" in run_id:
            continue
        if not any(run_id.endswith(s) for s in main_run_suffixes):
            continue
        key = (r["library"], r["prime_index"])
        agg[key]["low_bit_mean"].append(r["low_bit_mean"])
        agg[key]["kurtosis"].append(r["kurtosis"])
    out = {}
    for (lib, prime_idx), v in agg.items():
        lb = v["low_bit_mean"]
        kt = v["kurtosis"]
        out[(lib, prime_idx)] = {
            "low_bit_mean": (float(np.mean(lb)), float(np.std(lb)) if len(lb) > 1 else 0.0),
            "kurtosis": (float(np.mean(kt)), float(np.std(kt)) if len(kt) > 1 else 0.0),
        }
    return out


def fig2_bias_per_prime(results_dir: Path, out_dir: Path):
    """Bias metrics per RNS prime, per library. Uses mean ± std across runs when multiple runs exist."""
    rows = load_bias_per_prime(results_dir)
    if not rows:
        print("  (fig2_bias.png skipped: no per-prime data)")
        return
    agg = _aggregate_bias_by_prime(rows)
    libs = ["seal", "openfhe", "helib"]
    data = {}
    for lib in libs:
        primes = sorted(set(p for (l, p) in agg if l == lib))
        if primes:
            data[lib] = [(p, agg[(lib, p)]) for p in primes]
    data = {k: v for k, v in data.items() if v}
    if not data:
        return

    fig, axes = plt.subplots(1, 2, figsize=(8, 4), constrained_layout=True)

    markers = {"seal": "o", "openfhe": "s", "helib": "^"}
    for ax_idx, (metric, ylabel, expected, ylim) in enumerate([
        ("low_bit_mean", "Low-bit mean", 0.5, (0.45, 0.55)),
        ("kurtosis", "Kurtosis", -1.2, (-1.3, -1.1)),
    ]):
        ax = axes[ax_idx]
        for lib in data:
            primes = [p for p, _ in data[lib]]
            means = [agg[(lib, p)][metric][0] for p in primes]
            stds = [agg[(lib, p)][metric][1] for p in primes]
            ax.errorbar(primes, means, yerr=stds if any(s > 0 for s in stds) else None,
                       fmt="-", marker=markers.get(lib, "o"), markersize=6,
                       label=lib.capitalize(), color=LIB_COLORS.get(lib, "#333333"),
                       linewidth=1.5, capsize=3)
        ax.axhline(expected, color="#888", linestyle="--", linewidth=0.8)
        ax.set_xlabel("Prime index")
        ax.set_ylabel(ylabel)
        ax.set_title(f"({'a' if ax_idx == 0 else 'b'}) {ylabel} (expect {expected})")
        ax.set_ylim(ylim)
        ax.legend(frameon=True, fontsize=8, loc="upper right", framealpha=0.95)

    fig.savefig(out_dir / "fig2_bias.png", dpi=300, bbox_inches="tight", pad_inches=0.15)
    plt.close()
    print("  fig2_bias.png")


def fig3_control_validation(csv_dir: Path, out_dir: Path):
    """Control experiments: distinguishers detect structure when present.
    Always produces fig3_controls.png; if no control data, shows a placeholder."""
    rows = load_results_csv(csv_dir)
    controls = [r for r in rows if "control" in r["run_id"].lower()]
    pos = next((r for r in controls if "positive" in r["run_id"].lower()), None)
    scaled = next((r for r in controls if "scaled" in r["run_id"].lower()), None)
    fresh = next((r for r in controls if "fresh" in r["run_id"].lower()), None)

    fig, axes = plt.subplots(1, 2, figsize=(7, 3.5), constrained_layout=True)

    # Collision: positive vs fresh
    ax = axes[0]
    names, vals = [], []
    if pos:
        names.append("Positive\n(duplicate)")
        vals.append(int(pos.get("collision_count", 0) or 0))
    if fresh:
        names.append("Fresh\n(independent)")
        vals.append(int(fresh.get("collision_count", 0) or 0))
    if names:
        x = np.arange(len(names))
        colors = ["#de8f05" if v > 0 else "#029e73" for v in vals]  # orange=detected, green=clean
        y_top = max(max(vals) * 1.15, 0.2)
        for i, (xi, v) in enumerate(zip(x, vals)):
            if v == 0:
                ax.plot(xi, 0, "o", color=colors[i], markersize=12, zorder=3)
                ax.text(xi, 0.06 * y_top, "0", ha="center", va="bottom", fontsize=10, fontweight="bold")
            else:
                ax.bar(xi, v, 0.5, color=colors[i], edgecolor="none")
        ax.axhline(0, color="#888", linestyle="-", linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(names, fontsize=9, ha="center")
        ax.set_ylabel("Collisions")
        ax.set_title("(a) Collision: structure detected")
        ax.set_ylim(-0.02, y_top)
    else:
        ax.text(0.5, 0.5, "No control data available.\n\nRun without --no-controls and ensure\ncontrol dumps exist (control_fresh_*,\ncontrol_positive_*, control_scaled_*).", ha="center", va="center", fontsize=9, color="#666", transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title("(a) Collision: structure detected")
        ax.set_ylim(0, 1)

    # Rank: scaled vs fresh
    ax = axes[1]
    names, vals = [], []
    if scaled:
        names.append("Scaled\n(linear dep.)")
        vals.append(int(scaled.get("rank_deficit", 0) or 0))
    if fresh:
        names.append("Fresh")
        vals.append(int(fresh.get("rank_deficit", 0) or 0))
    if names:
        x = np.arange(len(names))
        colors = ["#de8f05" if v > 0 else "#029e73" for v in vals]
        y_top = max(max(vals) * 1.15, 0.2)
        for i, (xi, v) in enumerate(zip(x, vals)):
            if v == 0:
                ax.plot(xi, 0, "o", color=colors[i], markersize=12, zorder=3)
                ax.text(xi, 0.06 * y_top, "0", ha="center", va="bottom", fontsize=10, fontweight="bold")
            else:
                ax.bar(xi, v, 0.5, color=colors[i], edgecolor="none")
        ax.axhline(0, color="#888", linestyle="-", linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(names, fontsize=9, ha="center")
        ax.set_ylabel("Rank deficit")
        ax.set_title("(b) Rank: structure detected")
        ax.set_ylim(-0.02, y_top)
    else:
        ax.text(0.5, 0.5, "No control data available.\n\nSee scripts/control_fresh_keys.*,\ncontrol_reuse_dump.py,\ncontrol_scaled_dump.py.", ha="center", va="center", fontsize=9, color="#666", transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title("(b) Rank: structure detected")
        ax.set_ylim(0, 1)

    fig.savefig(out_dir / "fig3_controls.png", dpi=300, bbox_inches="tight", pad_inches=0.15)
    plt.close()
    if controls:
        print("  fig3_controls.png")
    else:
        print("  fig3_controls.png (placeholder: no control dumps)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-dir", type=Path, default=CSV_DIR)
    ap.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    ap.add_argument("--output-dir", "-o", type=Path, default=FIGURES_DIR)
    args = ap.parse_args()

    csv_dir = args.csv_dir
    results_dir = args.results_dir
    out_dir = args.output_dir

    if not csv_dir.exists():
        print("Error: Run export_experiment_results.py first.")
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    print("Generating figures...")

    fig1_main_results(csv_dir, out_dir)
    fig2_bias_per_prime(results_dir, out_dir)
    fig3_control_validation(csv_dir, out_dir)

    print("Done. output/figures/fig1_main.png, fig2_bias.png, fig3_controls.png")


if __name__ == "__main__":
    main()
