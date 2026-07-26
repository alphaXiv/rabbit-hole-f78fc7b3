#!/usr/bin/env bash
set -euo pipefail

python -m pip install --quiet --no-cache-dir --break-system-packages -r requirements.txt

export OMP_NUM_THREADS=4
export PYTHONUNBUFFERED=1

torchrun --standalone --nproc_per_node=4 src/run_experiment.py --config configs/experiment.json
