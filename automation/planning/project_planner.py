from __future__ import annotations

import json
from pathlib import Path
from pathlib import PurePosixPath
import subprocess
from typing import Any
from typing import Mapping

from orchestrator.policy_loader import load_change_categories_policy
from orchestrator.policy_loader import load_merge_gate_policy

PROJECT_BRIEF_FILENAME = "project_brief.json"
REPO_FACTS_FILENAME = "repo_facts.json"
ROADMAP_FILENAME = "roadmap.json"
PR_PLAN_FILENAME = "pr_plan.json"

_SOFT_FILE_CAP = 6
_DEFAULT_CREATED_AT = "1970-01-01T00:00:00+00:00"

_RISK_ORDER = {
    "low": 0,
    "medium": 1,
    "high": 2,
}

_DEFAULT_VALIDATION_BY_TIER = {
    "docs_only": (),
    "ci_only": ("python3 -m unittest discover -s tests",),
    "test_only": ("python3 -m unittest discover -s tests",),
    "contract_guard_only": ("python3 -m unittest discover -s tests",),
    "runtime_fix_low_risk": ("python3 -m unittest discover -s tests",),
    "runtime_fix_high_risk": ("python3 -m unittest discover -s tests",),
    "feature": ("python3 -m unittest discover -s tests",),
}


def _repo_root_from_path(path: str | Path | None) -> Path:
    if path is None:
        return Path(__file__).resolve().parents[2]
    return Path(path).resolve()


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y"}:
            return True
    return False


def _normalize_string_list(value: Any, *, sort_items: bool = False) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    if sort_items:
        return sorted(result)
    return result


def _normalize_repo_path(path_value: Any, *, repo_root: Path) -> str | None:
    text = _normalize_text(path_value)
    if not text:
        return None

    normalized = text.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]

    path = Path(normalized)
    if path.is_absolute():
        try:
            normalized = str(path.resolve().relative_to(repo_root)).replace("\\", "/")
        except Exception:
            return None

    normalized = normalized.strip("/")
    if not normalized:
        return None
    return normalized


def _git_stdout(repo_root: Path, args: tuple[str, ...]) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return None
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    return value or None


def _derive_default_branch(*, repo_root: Path, target_branch: str) -> str:
    remote_head = _git_stdout(repo_root, ("symbolic-ref", "--short", "refs/remotes/origin/HEAD"))
    if remote_head and "/" in remote_head:
        return remote_head.split("/")[-1]

    current_branch = _git_stdout(repo_root, ("rev-parse", "--abbrev-ref", "HEAD"))
    if current_branch and current_branch != "HEAD":
        return current_branch

    return target_branch or "main"


def _derive_source_of_truth_commit(*, repo_root: Path) -> str:
    commit = _git_stdout(repo_root, ("rev-parse", "HEAD"))
    return commit or "unknown"


def _load_merge_gate_policy_safe(repo_root: Path) -> dict[str, Any]:
    try:
        return load_merge_gate_policy(str(repo_root / "config" / "merge_gate.yaml"))
    except Exception:
        return {}


def _load_change_categories_policy_safe(repo_root: Path) -> dict[str, Any]:
    try:
        return load_change_categories_policy(str(repo_root / "config" / "change_categories.yaml"))
    except Exception:
        return {}


def _derive_current_branch_rules(policy: Mapping[str, Any]) -> list[str]:
    if not isinstance(policy, Mapping):
        return []

    auto_merge_categories = _normalize_string_list(policy.get("auto_merge_categories"), sort_items=True)
    write_authority = policy.get("write_authority") if isinstance(policy.get("write_authority"), Mapping) else {}
    retry_replan = policy.get("retry_replan") if isinstance(policy.get("retry_replan"), Mapping) else {}

    rules = [
        f"require_ci_green={str(bool(policy.get('require_ci_green', False))).lower()}",
        f"require_rubric_all_pass={str(bool(policy.get('require_rubric_all_pass', False))).lower()}",
        (
            "require_declared_equals_observed_category="
            f"{str(bool(policy.get('require_declared_equals_observed_category', False))).lower()}"
        ),
        (
            "require_no_forbidden_paths_touched="
            f"{str(bool(policy.get('require_no_forbidden_paths_touched', False))).lower()}"
        ),
        (
            "require_diff_size_within_limit="
            f"{str(bool(policy.get('require_diff_size_within_limit', False))).lower()}"
        ),
        "auto_merge_categories=" + (",".join(auto_merge_categories) if auto_merge_categories else "none"),
        (
            "write_authority.enabled="
            f"{str(bool(write_authority.get('enabled', False))).lower()}"
        ),
        (
            "write_authority.dry_run="
            f"{str(bool(write_authority.get('dry_run', False))).lower()}"
        ),
        (
            "write_authority.kill_switch="
            f"{str(bool(write_authority.get('kill_switch', False))).lower()}"
        ),
    ]

    max_attempts = retry_replan.get("max_attempts")
    if isinstance(max_attempts, bool):
        max_attempts = None
    if isinstance(max_attempts, int):
        rules.append(f"retry_replan.max_attempts={max_attempts}")
    elif isinstance(max_attempts, str) and max_attempts.strip().isdigit():
        rules.append(f"retry_replan.max_attempts={int(max_attempts.strip())}")

    return rules


