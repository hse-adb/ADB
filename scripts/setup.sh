#!/usr/bin/env bash
set -e

python3 -m pip install -r static_requirements.txt
python3 -m playwright install chromium
