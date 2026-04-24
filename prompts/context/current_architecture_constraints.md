# Current architecture constraints

These are the current preserved constraints for new narrow PR prompts.
Reuse and preserve unless a prompt explicitly says otherwise.

## Core preserved behavior
- Preserve PR63 approval safety gates and precedence.
- Preserve PR65 one-shot bounded automatic restart execution.
- Preserve PR66 narrow low-risk approval-skip gating.
- Preserve PR67 continuation-budget gating at run/objective/lane scope.
- Preserve PR68 branch-specific continuation ceilings for retry / replan / truth_gather.
- Preserve PR69 no-progress stopping and failure-bucket continuation denial.
- Preserve PR70 deterministic failure-bucket -> repair-playbook selection.
- Preserve PR71 deterministic next-step selection among retry / replan / truth_gather / supported_repair.
- Preserve PR72 one bounded supported_repair execute-verify loop.
- Preserve PR73 explicit final human-review-required gate.
- Preserve PR74 deterministic project-planning summary/compiler.
- Preserve PR75 deterministic roadmap generation, bounded PR slicing, and simple prioritization/order.
- Preserve PR76 deterministic implementation-prompt generation from bounded PR slices.
- Preserve PR77 deterministic bounded PR-queue state and one-item execution handoff preparation.
- Preserve PR78 deterministic review-assimilation from bounded queue/handoff/result outcomes.
- Preserve PR79 deterministic bounded self-healing transitions from review-assimilation outputs.
- Preserve PR80 deterministic long-running stability with watchdog, stale/stuck detection, replay-safe pause/resume.
- Preserve PR81 deterministic objective / done-criteria compiler from planning, queue, recovery, and stability state.
- Preserve PR82 deterministic project-level prioritization and autonomy-budget compiler from objective/completion and bounded execution state.
- Preserve PR83 deterministic quality-gate orchestration with merge-ready / review-ready / retry-needed posture.
- Preserve PR84 deterministic merge / branch lifecycle compiler with merge-ready, cleanup, quarantine, and local-main-sync posture.
- Preserve PR85 deterministic failure-memory and repeated-mistake suppression compiler from retry/repair/review/lifecycle state.
- Preserve PR85 deterministic failure-memory and repeated-mistake suppression compiler from retry/repair/review/lifecycle state.
- Preserve PR86 deterministic external dependency boundary compiler for GitHub/CI/secrets/network/manual-only posture.
- Preserve PR87 deterministic project-level human escalation compiler from review, boundary, budget, and failure-risk state.
- Preserve PR88 deterministic mobile-friendly approval-notification posture from approval-email/reply and escalation state.




@@
 ## Long-running stability constraints

## Prompting / implementation constraints
- Prefer changing `automation/orchestration/planned_execution_runner.py` and `tests/test_planned_execution_runner.py` first.
- Touch summary / artifact / inspect surfaces only if strictly required.
- Additive changes only.
- Deterministic outputs and decisions only.
- Local-first only.
- No free-form NLP.
- No broad controller / scheduler / autopilot framework redesign.
- Preserve human-gated fallback whenever automation cannot proceed safely.

## Planning / slicing constraints
- Derive roadmap and PR slices only from the existing deterministic planning summary surface.
- If planning summary truth is insufficient, preserve deterministic insufficient state and emit zero roadmap items / zero PR slices.
- Preserve deterministic ordering behavior:
  - blocked-last
  - narrower-scope-first
  - prerequisites-before-dependents
- Preserve bounded PR sizing posture:
  - single_theme_single_pr
  - avoid mixing unrelated subsystems
  - do not widen bounded slice scope during later prompt generation or queue preparation

## Boundedness defaults
- Do not introduce unbounded chaining.
- Preserve one-shot bounded restart behavior unless a prompt explicitly changes it.
- Preserve existing continuation budgets / ceilings / denial precedence unless a prompt explicitly changes them.

## Prompt-generation constraints
- Derive implementation prompt payloads only from existing deterministic bounded PR-slice state.
- If slice or planning truth is insufficient, preserve deterministic prompt unavailable/insufficient state and do not emit speculative payload content.
- Preserve compact machine-readable prompt payload shape rather than verbose prose-only prompt state.
- Preserve bounded slice intent during prompt generation:
  - do not widen bounded slice scope
  - do not merge multiple slices during prompt generation
  - preserve slice identity and roadmap-item linkage when available

## Queue / handoff constraints
- Derive queue selection and one-item handoff only from existing deterministic PR-slice state and implementation-prompt payload state.
- Prepare at most one runnable queue item per decision step.
- If prompt payload is unavailable/insufficient for the selected slice, preserve blocked/non-handoff state and do not fabricate execution handoff.
- Preserve compact deterministic queue outcomes such as:
  - prepared
  - blocked
  - empty
  - insufficient_truth
