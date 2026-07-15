#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
ENV_FILE="${SCRIPT_DIR}/../.env"
PY="${SCRIPT_DIR}/hunt-lite.py"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

exec python3 "$PY" --min-score "${INCOME_AGENT_MIN_SCORE:-8}" --telegram "$@"