def _derive_sensitive_paths(
    *,
    repo_root: Path,
    merge_gate_policy: Mapping[str, Any],
    change_categories_policy: Mapping[str, Any],
) -> list[str]:
    paths: set[str] = set()

    auto_progression = (
        merge_gate_policy.get("auto_progression")
        if isinstance(merge_gate_policy.get("auto_progression"), Mapping)
        else {}
    )
    paths.update(_normalize_string_list(auto_progression.get("runtime_sensitive_path_patterns"), sort_items=False))
    paths.update(_normalize_string_list(auto_progression.get("contract_sensitive_path_patterns"), sort_items=False))

    categories = (
        change_categories_policy.get("categories")
        if isinstance(change_categories_policy.get("categories"), Mapping)
        else {}
    )
    if categories:
        paths.add("config/change_categories.yaml")

    deterministic_candidates = [
        "config/change_categories.yaml",
        "config/merge_gate.yaml",
        "orchestrator/**",
        "orchestrator/github_backend.py",
        "orchestrator/ledger.py",
        "orchestrator/merge_executor.py",
        "orchestrator/rollback_executor.py",
        "scripts/operator_review_decision.py",
        "scripts/inspect_job.py",
        "scripts/build_operator_summary.py",
        "state/**",
    ]
    for candidate in deterministic_candidates:
        candidate_path = candidate.rstrip("/**")
        if (repo_root / candidate_path).exists():
            paths.add(candidate)

    return sorted(path for path in paths if path)


def _is_sensitive_path(path_value: str, *, sensitive_paths: list[str]) -> bool:
    normalized = path_value.replace("\\", "/").lstrip("./")
    if not normalized:
        return False

    path_obj = PurePosixPath(normalized)
    for pattern in sensitive_paths:
        text = pattern.strip()
        if not text:
            continue
        if normalized == text:
            return True
        if text.endswith("/**"):
            base = text[: -len("/**")].rstrip("/")
            if normalized == base or normalized.startswith(base + "/"):
                return True
        if path_obj.match(text):
            return True
    return False


def _subsystem_for_path(path_value: str) -> str:
    normalized = path_value.replace("\\", "/").lstrip("./")
    if normalized.startswith("docs/"):
        return "docs"
    if normalized.startswith("tests/"):
        return "tests"
    if normalized.startswith("automation/planning/") or normalized == "prompt_builder.py":
        return "planning"
    if normalized.startswith("scripts/"):
        return "scripts"
    if normalized.startswith("orchestrator/"):
        return "orchestrator"
    if normalized.startswith("config/"):
        return "config"
    if normalized.startswith("prompts/"):
        return "prompts"
    if normalized.startswith("adapters/"):
        return "adapters"
    if "/" in normalized:
        return normalized.split("/", 1)[0]
    return "root"


def _risk_bucket_for_path(path_value: str, *, sensitive_paths: list[str]) -> str:
    normalized = path_value.replace("\\", "/").lstrip("./")
    if _is_sensitive_path(normalized, sensitive_paths=sensitive_paths):
        return "high"
    if normalized.startswith("docs/") or normalized.endswith(".md"):
        return "low"
    return "medium"


def _tier_category_for_files(
    touched_files: list[str],
    *,
    sensitive_paths: list[str],
) -> str:
    if not touched_files:
        return "feature"

    if all(path.startswith("docs/") for path in touched_files):
        return "docs_only"
    if all(path.startswith("tests/") for path in touched_files):
        return "test_only"
    if all(path.startswith(".github/workflows/") for path in touched_files):
        return "ci_only"
    if all(path.startswith("docs/") or path.startswith("tests/") for path in touched_files):
        return "contract_guard_only"
    if any(_is_sensitive_path(path, sensitive_paths=sensitive_paths) for path in touched_files):
        return "runtime_fix_high_risk"
    if any(path.startswith("orchestrator/") or path.startswith("config/") for path in touched_files):
        return "runtime_fix_low_risk"
    return "feature"