- Do not introduce queue draining or broad scheduler behavior during queue-state/handoff preparation.

## Review / assimilation constraints
- Derive review-assimilation only from existing deterministic bounded queue/handoff/result posture.
- If queue state is empty, blocked, prompt-unavailable, or insufficient_truth, preserve compact no-action or unavailable assimilation state and do not fabricate bounded next actions.
- Preserve bounded assimilation actions only:
  - accept
  - retry
  - replan
  - split
  - escalate
- Preserve compact machine-readable assimilation state, including queue/result linkage when available.
- Do not introduce broad self-healing chains or redesign queue behavior during review-assimilation.

## Self-healing constraints
- Derive bounded self-healing transitions only from existing deterministic review-assimilation outputs and already-available bounded execution/safety state.
- Allow at most one bounded self-healing transition per chain budget window.
- Preserve bounded transition mapping only:
  - retry -> retry
  - replan -> replan
  - split -> truth_gather
  - escalate -> alternative_supported_repair only when explicitly allowed
- If review assimilation is no_action, unavailable, insufficient_truth, or current queue posture is non-runnable, preserve compact non-transition state and do not fabricate recovery.
- Preserve human fallback on safety blocks, continuation/no-progress/failure denies, exhausted budgets, and final human-review-required posture unless an explicit narrow exception already exists.
- Do not introduce unbounded retry/replan/repair loops or redesign queue behavior during self-healing.

## Long-running stability constraints
- Derive long-running stability only from existing deterministic queue, review-assimilation, self-healing, fallback, and final-review state.
- Preserve bounded long-running behavior:
  - no blind continuation on queue empty / blocked / insufficient_truth
  - no blind continuation on human-fallback-preserved or final-human-review-required posture
  - no blind continuation when self-healing chain budget is exhausted
- Preserve deterministic stale/stuck handling:
  - stale -> paused or safe-stop
  - stuck -> escalated or safe-stop
  - resume_ready only when deterministic replay-safe state exists
- Preserve compact machine-readable long-running state, including replay-safe identity / signature / resume-token style fields when available.
- Do not redesign queue, review-assimilation, or self-healing behavior while adding long-running stability.

## Objective / completion constraints
- Derive objective identity, done criteria, stop criteria, completion posture, and scope-drift signals only from existing deterministic planning, queue, review-assimilation, self-healing, long-running stability, fallback, and final-review state.
- Preserve compact completion posture only:
  - objective_active
  - objective_completed
  - objective_blocked
  - objective_insufficient_truth
- If objective or completion truth is insufficient, preserve compact insufficient/unavailable state and do not fabricate completion claims.
- Derive done criteria only from already-available machine-readable bounded execution signals such as slice count, processed slice count, queue posture, and explicit completion-compatible state.
- Derive stop criteria only from already-available explicit stop signals such as final human review, preserved human fallback, and long-running pause/escalation posture.
- Emit scope-drift only from explicit deterministic signals such as queue/prompt mismatch or split-compatible posture; never speculate.
- Do not redesign planning, queue, self-healing, or long-running control flow while adding objective/completion compilation.

## Prioritization / autonomy-budget constraints
- Derive project-level prioritization and autonomy-budget posture only from existing deterministic objective/completion, planning, queue, review-assimilation, self-healing, long-running stability, budget, risk, fallback, and final-review state.
- Reuse PR81 objective/completion posture directly when practical; do not create a separate objective truth owner.
- Preserve compact machine-readable posture for:
  - project priority
  - per-objective budget
  - per-run budget
  - per-PR retry budget
  - high-risk defer / lower-priority posture
- If prioritization or budget truth is insufficient, preserve compact insufficient/unavailable state and do not fabricate budget numbers or project priority.
- Do not redesign existing execution/control flow while adding prioritization/budget compilation.
- Do not introduce a broad scoring framework in this layer.

## Quality-gate constraints
- Derive quality-gate posture only from existing deterministic slice, prompt, queue, result, objective/completion, prioritization/budget, risk, and fallback state.
- Reuse PR82 project-level prioritization / autonomy-budget posture directly when practical.
- Preserve compact recommended gate outputs only from bounded set:
  - unit
  - targeted_regression
  - lint
  - typecheck
- Preserve compact posture outputs only:
  - merge_ready
  - review_ready
  - retry_needed
  - insufficient_truth
