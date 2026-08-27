#!/usr/bin/env bash
# Memory-safe data collection for laptops. Run batches; resumes automatically.
set -euo pipefail
cd "$(dirname "$0")/.."

BATCH="${1:-30}"
MAX_TOKENS="${MAX_TOKENS:-64}"

echo "=== Batch collection: ${BATCH} new prompts per batch ==="
echo "Close other heavy apps. Do not run demo.py in parallel."
echo ""

while true; do
  BEFORE=$(($(wc -l < data/labeled_requests.csv) - 1))
  [ "$BEFORE" -lt 0 ] && BEFORE=0

  python packages/complexity_classifier/collect_data.py \
    --max-new "$BATCH" \
    --max-tokens "$MAX_TOKENS" \
    2>&1 | tee -a data/collection.log

  AFTER=$(($(wc -l < data/labeled_requests.csv) - 1))
  ADDED=$((AFTER - BEFORE))
  echo "Progress: ${AFTER}/150 labeled rows (+${ADDED} this batch)"

  if [ "$AFTER" -ge 150 ]; then
    echo "Done — 150 rows collected."
    break
  fi
  if [ "$ADDED" -eq 0 ]; then
    echo "No new rows — collection complete or stuck."
    break
  fi

  echo "Sleeping 5s before next batch..."
  sleep 5
done