def _split_files_for_slice(files: list[str], *, atomic: bool) -> list[list[str]]:
    if len(files) <= _SOFT_FILE_CAP or atomic:
        return [files]
    chunks: list[list[str]] = []
    for idx in range(0, len(files), _SOFT_FILE_CAP):
        chunks.append(files[idx : idx + _SOFT_FILE_CAP])
    return chunks


def _extract_work_items(intake: Mapping[str, Any], *, repo_root: Path) -> list[dict[str, Any]]:
    raw_items: Any = None
    for key in ("requested_changes", "work_items", "changes"):
        value = intake.get(key)
        if isinstance(value, list):
            raw_items = value
            break

    parsed: list[dict[str, Any]] = []
    if isinstance(raw_items, list):
        for index, raw in enumerate(raw_items, start=1):
            if not isinstance(raw, Mapping):
                continue
            title = _normalize_text(raw.get("summary"), default=_normalize_text(raw.get("title")))
            if not title:
                title = f"change-{index:02d}"

            touched_raw = raw.get("touched_files")
            if touched_raw is None:
                touched_raw = raw.get("files")
            if touched_raw is None:
                touched_raw = raw.get("paths")
            touched_files: list[str] = []
            if isinstance(touched_raw, (list, tuple)):
                for path_value in touched_raw:
                    normalized = _normalize_repo_path(path_value, repo_root=repo_root)
                    if normalized is None:
                        continue
                    touched_files.append(normalized)

            parsed.append(
                {
                    "summary": title,
                    "touched_files": sorted(set(touched_files)),
                    "acceptance_criteria": _normalize_string_list(raw.get("acceptance_criteria")),
                    "validation_commands": _normalize_string_list(raw.get("validation_commands")),
                    "rollback_notes": _normalize_text(raw.get("rollback_notes")),
                    "forbidden_files": _normalize_string_list(raw.get("forbidden_files"), sort_items=True),
                    "depends_on": _normalize_string_list(raw.get("depends_on"), sort_items=False),
                    "atomic": _normalize_bool(raw.get("atomic", False)),
                }
            )

    if parsed:
        return parsed

    fallback_touched: list[str] = []
    for key in ("changed_files", "requested_paths", "relevant_paths"):
        values = intake.get(key)
        if not isinstance(values, (list, tuple)):
            continue
        for value in values:
            normalized = _normalize_repo_path(value, repo_root=repo_root)
            if normalized is not None:
                fallback_touched.append(normalized)
        if fallback_touched:
            break

    return [
        {
            "summary": _normalize_text(intake.get("objective"), default="project intake"),
            "touched_files": sorted(set(fallback_touched)),
            "acceptance_criteria": [],
            "validation_commands": [],
            "rollback_notes": "",
            "forbidden_files": _normalize_string_list(intake.get("forbidden_files"), sort_items=True),
            "depends_on": [],
            "atomic": False,
        }
    ]


def _infer_relevant_paths_from_objective(*, objective: str, repo_root: Path) -> list[str]:
    lower = objective.lower()
    candidate_map = [
        (
            ("plan", "planner", "roadmap", "project brief", "pr plan"),
            [
                "automation/planning",
                "scripts",
                "tests",
            ],
        ),
        (
            ("inspect",),
            [
                "scripts/inspect_job.py",
                "tests/test_inspect_job.py",
            ],
        ),
        (
            ("operator summary", "build_operator_summary"),
            [
                "scripts/build_operator_summary.py",
                "tests/test_build_operator_summary.py",
            ],
        ),
    ]

    inferred: list[str] = []
    for keywords, paths in candidate_map:
        if any(keyword in lower for keyword in keywords):
            for path in paths:
                if (repo_root / path).exists():
                    inferred.append(path)

    return sorted(set(inferred))


