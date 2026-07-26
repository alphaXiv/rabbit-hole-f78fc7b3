"""Render the four evidence figures used by the public reproduction report."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = pd.read_csv(ROOT / "results" / "qm9_results.csv")
OUT = ROOT / "reports" / "qm9-reproduction" / "images"
OUT.mkdir(parents=True, exist_ok=True)

COLORS = {
    "eflow": "#13a085",
    "fixed": "#64748b",
    "distilled_efm": "#13a085",
    "distilled_fixed": "#64748b",
    "distilled_insertion_disabled": "#e8792e",
}

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "bold",
        "axes.facecolor": "#fbfcfd",
        "figure.facecolor": "white",
        "grid.color": "#dbe3ea",
        "grid.linewidth": 0.7,
    }
)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=180, bbox_inches="tight")
    plt.close(fig)


# Figure 1: central low-step validity / uniqueness result with both seeds visible.
multi = DATA[DATA.claim == "multi_step"]
fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.7), sharex=True)
for ax, metric, title in zip(
    axes,
    ["validity", "uniqueness"],
    ["Validity: expanding wins", "Uniqueness: fixed canvas wins"],
):
    for method, label in [("eflow", "Expanding"), ("fixed", "Fixed canvas")]:
        part = multi[multi.method == method]
        for _, seed in part.groupby("seed"):
            ax.plot(seed.steps, 100 * seed[metric], color=COLORS[method], alpha=0.25)
            ax.scatter(seed.steps, 100 * seed[metric], color=COLORS[method], alpha=0.55, s=28)
        mean = part.groupby("steps")[metric].mean()
        ax.plot(mean.index, 100 * mean.values, "-o", lw=3, ms=7, color=COLORS[method], label=label)
    ax.set_title(title)
    ax.set_xlabel("Sampling steps")
    ax.set_ylabel(f"{metric.title()} (%)")
    ax.set_xticks([4, 10])
    ax.grid(axis="y")
axes[0].legend(frameon=False)
fig.suptitle("Matched reduced-QM9 models, 10,000 samples per seed", fontweight="bold")
save(fig, "headline_steps.png")


# Figure 2: ChemNet distance at the same step budgets; lower is better.
fig, ax = plt.subplots(figsize=(6.8, 3.8))
x = np.arange(2)
width = 0.34
for offset, (method, label) in zip(
    [-width / 2, width / 2],
    [("eflow", "Expanding"), ("fixed", "Fixed canvas")],
):
    part = multi[multi.method == method]
    means = part.groupby("steps").fcd.mean().reindex([4, 10])
    std = part.groupby("steps").fcd.std().reindex([4, 10]).fillna(0)
    ax.bar(x + offset, means, width, yerr=std, capsize=4, color=COLORS[method], label=label)
ax.set_xticks(x, ["4 steps", "10 steps"])
ax.set_ylabel("FCD (lower is better)")
ax.set_title("Expanding outputs are valid but far from QM9 in ChemNet space")
ax.grid(axis="y")
ax.legend(frameon=False)
save(fig, "fcd_steps.png")


# Figure 3: two-step distillation and mechanism ablation.
few = DATA[DATA.claim == "few_step"]
order = ["distilled_efm", "distilled_fixed", "distilled_insertion_disabled"]
labels = ["Learned insertion", "Fixed canvas", "Insertion disabled"]
means = few.groupby("method")[["validity", "uniqueness", "fcd"]].mean()
fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.7))
for ax, metric, title, scale in zip(
    axes,
    ["validity", "uniqueness", "fcd"],
    ["Validity", "Uniqueness", "FCD ↓"],
    [100, 100, 1],
):
    vals = [means.loc[m, metric] * scale for m in order]
    ax.bar(range(3), vals, color=[COLORS[m] for m in order])
    ax.set_xticks(range(3), labels, rotation=20, ha="right")
    ax.set_title(title)
    ax.grid(axis="y")
    for i, v in enumerate(vals):
        ax.text(i, v, f"{v:.1f}", ha="center", va="bottom", fontsize=9)
axes[0].set_ylabel("Percent")
axes[1].set_ylabel("Percent")
fig.suptitle("Two-step result: insertion raises validity, not distributional quality", fontweight="bold")
save(fig, "two_step_mechanism.png")


# Figure 4: decoded size diagnostic.
fig, ax = plt.subplots(figsize=(7.5, 3.9))
diagnostic = (
    DATA.groupby("method").node_count_9_fraction.mean().reindex(order + ["eflow", "fixed"])
)
diagnostic_labels = [
    "2-step EFM",
    "2-step fixed",
    "2-step no insertion",
    "4/10-step EFlow",
    "4/10-step fixed",
]
bars = ax.barh(
    range(len(diagnostic)),
    100 * diagnostic.values,
    color=[COLORS[m] for m in order + ["eflow", "fixed"]],
)
ax.set_yticks(range(len(diagnostic)), diagnostic_labels)
ax.set_xlabel("Samples decoded with 9 heavy atoms (%)")
ax.set_xlim(0, 104)
ax.set_title("The learned count decoder collapses near the maximum size")
ax.grid(axis="x")
for bar, v in zip(bars, 100 * diagnostic.values):
    ax.text(v + 0.7, bar.get_y() + bar.get_height() / 2, f"{v:.1f}%", va="center")
save(fig, "node_count_diagnostic.png")
