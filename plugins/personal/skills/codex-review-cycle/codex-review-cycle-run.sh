#!/usr/bin/env bash
# Usage: codex-review-cycle-run.sh <iteration_number> [extra_args...]
# Runs codex review and extracts clean output (lines after last "codex" mention).

set -euo pipefail

ITERATION="${1:?Usage: codex-review-cycle-run.sh <iteration_number> [extra_args...]}"
shift
EXTRA_ARGS="${*:-}"

OUTFILE="/tmp/codex-review-output-${ITERATION}.txt"

echo "=== Codex Review Cycle: iteration ${ITERATION}/3 ==="

codex review --uncommitted ${EXTRA_ARGS} &> "${OUTFILE}" || true

LAST_CODEX_LINE=$(grep -in 'codex' "${OUTFILE}" | tail -1 | cut -d: -f1)

if [ -z "${LAST_CODEX_LINE}" ]; then
  cat "${OUTFILE}"
else
  tail -n +"$(( LAST_CODEX_LINE + 1 ))" "${OUTFILE}"
fi
