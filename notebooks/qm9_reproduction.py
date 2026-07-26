# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "altair>=5.5.0",
#     "marimo>=0.18.0",
#     "pandas>=2.2.0",
# ]
# ///

import marimo

__generated_with = "0.23.15"
app = marimo.App(width="medium")


@app.cell
def _():
    import altair as alt
    import marimo as mo
    import pandas as pd

    return alt, mo, pd


@app.cell
def _(pd):
    # Embedded formal evidence: Molab does not need repository-relative files.
    records = [
        ("multi_step", "Expanding", 0, 4, 0.9082, 0.22340894, 11.67912986, 0.9956),
        ("multi_step", "Expanding", 0, 10, 0.8726, 0.32867293, 9.18227433, 0.9874),
        ("multi_step", "Expanding", 1, 4, 0.8857, 0.26487524, 10.93667093, 0.9933),
        ("multi_step", "Expanding", 1, 10, 0.8577, 0.38440014, 8.93412396, 0.9914),
        ("multi_step", "Fixed canvas", 0, 4, 0.5780, 0.97283737, 2.59483867, 0.8382),
        ("multi_step", "Fixed canvas", 0, 10, 0.6841, 0.97295717, 2.30671058, 0.8515),
        ("multi_step", "Fixed canvas", 1, 4, 0.4578, 0.98470948, 2.28778478, 0.7644),
        ("multi_step", "Fixed canvas", 1, 10, 0.5563, 0.98472047, 1.78443251, 0.7682),
        ("few_step", "Learned insertion", 0, 2, 0.9101, 0.10394462, 16.16540782, 1.0),
        ("few_step", "Learned insertion", 1, 2, 0.9302, 0.16910342, 13.60588867, 1.0),
        ("few_step", "Fixed canvas", 0, 2, 0.8452, 0.22539044, 12.67774020, 0.9522),
        ("few_step", "Fixed canvas", 1, 2, 0.7186, 0.29724464, 11.22880326, 0.8419),
        ("few_step", "Insertion disabled", 0, 2, 0.8451, 0.27192048, 11.46680516, 1.0),
        ("few_step", "Insertion disabled", 1, 2, 0.8936, 0.42658908, 9.81241427, 1.0),
    ]
    results = pd.DataFrame(
        records,
        columns=[
            "claim",
            "method",
            "seed",
            "steps",
            "validity",
            "uniqueness",
            "fcd",
            "nine_atom_fraction",
        ],
    )
    return (results,)


