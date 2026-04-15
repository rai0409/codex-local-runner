# Codex Run Record

## Metadata
- Date: 2026-04
- Repo: codex-local-runner
- Branch: feat/inspect-advisory-7a
- Prompt name: prompt7a_advisory_readonly
- Task type: inspect_read_only_extension
- Decision: pass

## Prompt
Stored separately at:
- prompts/examples/good/prompt7a_advisory_readonly.md

## Repository reading proof
- scripts/build_operator_summary.py
- scripts/inspect_job.py
- scripts/operator_review_decision.py
- scripts/inspect_decision_history.py
- orchestrator/ledger.py
- tests/test_build_operator_summary.py
- tests/test_inspect_job.py
- tests/test_operator_review_decision.py

## Implementation map
### Before edits
- build_operator_summary.py already generated machine-review payload and ledger-backed machine_review_payload_path
- inspect_job.py already showed ledger-backed machine-review output
- operator_review_decision.py was explicit human decision path and remained unchanged

### Expected narrow change
- add inspect-time advisory derived from existing machine-review facts only
- keep advisory read-only
- keep execution behavior unchanged

### Boundaries preserved
- ledger remained source of truth
- inspect remained read-only
- no notifier / scheduler / runtime expansion
- operator_review_decision.py unchanged

## Codex output summary
- Added _derive_recommendation_advisory(...) in scripts/inspect_job.py
- Added machine_review.advisory to JSON output
- Added advisory lines to human-readable output
- Updated tests/test_inspect_job.py for advisory presence/defaults and compatibility

## Exact files changed
- scripts/inspect_job.py
- tests/test_inspect_job.py

## Why narrow/safe
- advisory computed only at inspect time
- reused existing machine-review facts
- no persistence change
- no control signal introduced
- execution_allowed stayed false

## Commands run
```bash id="2wqfho"
python -m compileall scripts/inspect_job.py tests/test_inspect_job.py
python -m unittest tests.test_build_operator_summary tests.test_inspect_job tests.test_operator_review_decision -v
Test results
Compile: passed
Unit tests: passed
Result: Ran 36 tests / OK
Evaluation
Score: pass-grade
Failure taxonomy hits: none critical
Final judgment: pass
Follow-up
Accept as-is: yes
Needed micro-fixes: none required at record time
Next prompt: execution_bridge read-only visibility
