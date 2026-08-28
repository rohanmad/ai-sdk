#!/usr/bin/env bash
# Collect batch-2 prompts (150 new) and append to labeled_requests.csv.
# Run only when ready — each prompt needs small + large model inference (~1-2 min each).
set -euo pipefail
cd "$(dirname "$0")/.."

BATCH="${1:-30}"
MAX_TOKENS="${MAX_TOKENS:-64}"
PROMPTS="${PROMPTS:-data/sample_prompts_batch2.txt}"
OUTPUT="${OUTPUT:-data/labeled_requests.csv}"
TARGET="${TARGET:-300}"

echo "=== Batch-2 collection: ${BATCH} new prompts per batch ==="
echo "Prompts file: ${PROMPTS}"
echo "Output:       ${OUTPUT}"
echo "Target total: ${TARGET} labeled rows"
echo "Close other heavy apps. Do not run demo.py in parallel."
echo ""

while true; do
  BEFORE=$(($(wc -l < "$OUTPUT") - 1))
  [ "$BEFORE" -lt 0 ] && BEFORE=0

  python packages/complexity_classifier/collect_data.py \
    --prompts "$PROMPTS" \
    --output "$OUTPUT" \
    --max-new "$BATCH" \
    --max-tokens "$MAX_TOKENS" \
    2>&1 | tee -a data/collection_batch2.log

  AFTER=$(($(wc -l < "$OUTPUT") - 1))
  ADDED=$((AFTER - BEFORE))
  echo "Progress: ${AFTER}/${TARGET} labeled rows (+${ADDED} this batch)"

  if [ "$AFTER" -ge "$TARGET" ]; then
    echo "Done — ${TARGET} rows collected."
    break
  fi
  if [ "$ADDED" -eq 0 ]; then
    echo "No new rows — collection complete or stuck."
    break
  fi

  echo "Sleeping 5s before next batch..."
  sleep 5
done
