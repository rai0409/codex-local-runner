# Prompt654 Prompt-Generation — Project-Level Live E2E Acceptance

**Status:** success · **Base:** 7d4cff1 (tag prompt653-live-auto-execution-bridge)
**Generated:** prompts/generated/prompt654_project_level_live_e2e_acceptance.md

Target: project_level_live_e2e_acceptance — a bounded, operator-triggered, dry-run-default,
token-gated /tmp live E2E harness wrapping the Prompt653 bridge. It clones the repo to
/tmp, builds intent+descriptors (harmless add_function), runs the bridge live (≤1/1/1),
ingests a REAL run_report into the completion gate, and verifies main-repo HEAD unchanged.
Verified prompt654 harness/test/script/report/tag absent. Proceeding to implement + test +
run one bounded live acceptance in the same run.
