"""External analysis handoff controller (Prompt657).

A safe, offline, deterministic ARTIFACT-BASED handoff between browser-side analysis
(e.g. ChatGPT) and repo-side implementation (Claude Code / Codex via the existing
prompt-batch controller). It does NOT automate any browser, call any API, perform any
network I/O, store credentials/cookies, or execute prompt text. It only:

1. builds a ChatGPT *analysis request* file (what to analyze + required output schema),
2. validates the *analysis artifact* a human pastes back from ChatGPT,
3. converts an accepted artifact into a Prompt655-compatible prompt batch,
4. scores an artifact and emits the next deterministic ChatGPT instruction.

All validation is non-raising; paths are safety-checked (no absolute, no traversal).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from automation.orchestration.planned_runner.project_prompt_batch import (
    MAX_PROMPTS_CAP,
    validate_prompt_batch,
)

ANALYSIS_REQUEST_SCHEMA = "analysis_request_v1"
ANALYSIS_ARTIFACT_SCHEMA = "analysis_artifact_v1"
MAX_RECOMMENDED_PROMPTS = MAX_PROMPTS_CAP  # <= 10

ALLOWED_NEXT_ACTIONS = (
    "generate_prompt_batch",
    "continue_existing_batch",
    "manual_review_required",
)

_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_TAG_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_SLUGIFY = re.compile(r"[^a-z0-9._-]+")


def _txt(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [_txt(v) for v in value if _txt(v)]


def _is_safe_relpath(value: str) -> bool:
    text = _txt(value)
    if not text or text.startswith("/") or text.startswith("~"):
        return False
    if ".." in Path(text).parts or "\x00" in text:
        return False
    return True


def _is_safe_tag(value: str) -> bool:
    return bool(_TAG_PATTERN.match(_txt(value)))


def _slug(value: Any) -> str:
    text = _txt(value).lower()
    if not text:
        return ""
    return _SLUGIFY.sub("-", text).strip("-._")[:64]


# --------------------------------------------------------------------------- request
def validate_analysis_request(payload: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        return {}, ["analysis request must be a JSON object"]
    request_id = _txt(payload.get("request_id"))
    if not request_id or not _SLUG_PATTERN.match(request_id):
        errors.append("request_id must match ^[a-z0-9][a-z0-9._-]{0,63}$")
    project_goal = _txt(payload.get("project_goal"))
    if not project_goal:
        errors.append("project_goal is required")
    questions = _str_list(payload.get("questions"))
    if not questions:
        errors.append("questions must be a non-empty list")
    allowed = _str_list(payload.get("allowed_next_actions")) or list(ALLOWED_NEXT_ACTIONS)
    bad = [a for a in allowed if a not in ALLOWED_NEXT_ACTIONS]
    if bad:
        errors.append(f"allowed_next_actions contains unsupported values: {bad}")
    context_files = _str_list(payload.get("context_files"))
    for cf in context_files:
        if not _is_safe_relpath(cf):
            errors.append(f"context_files path is not repo-relative safe: {cf!r}")
    request = {
        "schema_version": ANALYSIS_REQUEST_SCHEMA,
        "request_id": request_id,
        "project_goal": project_goal,
        "current_capability_boundary": _txt(payload.get("current_capability_boundary")),
        "questions": questions,
        "required_output_schema": _txt(payload.get("required_output_schema"), default=ANALYSIS_ARTIFACT_SCHEMA),
        "allowed_next_actions": allowed,
        "context_files": context_files,
    }
    return request, errors


def prepare_next_chatgpt_instruction(request: Mapping[str, Any]) -> str:
    """Deterministic instruction telling ChatGPT exactly what artifact to return."""
    req, errors = validate_analysis_request(request)
    if errors:
        return "INVALID ANALYSIS REQUEST:\n" + "\n".join(f"- {e}" for e in errors)
    lines = [
        f"ANALYSIS REQUEST: {req['request_id']}",
        f"Project goal: {req['project_goal']}",
        f"Current capability boundary: {req['current_capability_boundary'] or '(unspecified)'}",
        "",
        "Answer these questions:",
        *[f"  - {q}" for q in req["questions"]],
        "",
        f"Return ONE JSON object with schema_version=\"{req['required_output_schema']}\" and fields:",
        "  request_id, source, status, current_state_summary, confirmed_completed[],",
        "  missing_gaps[], recommended_next_action, recommended_prompts[] (each: prompt_id,",
        "  title, body, expected_tag, expected_report_path, expected_summary_path),",
        "  evaluation_score_out_of_100, risk_notes[].",
        f"recommended_next_action must be one of: {list(req['allowed_next_actions'])}.",
        f"At most {MAX_RECOMMENDED_PROMPTS} recommended_prompts; each body must be non-empty.",
        "Do NOT include secrets, credentials, tokens, or cookies.",
        "Save the JSON to an analysis artifact file; the runner validates it offline.",
    ]
    if req["context_files"]:
        lines += ["", "Context files to consider:", *[f"  - {c}" for c in req["context_files"]]]
    return "\n".join(lines) + "\n"


def create_analysis_request(payload: Mapping[str, Any], output_path: str | Path) -> dict[str, Any]:
    """Validate a request and write a human-readable request file. No network."""
    request, errors = validate_analysis_request(payload)
    out_text = _txt(output_path)
    if not out_text or not _is_safe_relpath(out_text):
        errors = errors + ["output_path must be a repo-relative safe path (no absolute, no '..')"]
    if errors:
        return {"status": "blocked", "errors": errors, "output_path": out_text, "request": request}
    body = (
        f"# ChatGPT Analysis Request — {request['request_id']}\n\n"
        + prepare_next_chatgpt_instruction(request)
        + "\n## Machine-readable request\n```json\n"
        + json.dumps(request, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n```\n"
    )
    out = Path(out_text)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    return {"status": "success", "errors": [], "output_path": out.as_posix(), "request": request}


# --------------------------------------------------------------------------- artifact
def _validate_recommended_prompt(raw: Any, index: int, seen: set[str], errors: list[str]) -> dict[str, Any]:
    loc = f"recommended_prompts[{index}]"
    if not isinstance(raw, Mapping):
        errors.append(f"{loc} must be an object")
        raw = {}
    prompt_id = _txt(raw.get("prompt_id"))
    if not prompt_id or not _SLUG_PATTERN.match(prompt_id):
        errors.append(f"{loc}.prompt_id must match ^[a-z0-9][a-z0-9._-]{{0,63}}$")
    elif prompt_id in seen:
        errors.append(f"{loc}.prompt_id duplicate: {prompt_id}")
    else:
        seen.add(prompt_id)
    body = raw.get("body")
    if not isinstance(body, str) or not body.strip():
        errors.append(f"{loc}.body must be a non-empty string")
        body = "" if not isinstance(body, str) else body
    expected_tag = _txt(raw.get("expected_tag"))
    if expected_tag and not _is_safe_tag(expected_tag):
        errors.append(f"{loc}.expected_tag is not a safe tag name: {expected_tag!r}")
    expected_report = _txt(raw.get("expected_report_path"))
    if expected_report and not _is_safe_relpath(expected_report):
        errors.append(f"{loc}.expected_report_path must be repo-relative safe: {expected_report!r}")
    expected_summary = _txt(raw.get("expected_summary_path"))
    if expected_summary and not _is_safe_relpath(expected_summary):
        errors.append(f"{loc}.expected_summary_path must be repo-relative safe: {expected_summary!r}")
    pc = raw.get("pass_conditions", {})
    status_field = _txt(pc.get("status_field")) if isinstance(pc, Mapping) else ""
    status_value = _txt(pc.get("status_value")) if isinstance(pc, Mapping) else ""
    return {
        "prompt_id": prompt_id, "title": _txt(raw.get("title")), "body": body,
        "expected_tag": expected_tag, "expected_report_path": expected_report,
        "expected_summary_path": expected_summary,
        "required_tests": _str_list(raw.get("required_tests")),
        "pass_conditions": {"status_field": status_field, "status_value": status_value},
    }


def validate_analysis_artifact(payload: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        return {}, ["analysis artifact must be a JSON object"]
    schema = _txt(payload.get("schema_version"))
    if schema != ANALYSIS_ARTIFACT_SCHEMA:
        errors.append(f"schema_version must be {ANALYSIS_ARTIFACT_SCHEMA!r}")
    request_id = _txt(payload.get("request_id"))
    if not request_id or not _SLUG_PATTERN.match(request_id):
        errors.append("request_id must match ^[a-z0-9][a-z0-9._-]{0,63}$")
    source = _txt(payload.get("source"))
    if not source:
        errors.append("source is required")
    status = _txt(payload.get("status"))
    if not status:
        errors.append("status is required")
    current_state_summary = _txt(payload.get("current_state_summary"))
    if not current_state_summary:
        errors.append("current_state_summary is required")
    recommended_next_action = _txt(payload.get("recommended_next_action"))
    if recommended_next_action not in ALLOWED_NEXT_ACTIONS:
        errors.append(f"recommended_next_action must be one of {list(ALLOWED_NEXT_ACTIONS)}")

    raw_prompts = payload.get("recommended_prompts", [])
    prompts: list[dict[str, Any]] = []
    if raw_prompts is not None:
        if not isinstance(raw_prompts, list):
            errors.append("recommended_prompts must be a list")
        else:
            if len(raw_prompts) > MAX_RECOMMENDED_PROMPTS:
                errors.append(f"recommended_prompts count {len(raw_prompts)} exceeds cap {MAX_RECOMMENDED_PROMPTS}")
            seen: set[str] = set()
            for i, rp in enumerate(raw_prompts):
                prompts.append(_validate_recommended_prompt(rp, i, seen, errors))
    if recommended_next_action == "generate_prompt_batch" and not prompts:
        errors.append("recommended_next_action=generate_prompt_batch requires recommended_prompts")

    score = payload.get("evaluation_score_out_of_100", 0)
    try:
        score_int = int(score)
    except (TypeError, ValueError):
        score_int = 0
        errors.append("evaluation_score_out_of_100 must be an integer")
    if not (0 <= score_int <= 100):
        errors.append("evaluation_score_out_of_100 must be in [0, 100]")

    artifact = {
        "schema_version": ANALYSIS_ARTIFACT_SCHEMA,
        "request_id": request_id,
        "source": source,
        "status": status,
        "current_state_summary": current_state_summary,
        "confirmed_completed": _str_list(payload.get("confirmed_completed")),
        "missing_gaps": _str_list(payload.get("missing_gaps")),
        "recommended_next_action": recommended_next_action,
        "recommended_prompts": prompts,
        "evaluation_score_out_of_100": score_int,
        "risk_notes": _str_list(payload.get("risk_notes")),
    }
    return artifact, errors


def load_analysis_artifact(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        return {"payload": {}, "errors": [f"artifact not found: {p.as_posix()}"]}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"payload": {}, "errors": [f"artifact unreadable/invalid JSON: {exc}"]}
    if not isinstance(payload, Mapping):
        return {"payload": {}, "errors": ["artifact must be a JSON object"]}
    return {"payload": dict(payload), "errors": []}


def evaluate_analysis_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    """Score an analysis artifact out of 100 with a breakdown. Deterministic."""
    norm, errors = validate_analysis_artifact(artifact)
    if errors:
        return {"status": "invalid", "passed": False, "score": 0, "errors": errors, "breakdown": {}}
    structure = 30  # validated schema/required fields present
    has_state = 20 if norm["current_state_summary"] else 0
    gaps_or_done = 20 if (norm["confirmed_completed"] or norm["missing_gaps"]) else 0
    actionable = 20 if (
        norm["recommended_next_action"] != "manual_review_required"
        and (norm["recommended_next_action"] != "generate_prompt_batch" or norm["recommended_prompts"])
    ) else 0
    risk = 10 if norm["risk_notes"] else 0
    score = structure + has_state + gaps_or_done + actionable + risk
    return {
        "status": "ok", "passed": True, "score": score, "errors": [],
        "breakdown": {
            "structure_valid": structure, "state_summary": has_state,
            "gaps_or_completed": gaps_or_done, "actionable_recommendation": actionable,
            "risk_notes": risk,
        },
        "self_reported_score": norm["evaluation_score_out_of_100"],
        "recommended_next_action": norm["recommended_next_action"],
    }


# ------------------------------------------------------------------ artifact -> batch
def analysis_artifact_to_prompt_batch(
    artifact: Mapping[str, Any], batch_dir: str | Path
) -> dict[str, Any]:
    """Convert a validated artifact into a Prompt655-compatible prompt batch.

    Writes one prompt file per recommended prompt INSIDE batch_dir and a manifest.json,
    then validates the manifest with the Prompt655 validator. Never executes anything."""
    norm, errors = validate_analysis_artifact(artifact)
    if errors:
        return {"status": "blocked", "reason": "invalid_artifact", "errors": errors,
                "batch_dir": _txt(batch_dir), "manifest_path": "", "prompt_files": []}
    if norm["recommended_next_action"] != "generate_prompt_batch":
        return {"status": "blocked", "reason": "recommended_next_action_not_generate_prompt_batch",
                "errors": [f"recommended_next_action is {norm['recommended_next_action']!r}"],
                "batch_dir": _txt(batch_dir), "manifest_path": "", "prompt_files": []}
    base = Path(batch_dir)
    base_text = _txt(batch_dir)
    if not base_text:
        return {"status": "blocked", "reason": "missing_batch_dir", "errors": ["batch_dir is required"],
                "batch_dir": "", "manifest_path": "", "prompt_files": []}
    base.mkdir(parents=True, exist_ok=True)

    manifest_prompts: list[dict[str, Any]] = []
    written: list[str] = []
    conv_errors: list[str] = []
    for index, rp in enumerate(norm["recommended_prompts"]):
        if not rp["expected_tag"]:
            conv_errors.append(f"recommended prompt {rp['prompt_id']} missing expected_tag (required for batch)")
        if not rp["expected_report_path"] or not rp["expected_summary_path"]:
            conv_errors.append(f"recommended prompt {rp['prompt_id']} missing expected report/summary path")
        fname = f"{index:03d}_{_slug(rp['prompt_id'])}.md"  # safe, inside batch dir
        (base / fname).write_text(
            f"# {rp['title'] or rp['prompt_id']}\n\n{rp['body']}\n", encoding="utf-8"
        )
        written.append((base / fname).as_posix())
        pc = rp["pass_conditions"]
        manifest_prompts.append({
            "prompt_id": rp["prompt_id"],
            "prompt_path": fname,
            "expected_tag": rp["expected_tag"],
            "expected_report_path": rp["expected_report_path"],
            "expected_summary_path": rp["expected_summary_path"],
            "required_tests": rp["required_tests"],
            "pass_conditions": {
                "status_field": pc["status_field"] or f"{rp['prompt_id']}_status",
                "status_value": pc["status_value"] or "success",
            },
        })

    manifest = {
        "batch_id": norm["request_id"],
        "goal": norm["current_state_summary"][:200] or f"batch from analysis {norm['request_id']}",
        "max_prompts": min(MAX_RECOMMENDED_PROMPTS, max(1, len(manifest_prompts))),
        "stop_on_failure": True,
        "require_clean_source_before_each_prompt": True,
        "require_commit_tag_per_prompt": True,
        "prompts": manifest_prompts,
        "source": "external_analysis_artifact",
    }
    manifest_path = base / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Prompt655 compatibility check.
    _, batch_errors = validate_prompt_batch(manifest, base)
    all_errors = conv_errors + [f"manifest invalid: {e}" for e in batch_errors]
    status = "success" if not all_errors else "blocked"
    return {
        "status": status,
        "reason": "converted" if status == "success" else "conversion_failed",
        "errors": all_errors,
        "batch_dir": base.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "prompt_files": written,
        "prompt655_compatible": not batch_errors,
    }


__all__ = [
    "ANALYSIS_REQUEST_SCHEMA",
    "ANALYSIS_ARTIFACT_SCHEMA",
    "ALLOWED_NEXT_ACTIONS",
    "MAX_RECOMMENDED_PROMPTS",
    "validate_analysis_request",
    "create_analysis_request",
    "prepare_next_chatgpt_instruction",
    "load_analysis_artifact",
    "validate_analysis_artifact",
    "evaluate_analysis_artifact",
    "analysis_artifact_to_prompt_batch",
]