def _derive_relevant_paths(
    *,
    intake: Mapping[str, Any],
    work_items: list[dict[str, Any]],
    objective: str,
    repo_root: Path,
) -> list[str]:
    collected: list[str] = []

    explicit = intake.get("relevant_paths")
    if isinstance(explicit, (list, tuple)):
        for item in explicit:
            normalized = _normalize_repo_path(item, repo_root=repo_root)
            if normalized is not None:
                collected.append(normalized)

    for item in work_items:
        for path in item.get("touched_files", []):
            normalized = _normalize_repo_path(path, repo_root=repo_root)
            if normalized is not None:
                collected.append(normalized)

    if not collected:
        collected.extend(_infer_relevant_paths_from_objective(objective=objective, repo_root=repo_root))

    if not collected:
        fallback = [
            "automation/planning",
            "scripts",
            "tests",
            "README.md",
        ]
        for path in fallback:
            if (repo_root / path).exists():
                collected.append(path)

    return sorted(set(collected))


def _collect_entrypoints(repo_root: Path) -> list[str]:
    candidates = [
        "app.py",
        "run_codex.py",
        "orchestrator/main.py",
        "scripts/evaluate_job.py",
        "scripts/inspect_job.py",
        "scripts/build_operator_summary.py",
        "prompt_builder.py",
        "automation/planning/prompt_builder.py",
    ]
    result: list[str] = []
    for path in candidates:
        if (repo_root / path).exists():
            result.append(path)
    return result


def _collect_tests_available(repo_root: Path) -> list[str]:
    tests_root = repo_root / "tests"
    if not tests_root.exists():
        return []
    return sorted(
        str(path.relative_to(repo_root)).replace("\\", "/")
        for path in tests_root.glob("test_*.py")
        if path.is_file()
    )


def _collect_build_commands(repo_root: Path) -> list[str]:
    commands: list[str] = []
    if (repo_root / "requirements.txt").exists():
        commands.append("python3 -m pip install -r requirements.txt")
    if (repo_root / "orchestrator" / "main.py").exists():
        commands.append("python3 -m orchestrator.main --help")
    return commands


def _collect_lint_commands(repo_root: Path) -> list[str]:
    commands: list[str] = []
    pyproject_path = repo_root / "pyproject.toml"
    if pyproject_path.exists():
        text = pyproject_path.read_text(encoding="utf-8")
        if "ruff" in text:
            commands.append("ruff check .")
        if "mypy" in text:
            commands.append("mypy .")
    if (repo_root / ".ruff.toml").exists() and "ruff check ." not in commands:
        commands.append("ruff check .")
    if (repo_root / ".flake8").exists():
        commands.append("flake8")
    return commands


def _build_project_brief(intake: Mapping[str, Any], *, repo_root: Path) -> dict[str, Any]:
    project_id = _normalize_text(intake.get("project_id"), default="project")
    objective = _normalize_text(intake.get("objective"), default="(not provided)")
    success_definition = _normalize_text(intake.get("success_definition"), default="(not provided)")
    constraints = _normalize_string_list(intake.get("constraints"), sort_items=False)
    non_goals = _normalize_string_list(intake.get("non_goals"), sort_items=False)
    allowed_risk_level = _normalize_text(intake.get("allowed_risk_level"), default="conservative")
    target_repo = _normalize_text(intake.get("target_repo"), default=repo_root.name)
    target_branch = _normalize_text(intake.get("target_branch"), default="")
    requested_by = _normalize_text(intake.get("requested_by"), default="unknown")
    created_at = _normalize_text(intake.get("created_at"), default=_DEFAULT_CREATED_AT)

    return {
        "project_id": project_id,
        "objective": objective,
        "success_definition": success_definition,
        "constraints": constraints,
        "non_goals": non_goals,
        "allowed_risk_level": allowed_risk_level,
        "target_repo": target_repo,
        "target_branch": target_branch,
        "requested_by": requested_by,
        "created_at": created_at,
    }


