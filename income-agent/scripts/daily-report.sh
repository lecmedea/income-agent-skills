#!/usr/bin/env bash
# Quick helper: show leads journal tail and remind operator of pending actions.
set -euo pipefail
JOURNAL="${HOME}/.grok/skills/income-agent/references/leads-journal.md"
echo "=== Income Agent — $(date '+%d.%m.%Y %H:%M') ==="
echo ""
if [[ -f "$JOURNAL" ]]; then
  echo "--- Leads journal (last 15 lines) ---"
  tail -n 15 "$JOURNAL"
else
  echo "Journal not found: $JOURNAL"
fi
echo ""
echo "Run hunt: ask Grok «/income-agent hunt» or «найди заказы»"