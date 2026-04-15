You are working inside the codex-local-runner repository.

Goal:
Add a narrow, operator-facing recommendation-assist layer on top of the existing machine-review payload / ledger / inspect foundation, without introducing execution behavior.

Current repo state you must respect:
- Prompt 1 through Prompt 6.5 are already implemented and merged.
- Prompt 5 is already implemented in the current baseline:
  - machine_review payload includes retry_metadata
  - inspect_job.py surfaces retry_metadata read-only
  - backward compatibility for missing retry_metadata is preserved
- machine_review payload generation is already working.
- ledger-backed machine_review_payload_path synchronization is already working.
- inspect_job.py already treats ledger-recorded machine review state as the source of truth.
- retry / escalate vocabulary already exists as representation-only outcomes.

Primary objective:
Introduce a recommendation-assist surface that helps an operator understand the current suggested path and its rationale, while remaining strictly read-only / advisory.

This prompt is NOT about execution.
Do not implement retry execution, rollback execution, merge execution, redispatch, or any automatic state transition.

Before making changes:
1. Read the existing implementation first and print a short implementation map before editing.
2. Read at minimum:
   - scripts/build_operator_summary.py
   - scripts/inspect_job.py
   - scripts/operator_review_decision.py
   - scripts/inspect_decision_history.py
   - orchestrator/ledger.py
   - tests/test_build_operator_summary.py
   - tests/test_inspect_job.py
   - tests/test_operator_review_decision.py
3. Reuse the existing retry_metadata shape exactly as already implemented.
4. Keep the diff minimal and additive.
5. Preserve payload ↔ ledger ↔ inspect alignment.

Hard constraints:
- Do not change notifier, scheduler, delivery, or worker semantics.
- Do not introduce auto execution.
- Do not change operator_review_decision.py to execute new behaviors.
- Do not broaden machine_review.recorded semantics.
- Do not add filesystem fallback discovery.
- Do not create a second source of truth outside ledger-backed inspect visibility.
- Do not redesign existing machine_review payload fields.
- Do not broaden this into Prompt 7B or 7C concerns.
- Do not duplicate retry_metadata under a second differently named structure.
- Any new advisory data must be deterministic and derived from already-recorded machine_review facts only.

Specific task:
Add a minimal advisory recommendation-assist structure that makes the current recommendation easier for operators to inspect and reason about.

Recommended design target:
- Prefer a derived advisory section in inspect output if possible.
- Only add advisory into machine_review payload if needed for consistency with existing payload architecture.
- Keep it grounded in existing machine_review fields:
  - recommended_action
  - policy_version
  - policy_reasons
  - requires_human_review
  - retry_metadata

Example target shape:
{
  "advisory": {
    "display_recommendation": "keep|rollback|retry|escalate|null",
    "decision_confidence": "high|medium|low|null",
    "operator_attention_flags": ["..."],
    "execution_allowed": false
  }
}

Required semantics:
- advisory must be derived from already-recorded machine_review facts only
- execution_allowed must remain false
- decision_confidence must be deterministic and conservative
- operator_attention_flags should prefer existing policy-style reason tags
- Use a small deterministic vocabulary for operator_attention_flags and prefer reusing existing policy-style reason tags if similar tags already exist in the repository
- advisory must not change or reinterpret the meaning of recommended_action
- advisory must not introduce any execution semantics

Suggested conservative derivation rules:
- If recommended_action is "retry" and retry_metadata.retry_recommended is true:
  - display_recommendation = "retry"
  - decision_confidence = "medium" unless a stricter existing policy reason implies "low"
- If recommended_action is "keep" or "rollback" and requires_human_review is false:
  - decision_confidence = "high" or "medium" conservatively
- If recommended_action is "escalate" or requires_human_review is true:
  - decision_confidence = "low"
- operator_attention_flags should primarily reuse policy_reasons, then retry_basis / retry_blockers when useful, without inventing broad new vocabularies

Backward compatibility:
- Old payloads / old jobs without retry_metadata must remain safe and readable
- Missing fields should degrade conservatively
- inspect must still work when only ledger-recorded machine_review payload exists

Success criteria:
- advisory layer is visible to operators
- no execution behavior is added
- existing machine_review fields remain intact
- payload ↔ ledger ↔ inspect alignment remains intact
- backward compatibility is preserved

Validation requirements:
- Add/update focused tests for build/inspect/decision visibility as needed
- Run syntax/compile checks if applicable
- Run targeted tests and report exact commands and exact pass/fail results

Output requirements:
- concise summary of what changed
- exact files changed
- exact commands run
- exact test results
- final advisory structure shape
- whether any existing semantics changed
- why this is read-only and safe