def _build_pr_plan(
    *,
    project_brief: Mapping[str, Any],
    intake: Mapping[str, Any],
    repo_facts: Mapping[str, Any],
    work_items: list[dict[str, Any]],
) -> dict[str, Any]:
    project_id = _normalize_text(project_brief.get("project_id"), default="project")
    plan_id = f"{project_id}-plan-v1"

    global_forbidden = _normalize_string_list(intake.get("forbidden_files"), sort_items=True)
    global_validation = _normalize_string_list(intake.get("validation_commands"), sort_items=False)

    sensitive_paths = _normalize_string_list(repo_facts.get("sensitive_paths"), sort_items=True)
    planning_warnings: list[str] = []

    prs: list[dict[str, Any]] = []
    for item in work_items:
        files = _normalize_string_list(item.get("touched_files"), sort_items=True)
        grouped: dict[tuple[str, str], list[str]] = {}
        for file_path in files:
            subsystem = _subsystem_for_path(file_path)
            risk_bucket = _risk_bucket_for_path(file_path, sensitive_paths=sensitive_paths)
            grouped.setdefault((subsystem, risk_bucket), []).append(file_path)

        keys = sorted(grouped.keys(), key=lambda key: (key[0], _RISK_ORDER.get(key[1], 99)))
        item_pr_ids: list[str] = []

        if not keys:
            keys = [("unspecified", "medium")]
            grouped[("unspecified", "medium")] = []

        for subsystem, risk_bucket in keys:
            grouped_files = sorted(set(grouped.get((subsystem, risk_bucket), [])))
            chunks = _split_files_for_slice(grouped_files, atomic=bool(item.get("atomic", False)))
            if bool(item.get("atomic", False)) and len(grouped_files) > _SOFT_FILE_CAP:
                planning_warnings.append(
                    (
                        f"{item.get('summary')}: atomic slice exceeds soft cap "
                        f"({_SOFT_FILE_CAP}) with {len(grouped_files)} files"
                    )
                )

            for chunk_index, chunk in enumerate(chunks, start=1):
                pr_id = f"{plan_id}-pr-{len(prs) + 1:02d}"
                chunk_suffix = ""
                if len(chunks) > 1:
                    chunk_suffix = f" (chunk {chunk_index}/{len(chunks)} capped at {_SOFT_FILE_CAP} files)"

                exact_scope = (
                    f"{item.get('summary')} | subsystem={subsystem} | risk={risk_bucket}{chunk_suffix}"
                )
                if bool(item.get("atomic", False)) and len(grouped_files) > _SOFT_FILE_CAP:
                    exact_scope += " | atomic=true required by intake"

                tier_category = _tier_category_for_files(chunk, sensitive_paths=sensitive_paths)
                item_validation = _normalize_string_list(item.get("validation_commands"), sort_items=False)
                validation_commands = item_validation or global_validation or list(
                    _DEFAULT_VALIDATION_BY_TIER.get(tier_category, ())
                )

                acceptance_criteria = _normalize_string_list(item.get("acceptance_criteria"), sort_items=False)
                if not acceptance_criteria:
                    success_definition = _normalize_text(project_brief.get("success_definition"))
                    if success_definition and success_definition != "(not provided)":
                        acceptance_criteria = [success_definition]

                forbidden = sorted(
                    set(global_forbidden + _normalize_string_list(item.get("forbidden_files"), sort_items=True))
                )

                depends_on = item_pr_ids[-1:] if item_pr_ids else _normalize_string_list(
                    item.get("depends_on"),
                    sort_items=False,
                )

                rollback_notes = _normalize_text(
                    item.get("rollback_notes"),
                    default="Revert this PR slice commit if validation fails.",
                )

                prs.append(
                    {
                        "pr_id": pr_id,
                        "title": f"[{subsystem}] {item.get('summary')}",
                        "exact_scope": exact_scope,
                        "touched_files": chunk,
                        "forbidden_files": forbidden,
                        "acceptance_criteria": acceptance_criteria,
                        "validation_commands": validation_commands,
                        "rollback_notes": rollback_notes,
                        "tier_category": tier_category,
                        "depends_on": depends_on,
                    }
                )
                item_pr_ids.append(pr_id)

    return {
        "plan_id": plan_id,
        "prs": prs,
        "canonical_surface_notes": [
            "inspect_job remains the primary human-facing surfaced-field authority.",
            "planner artifacts are additive and do not redefine inspect/operator-summary contracts.",
        ],
        "compatibility_notes": [
            "legacy replan_input.* compatibility remains intact.",
            "aligned top-level retry/failure surfaced fields remain untouched.",
        ],
        "planning_warnings": sorted(set(planning_warnings)),
    }


