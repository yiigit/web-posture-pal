#!/usr/bin/env bash
# Initialize an existing native MySQL server; no Docker required.
set -euo pipefail
set +x
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if [[ ! -f backend/posturepal/commands/init_database.py ]]; then
    echo 'Incomplete deployment: backend/posturepal/commands/init_database.py is missing.' >&2
    echo 'Deploy the complete backend and scripts from the same revision, then retry.' >&2
    exit 1
fi
python_bin="${POSTUREPAL_PYTHON:-.venv/bin/python}"
if [[ ! -x "$python_bin" ]]; then
    echo 'Create .venv and install requirements.txt first (see README).' >&2
    exit 1
fi
export PYTHONPATH="$PWD/backend${PYTHONPATH:+:$PYTHONPATH}"
exec "$python_bin" -m posturepal.commands.init_database --env-file "$PWD/.env" --create-database "$@"
