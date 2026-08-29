#!/usr/bin/env bash
# Shared helpers for adaptive-router shell scripts.

resolve_python() {
  # Prefer project venv when present (avoids externally-managed-environment on system Python).
  if [ -z "${PYTHON:-}" ] && [ -x "$(dirname "$0")/../.venv/bin/python" ]; then
    echo "$(cd "$(dirname "$0")/.." && pwd)/.venv/bin/python"
    return 0
  fi
  if [ -n "${PYTHON:-}" ] && command -v "$PYTHON" >/dev/null 2>&1; then
    echo "$PYTHON"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    echo python3
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    echo python
    return 0
  fi
  cat >&2 <<'EOF'
Error: Python not found.

Install Python 3.10+ and dependencies from the repo root:

  python3 -m venv .venv
  source .venv/bin/activate
  pip install -e ".[local,ml,dev]"

Or set PYTHON to your interpreter, e.g.:

  PYTHON=/opt/anaconda3/bin/python ./scripts/collect_batch2.sh 30
EOF
  return 1
}
