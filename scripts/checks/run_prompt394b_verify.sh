#!/usr/bin/env bash
set -o pipefail

cd ~/codex-local-runner || exit 1

VERIFY_DIR=/tmp/codex-local-runner-checks/current_prompt_verify
ARTIFACTS_DIR="$VERIFY_DIR/prompt392b_source_aware_artifacts"
VALID_PROMPT="$VERIFY_DIR/prompt379_valid_generated_prompt_v2.md"
RUNLOG="$VERIFY_DIR/run_prompt394b_verify.log"
FIELDS="$VERIFY_DIR/fields_prompt394b_verify.txt"
OUT_DIR="$VERIFY_DIR/out_prompt394b_verify"

mkdir -p "$VERIFY_DIR" "$OUT_DIR"
: > "$RUNLOG"
: > "$FIELDS"

echo "=== precheck ==="
git status --short
ls -ld "$ARTIFACTS_DIR" || exit 10
ls -l "$ARTIFACTS_DIR"/project_brief.json "$ARTIFACTS_DIR"/repo_facts.json "$ARTIFACTS_DIR"/roadmap.json "$ARTIFACTS_DIR"/pr_plan.json || exit 11
ls -l "$VALID_PROMPT" || exit 12
wc -c "$VALID_PROMPT"

echo
echo "=== run planned execution ==="
timeout 180s .venv/bin/python scripts/run_planned_execution.py \
  --artifacts-dir "$ARTIFACTS_DIR" \
  --out-dir "$OUT_DIR" \
  --job-id prompt394b_relaxed_observation_verify \
  --transport-mode dry-run \
  --repo-path "$PWD" \
  --prompt378-generated-prompt-path "$VALID_PROMPT" \
  --prompt379-codex-execution-requested \
  --prompt379-codex-execution-confirmed \
  --enable-prompt387-success-path-dispatch \
  --enable-prompt389-bounded-repeated-success-path-loop \
  --prompt389-max-cycles 1 \
  --json > "$RUNLOG" 2>&1

RUN_RC=$?
echo "RUN_RC=$RUN_RC"

tail -160 "$RUNLOG" || true
exit "$RUN_RC"
