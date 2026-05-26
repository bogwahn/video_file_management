#!/bin/bash
# Quick Action wrapper for remux.

set -euo pipefail

# Use a deterministic PATH for Finder/Automator-launched shells.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PYTHON="${REPO_DIR}/.venv/bin/python"

if [ -x "${VENV_PYTHON}" ]; then
	PYTHON_BIN="${VENV_PYTHON}"
elif command -v python3 >/dev/null 2>&1; then
	PYTHON_BIN="$(command -v python3)"
else
	PYTHON_BIN="python3"
fi

export PYTHONPATH="${REPO_DIR}/src:${PYTHONPATH:-}"

exec "${PYTHON_BIN}" -m video_file_management.remux.remux_quickaction "$@"
