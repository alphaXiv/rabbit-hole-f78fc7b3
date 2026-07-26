# Expanding Flow Maps: reduced-QM9 reproduction

This repository reproduces the few-step molecule-generation claims in [*Expanding Flow Maps* (arXiv:2607.21585)](https://arxiv.org/abs/2607.21585). We trained matched expanding and fixed-canvas discrete flows from scratch on a public QM9 subset, distilled two-step maps, and ablated learned insertion.

**Assessment: partially reproduced.** At four steps, expanding flow matched the paper’s validity advantage (observed **89.7% vs 51.8%**, paper **91.7% vs 53.6%**) but reversed its uniqueness advantage (observed **24.4% vs 97.9%**, paper **92.8% vs 63.1%**). At two steps, expanding distillation had worse FCD than fixed canvas (**14.89 vs 11.95**, paper **0.40 vs 0.49**), and disabling insertion improved rather than degraded FCD (**10.64**).

![Headline validity and uniqueness result](reports/qm9-reproduction/images/headline_steps.png)

- [Detailed illustrated report](reports/qm9-reproduction/report.md)
- [Self-contained tutorial notebook](notebooks/qm9_reproduction.py)
- [Machine-readable measurements](results/qm9_results.csv)

[![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/alphaXiv/rabbit-hole-f78fc7b3/blob/main/notebooks/qm9_reproduction.py)

Molab direct URL: https://molab.marimo.io/github/alphaXiv/rabbit-hole-f78fc7b3/blob/main/notebooks/qm9_reproduction.py

## Scope and substitutions

The named benchmark and outcomes were retained: public QM9, RDKit validity and uniqueness, and public ChemNet FCD. The bounded campaign uses a fixed 20K/2K/2K split, a six-layer graph transformer, 30K teacher updates, 10K distillation updates, two seeds, and 10,000 samples per condition. The paper uses 100K training molecules, nine layers, and two million updates; no author implementation was available, so loss weighting and time reparameterization are documented substitutions.

All formal evidence ran on **Kubernetes** using **NVIDIA RTX PRO 6000 Blackwell** GPUs, with a peak of **16 concurrently allocated GPUs**. Actual fresh-campaign elapsed wall time was **1.178 hours** from the first formal launch at 04:12:18 UTC to the last terminal run at 05:22:59 UTC; each row below used four GPUs for roughly 8.8–12.1 minutes.

## Experiment log

The command column is copied verbatim from `orx exp status`. Raw run identifiers and detailed notes remain in the OpenResearch experiment descriptions.

| Branch / experiment | Purpose or change | Exact run command | Assessment / outcome | Compute |
|---|---|---|---|---|
| `main` | Reader-facing publication surface | Not run as an experiment (publication surface) | Report, notebook, data, and implementation | — |
| [EFlow ChemNet, seed 0](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/eflow-chemnet-recovery-seed-0) | Learned insertion, 4/10-step evaluation | `bash scripts/run.sh` | validity 90.8/87.3%; FCD 11.68/9.18 | 4 GPUs, 9.0 min |
| [EFlow ChemNet, seed 1](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/eflow-chemnet-recovery-seed-1) | Seed robustness | `bash scripts/run.sh` | validity 88.6/85.8%; FCD 10.94/8.93 | 4 GPUs, 8.8 min |
| [Fixed ChemNet, seed 0](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/fixed-canvas-chemnet-recovery-seed-0) | Matched fixed-canvas control | `bash scripts/run.sh` | validity 57.8/68.4%; FCD 2.59/2.31 | 4 GPUs, 8.9 min |
| [Fixed ChemNet, seed 1](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/fixed-canvas-chemnet-recovery-seed-1) | Seed robustness | `bash scripts/run.sh` | validity 45.8/55.6%; FCD 2.29/1.78 | 4 GPUs, 8.8 min |
| [Two-step EFM, seed 0](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/distilled-two-step-efm-seed-0) | Teacher plus two-time student distillation | `bash scripts/run.sh` | validity 91.0%; FCD 16.17 | 4 GPUs, 12.0 min |
| [Two-step EFM, seed 1](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/distilled-two-step-efm-seed-1) | Seed robustness | `bash scripts/run.sh` | validity 93.0%; FCD 13.61 | 4 GPUs, 12.1 min |
| [Two-step fixed, seed 0](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/distilled-two-step-fixed-map-seed-0) | Compute-matched fixed map | `bash scripts/run.sh` | validity 84.5%; FCD 12.68 | 4 GPUs, 11.8 min |
| [Two-step fixed, seed 1](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/distilled-two-step-fixed-map-seed-1) | Seed robustness | `bash scripts/run.sh` | validity 71.9%; FCD 11.23 | 4 GPUs, 12.0 min |
| [No-insertion, seed 0](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/distilled-two-step-insertion-disabled-ablation) | Disable learned insertion | `bash scripts/run.sh` | FCD improved to 11.47 | 4 GPUs, 12.0 min |
| [No-insertion, seed 1](https://github.com/alphaXiv/rabbit-hole-f78fc7b3/tree/orx/distilled-two-step-insertion-disabled-ablation-s) | Mechanism robustness | `bash scripts/run.sh` | FCD improved to 9.81 | 4 GPUs, 11.9 min |

## Reproduce the implementation

The formal runs use the committed [Kubernetes manifest](.orx/k8s.yaml) and one entrypoint:

```bash
orx exp run <experiment-id> --backend k8s
```

`scripts/run.sh` installs the pinned Python dependencies in an ephemeral CUDA 13 container and launches distributed training. `configs/experiment.json` selects expanding, fixed, distilled, or insertion-disabled behavior. The tutorial notebook already embeds every formal result; opening it does not rerun expensive training.

To inspect the notebook locally:

```bash
uvx marimo edit notebooks/qm9_reproduction.py
uvx marimo run notebooks/qm9_reproduction.py
```
