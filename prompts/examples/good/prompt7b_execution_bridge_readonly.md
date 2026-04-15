You are working inside the codex-local-runner repository.

Goal:
Add the narrowest possible execution-eligibility visibility layer on top of the existing machine-review / retry-metadata / advisory flow, without introducing any execution behavior, state transition, or operator-decision semantic change.

Repository context you must respect:
- This repository is building a deterministic operator-assist / review-control flow, not an autonomous execution engine.
- The current strength of the repo is:
  - ledger-backed source of truth
  - deterministic machine-review payload generation
  - read-only inspect visibility
  - explicit human operator decision path
- The current weak points / risks are:
  - mixing representation with execution semantics
  - accidentally broadening inspect-only metadata into runtime behavior
  - growing a second taxonomy instead of reusing existing reason tags
  - drifting away from ledger-backed source of truth
  - over-designing “future execution” before actual execution support exists

Current repo state you must assume as baseline:
- Prompt 1 through Prompt 6.5 are already implemented and merged.
- Prompt 5 is already implemented and merged:
  - machine_review payload includes retry_metadata
  - retry_metadata shape is already established and must be reused as-is
- Prompt 7A is already implemented and merged:
  - inspect_job.py already derives a read-only advisory layer
  - advisory already includes:
    - display_recommendation
    - decision_confidence
    - operator_attention_flags
    - execution_allowed = false
- machine_review payload / ledger / inspect alignment already works.
- inspect_job.py already treats ledger-recorded machine_review payload as the source of truth.
- operator_review_decision.py remains the explicit human decision path and should not be changed unless there is an unavoidable compatibility reason for read-only visibility support.
- retry / rollback / escalate / keep are still recommendation vocabulary, not runtime execution permissions.

Primary objective:
Represent, in the most conservative possible way, whether a reviewed outcome could be considered eligible for bounded execution in the future, while keeping current execution disabled and explicit human gating intact.

This prompt is NOT for:
- implementing retry execution
- implementing rollback execution
- implementing merge execution
- implementing redispatch
- implementing a worker or scheduler path
- implementing policy-driven automatic transitions
- changing operator decision semantics
- enabling any action based on recommended_action alone

This prompt is visibility-only.

Before making changes:
1. Read the current implementation first and print a short implementation map before editing.
2. Read at minimum:
   - scripts/build_operator_summary.py
   - scripts/inspect_job.py
   - scripts/operator_review_decision.py
   - scripts/inspect_decision_history.py
   - orchestrator/ledger.py
   - tests/test_build_operator_summary.py
   - tests/test_inspect_job.py
   - tests/test_operator_review_decision.py
3. Explicitly confirm which existing fields are reused:
   - recommended_action
   - policy_version
   - policy_reasons
   - requires_human_review
   - retry_metadata
   - advisory
4. Keep the diff minimal and additive.
5. Prefer inspect-time derived visibility over new persisted payload fields.

Hard constraints:
- Do not add any execution behavior.
- Do not add any side effects.
- Do not add any state transitions.
- Do not add background workers, scheduler hooks, or notifier behavior.
- Do not modify the FSM.
- Do not make recommended_action executable.
- Do not make retry_metadata imply runnable retry behavior.
- Do not reinterpret advisory.decision_confidence as execution confidence.
- Do not weaken explicit human review / operator gating.
- Do not create a second source of truth outside ledger-backed inspect visibility.
- Do not add loose-file fallback discovery.
- Do not broaden this prompt into Prompt 7C mode-progression work.
- Do not redesign machine_review, retry_metadata, or advisory structures unless strictly required for a tiny additive compatibility reason.
- Prefer not to modify build_operator_summary.py unless absolutely necessary.
- Prefer not to modify operator_review_decision.py at all.
- Prefer not to modify inspect_decision_history.py unless a tiny read-only display consistency update is clearly required.
- Do not create a large new vocabulary for eligibility.
- Reuse existing policy-style reason tags and advisory flags wherever possible.

Specific task:
Add a minimal, read-only execution eligibility visibility layer, ideally derived in inspect output from already-recorded facts.

Preferred target shape:
{
  "execution_bridge": {
    "eligible_for_bounded_execution": false,
    "eligibility_basis": ["..."],
    "eligibility_blockers": ["..."],
    "requires_explicit_operator_decision": true
  }
}

