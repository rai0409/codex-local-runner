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
