#!/usr/bin/env bash
# Linux / macOS launcher: finds Python 3.10-3.13 and runs setup_project.py.
#   bash setup.sh            (interactive)
#   bash setup.sh --help     (options)
set -e
cd "$(dirname "$0")"
echo "Detected OS: $(uname -s) $(uname -r) $(uname -m)"
for candidate in python3.11 python3.12 python3.10 python3.13 python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,13) else 1)' 2>/dev/null; then
      if "$candidate" -c 'import venv, ensurepip' 2>/dev/null; then
        echo "Using $(command -v "$candidate") ($("$candidate" --version 2>&1))"
        exec "$candidate" setup_project.py "$@"
      else
        echo "$candidate has no venv/ensurepip module (Ubuntu/Debian: sudo apt install python3-venv)"
      fi
    fi
  fi
done
echo "ERROR: Python 3.10 - 3.13 with venv support was not found."
echo "Install Python 3.11: https://www.python.org/downloads/  (Ubuntu: sudo apt install python3.11 python3.11-venv)"
exit 1
