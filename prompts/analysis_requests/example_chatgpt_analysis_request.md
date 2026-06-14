# ChatGPT Analysis Request — analysis-example-001

ANALYSIS REQUEST: analysis-example-001
Project goal: Advance codex-local-runner toward project-level autonomous development
Current capability boundary: two_executable_task_kinds_add_function_and_add_file_live_proven

Answer these questions:
  - What is complete?
  - What is missing?
  - What should be implemented next?

Return ONE JSON object with schema_version="analysis_artifact_v1" and fields:
  request_id, source, status, current_state_summary, confirmed_completed[],
  missing_gaps[], recommended_next_action, recommended_prompts[] (each: prompt_id,
  title, body, expected_tag, expected_report_path, expected_summary_path),
  evaluation_score_out_of_100, risk_notes[].
recommended_next_action must be one of: ['generate_prompt_batch', 'continue_existing_batch', 'manual_review_required'].
At most 10 recommended_prompts; each body must be non-empty.
Do NOT include secrets, credentials, tokens, or cookies.
Save the JSON to an analysis artifact file; the runner validates it offline.

Context files to consider:
  - artifacts/autonomous_runtime/prompt656_summary.md

## Machine-readable request
```json
{
  "allowed_next_actions": [
    "generate_prompt_batch",
    "continue_existing_batch",
    "manual_review_required"
  ],
  "context_files": [
    "artifacts/autonomous_runtime/prompt656_summary.md"
  ],
  "current_capability_boundary": "two_executable_task_kinds_add_function_and_add_file_live_proven",
  "project_goal": "Advance codex-local-runner toward project-level autonomous development",
  "questions": [
    "What is complete?",
    "What is missing?",
    "What should be implemented next?"
  ],
  "request_id": "analysis-example-001",
  "required_output_schema": "analysis_artifact_v1",
  "schema_version": "analysis_request_v1"
}
```
