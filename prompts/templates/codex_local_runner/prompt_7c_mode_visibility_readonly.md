You are working inside the codex-local-runner repository.

Goal:
Add the narrowest possible mode-visibility layer on top of the existing machine-review / retry-metadata / advisory / execution-bridge inspect flow, without introducing any execution behavior, state transition, policy expansion, or control-signal semantics.

Repository context you must respect:
- This repository is building a deterministic, ledger-backed operator-assist / review-control plane.
- It is not currently building an autonomous execution engine.
- The current strength of the repo is:
  - machine-review payload generation
  - ledger-backed inspect visibility
  - deterministic read-only derived surfaces
  - explicit human operator decision path
- The current risk areas are:
  - mixing representation with execution semantics
  - implying future capability that the repo does not actually implement
  - expanding inspect metadata into control-plane behavior
  - creating a second taxonomy or second source of truth

Current repo state you must assume as baseline:
- Prompt 1 through Prompt 6.5 are already implemented and merged.
- Prompt 5 is already implemented and merged:
  - machine_review payload includes retry_metadata
- Prompt 7A is already implemented and merged:
  - inspect_job.py derives advisory read-only
- Prompt 7B is already implemented and merged:
  - inspect_job.py derives execution_bridge read-only
  - execution_bridge is conservative and non-executable:
    - eligible_for_bounded_execution = false
    - eligibility_basis = []
    - requires_explicit_operator_decision = true
- machine_review payload / ledger / inspect alignment already works.
- inspect_job.py already treats ledger-recorded machine_review payload as the source of truth.
- operator_review_decision.py remains the only explicit human decision path and should not be changed unless absolutely unavoidable for tiny read-only compatibility reasons.

Primary objective:
Expose a minimal, truthful mode-visibility layer that helps operators understand the current automation maturity / operating mode of a reviewed job, while keeping current behavior unchanged.

This prompt is NOT for:
- enabling automatic mode changes
- adding autonomous execution
- adding workers, schedulers, or notifier behavior
- expanding execution capability
- altering operator review decision semantics
- changing ledger behavior
- introducing policy-driven transitions

This prompt is visibility-only.

Before making changes:
1. Read the current implementation and print a short implementation map before editing.
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
   - execution_bridge
4. Keep the diff minimal and additive.
5. Prefer inspect-time derived visibility over new persisted payload fields.

Hard constraints:
- Do not add any execution behavior.
- Do not add any state transitions.
- Do not add mode-changing behavior.
- Do not add side effects.
- Do not add background workers, schedulers, or notifier behavior.
- Do not modify the FSM.
- Do not create a second source of truth outside ledger-backed inspect visibility.
- Do not add loose-file fallback discovery.
- Do not redesign machine_review, retry_metadata, advisory, or execution_bridge.
- Prefer not to modify build_operator_summary.py.
- Prefer not to modify operator_review_decision.py at all.
- Prefer not to modify inspect_decision_history.py unless a tiny read-only display consistency change is clearly required.
- Do not create a broad new mode taxonomy.
- Reuse existing reason tags / attention flags / blockers wherever possible.
- mode_visibility must not be consumed as a control signal anywhere; it is inspect-only operator-facing metadata.

Specific task:
Add a minimal, inspect-derived, read-only mode visibility structure that truthfully represents the current mode and its blockers.

Preferred target shape:
{
  "mode_visibility": {
    "current_mode": "manual_review_only",
    "next_possible_mode": null,
    "mode_basis": ["..."],
    "mode_blockers": ["..."]
  }
}

Required semantics:
- current_mode must reflect actual current repository behavior conservatively
- next_possible_mode should default to null unless there is a clearly grounded, already-implemented, inspect-visible, non-speculative next mode concept
- prefer keeping next_possible_mode = null for all current cases unless the repository already has an implemented, inspect-visible, non-speculative next mode concept
- mode_basis should be small, deterministic, and grounded in current repo facts
- prefer a very small mode_basis and do not invent explanatory basis entries when current_mode = manual_review_only is already sufficiently grounded by existing facts
- mode_blockers should carry most of the present-state meaning
- prefer blocker-heavy representation because the repo does not yet implement automated mode progression
- do not imply future runtime capability that does not exist

Strong implementation preference:
- Implement this as inspect-time derived visibility only
- Prefer adding this only in:
  - scripts/inspect_job.py
  - tests/test_inspect_job.py
- Only touch other files if strictly necessary for compatibility or reuse of an already-existing read-only helper
- If in doubt, keep the implementation entirely inside inspect_job.py

Grounding rules:
- Derive only from already-recorded machine_review facts and already-derived inspect facts:
  - retry_metadata
  - advisory
  - execution_bridge
- Treat advisory as an operator aid, not a control signal
- Treat execution_bridge as a visibility layer, not a runtime bridge
- Do not infer a future operating mode merely from a recommendation
- Do not infer a future operating mode merely from advisory confidence
- Do not infer a future operating mode merely from execution_bridge blockers or basis unless the current repository behavior truly supports that inference

Recommended conservative derivation:
- current_mode = "manual_review_only"
- next_possible_mode = null
- mode_basis:
  - may include a very small deterministic set grounded in current repo facts, such as:
    - ledger_backed_machine_review_visible
    - explicit_operator_decision_required
  - it is acceptable to keep mode_basis very small
- mode_blockers:
  - prefer existing execution_bridge.eligibility_blockers
  - then reuse advisory.operator_attention_flags if needed
  - if still needed, use a very small deterministic vocabulary grounded in current repository limitations, such as:
    - execution_not_implemented
    - explicit_operator_gate_required
  - do not introduce a larger mode taxonomy

Decision-boundary rules:
- If the current repository does not genuinely support multiple operating modes, do not invent them
- It is completely acceptable and preferred if the final implementation always shows:
  - current_mode = "manual_review_only"
  - next_possible_mode = null
  - mode_basis = [...]
  - mode_blockers = [...]
  for all currently supported cases
- This is a success if it is the smallest truthful design

Backward compatibility:
- Old payloads / old jobs without retry_metadata must remain readable
- Old payloads / old jobs without advisory must remain readable
- Old payloads / old jobs without execution_bridge must remain readable
- Missing machine_review subfields must degrade conservatively
- inspect must continue to function when only ledger-recorded machine_review payload is available
- No existing machine_review semantics may change
- machine_review.recorded meaning must remain unchanged

Success criteria:
- mode visibility is exposed in inspect output
- it is derived only from already-recorded / already-derived facts
- it introduces no new behavior
- it preserves explicit operator gating
- it preserves ledger-backed source of truth
- it does not confuse recommendation, confidence, execution eligibility, and current operating mode
- it uses a very small deterministic vocabulary
- it remains backward compatible
- it is smaller than a typical feature implementation and clearly read-only

Validation requirements:
- Add/update focused tests only where needed
- Prefer tests in tests/test_inspect_job.py
- Add compatibility tests for:
  - old payload without retry_metadata
  - old payload without advisory
  - old payload without execution_bridge
  - unrecorded machine-review case
- Ensure tests verify that current_mode remains conservative
- Run compile/syntax checks if applicable
- Run targeted tests and report exact commands and exact results

Output requirements:
- implementation map before edits
- concise summary of what changed
- exact files changed
- exact commands run
- exact test results
- final mode_visibility shape
- explicit statement that execution behavior did not change
- explicit statement that operator_review_decision semantics did not change
- why the implementation is narrow, truthful, read-only, and safe

Non-goals reminder:
- not execution
- not auto mode switching
- not policy expansion
- not a second control plane
- not a hidden runtime bridge