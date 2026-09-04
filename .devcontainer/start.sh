#!/usr/bin/env bash
set -e

cd /workspaces/* || exit 1
pip install -r requirements.txt
python app.py --host 0.0.0.0 --port 8765 --live
