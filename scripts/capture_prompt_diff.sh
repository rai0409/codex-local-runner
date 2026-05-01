#!/usr/bin/env bash
set -u

# Usage:
#   ./scripts/capture_prompt_diff.sh
#   ./scripts/capture_prompt_diff.sh prompt258 explicit-real-input-injection
#
# No-arg mode:
#   Infers the next prompt id from the latest promptNNN-* tag.
#   Example: latest tag prompt257-explicit-dev-loop-input-readiness -> prompt258

INPUT_PROMPT_ID="${1:-}"
INPUT_TITLE="${2:-}"

LATEST_PROMPT_TAG="$(
  git tag --list 'prompt[0-9]*' \
    | grep -E '^prompt[0-9]+' \
    | sed -E 's/^(prompt[0-9]+).*/\1 &/' \
    | sort -V \
    | tail -n 1 \
    | cut -d' ' -f2-
)"

if [ -z "$INPUT_PROMPT_ID" ]; then
  if [ -n "$LATEST_PROMPT_TAG" ]; then
    LATEST_NUM="$(
      printf '%s\n' "$LATEST_PROMPT_TAG" \
        | sed -E 's/^prompt([0-9]+).*/\1/'
    )"
    NEXT_NUM=$((10#$LATEST_NUM + 1))
    PROMPT_ID="prompt${NEXT_NUM}"
  else
    PROMPT_ID="prompt_unknown"
  fi
else
  PROMPT_ID="$INPUT_PROMPT_ID"
fi

if [ -z "$INPUT_TITLE" ]; then
  TITLE="auto-diff"
else
  TITLE="$INPUT_TITLE"
fi

TS="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="${DIFF_LOG_DIR:-/tmp/codex-local-runner-diff-logs}"
mkdir -p "$OUT_DIR"

SAFE_TITLE="$(printf '%s' "$TITLE" | tr ' /:' '---' | tr -cd '[:alnum:]_.-')"
REPORT="$OUT_DIR/${TS}_${PROMPT_ID}_${SAFE_TITLE}_diff_report.txt"
PATCH="$OUT_DIR/${TS}_${PROMPT_ID}_${SAFE_TITLE}_full.patch"

{
  echo "# Diff report"
  echo "timestamp=$TS"
  echo "prompt_id=$PROMPT_ID"
  echo "title=$TITLE"
  echo "repo=$(pwd)"
  echo "latest_prompt_tag=${LATEST_PROMPT_TAG:-}"
  echo

  echo "## Git HEAD"
  git log --oneline --decorate -1
  echo

  echo "## Status"
  git status --short
  echo

  echo "## Diff stat - unstaged tracked"
  git diff --stat
  echo

  echo "## Diff name-status - unstaged tracked"
  git diff --name-status
  echo

  echo "## Diff stat - staged"
  git diff --cached --stat
  echo

  echo "## Diff name-status - staged"
  git diff --cached --name-status
  echo

  echo "## Untracked files"
  git ls-files --others --exclude-standard
  echo

  echo "## Diff check"
  git diff --check || true
  git diff --cached --check || true
  echo

  echo "## Added builder symbols excerpt"
  git diff -- automation/orchestration/planned_execution_runner.py \
    | grep -E '^\+def _build_project_browser_autonomous_' \
    | sed 's/^+//' || true
  git diff --cached -- automation/orchestration/planned_execution_runner.py \
    | grep -E '^\+def _build_project_browser_autonomous_' \
    | sed 's/^+//' || true
  echo

  echo "## Added key field lines excerpt"
  git diff -- automation/orchestration/planned_execution_runner.py \
    | grep -E '^\+.*project_browser_autonomous_.*(status|next_action|ready|detected|allowed|decision|prompt|enabled|reason|candidate|complete)' \
    || true
  git diff --cached -- automation/orchestration/planned_execution_runner.py \
    | grep -E '^\+.*project_browser_autonomous_.*(status|next_action|ready|detected|allowed|decision|prompt|enabled|reason|candidate|complete)' \
    || true
  echo

  echo "## Full unstaged tracked diff"
  git diff --find-renames --find-copies --binary
  echo

  echo "## Full staged diff"
  git diff --cached --find-renames --find-copies --binary
  echo

  echo "## Untracked file contents / patches"
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    echo
    echo "### UNTRACKED: $f"
    if [ -f "$f" ]; then
      if file "$f" | grep -qiE 'text|json|python|shell|markdown|yaml|xml|csv'; then
        git diff --no-index -- /dev/null "$f" || true
      else
        echo "(binary or non-text file; content not embedded)"
        ls -lh "$f"
      fi
    fi
  done < <(git ls-files --others --exclude-standard)

} > "$REPORT"

{
  git diff --find-renames --find-copies --binary
  git diff --cached --find-renames --find-copies --binary
} > "$PATCH"

echo "PROMPT_ID=$PROMPT_ID"
echo "TITLE=$TITLE"
echo "LATEST_PROMPT_TAG=${LATEST_PROMPT_TAG:-}"
echo "REPORT=$REPORT"
echo "PATCH=$PATCH"