def _build_roadmap(
    *,
    project_brief: Mapping[str, Any],
    pr_plan: Mapping[str, Any],
    intake: Mapping[str, Any],
) -> dict[str, Any]:
    project_id = _normalize_text(project_brief.get("project_id"), default="project")
    roadmap_id = f"{project_id}-roadmap-v1"

    prs = pr_plan.get("prs") if isinstance(pr_plan.get("prs"), list) else []

    tier_order = [
        "docs_only",
        "test_only",
        "ci_only",
        "contract_guard_only",
        "runtime_fix_low_risk",
        "runtime_fix_high_risk",
        "feature",
    ]

    milestones: list[dict[str, Any]] = []
    for tier in tier_order:
        tier_pr_ids = [
            str(pr.get("pr_id"))
            for pr in prs
            if isinstance(pr, Mapping) and str(pr.get("tier_category")) == tier
        ]
        if not tier_pr_ids:
            continue
        milestones.append(
            {
                "milestone_id": f"{roadmap_id}-m{len(milestones) + 1:02d}",
                "title": f"{tier} slices",
                "tier_category": tier,
                "pr_ids": tier_pr_ids,
            }
        )

    dependency_edges: list[dict[str, str]] = []
    for pr in prs:
        if not isinstance(pr, Mapping):
            continue
        pr_id = _normalize_text(pr.get("pr_id"))
        if not pr_id:
            continue
        for dependency in _normalize_string_list(pr.get("depends_on"), sort_items=False):
            dependency_edges.append(
                {
                    "from": dependency,
                    "to": pr_id,
                }
            )

    tiers = [
        str(pr.get("tier_category"))
        for pr in prs
        if isinstance(pr, Mapping) and str(pr.get("tier_category", "")).strip()
    ]
    if any(tier in {"runtime_fix_high_risk", "feature"} for tier in tiers):
        estimated_risk = "high"
    elif any(tier in {"runtime_fix_low_risk", "contract_guard_only", "ci_only"} for tier in tiers):
        estimated_risk = "medium"
    else:
        estimated_risk = "low"

    return {
        "roadmap_id": roadmap_id,
        "milestones": milestones,
        "dependency_edges": dependency_edges,
        "blocked_by": _normalize_string_list(intake.get("blocked_by"), sort_items=False),
        "estimated_risk": estimated_risk,
    }


def generate_planning_artifacts(
    intake: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    repo_root_path = _repo_root_from_path(repo_root)

    project_brief = _build_project_brief(intake, repo_root=repo_root_path)
    merge_gate_policy = _load_merge_gate_policy_safe(repo_root_path)
    change_categories_policy = _load_change_categories_policy_safe(repo_root_path)

    work_items = _extract_work_items(intake, repo_root=repo_root_path)

    target_branch = _normalize_text(project_brief.get("target_branch"), default="")
    default_branch = _derive_default_branch(
        repo_root=repo_root_path,
        target_branch=target_branch,
    )
    project_brief["target_branch"] = target_branch or default_branch

    objective = _normalize_text(project_brief.get("objective"), default="")
    relevant_paths = _derive_relevant_paths(
        intake=intake,
        work_items=work_items,
        objective=objective,
        repo_root=repo_root_path,
    )

    sensitive_paths = _derive_sensitive_paths(
        repo_root=repo_root_path,
        merge_gate_policy=merge_gate_policy,
        change_categories_policy=change_categories_policy,
    )

    repo_facts = {
        "repo": _normalize_text(project_brief.get("target_repo"), default=repo_root_path.name),
        "default_branch": default_branch,
        "relevant_paths": relevant_paths,
        "entrypoints": _collect_entrypoints(repo_root_path),
        "tests_available": _collect_tests_available(repo_root_path),
        "build_commands": _collect_build_commands(repo_root_path),
        "lint_commands": _collect_lint_commands(repo_root_path),
        "current_branch_rules": _derive_current_branch_rules(merge_gate_policy),
        "sensitive_paths": sensitive_paths,
        "source_of_truth_commit": _derive_source_of_truth_commit(repo_root=repo_root_path),
    }

    pr_plan = _build_pr_plan(
        project_brief=project_brief,
        intake=intake,
        repo_facts=repo_facts,
        work_items=work_items,
    )
    roadmap = _build_roadmap(project_brief=project_brief, pr_plan=pr_plan, intake=intake)

    return {
        "project_brief": project_brief,
        "repo_facts": repo_facts,
        "roadmap": roadmap,
        "pr_plan": pr_plan,
    }


def write_planning_artifacts(
    artifacts: Mapping[str, Mapping[str, Any]],
    out_dir: str | Path,
) -> tuple[str, ...]:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    write_map = [
        (PROJECT_BRIEF_FILENAME, artifacts.get("project_brief", {})),
        (REPO_FACTS_FILENAME, artifacts.get("repo_facts", {})),
        (ROADMAP_FILENAME, artifacts.get("roadmap", {})),
        (PR_PLAN_FILENAME, artifacts.get("pr_plan", {})),
    ]

    written: list[str] = []
    for filename, payload in write_map:
        (out_path / filename).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        written.append(filename)

    return tuple(written)
