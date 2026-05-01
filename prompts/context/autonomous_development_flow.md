# Autonomous Development Flow MVP

Target flow:
1. User provides a project request.
2. ChatGPT analyzes the project.
3. ChatGPT creates a roadmap.
4. ChatGPT splits the roadmap into PR-sized units.
5. ChatGPT generates the next PR implementation prompt.
6. The PR prompt is handed to Codex.
7. Codex implements the change.
8. ChatGPT reviews Codex output.
9. If good, proceed to commit / merge or next PR.
10. If bad, revise prompt or return to an earlier stage.

MVP policy:
- Build a working end-to-end autonomous control spine first.
- Preserve minimum safety gates, explicit permissions, stop conditions, and validation.
- Prefer larger vertical-slice prompts over tiny single-surface prompts.
- Improve precision and additional safety after the MVP loop runs.

Core exposed fields should include:
- current_stage
- next_action
- block_reason
- project_request_detected
- roadmap_ready
- active_pr_index
- pr_prompt_ready
- codex_handoff_ready
- codex_result_detected
- review_decision
- commit_decision
- should_continue
- should_stop

## Prompt252 implemented MVP spine

Prompt252 added the first full autonomous development MVP control spine.

Available surfaces:
- project_browser_autonomous_dev_loop_input_*
- project_browser_autonomous_project_intake_*
- project_browser_autonomous_project_analysis_request_*
- project_browser_autonomous_roadmap_pr_split_queue_*
- project_browser_autonomous_pr_prompt_generation_*
- project_browser_autonomous_codex_handoff_*
- project_browser_autonomous_codex_result_review_decision_*
- project_browser_autonomous_dev_loop_mvp_*

Current next milestone:
- Provide explicit synthetic dev-loop input.
- Advance from missing_project_request to generated PR prompt and Codex handoff readiness.
- Keep ChatGPT/Codex/git execution external or metadata-only.

## Prompt253 implemented synthetic MVP handoff readiness

Prompt253 added dry-run synthetic input so the MVP spine can advance to PR prompt generation and Codex handoff readiness.

Current next milestone:
- Add Codex result ingestion metadata.
- Add approve/fix review decision.
- Add fix prompt generation.
- Add commit/next-PR decision metadata without executing git mutation.

## Prompt254 implemented Codex result review decision

Prompt254 added synthetic Codex result ingestion and review/fix decision metadata.

Current MVP path validated:
- project input
- analysis summary
- roadmap PR queue
- PR prompt generation
- Codex handoff readiness
- Codex result ingestion
- review approve decision

Current next milestone:
- Add commit/tag command suggestions.
- Add next PR advancement metadata.
- Add project completion detection.
- Add fix retry route metadata.
- Do not execute git mutation in-run.

## Prompt255 implemented MVP completion metadata

Prompt255 completed the synthetic approve-path MVP loop as metadata.

Validated synthetic path:
- project input
- analysis summary
- roadmap PR queue
- PR prompt generation
- Codex handoff readiness
- Codex result ingestion
- review approve decision
- commit/next PR metadata
- project_complete

Current next milestone:
- Validate failed-result fix route.
- Validate multi-PR next_pr_available path.
- Add explicit scenario mode for MVP verification.
- Keep all mutation and external execution disabled.

## Prompt256 implemented MVP scenario modes

Prompt256 added scenario selection and scenario result matrix validation.

Validated metadata capability:
- approve_single_pr_project_complete
- failed_result_fix_route
- approve_multi_pr_next_pr_available

Current next milestone:
- Add explicit real dev-loop input readiness.
- Use explicit project request / analysis / roadmap PR queue / active PR / Codex result metadata.
- Keep synthetic seeds only as fallback dry-run verification.

## Prompt257 implemented explicit real input readiness

Prompt257 added readiness surfaces for explicit real dev-loop input.

Current capability:
- Detect explicit project request / analysis / roadmap PR queue / active PR / scenario / Codex result metadata.
- Classify real-input path readiness.
- Preserve synthetic MVP fallback when no explicit input is present.

Current next milestone:
- Add explicit real input injection / override metadata for dry-run verification.
- Verify explicit input can drive PR prompt generation and Codex handoff readiness without synthetic seed reliance.
