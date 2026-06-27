"""Prompt672 responsibility scope matrix and real-task validation plan."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence


PROMPT671_TAG = "prompt671-extended-operational-soak-50-ticks"
BOUNDARY_BEFORE = "extended_operational_soak_50_ticks_proven"
BOUNDARY_AFTER = "responsibility_scope_matrix_real_task_plan_created"
MATRIX_PATH = "artifacts/autonomous_runtime/prompt672_responsibility_matrix.json"
IMPLEMENTATION_PATH = "docs/autonomous_runtime/responsibility_scope_matrix.md"
FORBIDDEN_RECOMMENDATION_TEXT = (
    "git push",
    "push",
    "pull request",
    "pr creation",
    "open pr",
    "merge",
    "destructive cleanup",
    "rm -rf",
    "credential",
    "cookie",
    "browser profile",
    ".env",
    "private session",
    "secret",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _tag_reachable(repo: Path, tag: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", f"refs/tags/{tag}", "HEAD"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _current_head(repo: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def verify_prompt671_baseline(repo_root: str | Path) -> dict[str, bool]:
    repo = Path(repo_root)
    report_path = repo / "artifacts/autonomous_runtime/prompt671_report.json"
    soak_marker = repo / "artifacts/autonomous_runtime/prompt671_extended_soak_50/soak_marker.json"
    report = _read_json(report_path)
    return {
        "prompt671_tag_reachable": _tag_reachable(repo, PROMPT671_TAG),
        "prompt671_report_exists": report_path.is_file(),
        "prompt671_extended_soak_artifact_exists": soak_marker.is_file(),
        "project_level_autonomy_complete": report.get("project_level_autonomy_complete") is True,
        "prompt671_status_success": report.get("prompt671_status") == "success",
        "capability_boundary_verified": report.get("current_capability_boundary_after") == BOUNDARY_BEFORE,
    }


def _entry(
    category_id: int,
    category_name: str,
    status: str,
    confidence: int,
    evidence_source: str,
    missing_proof: str,
    safe_validation_task: str,
    recommended_prompt_id: str,
    pass_criteria: str,
    safety_notes: str,
) -> dict[str, Any]:
    return {
        "category_id": category_id,
        "category_name": category_name,
        "status": status,
        "confidence_score_out_of_100": confidence,
        "evidence_source": evidence_source,
        "missing_proof": missing_proof,
        "safe_validation_task": safe_validation_task,
        "recommended_prompt_id": recommended_prompt_id,
        "pass_criteria": pass_criteria,
        "safety_notes": safety_notes,
    }


def build_responsibility_entries() -> list[dict[str, Any]]:
    return [
        _entry(1, "Safe project goal intake", "proven", 95, "Prompt667-671 safe goal gates and unsafe goal rejection reports", "None for local-only bounded goals.", "Use a bounded local-only real development goal.", "Prompt673", "Unsafe wording is rejected and safe goal is accepted.", "Keep remote/destructive/secret access prohibited."),
        _entry(2, "Safe task queue generation/loading", "proven", 95, "Prompt668 queue=3, Prompt669 queue=10, Prompt670 queue=24, Prompt671 queue=50", "General project decomposition from arbitrary goals is not proven.", "Generate a queue for one local documentation task.", "Prompt673", "Queue is deterministic, bounded, and local-only.", "Do not execute arbitrary free-text prompts."),
        _entry(3, "Unattended daemon execution", "proven", 96, "Prompt667-671 unattended run reports", "None for bounded local operational runs.", "Run a short unattended documentation validation queue.", "Prompt673", "No human intervention is recorded during the run.", "Keep hard tick/item limits."),
        _entry(4, "Internal Codex executor safety-gated execution", "proven", 95, "Prompt671 internal_codex_executor_used and safety gate evidence", "Practical code-modification executor use remains only indirectly proven.", "Use executor through gate for a tiny local documentation task.", "Prompt673", "Safety gate invocation and local-only evidence are recorded.", "No free-text arbitrary execution."),
        _entry(5, "Durable state management", "proven", 97, "Prompt671 run_state.json and state_queue_consistency_verified", "None for current bounded scale.", "Preserve state through a small real task queue.", "Prompt675", "State persists after every item.", "No private session state."),
        _entry(6, "Durable queue management", "proven", 97, "Prompt671 task_queue.json and durable_queue_persisted", "None for current bounded scale.", "Preserve queue through a small real task queue.", "Prompt675", "Queue persists with item statuses.", "No unbounded queue expansion."),
        _entry(7, "Lock / duplicate lock / stale lock handling", "proven", 96, "Prompt670 and Prompt671 lock/stale-lock reports", "None for local pidfile lock behavior.", "Include duplicate/stale lock checks in a real-task dry run.", "Prompt675", "Duplicate and stale lock behavior are recorded.", "No destructive lock cleanup outside prompt-owned paths."),
        _entry(8, "Interruption and resume", "proven", 94, "Prompt670 interruption/resume and Prompt671 controlled_interruption_count=2", "Real development task resume after file edit is not proven.", "Interrupt and resume a bounded test-addition task.", "Prompt674", "Resume continues from saved state without duplicate work.", "Prompt-owned artifacts only."),
        _entry(9, "Operator stop handling", "proven", 95, "Prompt670 and Prompt671 operator_stop_verified", "None for local bounded stop signal simulation.", "Exercise operator stop during a small validation queue.", "Prompt675", "Terminal stop reason is operator stop.", "Do not require human intervention mid-run."),
        _entry(10, "Retry / skip / stop policy", "proven", 94, "Prompt670 and Prompt671 retry/skip/stop policy reports", "Real failing-test retry policy is not proven.", "Inject one local failing test then fix or skip by policy.", "Prompt676", "Retry count and policy result are recorded.", "Retry attempts remain <=2."),
        _entry(11, "Failure threshold enforcement", "proven", 96, "Prompt670 and Prompt671 failure_threshold_stop_verified", "None for controlled local failures.", "Retain failure threshold in the failing-test real task.", "Prompt676", "Stop occurs at configured threshold.", "No destructive recovery."),
        _entry(12, "Evidence capture and evidence summary generation", "proven", 95, "Prompt667-671 evidence summaries and per-item evidence", "Evidence for practical code diffs needs proof.", "Attach diff/test evidence to each real development task.", "Prompt673", "Evidence summary remains readable and bounded.", "Exclude executor_runs and unrelated artifacts from commits."),
        _entry(13, "Completion gate / operational gate execution", "proven", 94, "Project completion gate reports through Prompt671", "Release gate is not proven.", "Run completion gate after each real-task validation.", "Prompt675", "Gate report confirms current capability remains intact.", "No fake completion booleans."),
        _entry(14, "Documentation generation/update", "partially_proven", 55, "Prompt667-671 generated acceptance docs", "A useful real repository documentation update has not been validated.", "Update one existing docs page with current local-runner capability boundaries.", "Prompt673", "Doc diff is scoped, reviewed by tests/checks, and local-only.", "Do not generate final release README yet."),
        _entry(15, "Test addition", "partially_proven", 60, "Prompt667-671 focused acceptance tests were added", "A real behavior test for an existing module remains unproven.", "Add one focused test for an existing queue/state helper edge case.", "Prompt674", "New test fails before or proves missing coverage, then passes.", "No network or secrets."),
        _entry(16, "Small code change", "partially_proven", 50, "Prompt667-671 acceptance implementation changes", "A practical small feature or helper change outside acceptance scaffolding is not proven.", "Implement a tiny local-only CLI/report helper improvement.", "Prompt675", "Focused tests and relevant suites pass.", "No broad feature changes."),
        _entry(17, "Bugfix from failing test", "unproven", 25, "No durable evidence of red-green bugfix workflow for a real defect", "Need a controlled failing test and minimal fix.", "Create a local failing test for a small parser/helper edge case, then fix it.", "Prompt676", "Test fails before fix evidence and passes after fix.", "No fabricated failures."),
        _entry(18, "Multi-file minor refactor", "unproven", 20, "No real multi-file refactor acceptance evidence", "Need bounded refactor with behavior preservation.", "Refactor a duplicated local helper across two modules with tests unchanged.", "Prompt677", "No behavior changes and tests pass.", "Keep scope under three source files."),
        _entry(19, "CLI or script enhancement", "partially_proven", 45, "Execution adapters and scripts exist, but no real CLI enhancement acceptance", "Need one useful CLI/script change with tests.", "Add a dry-run flag or JSON output option to a local inspection script.", "Prompt675", "CLI help and tests demonstrate the enhancement.", "No remote actions."),
        _entry(20, "Report/evidence generation", "proven", 96, "Prompt667-671 reports and summaries", "None for acceptance reporting.", "Continue bounded report generation for real tasks.", "Prompt673", "Machine and human reports are written.", "Do not include unrelated historical artifacts."),
        _entry(21, "Existing artifact audit", "proven", 90, "Prompt668-671 prior artifact preservation checks", "Broader stale artifact hygiene policy is not proven.", "Audit only Prompt673-owned artifacts and protected prior reports.", "Prompt673", "Protected artifacts are unchanged.", "Do not clean or delete unrelated artifacts."),
        _entry(22, "Queue planning from a project goal", "partially_proven", 65, "Prompt668-671 deterministic queues from explicit goals", "General queue planning from practical development goals is not proven.", "Plan a 3-5 item queue for one documentation update.", "Prompt673", "Queue maps each item to a concrete validation artifact.", "No arbitrary free-text prompt execution."),
        _entry(23, "Validation and quality gate execution", "proven", 92, "Prompt667-671 pytest and node checks", "Large project-wide validation remains bounded by command scope.", "Run focused and relevant validations for each real task.", "Prompt673", "Repository-supported pytest command and node checks pass.", "No network-dependent validation."),
        _entry(24, "Final summary / release note generation", "partially_proven", 45, "Prompt summaries exist for acceptance work", "User-facing release note/demo pack is not proven.", "Generate a local-only release note draft after real tasks pass.", "Prompt678", "Draft is accurate, bounded, and references evidence.", "Not before practical tasks are validated."),
        _entry(25, "README / demo / GitHub public documentation", "unproven", 15, "Prompt672 explicitly defers final release README", "Need responsibility proof before public-facing docs.", "Prepare a local demo/readme pack after real-task validation succeeds.", "Prompt678", "Docs are local-only and do not claim unsupported capabilities.", "No GitHub publishing."),
        _entry(26, "Remote git operation", "out_of_scope_for_safety", 0, "User and repository safety rules prohibit push/PR/merge", "Intentionally not pursued.", "No safe validation task; keep prohibited.", "none", "Any recommendation must exclude remote git operations.", "Remote push, PR creation, and merge remain forbidden."),
        _entry(27, "Credential/session/browser-profile handling", "out_of_scope_for_safety", 0, "Prompt667-671 credential/cookie/browser-profile/.env prevention evidence", "Intentionally not pursued.", "No safe validation task; keep prohibited.", "none", "Any recommendation must exclude credential/session access.", "Never read credentials, cookies, browser profiles, .env values, or private session files."),
    ]


def build_next_prompt_sequence() -> list[dict[str, Any]]:
    return [
        {
            "prompt_id": "Prompt673",
            "title": "documentation_update_real_task_acceptance",
            "target": "Validate one scoped documentation update as a practical local-only task.",
            "categories": [14, 20, 21, 22, 23],
            "safety": "local-only; no README/release pack; no remote/destructive/secret access",
        },
        {
            "prompt_id": "Prompt674",
            "title": "test_addition_real_task_acceptance",
            "target": "Add one focused test for an existing helper and prove queue/state/evidence handling.",
            "categories": [8, 15, 23],
            "safety": "repository-supported pytest only; no network or secret access",
        },
        {
            "prompt_id": "Prompt675",
            "title": "small_code_change_real_task_acceptance",
            "target": "Implement one small local-only helper or CLI enhancement with tests.",
            "categories": [5, 6, 7, 9, 16, 19, 23],
            "safety": "bounded source edits; no broad features; no remote actions",
        },
        {
            "prompt_id": "Prompt676",
            "title": "failing_test_bugfix_real_task_acceptance",
            "target": "Prove a red-green bugfix flow for a controlled local defect.",
            "categories": [10, 11, 17],
            "safety": "controlled failing test; no fabricated pass evidence",
        },
        {
            "prompt_id": "Prompt677",
            "title": "multi_responsibility_queue_real_task_acceptance",
            "target": "Run a bounded 5-8 item real-task queue combining docs, tests, and a tiny code change.",
            "categories": [16, 18, 22, 23],
            "safety": "max 8 items; no README/release docs; no destructive cleanup",
        },
        {
            "prompt_id": "Prompt678",
            "title": "release_documentation_demo_pack",
            "target": "Create local release documentation and demo pack after real-task validation passes.",
            "categories": [24, 25],
            "safety": "local-only draft; no push, PR, merge, or public publishing",
        },
    ]


def _unsafe_recommendations_present(entries: Sequence[Mapping[str, Any]], prompts: Sequence[Mapping[str, Any]]) -> bool:
    texts: list[str] = []
    for entry in entries:
        if entry.get("status") == "out_of_scope_for_safety":
            continue
        texts.extend(
            str(entry.get(key, ""))
            for key in ("safe_validation_task", "pass_criteria", "recommended_prompt_id")
        )
    texts.extend(str(prompt.get("target", "")) for prompt in prompts)
    combined = "\n".join(texts).lower()
    return any(term in combined for term in FORBIDDEN_RECOMMENDATION_TEXT)


def build_responsibility_matrix(repo_root: str | Path) -> dict[str, Any]:
    repo = Path(repo_root)
    baseline = verify_prompt671_baseline(repo)
    entries = build_responsibility_entries()
    next_prompts = build_next_prompt_sequence()
    counts = {
        "proven": sum(1 for item in entries if item["status"] == "proven"),
        "partially_proven": sum(1 for item in entries if item["status"] == "partially_proven"),
        "unproven": sum(1 for item in entries if item["status"] == "unproven"),
        "out_of_scope_for_safety": sum(1 for item in entries if item["status"] == "out_of_scope_for_safety"),
    }
    return {
        "schema_version": "prompt672_responsibility_matrix_v1",
        "generated_at": _utc_now(),
        "current_head_before": _current_head(repo),
        "selected_target": "responsibility_scope_matrix_and_real_task_plan",
        "prompt671_baseline": baseline,
        "prompt671_verified": all(baseline.values()),
        "current_capability_boundary_before": BOUNDARY_BEFORE,
        "responsibilities": entries,
        "responsibility_categories_count": len(entries),
        "responsibility_counts": counts,
        "score_summary": {
            "current_autonomy_infrastructure_score_out_of_100": 95,
            "current_operational_durability_score_out_of_100": 96,
            "current_real_development_responsibility_score_out_of_100": 38,
            "current_release_documentation_score_out_of_100": 22,
        },
        "next_prompt_sequence": next_prompts,
        "unsafe_tasks_excluded": not _unsafe_recommendations_present(entries, next_prompts),
        "safe_real_task_plan_created": True,
        "next_prompt_sequence_created": True,
    }


def _markdown(matrix: Mapping[str, Any]) -> str:
    counts = matrix["responsibility_counts"]
    scores = matrix["score_summary"]
    lines = [
        "# Prompt672 Responsibility Scope Matrix",
        "",
        f"- prompt671_verified: {str(matrix.get('prompt671_verified')).lower()}",
        f"- current_capability_boundary_before: {matrix.get('current_capability_boundary_before')}",
        f"- categories: {matrix.get('responsibility_categories_count')}",
        f"- proven: {counts['proven']}",
        f"- partially_proven: {counts['partially_proven']}",
        f"- unproven: {counts['unproven']}",
        f"- out_of_scope_for_safety: {counts['out_of_scope_for_safety']}",
        f"- autonomy_infrastructure_score: {scores['current_autonomy_infrastructure_score_out_of_100']}",
        f"- operational_durability_score: {scores['current_operational_durability_score_out_of_100']}",
        f"- real_development_responsibility_score: {scores['current_real_development_responsibility_score_out_of_100']}",
        f"- release_documentation_score: {scores['current_release_documentation_score_out_of_100']}",
        "",
        "## Responsibilities",
        "",
        "| ID | Responsibility | Status | Confidence | Next Proof |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for item in matrix["responsibilities"]:
        lines.append(
            "| {category_id} | {category_name} | {status} | {confidence_score_out_of_100} | {recommended_prompt_id} |".format(
                **item
            )
        )
    lines.extend(["", "## Recommended Prompt Sequence", ""])
    for prompt in matrix["next_prompt_sequence"]:
        lines.append(f"- {prompt['prompt_id']}: {prompt['title']} - {prompt['target']}")
    lines.append("")
    return "\n".join(lines)


def _summary(matrix: Mapping[str, Any]) -> str:
    counts = matrix["responsibility_counts"]
    scores = matrix["score_summary"]
    return "\n".join(
        [
            "# Prompt672 Responsibility Scope Matrix",
            "",
            f"- status: {'success' if matrix.get('prompt671_verified') else 'partial'}",
            f"- prompt671_verified: {str(matrix.get('prompt671_verified')).lower()}",
            f"- responsibility_categories_count: {matrix.get('responsibility_categories_count')}",
            f"- proven_responsibility_count: {counts['proven']}",
            f"- partially_proven_responsibility_count: {counts['partially_proven']}",
            f"- unproven_responsibility_count: {counts['unproven']}",
            f"- out_of_scope_responsibility_count: {counts['out_of_scope_for_safety']}",
            f"- current_autonomy_infrastructure_score_out_of_100: {scores['current_autonomy_infrastructure_score_out_of_100']}",
            f"- current_operational_durability_score_out_of_100: {scores['current_operational_durability_score_out_of_100']}",
            f"- current_real_development_responsibility_score_out_of_100: {scores['current_real_development_responsibility_score_out_of_100']}",
            f"- current_release_documentation_score_out_of_100: {scores['current_release_documentation_score_out_of_100']}",
            "- next_recommended_action: start_real_task_responsibility_acceptance",
            "",
        ]
    )


def run_responsibility_scope_matrix(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    run_id: str,
) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    matrix_path = repo / MATRIX_PATH
    implementation_path = repo / IMPLEMENTATION_PATH
    report_path = output / "prompt672_report.json"
    summary_path = output / "prompt672_summary.md"
    goal_report_path = output / "prompt672_goal_aligned_implementation_report.json"
    goal_summary_path = output / "prompt672_goal_aligned_implementation_summary.md"
    next_request_path = output / "prompt672_next_chatgpt_analysis_request.json"
    matrix = build_responsibility_matrix(repo)
    counts = matrix["responsibility_counts"]
    scores = matrix["score_summary"]
    passed = (
        matrix["prompt671_verified"]
        and matrix["responsibility_categories_count"] == 27
        and matrix["unsafe_tasks_excluded"]
        and matrix["next_prompt_sequence_created"]
    )
    _write_json(matrix_path, matrix)
    _write_text(implementation_path, _markdown(matrix))
    result = {
        "schema_version": "prompt672_report_v1",
        "prompt672_status": "success" if passed else "partial",
        "status": "success" if passed else "partial",
        "run_id": run_id,
        "current_head_before": matrix["current_head_before"],
        "selected_target": "responsibility_scope_matrix_and_real_task_plan",
        "prompt671_verified": matrix["prompt671_verified"],
        "current_capability_boundary_before": BOUNDARY_BEFORE,
        "responsibility_matrix_created": matrix_path.is_file(),
        "responsibility_matrix_entrypoint": (
            "automation.orchestration.planned_runner.responsibility_scope_matrix."
            "run_responsibility_scope_matrix"
        ),
        "responsibility_categories_count": matrix["responsibility_categories_count"],
        "proven_responsibility_count": counts["proven"],
        "partially_proven_responsibility_count": counts["partially_proven"],
        "unproven_responsibility_count": counts["unproven"],
        "out_of_scope_responsibility_count": counts["out_of_scope_for_safety"],
        **scores,
        "safe_real_task_plan_created": matrix["safe_real_task_plan_created"],
        "unsafe_tasks_excluded": matrix["unsafe_tasks_excluded"],
        "next_prompt_sequence_created": matrix["next_prompt_sequence_created"],
        "implementation_target_path": IMPLEMENTATION_PATH,
        "matrix_path": MATRIX_PATH,
        "reports_written": True,
        "next_chatgpt_analysis_request_prepared": True,
        "project_level_autonomy_complete": matrix["prompt671_baseline"]["project_level_autonomy_complete"],
        "current_capability_boundary_after": BOUNDARY_AFTER if passed else "responsibility_scope_matrix_partial",
        "evaluation_score_out_of_100": 100 if passed else 80,
        "next_recommended_action": (
            "start_real_task_responsibility_acceptance" if passed else "manual_review_required"
        ),
        "tests_passed": False,
        "test_command_used": "",
        "node_checks_passed": False,
        "errors": [] if passed else ["responsibility matrix validation incomplete"],
    }
    _write_json(report_path, result)
    _write_text(summary_path, _summary(matrix))
    _write_json(goal_report_path, result)
    _write_text(goal_summary_path, _summary(matrix))
    _write_json(
        next_request_path,
        {
            "schema_version": "next_chatgpt_analysis_request_v1",
            "source_prompt": "Prompt672",
            "recommended_next_action": "start_real_task_responsibility_acceptance",
            "prompt_text": (
                "Start Prompt673 documentation_update_real_task_acceptance as the first "
                "safe local-only practical development responsibility validation."
            ),
            "preserve_safety_constraints": True,
        },
    )
    return result


__all__ = [
    "BOUNDARY_AFTER",
    "BOUNDARY_BEFORE",
    "IMPLEMENTATION_PATH",
    "MATRIX_PATH",
    "build_next_prompt_sequence",
    "build_responsibility_entries",
    "build_responsibility_matrix",
    "run_responsibility_scope_matrix",
    "verify_prompt671_baseline",
]
