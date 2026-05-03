#!/usr/bin/env bash
# Render / Linux CI: smaller CPU-only PyTorch first, then app deps (faster + less RAM than default CUDA torch).
set -euo pipefail
export PIP_DEFAULT_TIMEOUT="${PIP_DEFAULT_TIMEOUT:-600}"
export PIP_DISABLE_PIP_VERSION_CHECK=1
python -m pip install --upgrade pip
pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
pip install --no-cache-dir --prefer-binary -r requirements.txt