- If quality-gate truth is insufficient, preserve compact unavailable/insufficient state and do not fabricate gate requirements.
- Do not execute validation or redesign existing execution/control flow while adding quality-gate compilation.

## Merge / branch lifecycle constraints
- Derive merge / branch lifecycle posture only from existing deterministic quality-gate, objective/completion, prioritization/budget, queue, result, fallback, and final-review state.
- Reuse PR83 quality-gate posture directly when practical.
- Preserve compact machine-readable lifecycle outputs only:
  - merge_ready / not_merge_ready / insufficient_truth
  - cleanup_candidate posture
  - quarantine_candidate posture
  - local_main_sync posture
- If lifecycle truth is insufficient, preserve compact unavailable/insufficient state and do not fabricate merge, cleanup, quarantine, or sync posture.
- Do not perform merge, branch cleanup, branch deletion, or git sync actions while adding lifecycle compilation.
- Do not redesign queue, review-assimilation, self-healing, long-running stability, or quality-gate behavior during lifecycle compilation.

## Failure-memory / suppression constraints
- Derive failure-memory and repeated-mistake suppression posture only from existing deterministic retry, repair, review, failure-bucket, queue, assimilation, self-healing, lifecycle, budget, and fallback state.
- Reuse PR84 merge / branch lifecycle posture directly when practical.
- Preserve compact machine-readable memory outputs only for:
  - ineffective_retry
  - failed_repair
  - repeated_review_issue
  - recurring_failure_bucket
  - suppression_posture
- If memory truth is insufficient, preserve compact unavailable/insufficient state and do not fabricate recurrence or suppression.
- Do not introduce probabilistic behavior, broad learning frameworks, or broad control-path redesign while adding failure-memory / suppression compilation.

## Failure-memory / suppression constraints
- Derive failure-memory and repeated-mistake suppression posture only from existing deterministic retry, repair, review, failure-bucket, queue, assimilation, self-healing, lifecycle, budget, and fallback state.
- Reuse PR84 merge / branch lifecycle posture directly when practical.
- Preserve compact machine-readable memory outputs only for:
  - ineffective_retry
  - failed_repair
  - repeated_review_issue
  - recurring_failure_bucket
  - suppression_posture
- If memory truth is insufficient, preserve compact unavailable/insufficient state and do not fabricate recurrence or suppression.
- Do not introduce probabilistic behavior, broad learning frameworks, or broad control-path redesign while adding failure-memory / suppression compilation.

## External dependency boundary constraints
- Derive external dependency boundary posture only from existing deterministic dependency/block/manual-only/fallback/lifecycle/memory/suppression state.
- Reuse PR85 failure-memory / suppression posture directly when practical.
- Preserve compact machine-readable dependency posture only:
  - dependency_available
  - dependency_blocked
  - manual_only
  - insufficient_truth
- Preserve compact boundary posture for:
  - network
  - CI
  - secrets
  - GitHub
  - external_API
- If boundary truth is insufficient, preserve compact unavailable/insufficient state and do not fabricate dependency availability or manual-only state.
- Do not introduce uncontrolled external actions or redesign execution/control flow while adding external-boundary compilation.

## Human escalation constraints
- Derive project-level human escalation posture only from existing deterministic final-review, external-boundary, budget, completion, quality, lifecycle, memory, suppression, and fallback state.
- Preserve PR73 final human-review-required behavior and extend it project-level only.
- Reuse PR86 external-boundary posture directly when practical.
- Preserve compact machine-readable escalation outputs only for:
  - escalation_status / posture / required / reason / reason_codes
  - architecture_risk
  - scope_risk
  - external_risk
  - budget_risk
  - repeated_failure_risk
  - manual_only_risk
- If escalation truth is insufficient, preserve compact unavailable/insufficient state and do not fabricate escalation reasons.
- Do not redesign approval delivery, queue, review-assimilation, self-healing, long-running stability, or lifecycle behavior while adding project-level human escalation compilation.

## Approval-notification constraints
- Derive approval-notification posture only from existing deterministic approval email/reply-ingest signals and project-level escalation state.
- Reuse existing PR59 / PR61 / PR62 approval-email and reply-ingest posture directly when practical.
- Reuse project-level escalation posture directly when practical.
- Preserve compact machine-readable approval-notification outputs only for:
  - notification_ready posture
  - reply_required posture
  - approval_channel posture
  - mobile_friendly concise approval summary posture
  - unavailable / insufficient posture
- If approval-notification truth is insufficient, preserve compact unavailable/insufficient state and do not fabricate delivery readiness or reply-required state.
- Do not redesign approval delivery flow, reply grammar/parsing, queue behavior, or execution/control flow while adding approval-notification compilation.