Important naming note:
- You may keep the name execution_bridge if it fits the current inspect JSON structure cleanly.
- However, do not let the name “bridge” justify adding any bridging runtime logic.
- This structure is visibility-only.
- If an existing inspect-facing naming convention suggests a more conservative name such as execution_eligibility_view, use it only if that change is clearly smaller and safer than introducing inconsistency.

Required semantics:
- execution eligibility must remain representational only
- current repo behavior remains unchanged
- eligible_for_bounded_execution must default to false
- requires_explicit_operator_decision must always be true in this prompt
- eligibility_basis may remain empty for all current cases if that is the safest deterministic design
- eligibility_blockers should carry most of the present-state meaning
- prefer putting current-state constraints into eligibility_blockers rather than inventing positive eligibility_basis entries
- prefer blocker-heavy representation because the repo does not yet implement bounded execution
- do not claim runtime capability that the repo does not actually have

Strong implementation preference:
- Implement this as inspect-time derived visibility only
- Prefer adding this only in:
  - scripts/inspect_job.py
  - tests/test_inspect_job.py
- Only touch other files if strictly necessary for compatibility or reuse of an already-existing read-only helper
- If in doubt, keep the implementation entirely inside inspect_job.py

Grounding rules:
- Derive only from already-recorded machine_review, retry_metadata, and advisory facts
- Treat advisory as an inspect-time aid, not a control signal
- A retry recommendation does not imply retry execution eligibility
- A keep recommendation does not imply merge/finalize eligibility
- An escalate recommendation does not imply a different runtime path
- Existing human operator decision remains the only explicit decision path

Recommended conservative derivation:
- requires_explicit_operator_decision = true for all current cases
- eligible_for_bounded_execution = false for all current cases is acceptable and preferred if that keeps the design smallest and safest
- eligibility_basis:
  - preferably []
  - only include entries if they are already clearly grounded by existing deterministic facts and do not overstate capability
- eligibility_blockers:
  - prefer existing policy_reasons
  - then reuse retry_metadata.retry_blockers
  - then reuse advisory.operator_attention_flags
  - if still needed, use a very small deterministic vocabulary grounded in actual repository limitations, such as:
    - explicit_operator_gate_required
    - execution_not_implemented
  - do not introduce broader taxonomy beyond what is needed for current visibility

Decision-boundary rules:
- If current repo behavior does not genuinely support bounded execution, do not mark any case as eligible
- It is completely acceptable for the final implementation to show:
  - eligible_for_bounded_execution = false
  - eligibility_basis = []
  - eligibility_blockers = [...]
for every currently supported case
- This is a success, not a failure, if it is the smallest truthful design

Backward compatibility:
- Old payloads / old jobs without retry_metadata must remain readable
- Old payloads / old jobs without advisory must remain readable
- Missing machine_review subfields must degrade conservatively
- inspect must continue to function when only ledger-recorded machine_review payload is available
- No existing machine_review semantics may change
- machine_review.recorded meaning must remain unchanged

Success criteria:
- execution eligibility visibility is exposed in inspect output
- it is derived only from already-recorded / already-derived facts
- it introduces no new behavior
- it preserves explicit operator gating
- it preserves ledger-backed source of truth
- it does not confuse recommendation, confidence, and execution capability
- it uses a small deterministic vocabulary
- it remains backward compatible
- it is smaller than a typical feature implementation and clearly read-only

Validation requirements:
- Add/update focused tests only where needed
- Prefer tests in tests/test_inspect_job.py
- Add compatibility tests for:
  - old payload without retry_metadata
  - old payload without advisory
  - retry recommendation still producing false eligibility if execution is not implemented
- Ensure tests verify that explicit operator gate remains represented as required
- Run compile/syntax checks if applicable
- Run targeted tests and report exact commands and exact results

Output requirements:
- implementation map before edits
- concise summary of what changed
- exact files changed
- exact commands run
- exact test results
- final execution_bridge (or chosen name) shape
- explicit statement that execution behavior did not change
- explicit statement that operator_review_decision semantics did not change
- why the implementation is narrow, truthful, read-only, and safe

Non-goals reminder:
- not Prompt 7C
- not execution
- not automation
- not policy expansion
- not a second control plane
- not a hidden runtime bridge