@app.cell
def _(alt, mo, results):
    headline_data = results[results["claim"] == "multi_step"].melt(
        id_vars=["method", "seed", "steps"],
        value_vars=["validity", "uniqueness"],
        var_name="metric",
        value_name="score",
    )
    headline = (
        alt.Chart(headline_data)
        .mark_line(point=True)
        .encode(
            x=alt.X("steps:O", title="Sampling steps"),
            y=alt.Y("mean(score):Q", title="Mean fraction", scale=alt.Scale(domain=[0, 1])),
            color=alt.Color(
                "method:N",
                scale=alt.Scale(
                    domain=["Expanding", "Fixed canvas"],
                    range=["#13a085", "#64748b"],
                ),
            ),
            column=alt.Column("metric:N", title=None),
            tooltip=[
                "method:N",
                "metric:N",
                alt.Tooltip("mean(score):Q", format=".3f"),
            ],
        )
        .properties(width=280, height=260)
    )
    mo.vstack(
        [
            mo.md(
                """
                # Expanding Flow Maps on reduced QM9

                Molecules have different numbers of atoms. This notebook tests whether
                learning when to add atom positions helps a generator remain useful when
                it has only a few updates.

                **Verdict: partially reproduced.** Expansion preserved validity at four
                and ten steps, but uniqueness and ChemNet FCD moved strongly in the
                opposite direction. The chart below is the central result; hover for
                exact two-seed means.
                """
            ),
            headline,
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## Experimental recipe

    We used the public QM9 CSV with a deterministic 20K/2K/2K split and at most
    nine C/N/O/F atoms. Both methods share a six-layer, width-256 graph transformer,
    30,000 training steps, global batch 512, and 10,000 generated molecules per
    condition. The expanding version adds per-node local times and a learned
    Poisson insertion head. Two-step models receive 10,000 additional
    consistency-distillation steps.

    This independently written implementation is smaller than the paper's 100K
    experiment. No author implementation was public, so architecture, interpolation
    loss weights, and distillation are explicit substitutions.
    """)
    return


@app.cell
def _(mo):
    budget = mo.ui.dropdown(options=[4, 10], value=4, label="Sampling-step budget")
    metric = mo.ui.dropdown(
        options=["validity", "uniqueness", "fcd"],
        value="validity",
        label="Metric",
    )
    mo.hstack([budget, metric], justify="start")
    return budget, metric


@app.cell
def _(alt, budget, metric, mo, results):
    selected = results[
        (results["claim"] == "multi_step") & (results["steps"] == budget.value)
    ]
    metric_name = metric.value
    interactive = (
        alt.Chart(selected)
        .mark_bar()
        .encode(
            x=alt.X("method:N", title=None),
            y=alt.Y(f"mean({metric_name}):Q", title=metric_name.title()),
            color=alt.Color(
                "method:N",
                legend=None,
                scale=alt.Scale(
                    domain=["Expanding", "Fixed canvas"],
                    range=["#13a085", "#64748b"],
                ),
            ),
            tooltip=[
                "method:N",
                alt.Tooltip(f"mean({metric_name}):Q", format=".4f"),
                alt.Tooltip(f"min({metric_name}):Q", title="Seed minimum", format=".4f"),
                alt.Tooltip(f"max({metric_name}):Q", title="Seed maximum", format=".4f"),
            ],
        )
        .properties(width=520, height=270, title=f"{budget.value}-step comparison")
    )
    note = (
        "Lower is better for FCD."
        if metric_name == "fcd"
        else "Higher is better for this metric."
    )
    mo.vstack([mo.md(f"## Explore the multistep result\n\n{note}"), interactive])
    return


@app.cell
def _(alt, mo, results):
    two_step = results[results["claim"] == "few_step"].melt(
        id_vars=["method", "seed"],
        value_vars=["validity", "uniqueness", "fcd"],
        var_name="metric",
        value_name="value",
    )
    chart = (
        alt.Chart(two_step)
        .mark_bar()
        .encode(
            x=alt.X("method:N", title=None, sort=["Learned insertion", "Fixed canvas", "Insertion disabled"]),
            y=alt.Y("mean(value):Q", title="Two-seed mean"),
            color=alt.Color(
                "method:N",
                legend=None,
                scale=alt.Scale(
                    domain=["Learned insertion", "Fixed canvas", "Insertion disabled"],
                    range=["#13a085", "#64748b", "#e8792e"],
                ),
            ),
            column=alt.Column("metric:N", title=None),
            tooltip=["method:N", "metric:N", alt.Tooltip("mean(value):Q", format=".4f")],
        )
        .properties(width=190, height=250)
    )
    mo.vstack(
        [
            mo.md(
                """
                ## Two-step distillation and the insertion mechanism

                The learned-insertion student reaches **92.0% validity**, but only
                **13.7% uniqueness** and **14.89 FCD**. Fixed canvas reaches 78.2%,
                26.1%, and 11.95. Disabling insertion lowers validity to 86.9%, while
                improving uniqueness to 34.9% and FCD to 10.64. This is opposite the
                proposed insertion-driven FCD advantage.
                """
            ),
            chart,
        ]
    )
    return


@app.cell
def _(alt, mo, results):
    count_data = (
        results.groupby("method", as_index=False)["nine_atom_fraction"]
        .mean()
        .sort_values("nine_atom_fraction")
    )
    count_chart = (
        alt.Chart(count_data)
        .mark_bar()
        .encode(
            x=alt.X(
                "nine_atom_fraction:Q",
                title="Fraction decoded with 9 heavy atoms",
                scale=alt.Scale(domain=[0, 1]),
            ),
            y=alt.Y("method:N", title=None),
            color=alt.Color("method:N", legend=None),
            tooltip=["method:N", alt.Tooltip("nine_atom_fraction:Q", format=".1%")],
        )
        .properties(width=520, height=230)
    )
    mo.vstack(
        [
            mo.md(
                """
                ## Diagnostic and conclusion

                The expanding decoder places essentially every sample at the nine-atom
                maximum. That count collapse explains why valid molecules can still be
                repetitive and far from the QM9 distribution.

                The bounded study therefore supports the paper's **low-step validity**
                mechanism, but not its uniqueness or FCD claims. A fuller reproduction
                should first calibrate the count process, then scale to the paper's 100K
                split and exact training recipe.

                **Compute:** OpenResearch Kubernetes; four NVIDIA RTX PRO 6000 Blackwell
                GPUs per run; 16 GPUs peak; 1.178 hours actual campaign wall time.
                """
            ),
            count_chart,
        ]
    )
    return


if __name__ == "__main__":
    app.run()
