#!/usr/bin/env bash
set -euo pipefail

pip install -q -r requirements.txt
pip install -q -r requirements-test.txt

python -m pytest tests/ -v "$@"
