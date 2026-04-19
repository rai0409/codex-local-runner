from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from automation.execution.codex_executor_adapter import CodexExecutorAdapter
from automation.orchestration.planned_execution_runner import DryRunCodexExecutionTransport
from automation.orchestration.planned_execution_runner import PlannedExecutionRunner
from automation.orchestration.planned_execution_runner import _augment_run_state_with_closed_loop
from automation.orchestration.planned_execution_runner import _augment_run_state_with_lifecycle_terminal_contract
from automation.orchestration.planned_execution_runner import _augment_run_state_with_operator_explainability
from automation.orchestration.planned_execution_runner import _augment_run_state_with_policy_overlay
from automation.orchestration.planned_execution_runner import _augment_run_state_with_rollback_aftermath
from automation.orchestration.planned_execution_runner import _execute_bounded_merge
from automation.orchestration.planned_execution_runner import _execute_bounded_pr_creation
from automation.orchestration.planned_execution_runner import _execute_bounded_push
from automation.orchestration.planned_execution_runner import _execute_bounded_rollback
from automation.orchestration.planned_execution_runner import _with_rollback_aftermath_surface
from automation.orchestration.run_state_summary_contract import build_manifest_run_state_summary_contract_surface
from automation.orchestration.run_state_summary_contract import is_manifest_summary_safe_field
from automation.orchestration.run_state_summary_contract import select_manifest_run_state_summary_compact


class _RecordingDryRunTransport(DryRunCodexExecutionTransport):
    def __init__(self, *, status_by_pr_id: dict[str, str] | None = None) -> None:
        super().__init__(status_by_pr_id=status_by_pr_id)
        self.launch_order: list[str] = []

    def launch_job(self, **kwargs):  # type: ignore[override]
        self.launch_order.append(str(kwargs.get("pr_id", "")))
        return super().launch_job(**kwargs)


class _RecordingLiveTransport:
    def __init__(
        self,
        *,
        status_by_pr_id: dict[str, str] | None = None,
        verify_status_by_pr_id: dict[str, str] | None = None,
    ) -> None:
        self.status_by_pr_id = dict(status_by_pr_id or {})
        self.verify_status_by_pr_id = dict(verify_status_by_pr_id or {})
        self.launch_order: list[str] = []
        self.runs: dict[str, dict[str, object]] = {}

    def launch_job(self, **kwargs):  # type: ignore[override]
        pr_id = str(kwargs.get("pr_id", "")).strip()
        job_id = str(kwargs.get("job_id", "")).strip()
        run_id = f"{job_id}:{pr_id}:live"
        self.launch_order.append(pr_id)

        status = self.status_by_pr_id.get(pr_id, "completed")
        if status not in {"completed", "failed", "timed_out", "not_started", "running"}:
            status = "failed"
        verify_status = self.verify_status_by_pr_id.get(pr_id, "passed")
        if verify_status not in {"passed", "failed", "not_run"}:
            verify_status = "not_run"

        verify_reason = (
            "validation_passed"
            if verify_status == "passed"
            else "validation_failed" if verify_status == "failed" else "validation_not_run"
        )
        failure_type = None
        failure_message = None
        if status == "failed":
            failure_type = "execution_failure"
            failure_message = "mocked execution failure"
        elif status == "timed_out":
            failure_type = "transport_timeout"
            failure_message = "mocked timeout"
        elif status == "not_started":
            failure_type = "transport_submission_failure"
            failure_message = "mocked submission failure"
        elif verify_status == "failed":
            failure_type = "evaluation_failure"
            failure_message = "mocked verify failure"
        elif verify_status == "not_run":
            failure_type = "missing_signal"
            failure_message = "mocked verify missing"

        run_payload = {
            "run_id": run_id,
            "status": status,
            "attempt_count": 1,
            "started_at": "2026-04-18T00:00:00",
            "finished_at": "2026-04-18T00:00:01",
            "stdout_path": f"/tmp/{pr_id}_stdout.txt",
            "stderr_path": f"/tmp/{pr_id}_stderr.txt",
            "verify": {
                "status": verify_status,
                "commands": ["python3 -m unittest tests.test_planned_execution_runner -v"],
                "reason": verify_reason,
            },
            "changed_files": [],
            "additions": 1,
            "deletions": 0,
            "generated_patch_summary": "mocked live execution",
            "failure_type": failure_type,
            "failure_message": failure_message,
            "cost": {"tokens_input": 100, "tokens_output": 50},
            "artifacts": [],
        }
        self.runs[run_id] = run_payload
        return {"run_id": run_id, "status": status, "dry_run": False}

    def poll_status(self, **kwargs):  # type: ignore[override]
        run_id = str(kwargs.get("run_id", ""))
        payload = dict(self.runs[run_id])
        payload["dry_run"] = False
        return payload

    def collect_artifacts(self, **kwargs):  # type: ignore[override]
        run_id = str(kwargs.get("run_id", ""))
        payload = self.runs[run_id]
        return {
            "run_id": run_id,
            "stdout_path": str(payload["stdout_path"]),
            "stderr_path": str(payload["stderr_path"]),
            "artifacts": [],
            "dry_run": False,
        }


class _RollbackSignalLiveTransport(_RecordingLiveTransport):
    def launch_job(self, **kwargs):  # type: ignore[override]
        payload = super().launch_job(**kwargs)
        run_id = str(payload.get("run_id", ""))
        if run_id in self.runs:
            self.runs[run_id]["status"] = "failed"
            self.runs[run_id]["failure_type"] = "rollback_required"
            self.runs[run_id]["failure_message"] = "mocked rollback requirement"
            payload["status"] = "failed"
        return payload


class _CommitReadyLiveTransport(_RecordingLiveTransport):
    def __init__(
        self,
        *,
        changed_files_by_pr_id: dict[str, list[str]] | None = None,
    ) -> None:
        super().__init__(status_by_pr_id=None, verify_status_by_pr_id=None)
        self.changed_files_by_pr_id = dict(changed_files_by_pr_id or {})

    def launch_job(self, **kwargs):  # type: ignore[override]
        payload = super().launch_job(**kwargs)
        pr_id = str(kwargs.get("pr_id", "")).strip()
        run_id = str(payload.get("run_id", ""))
        if run_id in self.runs:
            self.runs[run_id]["changed_files"] = list(self.changed_files_by_pr_id.get(pr_id, []))
            self.runs[run_id]["status"] = "completed"
            self.runs[run_id]["verify"] = {
                "status": "passed",
                "commands": ["python3 -m unittest tests.test_planned_execution_runner -v"],
                "reason": "validation_passed",
            }
            self.runs[run_id]["failure_type"] = None
            self.runs[run_id]["failure_message"] = None
            payload["status"] = "completed"
        return payload


class _FakeGitHubReadBackend:
    def __init__(
        self,
        *,
        lookup_status: str = "success",
        matched: bool = False,
        pr_number: int | None = None,
        pr_url: str = "",
        match_count: int = 0,
        pr_status_status: str = "success",
        pr_state: str = "open",
        mergeable_state: str = "clean",
        checks_state: str = "passing",
        review_state_status: str = "satisfied",
        branch_protection_status: str = "satisfied",
    ) -> None:
        self.lookup_status = lookup_status
        self.matched = matched
        self.pr_number = pr_number
        self.pr_url = pr_url
        self.match_count = match_count
        self.pr_status_status = pr_status_status
        self.pr_state = pr_state
        self.mergeable_state = mergeable_state
        self.checks_state = checks_state
        self.review_state_status = review_state_status
        self.branch_protection_status = branch_protection_status
        self.calls: list[tuple[str, str, str]] = []
        self.status_calls: list[tuple[str, int | None, str | None]] = []

    def find_open_pr(self, repo: str, *, head_branch: str, base_branch: str):  # type: ignore[override]
        self.calls.append((repo, head_branch, base_branch))
        if self.lookup_status != "success":
            return {"operation": "find_open_pr", "status": self.lookup_status, "data": {}}
        pr_payload: dict[str, object] = {}
        if self.matched:
            pr_payload = {
                "number": self.pr_number,
                "html_url": self.pr_url or "",
            }
        return {
            "operation": "find_open_pr",
            "status": "success",
            "data": {
                "matched": self.matched,
                "match_count": self.match_count if self.match_count > 0 else (1 if self.matched else 0),
                "pr": pr_payload,
            },
        }

    def get_pr_status_summary(
        self,
        repo: str,
        *,
        pr_number: int | None = None,
        commit_sha: str | None = None,
    ):  # type: ignore[override]
        self.status_calls.append((repo, pr_number, commit_sha))
        if self.pr_status_status != "success":
            return {
                "operation": "get_pr_status_summary",
                "status": self.pr_status_status,
                "data": {},
            }
        return {
            "operation": "get_pr_status_summary",
            "status": "success",
            "data": {
                "repository": repo,
                "pr_number": pr_number,
                "pr_state": self.pr_state,
                "mergeable_state": self.mergeable_state,
                "checks_state": self.checks_state,
                "review_state_status": self.review_state_status,
                "branch_protection_status": self.branch_protection_status,
            },
        }


class _FakeGitHubWriteBackend:
    def __init__(
        self,
        *,
        create_status: str = "success",
        merge_status: str = "success",
        created_pr_number: int = 101,
        created_pr_url: str = "https://example.local/pr/101",
        merge_commit_sha: str = "d" * 40,
    ) -> None:
        self.create_status = create_status
        self.merge_status = merge_status
        self.created_pr_number = created_pr_number
        self.created_pr_url = created_pr_url
        self.merge_commit_sha = merge_commit_sha
        self.create_calls: list[dict[str, object]] = []
        self.merge_calls: list[dict[str, object]] = []

    def create_draft_pr(
        self,
        *,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
    ):  # type: ignore[override]
        self.create_calls.append(
            {
                "repo": repo,
                "title": title,
                "body": body,
                "head_branch": head_branch,
                "base_branch": base_branch,
            }
        )
        if self.create_status != "success":
            return {"operation": "create_draft_pr", "status": self.create_status, "data": {}}
        return {
            "operation": "create_draft_pr",
            "status": "success",
            "data": {
                "pr": {
                    "number": self.created_pr_number,
                    "html_url": self.created_pr_url,
                }
            },
        }

    def merge_pull_request(
        self,
        *,
        repo: str,
        pr_number: int,
        expected_head_sha: str | None = None,
        merge_method: str = "merge",
    ):  # type: ignore[override]
        self.merge_calls.append(
            {
                "repo": repo,
                "pr_number": pr_number,
                "expected_head_sha": expected_head_sha,
                "merge_method": merge_method,
            }
        )
        if self.merge_status != "success":
            return {"operation": "merge_pull_request", "status": self.merge_status, "data": {}}
        return {
            "operation": "merge_pull_request",
            "status": "success",
            "data": {
                "pr_number": pr_number,
                "merge_commit_sha": self.merge_commit_sha,
            },
        }


class PlannedExecutionRunnerTests(unittest.TestCase):
    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _script_path(self) -> Path:
        return self._repo_root() / "scripts" / "run_planned_execution.py"

    def _write_planning_artifacts(self, root: Path) -> Path:
        artifacts_dir = root / "planning_artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        project_brief = {
            "project_id": "project-planned-exec",
            "objective": "Run deterministic planned dry-run execution",
            "success_definition": "Each PR slice gets prompt, result, and receipt",
            "constraints": ["additive only"],
            "non_goals": ["no scheduler"],
            "allowed_risk_level": "conservative",
            "target_repo": "codex-local-runner",
            "target_branch": "main",
            "requested_by": "operator",
            "created_at": "2026-04-18T00:00:00+00:00",
        }
        repo_facts = {
            "repo": "codex-local-runner",
            "default_branch": "main",
            "relevant_paths": ["automation/planning", "automation/execution", "automation/orchestration"],
            "entrypoints": ["scripts/run_planned_execution.py"],
            "tests_available": ["tests/test_planned_execution_runner.py"],
            "build_commands": ["python3 -m unittest discover -s tests"],
            "lint_commands": [],
            "current_branch_rules": ["require_ci_green=true"],
            "sensitive_paths": ["orchestrator/**"],
            "source_of_truth_commit": "abc123",
        }
        roadmap = {
            "roadmap_id": "project-planned-exec-roadmap-v1",
            "milestones": [
                {
                    "milestone_id": "m-01",
                    "title": "ordered slices",
                    "tier_category": "runtime_fix_low_risk",
                    "pr_ids": [
                        "project-planned-exec-pr-01",
                        "project-planned-exec-pr-02",
                        "project-planned-exec-pr-03",
                    ],
                }
            ],
            "dependency_edges": [
                {"from": "project-planned-exec-pr-01", "to": "project-planned-exec-pr-02"},
                {"from": "project-planned-exec-pr-02", "to": "project-planned-exec-pr-03"},
            ],
            "blocked_by": [],
            "estimated_risk": "medium",
        }
        pr_plan = {
            "plan_id": "project-planned-exec-plan-v1",
            "prs": [
                {
                    "pr_id": "project-planned-exec-pr-01",
                    "title": "[planning] first slice",
                    "exact_scope": "Create first scoped unit",
                    "touched_files": ["automation/planning/prompt_compiler.py"],
                    "forbidden_files": ["orchestrator/main.py"],
                    "acceptance_criteria": ["first unit compiled"],
                    "validation_commands": ["python3 -m unittest tests.test_prompt_compiler -v"],
                    "rollback_notes": "revert slice 1",
                    "tier_category": "runtime_fix_low_risk",
                    "depends_on": [],
                },
                {
                    "pr_id": "project-planned-exec-pr-02",
                    "title": "[execution] second slice",
                    "exact_scope": "Create second scoped unit",
                    "touched_files": ["automation/execution/codex_executor_adapter.py"],
                    "forbidden_files": ["orchestrator/merge_executor.py"],
                    "acceptance_criteria": ["second unit compiled"],
                    "validation_commands": ["python3 -m unittest tests.test_codex_executor_adapter -v"],
                    "rollback_notes": "revert slice 2",
                    "tier_category": "runtime_fix_high_risk",
                    "depends_on": ["project-planned-exec-pr-01"],
                },
                {
                    "pr_id": "project-planned-exec-pr-03",
                    "title": "[orchestration] third slice",
                    "exact_scope": "Create third scoped unit",
                    "touched_files": ["automation/orchestration/planned_execution_runner.py"],
                    "forbidden_files": ["orchestrator/rollback_executor.py"],
                    "acceptance_criteria": ["third unit compiled"],
                    "validation_commands": ["python3 -m unittest tests.test_planned_execution_runner -v"],
                    "rollback_notes": "revert slice 3",
                    "tier_category": "runtime_fix_high_risk",
                    "depends_on": ["project-planned-exec-pr-02"],
                },
            ],
            "canonical_surface_notes": ["inspect_job remains authority"],
            "compatibility_notes": ["legacy replan_input.* preserved"],
            "planning_warnings": [],
        }

        write_map = {
            "project_brief.json": project_brief,
            "repo_facts.json": repo_facts,
            "roadmap.json": roadmap,
            "pr_plan.json": pr_plan,
        }
        for filename, payload in write_map.items():
            (artifacts_dir / filename).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return artifacts_dir

    def _shrink_to_single_pr_slice(self, artifacts_dir: Path) -> str:
        pr_plan_path = artifacts_dir / "pr_plan.json"
        roadmap_path = artifacts_dir / "roadmap.json"
        pr_plan = json.loads(pr_plan_path.read_text(encoding="utf-8"))
        roadmap = json.loads(roadmap_path.read_text(encoding="utf-8"))
        first_pr = dict(pr_plan["prs"][0])
        first_pr["depends_on"] = []
        pr_plan["prs"] = [first_pr]
        roadmap["milestones"][0]["pr_ids"] = [first_pr["pr_id"]]
        roadmap["dependency_edges"] = []
        pr_plan_path.write_text(json.dumps(pr_plan, ensure_ascii=False, indent=2), encoding="utf-8")
        roadmap_path.write_text(json.dumps(roadmap, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(first_pr["touched_files"][0])

    def _init_git_repo_with_dirty_file(self, repo_dir: Path, *, changed_file: str) -> str:
        target = repo_dir / changed_file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("baseline\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo_dir), "init"], check=True, capture_output=True, text=True)
        subprocess.run(
            ["git", "-C", str(repo_dir), "config", "user.name", "Test Runner"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_dir), "config", "user.email", "test-runner@example.com"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(["git", "-C", str(repo_dir), "add", "--", changed_file], check=True, capture_output=True, text=True)
        subprocess.run(
            ["git", "-C", str(repo_dir), "commit", "-m", "initial"],
            check=True,
            capture_output=True,
            text=True,
        )
        target.write_text("baseline\nupdated\n", encoding="utf-8")
        head_before = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return head_before

    def _attach_origin_remote_and_push_initial(self, repo_dir: Path) -> Path:
        remote_dir = repo_dir.parent / "origin.git"
        subprocess.run(
            ["git", "init", "--bare", str(remote_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_dir), "remote", "add", "origin", str(remote_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_dir), "push", "-u", "origin", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return remote_dir

    def _git_commit(self, repo_dir: Path, message: str) -> str:
        subprocess.run(
            [
                "git",
                "-C",
                str(repo_dir),
                "-c",
                "user.name=Test Runner",
                "-c",
                "user.email=test-runner@example.com",
                "commit",
                "-m",
                message,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def _init_merged_repo(self, repo_dir: Path) -> dict[str, str]:
        subprocess.run(["git", "-C", str(repo_dir), "init"], check=True, capture_output=True, text=True)
        subprocess.run(
            ["git", "-C", str(repo_dir), "config", "user.name", "Test Runner"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_dir), "config", "user.email", "test-runner@example.com"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_dir), "checkout", "-b", "main"],
            check=True,
            capture_output=True,
            text=True,
        )
        readme = repo_dir / "README.md"
        readme.write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo_dir), "add", "--", "README.md"], check=True, capture_output=True, text=True)
        pre_merge_sha = self._git_commit(repo_dir, "base")

        subprocess.run(
            ["git", "-C", str(repo_dir), "checkout", "-b", "feature"],
            check=True,
            capture_output=True,
            text=True,
        )
        feature = repo_dir / "feature.txt"
        feature.write_text("feature\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo_dir), "add", "--", "feature.txt"], check=True, capture_output=True, text=True)
        source_sha = self._git_commit(repo_dir, "feature")

        subprocess.run(
            ["git", "-C", str(repo_dir), "checkout", "main"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(repo_dir),
                "-c",
                "user.name=Test Runner",
                "-c",
                "user.email=test-runner@example.com",
                "merge",
                "--no-ff",
                "--no-edit",
                source_sha,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        merge_sha = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return {
            "target_branch": "main",
            "pre_merge_sha": pre_merge_sha,
            "merge_sha": merge_sha,
        }

    def test_deterministic_processing_order_for_multiple_pr_slices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RecordingDryRunTransport()
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest_a = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
                retry_context={
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 1,
                },
            )
            order_a = list(transport.launch_order)

            transport_b = _RecordingDryRunTransport()
            runner_b = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport_b))
            manifest_b = runner_b.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
                retry_context={
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 1,
                },
            )
            order_b = list(transport_b.launch_order)

        self.assertEqual(
            order_a,
            [
                "project-planned-exec-pr-01",
                "project-planned-exec-pr-02",
                "project-planned-exec-pr-03",
            ],
        )
        self.assertEqual(order_a, order_b)
        self.assertEqual(
            [entry["pr_id"] for entry in manifest_a["pr_units"]],
            [entry["pr_id"] for entry in manifest_b["pr_units"]],
        )

    def test_pr_id_mapping_and_artifact_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RecordingDryRunTransport()
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )

            run_root = out_dir / manifest["job_id"]
            self.assertTrue((run_root / "manifest.json").exists())
            self.assertTrue((run_root / "next_action.json").exists())
            self.assertTrue((run_root / "action_handoff.json").exists())

            for entry in manifest["pr_units"]:
                pr_id = entry["pr_id"]
                unit_dir = run_root / pr_id
                self.assertTrue(unit_dir.exists())
                self.assertTrue((unit_dir / "compiled_prompt.md").exists())
                self.assertTrue((unit_dir / "bounded_step_contract.json").exists())
                self.assertTrue((unit_dir / "pr_implementation_prompt_contract.json").exists())
                self.assertTrue((unit_dir / "unit_progression.json").exists())
                self.assertTrue((unit_dir / "checkpoint_decision.json").exists())
                self.assertTrue((unit_dir / "commit_decision.json").exists())
                self.assertTrue((unit_dir / "merge_decision.json").exists())
                self.assertTrue((unit_dir / "rollback_decision.json").exists())
                self.assertTrue((unit_dir / "commit_execution.json").exists())
                self.assertTrue((unit_dir / "push_execution.json").exists())
                self.assertTrue((unit_dir / "pr_execution.json").exists())
                self.assertTrue((unit_dir / "merge_execution.json").exists())
                self.assertTrue((unit_dir / "rollback_execution.json").exists())
                self.assertTrue((unit_dir / "result.json").exists())
                self.assertTrue((unit_dir / "execution_receipt.json").exists())

                result_payload = json.loads((unit_dir / "result.json").read_text(encoding="utf-8"))
                receipt_payload = json.loads((unit_dir / "execution_receipt.json").read_text(encoding="utf-8"))
                prompt_text = (unit_dir / "compiled_prompt.md").read_text(encoding="utf-8")
                bounded_step_contract = json.loads(
                    (unit_dir / "bounded_step_contract.json").read_text(encoding="utf-8")
                )
                prompt_contract = json.loads(
                    (unit_dir / "pr_implementation_prompt_contract.json").read_text(encoding="utf-8")
                )
                unit_progression_payload = json.loads(
                    (unit_dir / "unit_progression.json").read_text(encoding="utf-8")
                )

                self.assertEqual(result_payload["pr_id"], pr_id)
                self.assertEqual(receipt_payload["pr_id"], pr_id)
                self.assertIn(f"Execute exactly one PR slice: {pr_id}", prompt_text)
                self.assertEqual(bounded_step_contract["step_id"], pr_id)
                self.assertEqual(prompt_contract["source_step_id"], pr_id)
                self.assertEqual(unit_progression_payload["pr_id"], pr_id)
                self.assertIn("contract_handoff", unit_progression_payload)
                self.assertEqual(
                    prompt_contract["progression_metadata"]["planned_step_id"],
                    pr_id,
                )
                commit_decision = json.loads((unit_dir / "commit_decision.json").read_text(encoding="utf-8"))
                merge_decision = json.loads((unit_dir / "merge_decision.json").read_text(encoding="utf-8"))
                rollback_decision = json.loads((unit_dir / "rollback_decision.json").read_text(encoding="utf-8"))
                checkpoint_decision = json.loads((unit_dir / "checkpoint_decision.json").read_text(encoding="utf-8"))
                commit_execution = json.loads((unit_dir / "commit_execution.json").read_text(encoding="utf-8"))
                self.assertEqual(
                    set(checkpoint_decision.keys()),
                    {
                        "schema_version",
                        "unit_id",
                        "checkpoint_stage",
                        "decision",
                        "rule_id",
                        "summary",
                        "blocking_reasons",
                        "required_signals",
                        "recommended_next_action",
                        "manual_intervention_required",
                        "global_stop_recommended",
                    },
                )
                self.assertEqual(
                    set(commit_decision.keys()),
                    {
                        "schema_version",
                        "unit_id",
                        "decision",
                        "rule_id",
                        "summary",
                        "blocking_reasons",
                        "required_signals",
                        "recommended_next_action",
                        "readiness_status",
                        "readiness_next_action",
                        "automation_eligible",
                        "manual_intervention_required",
                        "unresolved_blockers",
                        "prerequisites_satisfied",
                    },
                )
                self.assertEqual(
                    set(merge_decision.keys()),
                    {
                        "schema_version",
                        "unit_id",
                        "decision",
                        "rule_id",
                        "summary",
                        "blocking_reasons",
                        "required_signals",
                        "recommended_next_action",
                        "readiness_status",
                        "readiness_next_action",
                        "automation_eligible",
                        "manual_intervention_required",
                        "unresolved_blockers",
                        "prerequisites_satisfied",
                    },
                )
                self.assertEqual(
                    set(rollback_decision.keys()),
                    {
                        "schema_version",
                        "unit_id",
                        "decision",
                        "rule_id",
                        "summary",
                        "blocking_reasons",
                        "required_signals",
                        "recommended_next_action",
                        "readiness_status",
                        "readiness_next_action",
                        "automation_eligible",
                        "manual_intervention_required",
                        "unresolved_blockers",
                        "prerequisites_satisfied",
                    },
                )
                self.assertEqual(commit_decision["unit_id"], pr_id)
                self.assertEqual(merge_decision["unit_id"], pr_id)
                self.assertEqual(rollback_decision["unit_id"], pr_id)
                self.assertEqual(checkpoint_decision["unit_id"], pr_id)
                self.assertEqual(commit_execution["unit_id"], pr_id)
                self.assertEqual(commit_execution["execution_type"], "git_commit")
                self.assertIn(commit_execution["status"], {"blocked", "succeeded", "failed"})
                self.assertIn(
                    checkpoint_decision["checkpoint_stage"],
                    {
                        "post_execution",
                        "post_review",
                        "pre_commit_evaluation",
                        "pre_merge_evaluation",
                        "pre_rollback_evaluation",
                    },
                )
                self.assertIn(
                    checkpoint_decision["decision"],
                    {
                        "proceed",
                        "pause",
                        "retry",
                        "manual_review_required",
                        "escalate",
                        "commit_evaluation_ready",
                        "merge_evaluation_ready",
                        "rollback_evaluation_ready",
                        "global_stop_recommended",
                    },
                )
                self.assertIn(commit_decision["decision"], {"allowed", "blocked", "manual_required", "unknown"})
                self.assertIn(merge_decision["decision"], {"allowed", "blocked", "manual_required", "unknown"})
                self.assertIn(
                    rollback_decision["decision"],
                    {"required", "not_required", "blocked", "manual_required", "unknown"},
                )

            decision_payload = json.loads((run_root / "next_action.json").read_text(encoding="utf-8"))
            handoff_payload = json.loads((run_root / "action_handoff.json").read_text(encoding="utf-8"))
            run_state_payload = json.loads((run_root / "run_state.json").read_text(encoding="utf-8"))
            self.assertEqual(decision_payload["job_id"], manifest["job_id"])
            self.assertIn("next_action", decision_payload)
            self.assertIn("reason", decision_payload)
            self.assertIn("updated_retry_context", decision_payload)
            self.assertIn("progression_outcome", decision_payload)
            self.assertIn("progression_rule_id", decision_payload)
            self.assertEqual(handoff_payload["job_id"], manifest["job_id"])
            self.assertIn("action_consumable", handoff_payload)
            self.assertIn("handoff_created_at", handoff_payload)
            self.assertEqual(run_state_payload["run_id"], manifest["job_id"])
            self.assertIn(run_state_payload["state"], {
                "intake_received",
                "planning_completed",
                "units_generated",
                "execution_in_progress",
                "review_in_progress",
                "decision_in_progress",
                "commit_ready",
                "merge_ready",
                "post_merge_verifying",
                "paused",
                "rollback_in_progress",
                "rolled_back",
                "completed",
                "failed_terminal",
            })
            self.assertIn(
                run_state_payload["orchestration_state"],
                {
                    "planning_completed",
                    "units_generated",
                    "execution_in_progress",
                    "checkpoint_evaluation_in_progress",
                    "run_ready_to_continue",
                    "paused_for_manual_review",
                    "rollback_evaluation_pending",
                    "global_stop_pending",
                    "completed",
                    "failed_terminal",
                },
            )
            self.assertIn(
                run_state_payload["next_run_action"],
                {
                    "continue_run",
                    "pause_run",
                    "await_manual_review",
                    "evaluate_rollback",
                    "hold_for_global_stop",
                    "complete_run",
                },
            )
            self.assertEqual(
                set(run_state_payload.keys()),
                {
                    "schema_version",
                    "run_id",
                    "state",
                    "orchestration_state",
                    "summary",
                    "units_total",
                    "units_completed",
                    "units_blocked",
                    "units_failed",
                    "units_pending",
                    "global_stop",
                    "global_stop_reason",
                    "continue_allowed",
                    "run_paused",
                    "manual_intervention_required",
                    "rollback_evaluation_pending",
                    "global_stop_recommended",
                    "next_run_action",
                    "loop_state",
                    "next_safe_action",
                    "loop_blocked_reason",
                    "loop_blocked_reasons",
                    "resumable",
                    "terminal",
                    "loop_manual_intervention_required",
                    "loop_replan_required",
                    "rollback_completed",
                    "delivery_completed",
                    "loop_allowed_actions",
                    "unit_blocked",
                    "latest_unit_id",
                    "allowed_transitions",
                    "orchestration_allowed_transitions",
                    "readiness_summary",
                    "readiness_blocked",
                    "readiness_manual_required",
                    "readiness_awaiting_prerequisites",
                    "commit_execution_summary",
                    "commit_execution_executed",
                    "commit_execution_pending",
                    "commit_execution_failed",
                    "commit_execution_manual_intervention_required",
                    "push_execution_summary",
                    "pr_execution_summary",
                    "merge_execution_summary",
                    "push_execution_succeeded",
                    "pr_execution_succeeded",
                    "merge_execution_succeeded",
                    "push_execution_pending",
                    "pr_execution_pending",
                    "merge_execution_pending",
                    "push_execution_failed",
                    "pr_execution_failed",
                    "merge_execution_failed",
                    "delivery_execution_manual_intervention_required",
                    "rollback_execution_summary",
                    "rollback_execution_attempted",
                    "rollback_execution_succeeded",
                    "rollback_execution_pending",
                    "rollback_execution_failed",
                    "rollback_execution_manual_intervention_required",
                    "rollback_replan_required",
                    "rollback_automatic_continuation_blocked",
                    "rollback_aftermath_summary",
                    "rollback_aftermath_status",
                    "rollback_aftermath_blocked",
                    "rollback_aftermath_manual_required",
                    "rollback_aftermath_missing_or_ambiguous",
                    "rollback_aftermath_blocked_reason",
                    "rollback_aftermath_blocked_reasons",
                    "rollback_remote_followup_required",
                    "rollback_manual_followup_required",
                    "rollback_validation_failed",
                    "authority_validation_summary",
                    "authority_validation_blocked",
                    "execution_authority_blocked",
                    "validation_blocked",
                    "authority_validation_manual_required",
                    "authority_validation_missing_or_ambiguous",
                    "authority_validation_blocked_reason",
                    "authority_validation_blocked_reasons",
                    "remote_github_summary",
                    "remote_github_blocked",
                    "remote_github_manual_required",
                    "remote_github_missing_or_ambiguous",
                    "remote_github_blocked_reason",
                    "remote_github_blocked_reasons",
                    "policy_status",
                    "policy_blocked",
                    "policy_manual_required",
                    "policy_replan_required",
                    "policy_resume_allowed",
                    "policy_terminal",
                    "policy_blocked_reason",
                    "policy_blocked_reasons",
                    "policy_primary_blocker_class",
                    "policy_primary_action",
                    "policy_allowed_actions",
                    "policy_disallowed_actions",
                    "policy_manual_actions",
                    "policy_resumable_reason",
                    "operator_posture_summary",
                    "operator_primary_blocker_class",
                    "operator_primary_action",
                    "operator_action_scope",
                    "operator_resume_status",
                    "operator_next_safe_posture",
                    "lifecycle_closure_status",
                    "lifecycle_safely_closed",
                    "lifecycle_terminal",
                    "lifecycle_resumable",
                    "lifecycle_manual_required",
                    "lifecycle_replan_required",
                    "lifecycle_execution_complete_not_closed",
                    "lifecycle_rollback_complete_not_closed",
                    "lifecycle_blocked_reason",
                    "lifecycle_blocked_reasons",
                    "lifecycle_primary_closure_issue",
                    "lifecycle_stop_class",
                },
            )

    def test_launch_metadata_uses_structured_contract_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            transport = _RecordingDryRunTransport()
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )

            first = manifest["pr_units"][0]
            unit_dir = Path(first["compiled_prompt_path"]).parent
            bounded = json.loads((unit_dir / "bounded_step_contract.json").read_text(encoding="utf-8"))
            prompt_contract = json.loads(
                (unit_dir / "pr_implementation_prompt_contract.json").read_text(encoding="utf-8")
            )
            run_ids = sorted(transport._runs.keys())  # type: ignore[attr-defined]
            first_run = transport._runs[run_ids[0]]  # type: ignore[attr-defined]
            metadata = first_run["metadata"]

        self.assertEqual(metadata["planned_step_id"], bounded["step_id"])
        self.assertEqual(metadata["source_step_id"], prompt_contract["source_step_id"])
        self.assertEqual(
            metadata["strict_scope_files"],
            bounded["progression_metadata"]["strict_scope_files"],
        )
        self.assertEqual(
            metadata["validation_commands"],
            bounded["validation_expectations"],
        )

    def test_manifest_generation_and_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )

        self.assertIn("job_id", manifest)
        self.assertIn("run_status", manifest)
        self.assertIn("artifact_input_dir", manifest)
        self.assertIn("artifact_ownership", manifest)
        self.assertIn("started_at", manifest)
        self.assertIn("finished_at", manifest)
        self.assertIn("pr_units", manifest)
        self.assertEqual(manifest["run_status"], "dry_run_completed")
        self.assertGreaterEqual(len(manifest["pr_units"]), 1)
        self.assertIn("decision_summary", manifest)
        self.assertIn("progression_summary", manifest)
        self.assertIn("run_state_summary", manifest)
        self.assertIn("run_state_summary_compact", manifest)
        self.assertIn("run_state_summary_contract", manifest)
        self.assertIn("manifest_path", manifest)
        self.assertIn("next_action_path", manifest)
        self.assertIn("action_handoff_path", manifest)
        self.assertIn("run_state_path", manifest)
        self.assertIn("retry_context_store_path", manifest)
        self.assertIn("handoff_summary", manifest)
        self.assertEqual(
            manifest["decision_summary"]["next_action"],
            "signal_recollect",
        )
        self.assertEqual(
            manifest["handoff_summary"]["next_action"],
            "signal_recollect",
        )
        self.assertEqual(manifest["progression_summary"]["final_unit_state"], "reviewed")
        self.assertEqual(manifest["run_state_summary"]["state"], "paused")
        self.assertIn("orchestration_state", manifest["run_state_summary"])
        self.assertIn("continue_allowed", manifest["run_state_summary"])
        self.assertIn("run_paused", manifest["run_state_summary"])
        self.assertIn("manual_intervention_required", manifest["run_state_summary"])
        self.assertIn("rollback_evaluation_pending", manifest["run_state_summary"])
        self.assertIn("global_stop_recommended", manifest["run_state_summary"])
        self.assertIn("next_run_action", manifest["run_state_summary"])
        self.assertIn("loop_state", manifest["run_state_summary"])
        self.assertIn("next_safe_action", manifest["run_state_summary"])
        self.assertIn("loop_blocked_reason", manifest["run_state_summary"])
        self.assertIn("loop_blocked_reasons", manifest["run_state_summary"])
        self.assertIn("resumable", manifest["run_state_summary"])
        self.assertIn("terminal", manifest["run_state_summary"])
        self.assertIn("loop_manual_intervention_required", manifest["run_state_summary"])
        self.assertIn("loop_replan_required", manifest["run_state_summary"])
        self.assertIn("rollback_completed", manifest["run_state_summary"])
        self.assertIn("delivery_completed", manifest["run_state_summary"])
        self.assertIn("loop_allowed_actions", manifest["run_state_summary"])
        self.assertIn("readiness_summary", manifest["run_state_summary"])
        self.assertIn("readiness_blocked", manifest["run_state_summary"])
        self.assertIn("readiness_manual_required", manifest["run_state_summary"])
        self.assertIn("readiness_awaiting_prerequisites", manifest["run_state_summary"])
        self.assertIn("commit_execution_summary", manifest["run_state_summary"])
        self.assertIn("commit_execution_executed", manifest["run_state_summary"])
        self.assertIn("commit_execution_pending", manifest["run_state_summary"])
        self.assertIn("commit_execution_failed", manifest["run_state_summary"])
        self.assertIn("commit_execution_manual_intervention_required", manifest["run_state_summary"])
        self.assertIn("push_execution_summary", manifest["run_state_summary"])
        self.assertIn("pr_execution_summary", manifest["run_state_summary"])
        self.assertIn("merge_execution_summary", manifest["run_state_summary"])
        self.assertIn("push_execution_succeeded", manifest["run_state_summary"])
        self.assertIn("pr_execution_succeeded", manifest["run_state_summary"])
        self.assertIn("merge_execution_succeeded", manifest["run_state_summary"])
        self.assertIn("push_execution_pending", manifest["run_state_summary"])
        self.assertIn("pr_execution_pending", manifest["run_state_summary"])
        self.assertIn("merge_execution_pending", manifest["run_state_summary"])
        self.assertIn("push_execution_failed", manifest["run_state_summary"])
        self.assertIn("pr_execution_failed", manifest["run_state_summary"])
        self.assertIn("merge_execution_failed", manifest["run_state_summary"])
        self.assertIn("delivery_execution_manual_intervention_required", manifest["run_state_summary"])
        self.assertIn("rollback_execution_summary", manifest["run_state_summary"])
        self.assertIn("rollback_execution_attempted", manifest["run_state_summary"])
        self.assertIn("rollback_execution_succeeded", manifest["run_state_summary"])
        self.assertIn("rollback_execution_pending", manifest["run_state_summary"])
        self.assertIn("rollback_execution_failed", manifest["run_state_summary"])
        self.assertIn("rollback_execution_manual_intervention_required", manifest["run_state_summary"])
        self.assertIn("rollback_replan_required", manifest["run_state_summary"])
        self.assertIn("rollback_automatic_continuation_blocked", manifest["run_state_summary"])
        self.assertIn("rollback_aftermath_summary", manifest["run_state_summary"])
        self.assertIn("rollback_aftermath_status", manifest["run_state_summary"])
        self.assertIn("rollback_aftermath_blocked", manifest["run_state_summary"])
        self.assertIn("rollback_aftermath_manual_required", manifest["run_state_summary"])
        self.assertIn("rollback_aftermath_missing_or_ambiguous", manifest["run_state_summary"])
        self.assertIn("rollback_aftermath_blocked_reason", manifest["run_state_summary"])
        self.assertIn("rollback_aftermath_blocked_reasons", manifest["run_state_summary"])
        self.assertIn("rollback_remote_followup_required", manifest["run_state_summary"])
        self.assertIn("rollback_manual_followup_required", manifest["run_state_summary"])
        self.assertIn("rollback_validation_failed", manifest["run_state_summary"])
        self.assertIn("remote_github_summary", manifest["run_state_summary"])
        self.assertIn("remote_github_blocked", manifest["run_state_summary"])
        self.assertIn("remote_github_manual_required", manifest["run_state_summary"])
        self.assertIn("remote_github_missing_or_ambiguous", manifest["run_state_summary"])
        self.assertIn("remote_github_blocked_reason", manifest["run_state_summary"])
        self.assertIn("remote_github_blocked_reasons", manifest["run_state_summary"])
        self.assertIn("policy_status", manifest["run_state_summary"])
        self.assertIn("policy_blocked", manifest["run_state_summary"])
        self.assertIn("policy_manual_required", manifest["run_state_summary"])
        self.assertIn("policy_replan_required", manifest["run_state_summary"])
        self.assertIn("policy_resume_allowed", manifest["run_state_summary"])
        self.assertIn("policy_terminal", manifest["run_state_summary"])
        self.assertIn("policy_blocked_reason", manifest["run_state_summary"])
        self.assertIn("policy_blocked_reasons", manifest["run_state_summary"])
        self.assertIn("policy_primary_blocker_class", manifest["run_state_summary"])
        self.assertIn("policy_primary_action", manifest["run_state_summary"])
        self.assertIn("policy_allowed_actions", manifest["run_state_summary"])
        self.assertIn("policy_disallowed_actions", manifest["run_state_summary"])
        self.assertIn("policy_manual_actions", manifest["run_state_summary"])
        self.assertIn("policy_resumable_reason", manifest["run_state_summary"])
        self.assertIn("operator_posture_summary", manifest["run_state_summary"])
        self.assertIn("operator_primary_blocker_class", manifest["run_state_summary"])
        self.assertIn("operator_primary_action", manifest["run_state_summary"])
        self.assertIn("operator_action_scope", manifest["run_state_summary"])
        self.assertIn("operator_resume_status", manifest["run_state_summary"])
        self.assertIn("operator_next_safe_posture", manifest["run_state_summary"])
        self.assertIn("lifecycle_closure_status", manifest["run_state_summary"])
        self.assertIn("lifecycle_safely_closed", manifest["run_state_summary"])
        self.assertIn("lifecycle_terminal", manifest["run_state_summary"])
        self.assertIn("lifecycle_resumable", manifest["run_state_summary"])
        self.assertIn("lifecycle_manual_required", manifest["run_state_summary"])
        self.assertIn("lifecycle_replan_required", manifest["run_state_summary"])
        self.assertIn("lifecycle_execution_complete_not_closed", manifest["run_state_summary"])
        self.assertIn("lifecycle_rollback_complete_not_closed", manifest["run_state_summary"])
        self.assertIn("lifecycle_blocked_reason", manifest["run_state_summary"])
        self.assertIn("lifecycle_blocked_reasons", manifest["run_state_summary"])
        self.assertIn("lifecycle_primary_closure_issue", manifest["run_state_summary"])
        self.assertIn("lifecycle_stop_class", manifest["run_state_summary"])
        self.assertNotIn("operator_guidance_summary", manifest["run_state_summary"])
        self.assertNotIn("operator_safe_actions_summary", manifest["run_state_summary"])
        self.assertNotIn("operator_unsafe_actions_summary", manifest["run_state_summary"])
        self.assertIn("lifecycle_closure_status", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_safely_closed", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_terminal", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_resumable", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_manual_required", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_replan_required", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_execution_complete_not_closed", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_rollback_complete_not_closed", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_blocked_reason", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_primary_closure_issue", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_stop_class", manifest["run_state_summary_compact"])
        self.assertNotIn("lifecycle_blocked_reasons", manifest["run_state_summary_compact"])
        self.assertIn("operator_posture_summary", manifest["run_state_summary_compact"])
        self.assertIn("operator_primary_blocker_class", manifest["run_state_summary_compact"])
        self.assertIn("operator_primary_action", manifest["run_state_summary_compact"])
        self.assertIn("operator_resume_status", manifest["run_state_summary_compact"])
        self.assertIn("operator_next_safe_posture", manifest["run_state_summary_compact"])
        self.assertNotIn("operator_guidance_summary", manifest["run_state_summary_compact"])
        self.assertNotIn("operator_safe_actions_summary", manifest["run_state_summary_compact"])
        self.assertNotIn("operator_unsafe_actions_summary", manifest["run_state_summary_compact"])
        self.assertEqual(
            manifest["run_state_summary_contract"]["canonical_run_truth_owner"],
            "run_state.json",
        )
        self.assertIn(
            "operator_guidance_summary",
            manifest["run_state_summary_contract"]["rendering_only_operator_fields"],
        )
        self.assertIn(
            "lifecycle_closure_status",
            manifest["run_state_summary_contract"]["lifecycle_summary_safe_fields"],
        )

    def test_stop_on_failure_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RecordingDryRunTransport(
                status_by_pr_id={"project-planned-exec-pr-02": "failed"}
            )
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )

            decision_payload = json.loads(
                Path(manifest["next_action_path"]).read_text(encoding="utf-8")
            )

        self.assertEqual(manifest["run_status"], "failed")
        self.assertEqual(
            [entry["pr_id"] for entry in manifest["pr_units"]],
            [
                "project-planned-exec-pr-01",
                "project-planned-exec-pr-02",
            ],
        )
        self.assertIn(decision_payload["next_action"], {"same_prompt_retry", "escalate_to_human"})

    def test_dry_run_transport_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )
            first = manifest["pr_units"][0]
            result_payload = json.loads(Path(first["result_path"]).read_text(encoding="utf-8"))
            decision_payload = json.loads(
                Path(manifest["next_action_path"]).read_text(encoding="utf-8")
            )
            handoff_payload = json.loads(
                Path(manifest["action_handoff_path"]).read_text(encoding="utf-8")
            )

        self.assertEqual(result_payload["execution"]["status"], "not_started")
        self.assertEqual(result_payload["execution"]["verify"]["status"], "not_run")
        self.assertEqual(result_payload["failure_type"], "missing_signal")
        self.assertEqual(decision_payload["next_action"], "signal_recollect")
        self.assertEqual(handoff_payload["next_action"], "signal_recollect")
        self.assertFalse(decision_payload["next_action"] in {"proceed_to_pr", "proceed_to_merge"})

    def test_live_transport_path_integrates_with_controller(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RecordingLiveTransport()
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
            )

            decision_payload = json.loads(
                Path(manifest["next_action_path"]).read_text(encoding="utf-8")
            )
            first = manifest["pr_units"][0]
            result_payload = json.loads(Path(first["result_path"]).read_text(encoding="utf-8"))
            handoff_payload = json.loads(
                Path(manifest["action_handoff_path"]).read_text(encoding="utf-8")
            )
            commit_decision = json.loads((Path(first["compiled_prompt_path"]).parent / "commit_decision.json").read_text(encoding="utf-8"))
            merge_decision = json.loads((Path(first["compiled_prompt_path"]).parent / "merge_decision.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["run_status"], "completed")
        self.assertEqual(result_payload["execution"]["status"], "completed")
        self.assertEqual(result_payload["execution"]["verify"]["status"], "passed")
        self.assertEqual(decision_payload["next_action"], "proceed_to_pr")
        self.assertEqual(handoff_payload["next_action"], "proceed_to_pr")
        self.assertTrue(handoff_payload["action_consumable"])
        self.assertFalse(decision_payload["whether_human_required"])
        self.assertEqual(manifest["progression_summary"]["final_unit_state"], "advanced")
        self.assertEqual(commit_decision["readiness_status"], "ready")
        self.assertEqual(commit_decision["readiness_next_action"], "prepare_commit")
        self.assertTrue(commit_decision["automation_eligible"])
        self.assertTrue(commit_decision["prerequisites_satisfied"])
        self.assertEqual(merge_decision["readiness_status"], "awaiting_prerequisites")
        self.assertEqual(merge_decision["readiness_next_action"], "resolve_blockers")
        self.assertFalse(merge_decision["automation_eligible"])

    def test_checkpoint_decision_maps_progression_to_commit_evaluation_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RecordingLiveTransport()
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
            )

            first = manifest["pr_units"][0]
            checkpoint_payload = json.loads(
                Path(first["checkpoint_decision_path"]).read_text(encoding="utf-8")
            )
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))
            first = manifest["pr_units"][0]
            commit_decision = json.loads(
                (Path(first["compiled_prompt_path"]).parent / "commit_decision.json").read_text(
                    encoding="utf-8"
                )
            )
            merge_decision = json.loads(
                (Path(first["compiled_prompt_path"]).parent / "merge_decision.json").read_text(
                    encoding="utf-8"
                )
            )
            first = manifest["pr_units"][0]
            commit_decision = json.loads((Path(first["compiled_prompt_path"]).parent / "commit_decision.json").read_text(encoding="utf-8"))
            merge_decision = json.loads((Path(first["compiled_prompt_path"]).parent / "merge_decision.json").read_text(encoding="utf-8"))
            first = manifest["pr_units"][0]
            commit_decision = json.loads((Path(first["compiled_prompt_path"]).parent / "commit_decision.json").read_text(encoding="utf-8"))
            merge_decision = json.loads((Path(first["compiled_prompt_path"]).parent / "merge_decision.json").read_text(encoding="utf-8"))

        self.assertEqual(checkpoint_payload["decision"], "commit_evaluation_ready")
        self.assertEqual(checkpoint_payload["checkpoint_stage"], "pre_commit_evaluation")
        self.assertFalse(checkpoint_payload["manual_intervention_required"])
        self.assertFalse(checkpoint_payload["global_stop_recommended"])
        self.assertTrue(run_state_payload["continue_allowed"])
        self.assertEqual(run_state_payload["orchestration_state"], "run_ready_to_continue")
        self.assertEqual(run_state_payload["next_run_action"], "continue_run")
        self.assertFalse(run_state_payload["run_paused"])
        self.assertFalse(run_state_payload["rollback_evaluation_pending"])
        self.assertEqual(run_state_payload["readiness_summary"]["commit"]["ready"], 3)
        self.assertEqual(
            run_state_payload["readiness_summary"]["merge"]["awaiting_prerequisites"],
            3,
        )
        self.assertFalse(run_state_payload["readiness_blocked"])
        self.assertFalse(run_state_payload["readiness_manual_required"])
        self.assertTrue(run_state_payload["readiness_awaiting_prerequisites"])

    def test_run_state_orchestration_global_stop_pending_when_manual_gate_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RecordingLiveTransport(verify_status_by_pr_id={"project-planned-exec-pr-01": "failed"})
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
                retry_context={
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 0,
                },
            )
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))
            first = manifest["pr_units"][0]
            commit_decision = json.loads(
                (Path(first["compiled_prompt_path"]).parent / "commit_decision.json").read_text(
                    encoding="utf-8"
                )
            )
            merge_decision = json.loads(
                (Path(first["compiled_prompt_path"]).parent / "merge_decision.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(run_state_payload["state"], "paused")
        self.assertEqual(run_state_payload["orchestration_state"], "global_stop_pending")
        self.assertEqual(run_state_payload["next_run_action"], "hold_for_global_stop")
        self.assertFalse(run_state_payload["continue_allowed"])
        self.assertTrue(run_state_payload["run_paused"])
        self.assertTrue(run_state_payload["manual_intervention_required"])
        self.assertTrue(run_state_payload["global_stop_recommended"])
        self.assertEqual(commit_decision["readiness_status"], "manual_required")
        self.assertFalse(commit_decision["automation_eligible"])
        self.assertTrue(commit_decision["manual_intervention_required"])
        self.assertEqual(merge_decision["readiness_status"], "manual_required")
        self.assertFalse(merge_decision["automation_eligible"])

    def test_run_state_orchestration_rollback_evaluation_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RollbackSignalLiveTransport()
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
                retry_context={
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 2,
                },
            )
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))
            first = manifest["pr_units"][0]
            rollback_decision = json.loads((Path(first["compiled_prompt_path"]).parent / "rollback_decision.json").read_text(encoding="utf-8"))

        self.assertTrue(run_state_payload["rollback_evaluation_pending"])
        self.assertEqual(run_state_payload["orchestration_state"], "rollback_evaluation_pending")
        self.assertEqual(run_state_payload["next_run_action"], "evaluate_rollback")
        self.assertFalse(run_state_payload["continue_allowed"])
        self.assertTrue(run_state_payload["run_paused"])
        self.assertEqual(rollback_decision["decision"], "required")
        self.assertEqual(rollback_decision["readiness_status"], "awaiting_prerequisites")
        self.assertEqual(rollback_decision["readiness_next_action"], "resolve_blockers")
        self.assertFalse(rollback_decision["automation_eligible"])
        self.assertTrue(rollback_decision["prerequisites_satisfied"])

    def test_closed_loop_next_action_prefers_commit_when_commit_ready_and_not_executed(self) -> None:
        run_state = {
            "continue_allowed": True,
            "run_paused": False,
            "manual_intervention_required": False,
            "rollback_evaluation_pending": False,
            "global_stop_recommended": False,
            "global_stop": False,
            "merge_execution_succeeded": False,
            "rollback_execution_succeeded": False,
            "rollback_execution_failed": False,
            "rollback_replan_required": False,
            "rollback_automatic_continuation_blocked": False,
            "units_pending": 0,
        }
        manifest_units = [
            {
                "decision_summary": {
                    "commit_readiness_status": "ready",
                    "commit_execution_status": "blocked",
                },
                "commit_execution_summary": {"status": "blocked"},
            }
        ]

        augmented = _augment_run_state_with_closed_loop(
            run_state_payload=run_state,
            manifest_units=manifest_units,
            run_status="completed",
        )

        self.assertEqual(augmented["loop_state"], "delivery_in_progress")
        self.assertEqual(augmented["next_safe_action"], "execute_commit")
        self.assertTrue(augmented["resumable"])
        self.assertFalse(augmented["terminal"])

    def test_closed_loop_next_action_blocks_on_manual_and_global_stop(self) -> None:
        run_state = {
            "continue_allowed": False,
            "run_paused": True,
            "manual_intervention_required": True,
            "rollback_evaluation_pending": False,
            "global_stop_recommended": True,
            "global_stop": True,
            "merge_execution_succeeded": False,
            "rollback_execution_succeeded": False,
            "rollback_execution_failed": False,
            "rollback_replan_required": False,
            "rollback_automatic_continuation_blocked": False,
            "units_pending": 0,
        }

        augmented = _augment_run_state_with_closed_loop(
            run_state_payload=run_state,
            manifest_units=[
                {
                    "decision_summary": {
                        "merge_readiness_status": "ready",
                        "merge_execution_status": "succeeded",
                        "pr_execution_status": "succeeded",
                        "push_execution_status": "succeeded",
                        "commit_execution_status": "succeeded",
                    }
                }
            ],
            run_status="completed",
        )

        self.assertEqual(augmented["loop_state"], "manual_intervention_required")
        self.assertEqual(augmented["next_safe_action"], "require_manual_intervention")
        self.assertTrue(augmented["loop_manual_intervention_required"])
        self.assertFalse(augmented["terminal"])

    def test_closed_loop_next_action_requires_replan_after_rollback(self) -> None:
        run_state = {
            "continue_allowed": False,
            "run_paused": True,
            "manual_intervention_required": False,
            "rollback_evaluation_pending": False,
            "global_stop_recommended": False,
            "global_stop": False,
            "merge_execution_succeeded": False,
            "rollback_execution_succeeded": True,
            "rollback_execution_failed": False,
            "rollback_replan_required": True,
            "rollback_automatic_continuation_blocked": True,
            "units_pending": 0,
        }

        augmented = _augment_run_state_with_closed_loop(
            run_state_payload=run_state,
            manifest_units=[
                {
                    "decision_summary": {
                        "merge_readiness_status": "ready",
                        "merge_execution_status": "succeeded",
                        "pr_execution_status": "succeeded",
                        "push_execution_status": "succeeded",
                        "commit_execution_status": "succeeded",
                    }
                }
            ],
            run_status="completed",
        )

        self.assertEqual(augmented["loop_state"], "replan_required")
        self.assertEqual(augmented["next_safe_action"], "require_replanning")
        self.assertTrue(augmented["loop_replan_required"])
        self.assertFalse(augmented["terminal"])

    def test_closed_loop_next_action_terminal_success_only_after_delivery_completion(self) -> None:
        run_state = {
            "continue_allowed": False,
            "run_paused": False,
            "manual_intervention_required": False,
            "rollback_evaluation_pending": False,
            "global_stop_recommended": False,
            "global_stop": False,
            "merge_execution_succeeded": True,
            "rollback_execution_succeeded": False,
            "rollback_execution_failed": False,
            "rollback_replan_required": False,
            "rollback_automatic_continuation_blocked": False,
            "units_pending": 0,
        }

        augmented = _augment_run_state_with_closed_loop(
            run_state_payload=run_state,
            manifest_units=[
                {
                    "decision_summary": {
                        "merge_readiness_status": "ready",
                        "merge_execution_status": "succeeded",
                        "pr_execution_status": "succeeded",
                        "push_execution_status": "succeeded",
                        "commit_execution_status": "succeeded",
                    }
                }
            ],
            run_status="completed",
        )

        self.assertEqual(augmented["loop_state"], "terminal_success")
        self.assertEqual(augmented["next_safe_action"], "stop_terminal_success")
        self.assertTrue(augmented["terminal"])
        self.assertFalse(augmented["resumable"])

    def test_closed_loop_next_action_blocks_ambiguous_lifecycle_evidence(self) -> None:
        run_state = {
            "continue_allowed": True,
            "run_paused": False,
            "manual_intervention_required": False,
            "rollback_evaluation_pending": True,
            "next_run_action": "evaluate_rollback",
            "global_stop_recommended": False,
            "global_stop": False,
            "merge_execution_succeeded": False,
            "rollback_execution_succeeded": False,
            "rollback_execution_failed": False,
            "rollback_replan_required": False,
            "rollback_automatic_continuation_blocked": False,
            "units_pending": 0,
        }
        manifest_units = [
            {
                "decision_summary": {
                    "rollback_readiness_status": "awaiting_prerequisites",
                    "rollback_execution_status": "blocked",
                },
                "rollback_execution_summary": {"status": "blocked"},
            }
        ]

        augmented = _augment_run_state_with_closed_loop(
            run_state_payload=run_state,
            manifest_units=manifest_units,
            run_status="completed",
        )

        self.assertEqual(augmented["loop_state"], "runnable_blocked")
        self.assertEqual(augmented["next_safe_action"], "pause")
        self.assertEqual(augmented["loop_blocked_reason"], "rollback_pending_without_ready_unit")
        self.assertTrue(augmented["loop_manual_intervention_required"])

    def test_commit_execution_succeeds_when_readiness_and_run_state_allow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            changed_file = self._shrink_to_single_pr_slice(artifacts_dir)
            out_dir = root / "artifacts" / "executions"
            repo_dir = root / "execution_repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            head_before = self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)

            transport = _CommitReadyLiveTransport(
                changed_files_by_pr_id={"project-planned-exec-pr-01": [changed_file]}
            )
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
                execution_repo_path=repo_dir,
            )
            first = manifest["pr_units"][0]
            commit_execution = json.loads(
                Path(first["commit_execution_path"]).read_text(encoding="utf-8")
            )
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))
            progression = json.loads(Path(first["unit_progression_path"]).read_text(encoding="utf-8"))
            head_after = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

        self.assertEqual(commit_execution["status"], "succeeded")
        self.assertTrue(commit_execution["attempted"])
        self.assertTrue(commit_execution["commit_sha"])
        self.assertFalse(commit_execution["manual_intervention_required"])
        self.assertTrue(commit_execution["execution_allowed"])
        self.assertEqual(commit_execution["execution_authority_status"], "allowed")
        self.assertEqual(commit_execution["validation_status"], "passed")
        self.assertFalse(commit_execution["manual_approval_required"])
        self.assertNotEqual(head_before, head_after)
        self.assertTrue(run_state_payload["commit_execution_executed"])
        self.assertFalse(run_state_payload["commit_execution_failed"])
        states = [entry["state"] for entry in progression["checkpoints"]]
        self.assertIn("commit_execution_started", states)
        self.assertIn("commit_executed", states)
        self.assertNotIn("commit_execution_failed", states)

    def test_commit_execution_is_blocked_when_repo_path_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            changed_file = self._shrink_to_single_pr_slice(artifacts_dir)
            out_dir = root / "artifacts" / "executions"
            transport = _CommitReadyLiveTransport(
                changed_files_by_pr_id={"project-planned-exec-pr-01": [changed_file]}
            )
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
            )
            first = manifest["pr_units"][0]
            commit_execution = json.loads(
                Path(first["commit_execution_path"]).read_text(encoding="utf-8")
            )
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))
            progression = json.loads(Path(first["unit_progression_path"]).read_text(encoding="utf-8"))

        self.assertEqual(commit_execution["status"], "blocked")
        self.assertFalse(commit_execution["attempted"])
        self.assertIn("execution_repo_path_missing", commit_execution["blocking_reasons"])
        self.assertFalse(commit_execution["execution_allowed"])
        self.assertEqual(commit_execution["execution_authority_status"], "allowed")
        self.assertEqual(commit_execution["validation_status"], "blocked")
        self.assertTrue(commit_execution["manual_approval_required"])
        self.assertTrue(run_state_payload["commit_execution_pending"])
        self.assertFalse(run_state_payload["commit_execution_executed"])
        states = [entry["state"] for entry in progression["checkpoints"]]
        self.assertNotIn("commit_execution_started", states)

    def test_commit_execution_blocked_when_worktree_has_unscoped_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            changed_file = self._shrink_to_single_pr_slice(artifacts_dir)
            out_dir = root / "artifacts" / "executions"
            repo_dir = root / "execution_repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)
            unscoped_file = repo_dir / "README.md"
            unscoped_file.write_text("unexpected change\n", encoding="utf-8")

            transport = _CommitReadyLiveTransport(
                changed_files_by_pr_id={"project-planned-exec-pr-01": [changed_file]}
            )
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
                execution_repo_path=repo_dir,
            )
            first = manifest["pr_units"][0]
            commit_execution = json.loads(
                Path(first["commit_execution_path"]).read_text(encoding="utf-8")
            )

        self.assertEqual(commit_execution["status"], "blocked")
        self.assertEqual(
            commit_execution["failure_reason"],
            "working_tree_contains_out_of_scope_changes",
        )
        self.assertIn(
            "working_tree_contains_out_of_scope_changes",
            commit_execution["unsafe_repo_state"],
        )
        self.assertFalse(commit_execution["execution_allowed"])
        self.assertEqual(commit_execution["validation_status"], "blocked")
        self.assertTrue(commit_execution["manual_approval_required"])

    def test_commit_execution_failure_persists_receipt_and_progression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            changed_file = self._shrink_to_single_pr_slice(artifacts_dir)
            out_dir = root / "artifacts" / "executions"
            repo_dir = root / "execution_repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            head_before = self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)

            hooks_dir = root / "hooks"
            hooks_dir.mkdir(parents=True, exist_ok=True)
            pre_commit = hooks_dir / "pre-commit"
            pre_commit.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            pre_commit.chmod(0o755)
            subprocess.run(
                ["git", "-C", str(repo_dir), "config", "core.hooksPath", str(hooks_dir)],
                check=True,
                capture_output=True,
                text=True,
            )

            transport = _CommitReadyLiveTransport(
                changed_files_by_pr_id={"project-planned-exec-pr-01": [changed_file]}
            )
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
                execution_repo_path=repo_dir,
            )
            first = manifest["pr_units"][0]
            commit_execution = json.loads(
                Path(first["commit_execution_path"]).read_text(encoding="utf-8")
            )
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))
            progression = json.loads(Path(first["unit_progression_path"]).read_text(encoding="utf-8"))
            head_after = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

        self.assertEqual(commit_execution["status"], "failed")
        self.assertTrue(commit_execution["attempted"])
        self.assertEqual(commit_execution["failure_reason"], "git_commit_failed")
        self.assertTrue(commit_execution["manual_intervention_required"])
        self.assertTrue(commit_execution["execution_allowed"])
        self.assertEqual(commit_execution["execution_authority_status"], "allowed")
        self.assertEqual(commit_execution["validation_status"], "passed")
        self.assertEqual(head_before, head_after)
        self.assertTrue(run_state_payload["commit_execution_failed"])
        self.assertTrue(run_state_payload["commit_execution_manual_intervention_required"])
        states = [entry["state"] for entry in progression["checkpoints"]]
        self.assertIn("commit_execution_started", states)
        self.assertIn("commit_execution_failed", states)

    def test_push_pr_merge_execute_when_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            changed_file = self._shrink_to_single_pr_slice(artifacts_dir)
            out_dir = root / "artifacts" / "executions"
            repo_dir = root / "execution_repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)
            self._attach_origin_remote_and_push_initial(repo_dir)

            transport = _CommitReadyLiveTransport(
                changed_files_by_pr_id={"project-planned-exec-pr-01": [changed_file]}
            )
            read_backend = _FakeGitHubReadBackend(lookup_status="success", matched=False)
            write_backend = _FakeGitHubWriteBackend(create_status="success", merge_status="success")
            runner = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport),
                github_read_backend=read_backend,
                github_write_backend=write_backend,
            )
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
                execution_repo_path=repo_dir,
            )
            first = manifest["pr_units"][0]
            push_execution = json.loads(Path(first["push_execution_path"]).read_text(encoding="utf-8"))
            pr_execution = json.loads(Path(first["pr_execution_path"]).read_text(encoding="utf-8"))
            merge_execution = json.loads(Path(first["merge_execution_path"]).read_text(encoding="utf-8"))
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))
            merge_decision = json.loads(Path(first["merge_decision_path"]).read_text(encoding="utf-8"))
            progression = json.loads(Path(first["unit_progression_path"]).read_text(encoding="utf-8"))
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))

        self.assertEqual(push_execution["status"], "succeeded")
        self.assertEqual(pr_execution["status"], "succeeded")
        self.assertEqual(merge_execution["status"], "succeeded")
        self.assertEqual(push_execution["remote_state_status"], "ready")
        self.assertEqual(pr_execution["pr_creation_state_status"], "created")
        self.assertEqual(merge_execution["mergeability_status"], "clean")
        self.assertEqual(merge_execution["merge_requirements_status"], "satisfied")
        self.assertTrue(push_execution["execution_allowed"])
        self.assertTrue(pr_execution["execution_allowed"])
        self.assertTrue(merge_execution["execution_allowed"])
        self.assertEqual(push_execution["execution_authority_status"], "allowed")
        self.assertEqual(pr_execution["execution_authority_status"], "allowed")
        self.assertEqual(merge_execution["execution_authority_status"], "allowed")
        self.assertEqual(merge_decision["decision"], "allowed")
        self.assertEqual(merge_decision["readiness_status"], "ready")
        self.assertEqual(merge_decision["readiness_next_action"], "prepare_merge")
        self.assertTrue(merge_decision["automation_eligible"])
        self.assertTrue(run_state_payload["push_execution_succeeded"])
        self.assertTrue(run_state_payload["pr_execution_succeeded"])
        self.assertTrue(run_state_payload["merge_execution_succeeded"])
        self.assertFalse(run_state_payload["push_execution_failed"])
        self.assertFalse(run_state_payload["pr_execution_failed"])
        self.assertFalse(run_state_payload["merge_execution_failed"])
        states = [entry["state"] for entry in progression["checkpoints"]]
        self.assertIn("push_execution_started", states)
        self.assertIn("push_executed", states)
        self.assertIn("pr_creation_started", states)
        self.assertIn("pr_created", states)
        self.assertIn("merge_execution_started", states)
        self.assertIn("merge_executed", states)
        self.assertEqual(len(write_backend.create_calls), 1)
        self.assertEqual(len(write_backend.merge_calls), 1)

    def test_push_is_blocked_when_commit_execution_not_succeeded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            changed_file = self._shrink_to_single_pr_slice(artifacts_dir)
            out_dir = root / "artifacts" / "executions"
            transport = _CommitReadyLiveTransport(
                changed_files_by_pr_id={"project-planned-exec-pr-01": [changed_file]}
            )
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
            )
            first = manifest["pr_units"][0]
            commit_execution = json.loads(Path(first["commit_execution_path"]).read_text(encoding="utf-8"))
            push_execution = json.loads(Path(first["push_execution_path"]).read_text(encoding="utf-8"))
            pr_execution = json.loads(Path(first["pr_execution_path"]).read_text(encoding="utf-8"))
            merge_execution = json.loads(Path(first["merge_execution_path"]).read_text(encoding="utf-8"))

        self.assertEqual(commit_execution["status"], "blocked")
        self.assertEqual(push_execution["status"], "blocked")
        self.assertIn("commit_execution_not_succeeded", push_execution["blocking_reasons"])
        self.assertFalse(push_execution["execution_allowed"])
        self.assertEqual(push_execution["validation_status"], "blocked")
        self.assertEqual(pr_execution["status"], "blocked")
        self.assertEqual(merge_execution["status"], "blocked")

    def test_pr_creation_blocks_when_github_truth_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            changed_file = self._shrink_to_single_pr_slice(artifacts_dir)
            out_dir = root / "artifacts" / "executions"
            repo_dir = root / "execution_repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)
            self._attach_origin_remote_and_push_initial(repo_dir)

            transport = _CommitReadyLiveTransport(
                changed_files_by_pr_id={"project-planned-exec-pr-01": [changed_file]}
            )
            read_backend = _FakeGitHubReadBackend(lookup_status="api_failure", matched=False)
            write_backend = _FakeGitHubWriteBackend(create_status="success", merge_status="success")
            runner = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport),
                github_read_backend=read_backend,
                github_write_backend=write_backend,
            )
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
                execution_repo_path=repo_dir,
            )
            first = manifest["pr_units"][0]
            push_execution = json.loads(Path(first["push_execution_path"]).read_text(encoding="utf-8"))
            pr_execution = json.loads(Path(first["pr_execution_path"]).read_text(encoding="utf-8"))
            merge_execution = json.loads(Path(first["merge_execution_path"]).read_text(encoding="utf-8"))

        self.assertEqual(push_execution["status"], "succeeded")
        self.assertEqual(pr_execution["status"], "blocked")
        self.assertEqual(pr_execution["failure_reason"], "open_pr_lookup_api_failure")
        self.assertTrue(pr_execution["manual_intervention_required"])
        self.assertFalse(pr_execution["execution_allowed"])
        self.assertEqual(pr_execution["validation_status"], "passed")
        self.assertTrue(pr_execution["remote_state_missing_or_ambiguous"])
        self.assertIn("open_pr_lookup_api_failure", pr_execution["remote_pr_ambiguity"])
        self.assertTrue(pr_execution["remote_github_blocked"])
        self.assertEqual(merge_execution["status"], "blocked")
        run_state_path = Path(manifest["run_state_path"])
        run_state_payload = (
            json.loads(run_state_path.read_text(encoding="utf-8"))
            if run_state_path.exists()
            else dict(manifest.get("run_state_summary", {}))
        )
        self.assertTrue(run_state_payload["remote_github_blocked"])
        self.assertTrue(run_state_payload["remote_github_manual_required"])
        self.assertTrue(run_state_payload["remote_github_missing_or_ambiguous"])
        self.assertIn("open_pr_lookup_api_failure", run_state_payload["remote_github_blocked_reasons"])
        self.assertEqual(len(write_backend.create_calls), 0)
        self.assertEqual(len(write_backend.merge_calls), 0)

    def test_push_blocked_when_remote_state_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir = Path(tmp_dir) / "repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            changed_file = "automation/planning/prompt_compiler.py"
            self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)
            subprocess.run(
                ["git", "-C", str(repo_dir), "add", "--", changed_file],
                check=True,
                capture_output=True,
                text=True,
            )
            commit_sha = self._git_commit(repo_dir, "bounded commit")
            payload = _execute_bounded_push(
                unit_id="pr-push-no-remote",
                repo_path=str(repo_dir),
                remote_name="origin",
                configured_head_branch="feature/test",
                base_branch="main",
                run_state_payload={
                    "continue_allowed": True,
                    "run_paused": False,
                    "manual_intervention_required": False,
                    "global_stop_recommended": False,
                    "global_stop": False,
                    "rollback_evaluation_pending": False,
                },
                commit_execution_payload={"status": "succeeded", "commit_sha": commit_sha},
                dry_run=False,
                now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
            )

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("git_remote_missing", payload["blocking_reasons"])
        self.assertFalse(payload["execution_allowed"])
        self.assertEqual(payload["validation_status"], "passed")
        self.assertIn("git_remote_missing", payload["missing_required_refs"])
        self.assertTrue(payload["remote_state_blocked"])
        self.assertTrue(payload["remote_github_blocked"])

    def test_push_blocked_due_remote_divergence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir = Path(tmp_dir) / "repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            changed_file = "automation/planning/prompt_compiler.py"
            self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)
            remote_dir = self._attach_origin_remote_and_push_initial(repo_dir)
            branch_name = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "--abbrev-ref", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            peer_dir = Path(tmp_dir) / "peer"
            subprocess.run(["git", "clone", str(remote_dir), str(peer_dir)], check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "-C", str(peer_dir), "config", "user.name", "Peer Runner"],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "-C", str(peer_dir), "config", "user.email", "peer@example.com"],
                check=True,
                capture_output=True,
                text=True,
            )
            peer_target = peer_dir / changed_file
            peer_target.parent.mkdir(parents=True, exist_ok=True)
            peer_target.write_text("baseline\npeer\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(peer_dir), "add", "--", changed_file], check=True, capture_output=True, text=True)
            self._git_commit(peer_dir, "peer update")
            subprocess.run(
                ["git", "-C", str(peer_dir), "push", "origin", f"HEAD:{branch_name}"],
                check=True,
                capture_output=True,
                text=True,
            )

            commit_sha = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            payload = _execute_bounded_push(
                unit_id="pr-push-diverged",
                repo_path=str(repo_dir),
                remote_name="origin",
                configured_head_branch=branch_name,
                base_branch="main",
                run_state_payload={
                    "continue_allowed": True,
                    "run_paused": False,
                    "manual_intervention_required": False,
                    "global_stop_recommended": False,
                    "global_stop": False,
                    "rollback_evaluation_pending": False,
                },
                commit_execution_payload={"status": "succeeded", "commit_sha": commit_sha},
                dry_run=False,
                now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
            )

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("remote_non_fast_forward_risk", payload["blocking_reasons"])
        self.assertFalse(payload["execution_allowed"])
        self.assertEqual(payload["validation_status"], "passed")
        self.assertEqual(payload["remote_state_status"], "non_fast_forward_risk")
        self.assertEqual(payload["upstream_tracking_status"], "tracked")
        self.assertEqual(payload["remote_divergence_status"], "non_fast_forward_risk")
        self.assertTrue(payload["remote_state_blocked"])

    def test_push_blocked_when_upstream_tracking_is_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir = Path(tmp_dir) / "repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            changed_file = "automation/planning/prompt_compiler.py"
            self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)
            remote_dir = Path(tmp_dir) / "origin.git"
            subprocess.run(["git", "init", "--bare", str(remote_dir)], check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "-C", str(repo_dir), "remote", "add", "origin", str(remote_dir)],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "-C", str(repo_dir), "push", "origin", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            )
            commit_sha = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            payload = _execute_bounded_push(
                unit_id="pr-push-upstream-ambiguous",
                repo_path=str(repo_dir),
                remote_name="origin",
                configured_head_branch="feature/test",
                base_branch="main",
                run_state_payload={
                    "continue_allowed": True,
                    "run_paused": False,
                    "manual_intervention_required": False,
                    "global_stop_recommended": False,
                    "global_stop": False,
                    "rollback_evaluation_pending": False,
                },
                commit_execution_payload={"status": "succeeded", "commit_sha": commit_sha},
                dry_run=False,
                now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
            )

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("upstream_tracking_unresolved", payload["blocking_reasons"])
        self.assertEqual(payload["remote_state_status"], "ambiguous")
        self.assertTrue(payload["remote_state_missing_or_ambiguous"])
        self.assertEqual(payload["validation_status"], "passed")

    def test_pr_creation_blocked_when_existing_matching_pr_exists(self) -> None:
        payload = _execute_bounded_pr_creation(
            unit_id="pr-create-existing",
            job_id="job-1",
            repository="owner/repo",
            base_branch="main",
            run_state_payload={
                "continue_allowed": True,
                "run_paused": False,
                "manual_intervention_required": False,
                "global_stop_recommended": False,
                "global_stop": False,
                "rollback_evaluation_pending": False,
            },
            merge_decision_payload={
                "manual_intervention_required": False,
                "unresolved_blockers": [],
            },
            commit_execution_payload={"status": "succeeded", "commit_sha": "a" * 40},
            push_execution_payload={
                "status": "succeeded",
                "branch_name": "feature/test",
                "remote_name": "origin",
                "head_branch": "feature/test",
            },
            read_backend=_FakeGitHubReadBackend(
                lookup_status="success",
                matched=True,
                match_count=1,
                pr_number=77,
                pr_url="https://example.local/pr/77",
            ),
            write_backend=_FakeGitHubWriteBackend(),
            now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
        )
        payload = dict(payload)

        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["failure_reason"], "existing_open_pr_detected")
        self.assertEqual(payload["existing_pr_status"], "existing_open")
        self.assertEqual(payload["pr_creation_state_status"], "blocked_existing_pr")
        self.assertEqual(payload["pr_duplication_risk"], "detected")
        self.assertTrue(payload["remote_state_blocked"])
        self.assertEqual(payload["validation_status"], "passed")

    def test_pr_creation_blocked_when_existing_pr_lookup_is_ambiguous(self) -> None:
        payload = _execute_bounded_pr_creation(
            unit_id="pr-create-existing-ambiguous",
            job_id="job-1",
            repository="owner/repo",
            base_branch="main",
            run_state_payload={
                "continue_allowed": True,
                "run_paused": False,
                "manual_intervention_required": False,
                "global_stop_recommended": False,
                "global_stop": False,
                "rollback_evaluation_pending": False,
            },
            merge_decision_payload={
                "manual_intervention_required": False,
                "unresolved_blockers": [],
            },
            commit_execution_payload={"status": "succeeded", "commit_sha": "a" * 40},
            push_execution_payload={
                "status": "succeeded",
                "branch_name": "feature/test",
                "remote_name": "origin",
                "head_branch": "feature/test",
            },
            read_backend=_FakeGitHubReadBackend(
                lookup_status="success",
                matched=True,
                match_count=2,
                pr_number=88,
                pr_url="https://example.local/pr/88",
            ),
            write_backend=_FakeGitHubWriteBackend(),
            now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
        )
        payload = dict(payload)

        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["failure_reason"], "existing_pr_lookup_ambiguous")
        self.assertTrue(payload["remote_state_missing_or_ambiguous"])
        self.assertEqual(payload["validation_status"], "passed")

    def test_pr_creation_blocked_when_base_or_head_is_missing(self) -> None:
        payload = _execute_bounded_pr_creation(
            unit_id="pr-create-missing-refs",
            job_id="job-1",
            repository="owner/repo",
            base_branch="",
            run_state_payload={
                "continue_allowed": True,
                "run_paused": False,
                "manual_intervention_required": False,
                "global_stop_recommended": False,
                "global_stop": False,
                "rollback_evaluation_pending": False,
            },
            merge_decision_payload={
                "manual_intervention_required": False,
                "unresolved_blockers": [],
            },
            commit_execution_payload={"status": "succeeded", "commit_sha": "a" * 40},
            push_execution_payload={
                "status": "succeeded",
                "branch_name": "",
                "remote_name": "origin",
                "head_branch": "",
            },
            read_backend=_FakeGitHubReadBackend(),
            write_backend=_FakeGitHubWriteBackend(),
            now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
        )
        payload = dict(payload)

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("base_branch_missing", payload["blocking_reasons"])
        self.assertIn("head_branch_missing", payload["blocking_reasons"])
        self.assertFalse(payload["execution_allowed"])
        self.assertEqual(payload["validation_status"], "blocked")
        self.assertIn("base_branch_missing", payload["missing_required_refs"])
        self.assertIn("head_branch_missing", payload["missing_required_refs"])
        self.assertFalse(payload["remote_state_blocked"])

    def test_merge_blocked_when_pr_identity_missing(self) -> None:
        payload = _execute_bounded_merge(
            unit_id="pr-merge-missing-id",
            repository="owner/repo",
            run_state_payload={
                "continue_allowed": True,
                "run_paused": False,
                "manual_intervention_required": False,
                "global_stop_recommended": False,
                "global_stop": False,
                "rollback_evaluation_pending": False,
            },
            merge_decision_payload={
                "readiness_status": "ready",
                "automation_eligible": True,
                "manual_intervention_required": False,
                "unresolved_blockers": [],
                "prerequisites_satisfied": True,
            },
            commit_execution_payload={"status": "succeeded", "commit_sha": "a" * 40},
            push_execution_payload={"status": "succeeded", "branch_name": "feature/test", "remote_name": "origin"},
            pr_execution_payload={
                "status": "succeeded",
                "base_branch": "main",
                "head_branch": "feature/test",
                "pr_number": None,
            },
            read_backend=_FakeGitHubReadBackend(),
            write_backend=_FakeGitHubWriteBackend(),
            now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
        )
        payload = dict(payload)

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("pr_number_missing_or_invalid", payload["blocking_reasons"])
        self.assertFalse(payload["execution_allowed"])
        self.assertEqual(payload["validation_status"], "passed")
        self.assertIn("pr_number_missing_or_invalid", payload["remote_pr_ambiguity"])
        self.assertEqual(payload["mergeability_status"], "unknown")

    def test_merge_blocked_when_mergeability_is_unknown(self) -> None:
        payload = _execute_bounded_merge(
            unit_id="pr-merge-unknown-mergeability",
            repository="owner/repo",
            run_state_payload={
                "continue_allowed": True,
                "run_paused": False,
                "manual_intervention_required": False,
                "global_stop_recommended": False,
                "global_stop": False,
                "rollback_evaluation_pending": False,
            },
            merge_decision_payload={
                "readiness_status": "ready",
                "automation_eligible": True,
                "manual_intervention_required": False,
                "unresolved_blockers": [],
                "prerequisites_satisfied": True,
            },
            commit_execution_payload={"status": "succeeded", "commit_sha": "a" * 40},
            push_execution_payload={"status": "succeeded", "branch_name": "feature/test", "remote_name": "origin"},
            pr_execution_payload={
                "status": "succeeded",
                "base_branch": "main",
                "head_branch": "feature/test",
                "pr_number": 10,
            },
            read_backend=_FakeGitHubReadBackend(
                pr_status_status="success",
                pr_state="open",
                mergeable_state="",
                checks_state="passing",
            ),
            write_backend=_FakeGitHubWriteBackend(),
            now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
        )
        payload = dict(payload)

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("mergeability_unknown", payload["blocking_reasons"])
        self.assertEqual(payload["validation_status"], "passed")
        self.assertEqual(payload["mergeability_status"], "unknown")
        self.assertTrue(payload["remote_github_blocked"])

    def test_merge_blocked_when_required_checks_are_unsatisfied(self) -> None:
        payload = _execute_bounded_merge(
            unit_id="pr-merge-checks-unsatisfied",
            repository="owner/repo",
            run_state_payload={
                "continue_allowed": True,
                "run_paused": False,
                "manual_intervention_required": False,
                "global_stop_recommended": False,
                "global_stop": False,
                "rollback_evaluation_pending": False,
            },
            merge_decision_payload={
                "readiness_status": "ready",
                "automation_eligible": True,
                "manual_intervention_required": False,
                "unresolved_blockers": [],
                "prerequisites_satisfied": True,
            },
            commit_execution_payload={"status": "succeeded", "commit_sha": "a" * 40},
            push_execution_payload={"status": "succeeded", "branch_name": "feature/test", "remote_name": "origin"},
            pr_execution_payload={
                "status": "succeeded",
                "base_branch": "main",
                "head_branch": "feature/test",
                "pr_number": 11,
            },
            read_backend=_FakeGitHubReadBackend(
                pr_status_status="success",
                pr_state="open",
                mergeable_state="clean",
                checks_state="failing",
            ),
            write_backend=_FakeGitHubWriteBackend(),
            now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
        )
        payload = dict(payload)

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("required_checks_unsatisfied", payload["blocking_reasons"])
        self.assertEqual(payload["required_checks_status"], "unsatisfied")
        self.assertEqual(payload["merge_requirements_status"], "unsatisfied")
        self.assertTrue(payload["remote_state_blocked"])

    def test_merge_blocked_when_review_or_protection_requirements_are_unsatisfied(self) -> None:
        payload = _execute_bounded_merge(
            unit_id="pr-merge-review-protection-unsatisfied",
            repository="owner/repo",
            run_state_payload={
                "continue_allowed": True,
                "run_paused": False,
                "manual_intervention_required": False,
                "global_stop_recommended": False,
                "global_stop": False,
                "rollback_evaluation_pending": False,
            },
            merge_decision_payload={
                "readiness_status": "ready",
                "automation_eligible": True,
                "manual_intervention_required": False,
                "unresolved_blockers": [],
                "prerequisites_satisfied": True,
            },
            commit_execution_payload={"status": "succeeded", "commit_sha": "a" * 40},
            push_execution_payload={"status": "succeeded", "branch_name": "feature/test", "remote_name": "origin"},
            pr_execution_payload={
                "status": "succeeded",
                "base_branch": "main",
                "head_branch": "feature/test",
                "pr_number": 12,
            },
            read_backend=_FakeGitHubReadBackend(
                pr_status_status="success",
                pr_state="open",
                mergeable_state="clean",
                checks_state="passing",
                review_state_status="unsatisfied",
                branch_protection_status="unsatisfied",
            ),
            write_backend=_FakeGitHubWriteBackend(),
            now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
        )
        payload = dict(payload)

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("review_requirements_unsatisfied", payload["blocking_reasons"])
        self.assertIn("branch_protection_unsatisfied", payload["blocking_reasons"])
        self.assertEqual(payload["review_state_status"], "unsatisfied")
        self.assertEqual(payload["branch_protection_status"], "unsatisfied")
        self.assertEqual(payload["merge_requirements_status"], "unsatisfied")

    def test_merge_execution_failure_persists_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            changed_file = self._shrink_to_single_pr_slice(artifacts_dir)
            out_dir = root / "artifacts" / "executions"
            repo_dir = root / "execution_repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)
            self._attach_origin_remote_and_push_initial(repo_dir)

            transport = _CommitReadyLiveTransport(
                changed_files_by_pr_id={"project-planned-exec-pr-01": [changed_file]}
            )
            read_backend = _FakeGitHubReadBackend(lookup_status="success", matched=False)
            write_backend = _FakeGitHubWriteBackend(create_status="success", merge_status="api_failure")
            runner = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport),
                github_read_backend=read_backend,
                github_write_backend=write_backend,
            )
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
                execution_repo_path=repo_dir,
            )
            first = manifest["pr_units"][0]
            merge_execution = json.loads(Path(first["merge_execution_path"]).read_text(encoding="utf-8"))
            progression = json.loads(Path(first["unit_progression_path"]).read_text(encoding="utf-8"))
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))

        self.assertEqual(merge_execution["status"], "failed")
        self.assertTrue(merge_execution["attempted"])
        self.assertEqual(merge_execution["failure_reason"], "merge_execution_failed:api_failure")
        self.assertTrue(merge_execution["manual_intervention_required"])
        self.assertTrue(merge_execution["execution_allowed"])
        self.assertEqual(merge_execution["execution_authority_status"], "allowed")
        self.assertEqual(merge_execution["validation_status"], "passed")
        self.assertTrue(run_state_payload["merge_execution_failed"])
        self.assertTrue(run_state_payload["delivery_execution_manual_intervention_required"])
        states = [entry["state"] for entry in progression["checkpoints"]]
        self.assertIn("merge_execution_started", states)
        self.assertIn("merge_execution_failed", states)

    def test_execute_bounded_rollback_local_commit_only_succeeds_when_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir = Path(tmp_dir) / "repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            changed_file = "automation/planning/prompt_compiler.py"
            self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)
            subprocess.run(
                ["git", "-C", str(repo_dir), "add", "--", changed_file],
                check=True,
                capture_output=True,
                text=True,
            )
            commit_sha = self._git_commit(repo_dir, "bounded commit")

            payload = _execute_bounded_rollback(
                unit_id="pr-rollback-local",
                repo_path=str(repo_dir),
                run_state_payload={
                    "next_run_action": "evaluate_rollback",
                    "rollback_evaluation_pending": True,
                    "continue_allowed": False,
                    "manual_intervention_required": False,
                },
                rollback_decision_payload={
                    "decision": "required",
                    "readiness_status": "awaiting_prerequisites",
                    "automation_eligible": False,
                    "manual_intervention_required": False,
                    "unresolved_blockers": [
                        "run_global_stop_recommended",
                        "run_paused",
                        "run_rollback_evaluation_pending",
                    ],
                    "prerequisites_satisfied": True,
                    "recommended_next_action": "rollback_required",
                },
                commit_execution_payload={"status": "succeeded", "commit_sha": commit_sha},
                push_execution_payload={"status": "blocked"},
                pr_execution_payload={"status": "blocked"},
                merge_execution_payload={"status": "blocked"},
                dry_run=False,
                now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
            )
            head_after = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

        self.assertEqual(payload["status"], "succeeded")
        self.assertTrue(payload["attempted"])
        self.assertEqual(payload["rollback_mode"], "local_commit_only")
        self.assertTrue(payload["replan_required"])
        self.assertFalse(payload["manual_intervention_required"])
        self.assertNotEqual(commit_sha, head_after)

    def test_execute_bounded_rollback_pushed_or_pr_open_blocks_conservatively(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir = Path(tmp_dir) / "repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            changed_file = "automation/planning/prompt_compiler.py"
            self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)
            subprocess.run(
                ["git", "-C", str(repo_dir), "add", "--", changed_file],
                check=True,
                capture_output=True,
                text=True,
            )
            commit_sha = self._git_commit(repo_dir, "bounded commit")

            payload = _execute_bounded_rollback(
                unit_id="pr-rollback-pushed",
                repo_path=str(repo_dir),
                run_state_payload={
                    "next_run_action": "evaluate_rollback",
                    "rollback_evaluation_pending": True,
                    "continue_allowed": False,
                    "manual_intervention_required": False,
                },
                rollback_decision_payload={
                    "decision": "required",
                    "readiness_status": "awaiting_prerequisites",
                    "automation_eligible": False,
                    "manual_intervention_required": False,
                    "unresolved_blockers": [
                        "run_global_stop_recommended",
                        "run_rollback_evaluation_pending",
                    ],
                    "prerequisites_satisfied": True,
                    "recommended_next_action": "rollback_required",
                },
                commit_execution_payload={"status": "succeeded", "commit_sha": commit_sha},
                push_execution_payload={"status": "succeeded"},
                pr_execution_payload={"status": "blocked"},
                merge_execution_payload={"status": "blocked"},
                dry_run=False,
                now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
            )

        self.assertEqual(payload["status"], "blocked")
        self.assertFalse(payload["attempted"])
        self.assertEqual(payload["rollback_mode"], "pushed_or_pr_open")
        self.assertEqual(
            payload["failure_reason"],
            "rollback_mode_pushed_or_pr_open_requires_manual_path",
        )
        self.assertTrue(payload["manual_intervention_required"])

    def test_execute_bounded_rollback_merged_mode_succeeds_when_head_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir = Path(tmp_dir) / "repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            merged = self._init_merged_repo(repo_dir)
            merge_sha = merged["merge_sha"]
            payload = _execute_bounded_rollback(
                unit_id="pr-rollback-merged",
                repo_path=str(repo_dir),
                run_state_payload={
                    "next_run_action": "evaluate_rollback",
                    "rollback_evaluation_pending": True,
                    "continue_allowed": False,
                    "manual_intervention_required": False,
                },
                rollback_decision_payload={
                    "decision": "required",
                    "readiness_status": "awaiting_prerequisites",
                    "automation_eligible": False,
                    "manual_intervention_required": False,
                    "unresolved_blockers": [
                        "run_global_stop_recommended",
                        "run_rollback_evaluation_pending",
                    ],
                    "prerequisites_satisfied": True,
                    "recommended_next_action": "rollback_required",
                },
                commit_execution_payload={"status": "succeeded", "commit_sha": "a" * 40},
                push_execution_payload={"status": "succeeded", "base_branch": merged["target_branch"]},
                pr_execution_payload={"status": "succeeded", "base_branch": merged["target_branch"]},
                merge_execution_payload={
                    "status": "succeeded",
                    "base_branch": merged["target_branch"],
                    "merge_commit_sha": merge_sha,
                },
                dry_run=False,
                now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
            )
            head_after = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

        self.assertEqual(payload["status"], "succeeded")
        self.assertTrue(payload["attempted"])
        self.assertEqual(payload["rollback_mode"], "merged")
        self.assertTrue(payload["resulting_commit_sha"])
        self.assertNotEqual(head_after, merge_sha)

    def test_execute_bounded_rollback_blocks_on_ambiguous_lifecycle_evidence(self) -> None:
        payload = _execute_bounded_rollback(
            unit_id="pr-rollback-ambiguous",
            repo_path="",
            run_state_payload={
                "next_run_action": "evaluate_rollback",
                "rollback_evaluation_pending": True,
                "continue_allowed": False,
                "manual_intervention_required": False,
            },
            rollback_decision_payload={
                "decision": "required",
                "readiness_status": "awaiting_prerequisites",
                "automation_eligible": False,
                "manual_intervention_required": False,
                "unresolved_blockers": [
                    "run_global_stop_recommended",
                    "run_rollback_evaluation_pending",
                ],
                "prerequisites_satisfied": True,
                "recommended_next_action": "rollback_required",
            },
            commit_execution_payload={"status": "blocked"},
            push_execution_payload={"status": "blocked"},
            pr_execution_payload={"status": "blocked"},
            merge_execution_payload={"status": "blocked"},
            dry_run=False,
            now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
        )

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("rollback_mode_ambiguous", payload["blocking_reasons"])
        self.assertTrue(payload["manual_intervention_required"])
        self.assertFalse(payload["execution_allowed"])
        self.assertEqual(payload["validation_status"], "blocked")

    def test_rollback_aftermath_validation_failed_is_classified_conservatively(self) -> None:
        payload = _with_rollback_aftermath_surface(
            {
                "status": "succeeded",
                "rollback_mode": "local_commit_only",
                "resulting_commit_sha": "a" * 40,
                "manual_intervention_required": False,
                "replan_required": False,
                "automatic_continuation_blocked": False,
                "rollback_validation_status": "failed",
                "blocking_reasons": [],
            }
        )
        self.assertEqual(payload["rollback_aftermath_status"], "validation_failed")
        self.assertTrue(payload["rollback_aftermath_blocked"])
        self.assertEqual(payload["rollback_validation_status"], "failed")
        self.assertTrue(payload["rollback_manual_followup_required"])

    def test_rollback_aftermath_merged_without_post_validation_is_not_safe(self) -> None:
        payload = _with_rollback_aftermath_surface(
            {
                "status": "succeeded",
                "rollback_mode": "merged",
                "resulting_commit_sha": "b" * 40,
                "manual_intervention_required": False,
                "replan_required": False,
                "automatic_continuation_blocked": False,
                "blocking_reasons": [],
            }
        )
        self.assertNotEqual(payload["rollback_aftermath_status"], "completed_safe")
        self.assertTrue(payload["rollback_aftermath_blocked"])
        self.assertEqual(payload["rollback_validation_status"], "unavailable")
        self.assertTrue(payload["rollback_remote_followup_required"])
        self.assertTrue(payload["rollback_aftermath_missing_or_ambiguous"])

    def test_rollback_aftermath_completed_safe_can_be_classified_explicitly(self) -> None:
        payload = _with_rollback_aftermath_surface(
            {
                "status": "succeeded",
                "rollback_mode": "local_commit_only",
                "resulting_commit_sha": "c" * 40,
                "manual_intervention_required": False,
                "replan_required": False,
                "automatic_continuation_blocked": False,
                "rollback_validation_status": "satisfied",
                "rollback_post_validation_status": "satisfied",
                "rollback_manual_followup_required": False,
                "rollback_remote_followup_required": False,
                "blocking_reasons": [],
            }
        )
        self.assertEqual(payload["rollback_aftermath_status"], "completed_safe")
        self.assertFalse(payload["rollback_aftermath_blocked"])
        self.assertEqual(payload["rollback_validation_status"], "satisfied")

    def test_run_state_rollback_aftermath_summary_is_aggregated(self) -> None:
        run_state = _augment_run_state_with_rollback_aftermath(
            run_state_payload={},
            manifest_units=[
                {
                    "rollback_execution_summary": {
                        "rollback_aftermath_status": "remote_followup_required",
                        "rollback_aftermath_blocked": True,
                        "rollback_aftermath_blocked_reasons": ["rollback_remote_followup_required"],
                        "rollback_validation_status": "unavailable",
                        "rollback_remote_followup_required": True,
                        "rollback_manual_followup_required": False,
                        "rollback_aftermath_missing_or_ambiguous": True,
                    }
                }
            ],
        )
        self.assertTrue(run_state["rollback_aftermath_blocked"])
        self.assertTrue(run_state["rollback_remote_followup_required"])
        self.assertFalse(run_state["rollback_manual_followup_required"])
        self.assertFalse(run_state["rollback_validation_failed"])
        self.assertTrue(run_state["rollback_aftermath_missing_or_ambiguous"])
        self.assertIn(
            "rollback_remote_followup_required",
            run_state["rollback_aftermath_blocked_reasons"],
        )

    def test_closed_loop_blocks_when_authority_validation_state_is_blocked(self) -> None:
        run_state = {
            "continue_allowed": True,
            "run_paused": False,
            "manual_intervention_required": False,
            "rollback_evaluation_pending": False,
            "next_run_action": "continue_run",
            "global_stop_recommended": False,
            "global_stop": False,
            "merge_execution_succeeded": False,
            "rollback_execution_succeeded": False,
            "rollback_execution_failed": False,
            "rollback_replan_required": False,
            "rollback_automatic_continuation_blocked": False,
            "units_pending": 0,
            "authority_validation_blocked": True,
            "execution_authority_blocked": False,
            "validation_blocked": True,
            "authority_validation_blocked_reasons": ["working_tree_contains_out_of_scope_changes"],
        }
        manifest_units = [
            {
                "decision_summary": {
                    "commit_readiness_status": "ready",
                    "commit_execution_status": "blocked",
                },
                "commit_execution_summary": {
                    "status": "blocked",
                    "execution_allowed": False,
                    "execution_authority_status": "allowed",
                    "validation_status": "blocked",
                },
            }
        ]

        augmented = _augment_run_state_with_closed_loop(
            run_state_payload=run_state,
            manifest_units=manifest_units,
            run_status="completed",
        )

        self.assertEqual(augmented["loop_state"], "manual_intervention_required")
        self.assertEqual(augmented["next_safe_action"], "require_manual_intervention")
        self.assertEqual(
            augmented["loop_blocked_reason"],
            "working_tree_contains_out_of_scope_changes",
        )
        self.assertTrue(augmented["loop_manual_intervention_required"])

    def test_closed_loop_blocks_when_remote_github_state_is_blocked(self) -> None:
        run_state = {
            "continue_allowed": True,
            "run_paused": False,
            "manual_intervention_required": False,
            "rollback_evaluation_pending": False,
            "next_run_action": "continue_run",
            "global_stop_recommended": False,
            "global_stop": False,
            "merge_execution_succeeded": False,
            "rollback_execution_succeeded": False,
            "rollback_execution_failed": False,
            "rollback_replan_required": False,
            "rollback_automatic_continuation_blocked": False,
            "units_pending": 0,
            "authority_validation_blocked": False,
            "execution_authority_blocked": False,
            "validation_blocked": False,
            "remote_github_blocked": True,
            "remote_github_manual_required": True,
            "remote_github_missing_or_ambiguous": True,
            "remote_github_blocked_reasons": ["existing_open_pr_detected"],
        }
        manifest_units = [
            {
                "decision_summary": {
                    "commit_readiness_status": "ready",
                    "commit_execution_status": "blocked",
                },
                "pr_execution_summary": {
                    "status": "blocked",
                    "remote_github_blocked": True,
                    "remote_state_blocked": True,
                },
            }
        ]

        augmented = _augment_run_state_with_closed_loop(
            run_state_payload=run_state,
            manifest_units=manifest_units,
            run_status="completed",
        )

        self.assertEqual(augmented["loop_state"], "manual_intervention_required")
        self.assertEqual(augmented["next_safe_action"], "require_manual_intervention")
        self.assertEqual(augmented["loop_blocked_reason"], "existing_open_pr_detected")
        self.assertTrue(augmented["loop_manual_intervention_required"])

    def test_closed_loop_blocks_when_rollback_aftermath_is_unresolved(self) -> None:
        run_state = {
            "continue_allowed": False,
            "run_paused": False,
            "manual_intervention_required": False,
            "rollback_evaluation_pending": False,
            "next_run_action": "pause_run",
            "global_stop_recommended": False,
            "global_stop": False,
            "merge_execution_succeeded": False,
            "rollback_execution_succeeded": True,
            "rollback_execution_failed": False,
            "rollback_replan_required": False,
            "rollback_automatic_continuation_blocked": False,
            "rollback_aftermath_status": "validation_failed",
            "rollback_aftermath_blocked": True,
            "rollback_aftermath_manual_required": True,
            "rollback_aftermath_missing_or_ambiguous": True,
            "rollback_aftermath_blocked_reasons": ["rollback_validation_failed"],
            "rollback_remote_followup_required": False,
            "rollback_manual_followup_required": True,
            "rollback_validation_failed": True,
            "units_pending": 0,
            "authority_validation_blocked": False,
            "execution_authority_blocked": False,
            "validation_blocked": False,
            "remote_github_blocked": False,
            "remote_github_manual_required": False,
            "remote_github_missing_or_ambiguous": False,
        }
        manifest_units = [{"decision_summary": {"rollback_execution_status": "succeeded"}}]

        augmented = _augment_run_state_with_closed_loop(
            run_state_payload=run_state,
            manifest_units=manifest_units,
            run_status="completed",
        )

        self.assertEqual(augmented["loop_state"], "rollback_completed_blocked")
        self.assertEqual(augmented["next_safe_action"], "require_manual_intervention")
        self.assertEqual(augmented["loop_blocked_reason"], "rollback_validation_failed")
        self.assertTrue(augmented["loop_manual_intervention_required"])

    def test_policy_overlay_duplicate_pr_blocks_pr_action_without_terminalizing_run(self) -> None:
        run_state = _augment_run_state_with_policy_overlay(
            run_state_payload={
                "loop_state": "manual_intervention_required",
                "next_safe_action": "pause",
                "terminal": False,
                "resumable": True,
                "continue_allowed": False,
                "manual_intervention_required": True,
                "remote_github_blocked": True,
                "remote_github_missing_or_ambiguous": False,
                "remote_github_blocked_reasons": ["existing_open_pr_detected"],
                "remote_github_blocked_reason": "existing_open_pr_detected",
            }
        )
        self.assertEqual(run_state["policy_status"], "blocked")
        self.assertTrue(run_state["policy_blocked"])
        self.assertFalse(run_state["policy_terminal"])
        self.assertTrue(run_state["policy_resume_allowed"])
        self.assertEqual(run_state["policy_primary_blocker_class"], "remote_github")
        self.assertIn("proceed_to_pr", run_state["policy_disallowed_actions"])
        self.assertIn("inspect", run_state["policy_allowed_actions"])

    def test_policy_overlay_rollback_validation_failed_maps_to_replan_required(self) -> None:
        run_state = _augment_run_state_with_policy_overlay(
            run_state_payload={
                "loop_state": "rollback_completed_blocked",
                "next_safe_action": "require_replanning",
                "terminal": False,
                "resumable": False,
                "continue_allowed": False,
                "rollback_replan_required": True,
                "loop_replan_required": True,
                "rollback_validation_failed": True,
                "rollback_aftermath_blocked": True,
                "rollback_aftermath_blocked_reasons": ["rollback_validation_failed"],
                "rollback_aftermath_blocked_reason": "rollback_validation_failed",
            }
        )
        self.assertEqual(run_state["policy_status"], "replan_required")
        self.assertTrue(run_state["policy_replan_required"])
        self.assertFalse(run_state["policy_resume_allowed"])
        self.assertEqual(run_state["policy_primary_blocker_class"], "replan_required")
        self.assertIn("rollback_validation_failed", run_state["policy_blocked_reasons"])

    def test_policy_overlay_ambiguous_truth_maps_to_manual_only(self) -> None:
        run_state = _augment_run_state_with_policy_overlay(
            run_state_payload={
                "loop_state": "manual_intervention_required",
                "next_safe_action": "pause",
                "terminal": False,
                "resumable": True,
                "continue_allowed": False,
                "authority_validation_missing_or_ambiguous": True,
                "manual_intervention_required": True,
            }
        )
        self.assertEqual(run_state["policy_status"], "manual_only")
        self.assertTrue(run_state["policy_manual_required"])
        self.assertTrue(run_state["policy_resume_allowed"])
        self.assertTrue(run_state["policy_blocked"])
        self.assertIn("proceed_to_merge", run_state["policy_disallowed_actions"])

    def test_policy_overlay_terminal_success_is_explicitly_terminal(self) -> None:
        run_state = _augment_run_state_with_policy_overlay(
            run_state_payload={
                "loop_state": "terminal_success",
                "next_safe_action": "stop_terminal_success",
                "terminal": True,
                "resumable": False,
                "continue_allowed": False,
            }
        )
        self.assertEqual(run_state["policy_status"], "terminally_stopped")
        self.assertTrue(run_state["policy_terminal"])
        self.assertFalse(run_state["policy_blocked"])
        self.assertFalse(run_state["policy_resume_allowed"])

    def test_lifecycle_terminal_contract_distinguishes_safely_closed(self) -> None:
        run_state = _augment_run_state_with_lifecycle_terminal_contract(
            run_state_payload={
                "state": "completed",
                "orchestration_state": "completed",
                "loop_state": "terminal_success",
                "terminal": True,
                "resumable": False,
                "policy_status": "terminally_stopped",
                "policy_blocked": False,
                "policy_manual_required": False,
                "policy_replan_required": False,
                "policy_terminal": True,
                "policy_resume_allowed": False,
                "delivery_completed": True,
                "merge_execution_succeeded": True,
            }
        )
        self.assertEqual(run_state["lifecycle_closure_status"], "safely_closed")
        self.assertTrue(run_state["lifecycle_safely_closed"])
        self.assertTrue(run_state["lifecycle_terminal"])
        self.assertFalse(run_state["lifecycle_execution_complete_not_closed"])
        self.assertFalse(run_state["lifecycle_rollback_complete_not_closed"])
        self.assertEqual(run_state["lifecycle_primary_closure_issue"], "")

    def test_lifecycle_terminal_contract_distinguishes_execution_complete_and_rollback_not_closed(self) -> None:
        run_state = _augment_run_state_with_lifecycle_terminal_contract(
            run_state_payload={
                "state": "paused",
                "loop_state": "rollback_completed_blocked",
                "terminal": False,
                "resumable": True,
                "policy_status": "manual_only",
                "policy_blocked": True,
                "policy_manual_required": True,
                "policy_replan_required": False,
                "policy_terminal": False,
                "policy_resume_allowed": True,
                "delivery_completed": True,
                "merge_execution_succeeded": True,
                "rollback_execution_succeeded": True,
                "rollback_aftermath_status": "remote_followup_required",
                "rollback_aftermath_blocked": True,
                "rollback_aftermath_blocked_reason": "rollback_remote_followup_required",
                "rollback_remote_followup_required": True,
            }
        )
        self.assertEqual(run_state["lifecycle_closure_status"], "rollback_complete_not_closed")
        self.assertFalse(run_state["lifecycle_safely_closed"])
        self.assertTrue(run_state["lifecycle_execution_complete_not_closed"])
        self.assertTrue(run_state["lifecycle_rollback_complete_not_closed"])
        self.assertEqual(
            run_state["lifecycle_primary_closure_issue"],
            "rollback_remote_followup_required",
        )

    def test_lifecycle_terminal_contract_distinguishes_replan_manual_and_resumable(self) -> None:
        replan_state = _augment_run_state_with_lifecycle_terminal_contract(
            run_state_payload={
                "loop_state": "replan_required",
                "terminal": False,
                "resumable": False,
                "policy_status": "replan_required",
                "policy_blocked": True,
                "policy_replan_required": True,
                "policy_resume_allowed": False,
            }
        )
        self.assertEqual(replan_state["lifecycle_closure_status"], "stopped_replan_required")
        self.assertFalse(replan_state["lifecycle_terminal"])
        self.assertTrue(replan_state["lifecycle_replan_required"])

        manual_state = _augment_run_state_with_lifecycle_terminal_contract(
            run_state_payload={
                "loop_state": "manual_intervention_required",
                "terminal": False,
                "resumable": False,
                "policy_status": "manual_only",
                "policy_blocked": True,
                "policy_manual_required": True,
                "policy_resume_allowed": False,
            }
        )
        self.assertEqual(manual_state["lifecycle_closure_status"], "stopped_manual_only")
        self.assertTrue(manual_state["lifecycle_manual_required"])
        self.assertFalse(manual_state["lifecycle_resumable"])

        resumable_state = _augment_run_state_with_lifecycle_terminal_contract(
            run_state_payload={
                "loop_state": "manual_intervention_required",
                "terminal": False,
                "resumable": True,
                "policy_status": "blocked",
                "policy_blocked": True,
                "policy_manual_required": False,
                "policy_replan_required": False,
                "policy_resume_allowed": True,
                "policy_blocked_reason": "existing_open_pr_detected",
            }
        )
        self.assertEqual(resumable_state["lifecycle_closure_status"], "stopped_resumable")
        self.assertTrue(resumable_state["lifecycle_resumable"])
        self.assertFalse(resumable_state["lifecycle_terminal"])

    def test_operator_explainability_distinguishes_action_specific_denial(self) -> None:
        run_state = _augment_run_state_with_operator_explainability(
            run_state_payload={
                "state": "paused",
                "loop_state": "manual_intervention_required",
                "next_safe_action": "pause",
                "policy_status": "blocked",
                "policy_blocked": True,
                "policy_manual_required": False,
                "policy_replan_required": False,
                "policy_resume_allowed": True,
                "policy_terminal": False,
                "policy_primary_blocker_class": "remote_github",
                "policy_primary_action": "proceed_to_pr",
                "policy_blocked_reason": "existing_open_pr_detected",
                "policy_blocked_reasons": ["existing_open_pr_detected"],
                "policy_allowed_actions": ["inspect", "signal_recollect"],
                "policy_disallowed_actions": ["proceed_to_pr"],
                "resumable": True,
                "terminal": False,
            }
        )
        self.assertEqual(run_state["operator_posture_summary"], "action_specific_denial_non_terminal")
        self.assertEqual(run_state["operator_action_scope"], "action_specific")
        self.assertEqual(run_state["operator_resume_status"], "resumable")
        self.assertEqual(run_state["operator_primary_blocker_class"], "remote_github")
        self.assertEqual(run_state["operator_primary_action"], "proceed_to_pr")

    def test_operator_explainability_distinguishes_run_wide_replan_manual_followup(self) -> None:
        run_state = _augment_run_state_with_operator_explainability(
            run_state_payload={
                "state": "paused",
                "loop_state": "rollback_completed_blocked",
                "next_safe_action": "require_replanning",
                "policy_status": "replan_required",
                "policy_blocked": True,
                "policy_manual_required": True,
                "policy_replan_required": True,
                "policy_resume_allowed": False,
                "policy_terminal": False,
                "policy_primary_blocker_class": "replan_required",
                "policy_primary_action": "rollback_required",
                "policy_blocked_reason": "rollback_validation_failed",
                "policy_blocked_reasons": ["rollback_validation_failed"],
                "rollback_aftermath_blocked": True,
                "rollback_replan_required": True,
                "loop_replan_required": True,
                "resumable": False,
                "terminal": False,
            }
        )
        self.assertEqual(run_state["operator_posture_summary"], "execution_blocked_replan_required")
        self.assertEqual(run_state["operator_action_scope"], "run_wide")
        self.assertEqual(run_state["operator_resume_status"], "replan_required")
        self.assertEqual(run_state["operator_next_safe_posture"], "replan_required_before_execution")

    def test_operator_explainability_distinguishes_terminal_stop(self) -> None:
        run_state = _augment_run_state_with_operator_explainability(
            run_state_payload={
                "state": "completed",
                "loop_state": "terminal_success",
                "next_safe_action": "stop_terminal_success",
                "policy_status": "terminally_stopped",
                "policy_blocked": False,
                "policy_manual_required": False,
                "policy_replan_required": False,
                "policy_resume_allowed": False,
                "policy_terminal": True,
                "policy_primary_blocker_class": "terminal",
                "policy_primary_action": "",
                "resumable": False,
                "terminal": True,
            }
        )
        self.assertEqual(run_state["operator_posture_summary"], "terminal_stop")
        self.assertEqual(run_state["operator_resume_status"], "terminal")
        self.assertEqual(run_state["operator_next_safe_posture"], "stop_terminal")

    def test_manifest_summary_selector_is_compact_and_excludes_rendering_only_fields(self) -> None:
        compact = select_manifest_run_state_summary_compact(
            {
                "state": "paused",
                "orchestration_state": "paused_for_manual_review",
                "units_total": 2,
                "units_completed": 1,
                "units_blocked": 1,
                "units_failed": 0,
                "units_pending": 0,
                "global_stop": True,
                "continue_allowed": False,
                "run_paused": True,
                "manual_intervention_required": True,
                "rollback_evaluation_pending": False,
                "global_stop_recommended": True,
                "next_run_action": "hold_for_global_stop",
                "loop_state": "manual_intervention_required",
                "next_safe_action": "pause",
                "loop_blocked_reason": "existing_open_pr_detected",
                "resumable": True,
                "terminal": False,
                "policy_status": "blocked",
                "policy_blocked": True,
                "policy_manual_required": True,
                "policy_replan_required": False,
                "policy_resume_allowed": True,
                "policy_terminal": False,
                "policy_primary_blocker_class": "remote_github",
                "policy_primary_action": "proceed_to_pr",
                "policy_allowed_actions": ["inspect", "signal_recollect"],
                "policy_disallowed_actions": ["proceed_to_pr"],
            }
        )
        self.assertIn("operator_posture_summary", compact)
        self.assertIn("operator_primary_blocker_class", compact)
        self.assertIn("operator_primary_action", compact)
        self.assertIn("operator_resume_status", compact)
        self.assertIn("operator_next_safe_posture", compact)
        self.assertIn("lifecycle_closure_status", compact)
        self.assertIn("lifecycle_safely_closed", compact)
        self.assertIn("lifecycle_terminal", compact)
        self.assertIn("lifecycle_resumable", compact)
        self.assertIn("lifecycle_manual_required", compact)
        self.assertIn("lifecycle_replan_required", compact)
        self.assertIn("lifecycle_execution_complete_not_closed", compact)
        self.assertIn("lifecycle_rollback_complete_not_closed", compact)
        self.assertIn("lifecycle_primary_closure_issue", compact)
        self.assertIn("lifecycle_stop_class", compact)
        self.assertNotIn("lifecycle_blocked_reasons", compact)
        self.assertNotIn("operator_guidance_summary", compact)
        self.assertNotIn("operator_safe_actions_summary", compact)
        self.assertNotIn("operator_unsafe_actions_summary", compact)
        self.assertFalse(is_manifest_summary_safe_field("operator_guidance_summary"))
        contract = build_manifest_run_state_summary_contract_surface()
        self.assertEqual(contract["compact_summary_field"], "run_state_summary_compact")
        self.assertIn("operator_guidance_summary", contract["rendering_only_operator_fields"])
        self.assertIn("lifecycle_closure_status", contract["lifecycle_summary_safe_fields"])

    def test_manifest_summary_selector_is_stable_when_optional_operator_fields_are_absent(self) -> None:
        compact = select_manifest_run_state_summary_compact(
            {
                "state": "decision_in_progress",
                "loop_state": "runnable_waiting",
                "next_safe_action": "continue_waiting",
                "policy_status": "allowed",
                "policy_resume_allowed": True,
                "policy_terminal": False,
            }
        )
        self.assertEqual(compact["operator_primary_blocker_class"], "none")
        self.assertEqual(compact["operator_primary_action"], "")
        self.assertEqual(compact["operator_resume_status"], "resumable")
        self.assertEqual(compact["operator_posture_summary"], "safe_to_continue")
        self.assertEqual(compact["lifecycle_closure_status"], "stopped_resumable")
        self.assertFalse(compact["lifecycle_safely_closed"])
        self.assertTrue(compact["lifecycle_resumable"])

    def test_runner_persists_rollback_progression_checkpoints_when_execution_attempted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            self._shrink_to_single_pr_slice(artifacts_dir)
            out_dir = root / "artifacts" / "executions"
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            mocked_payload = {
                "schema_version": "v1",
                "unit_id": "project-planned-exec-pr-01",
                "execution_type": "rollback_execution",
                "rollback_mode": "local_commit_only",
                "status": "succeeded",
                "summary": "mocked rollback success",
                "started_at": "2026-04-18T00:00:00",
                "finished_at": "2026-04-18T00:00:01",
                "trigger_reason": "rollback_required",
                "source_execution_state_summary": {},
                "resulting_commit_sha": "f" * 40,
                "resulting_pr_state": "unchanged",
                "resulting_branch_state": {},
                "command_summary": {},
                "failure_reason": "",
                "manual_intervention_required": False,
                "replan_required": True,
                "automatic_continuation_blocked": True,
                "blocking_reasons": [],
                "attempted": True,
            }
            with patch(
                "automation.orchestration.planned_execution_runner._execute_bounded_rollback",
                return_value=mocked_payload,
            ):
                manifest = runner.run(
                    artifacts_input_dir=artifacts_dir,
                    output_dir=out_dir,
                    dry_run=True,
                    stop_on_failure=True,
                )
            first = manifest["pr_units"][0]
            progression = json.loads(Path(first["unit_progression_path"]).read_text(encoding="utf-8"))
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))

        states = [entry["state"] for entry in progression["checkpoints"]]
        self.assertIn("rollback_execution_started", states)
        self.assertIn("rollback_executed", states)
        self.assertEqual(first["rollback_execution_summary"]["status"], "succeeded")
        self.assertEqual(first["decision_summary"]["rollback_execution_status"], "succeeded")
        self.assertTrue(run_state_payload["rollback_execution_succeeded"])
        self.assertTrue(run_state_payload["rollback_replan_required"])

    def test_invalid_cli_input_handling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = root / "missing_artifacts"
            out_dir = root / "out"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(self._script_path()),
                    "--artifacts-dir",
                    str(artifacts_dir),
                    "--out-dir",
                    str(out_dir),
                    "--json",
                ],
                capture_output=True,
                text=True,
                cwd=self._repo_root(),
            )

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("artifacts directory does not exist", proc.stderr)

    def test_invalid_live_transport_gate_fails_non_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "out"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(self._script_path()),
                    "--artifacts-dir",
                    str(artifacts_dir),
                    "--out-dir",
                    str(out_dir),
                    "--transport-mode",
                    "live",
                    "--repo-path",
                    str(self._repo_root()),
                    "--json",
                ],
                capture_output=True,
                text=True,
                cwd=self._repo_root(),
            )

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--enable-live-transport", proc.stderr)

    def test_manifest_paths_and_status_fields_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )

            for entry in manifest["pr_units"]:
                self.assertIn("compiled_prompt_path", entry)
                self.assertIn("bounded_step_contract_path", entry)
                self.assertIn("pr_implementation_prompt_contract_path", entry)
                self.assertIn("result_path", entry)
                self.assertIn("receipt_path", entry)
                self.assertIn("unit_progression_path", entry)
                self.assertIn("unit_progression_state", entry)
                self.assertIn("checkpoint_decision_path", entry)
                self.assertIn("commit_decision_path", entry)
                self.assertIn("merge_decision_path", entry)
                self.assertIn("rollback_decision_path", entry)
                self.assertIn("commit_execution_path", entry)
                self.assertIn("push_execution_path", entry)
                self.assertIn("pr_execution_path", entry)
                self.assertIn("merge_execution_path", entry)
                self.assertIn("rollback_execution_path", entry)
                self.assertIn("checkpoint_summary", entry)
                self.assertIn("commit_execution_summary", entry)
                self.assertIn("push_execution_summary", entry)
                self.assertIn("pr_execution_summary", entry)
                self.assertIn("merge_execution_summary", entry)
                self.assertIn("rollback_execution_summary", entry)
                self.assertIn("decision_summary", entry)
                self.assertIn("status", entry)
                self.assertIn("commit_readiness_status", entry["decision_summary"])
                self.assertIn("merge_readiness_status", entry["decision_summary"])
                self.assertIn("rollback_readiness_status", entry["decision_summary"])
                self.assertIn("commit_readiness_next_action", entry["decision_summary"])
                self.assertIn("merge_readiness_next_action", entry["decision_summary"])
                self.assertIn("rollback_readiness_next_action", entry["decision_summary"])
                self.assertIn("commit_execution_status", entry["decision_summary"])
                self.assertIn("push_execution_status", entry["decision_summary"])
                self.assertIn("pr_execution_status", entry["decision_summary"])
                self.assertIn("merge_execution_status", entry["decision_summary"])
                self.assertIn("rollback_execution_status", entry["decision_summary"])
                self.assertIn(
                    "commit_execution_manual_intervention_required",
                    entry["decision_summary"],
                )
                self.assertIn(
                    "push_execution_manual_intervention_required",
                    entry["decision_summary"],
                )
                self.assertIn(
                    "pr_execution_manual_intervention_required",
                    entry["decision_summary"],
                )
                self.assertIn(
                    "merge_execution_manual_intervention_required",
                    entry["decision_summary"],
                )
                self.assertIn(
                    "rollback_execution_manual_intervention_required",
                    entry["decision_summary"],
                )
                self.assertTrue(Path(entry["compiled_prompt_path"]).exists())
                self.assertTrue(Path(entry["bounded_step_contract_path"]).exists())
                self.assertTrue(Path(entry["pr_implementation_prompt_contract_path"]).exists())
                self.assertTrue(Path(entry["result_path"]).exists())
                self.assertTrue(Path(entry["receipt_path"]).exists())
                self.assertTrue(Path(entry["unit_progression_path"]).exists())
                self.assertTrue(Path(entry["checkpoint_decision_path"]).exists())
                self.assertTrue(Path(entry["commit_decision_path"]).exists())
                self.assertTrue(Path(entry["merge_decision_path"]).exists())
                self.assertTrue(Path(entry["rollback_decision_path"]).exists())
                self.assertTrue(Path(entry["commit_execution_path"]).exists())
                self.assertTrue(Path(entry["push_execution_path"]).exists())
                self.assertTrue(Path(entry["pr_execution_path"]).exists())
                self.assertTrue(Path(entry["merge_execution_path"]).exists())
                self.assertTrue(Path(entry["rollback_execution_path"]).exists())
            self.assertTrue(Path(manifest["action_handoff_path"]).exists())
            self.assertTrue(Path(manifest["run_state_path"]).exists())

    def test_unit_progression_checkpoint_surface_is_explicit_and_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RecordingLiveTransport()
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
            )
            first = manifest["pr_units"][0]
            progression = json.loads(Path(first["unit_progression_path"]).read_text(encoding="utf-8"))
            checkpoints = progression["checkpoints"]
            states = [entry["state"] for entry in checkpoints]

        self.assertEqual(progression["schema_version"], "v1")
        self.assertEqual(states[:4], ["planned", "prompt_ready", "execution_ready", "execution_completed"])
        self.assertIn("decision_ready", states)
        self.assertIn("checkpoint_evaluated", states)
        self.assertIn("commit_evaluated", states)
        self.assertIn("merge_evaluated", states)
        self.assertIn("rollback_evaluated", states)
        self.assertIn("reviewed", states)
        self.assertEqual(progression["current_state"], "advanced")

    def test_result_shape_compatibility_with_current_expectations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )
            first = manifest["pr_units"][0]
            payload = json.loads(Path(first["result_path"]).read_text(encoding="utf-8"))

        self.assertIn("job_id", payload)
        self.assertIn("pr_id", payload)
        self.assertIn("changed_files", payload)
        self.assertIn("execution", payload)
        self.assertIn("additions", payload)
        self.assertIn("deletions", payload)
        self.assertIn("generated_patch_summary", payload)
        self.assertIn("failure_type", payload)
        self.assertIn("failure_message", payload)
        self.assertIn("cost", payload)
        self.assertIn("verify", payload["execution"])

    def test_one_run_one_decision_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            manifest_a = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
                retry_context={
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 1,
                },
            )
            decision_a = json.loads(Path(manifest_a["next_action_path"]).read_text(encoding="utf-8"))
            handoff_a = json.loads(Path(manifest_a["action_handoff_path"]).read_text(encoding="utf-8"))

            runner_b = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            manifest_b = runner_b.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
                retry_context={
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 1,
                },
            )
            decision_b = json.loads(Path(manifest_b["next_action_path"]).read_text(encoding="utf-8"))
            handoff_b = json.loads(Path(manifest_b["action_handoff_path"]).read_text(encoding="utf-8"))

        self.assertEqual(decision_a["next_action"], decision_b["next_action"])
        self.assertEqual(decision_a["reason"], decision_b["reason"])
        self.assertEqual(decision_a["updated_retry_context"], decision_b["updated_retry_context"])
        self.assertEqual(handoff_a["next_action"], handoff_b["next_action"])
        self.assertEqual(handoff_a["updated_retry_context"], handoff_b["updated_retry_context"])
        self.assertEqual(handoff_a["action_consumable"], handoff_b["action_consumable"])

    def test_retry_context_continuity_across_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            failing_transport_a = _RecordingDryRunTransport(
                status_by_pr_id={"project-planned-exec-pr-01": "failed"}
            )
            runner_a = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=failing_transport_a))
            manifest_a = runner_a.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )
            handoff_a = json.loads(Path(manifest_a["action_handoff_path"]).read_text(encoding="utf-8"))

            failing_transport_b = _RecordingDryRunTransport(
                status_by_pr_id={"project-planned-exec-pr-01": "failed"}
            )
            runner_b = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=failing_transport_b))
            manifest_b = runner_b.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )
            handoff_b = json.loads(Path(manifest_b["action_handoff_path"]).read_text(encoding="utf-8"))
            run_root = out_dir / manifest_b["job_id"]
            handoff_files = sorted(run_root.glob("action_handoff*.json"))

        self.assertEqual(handoff_a["next_action"], "same_prompt_retry")
        self.assertEqual(handoff_b["next_action"], "escalate_to_human")
        self.assertEqual(len(handoff_files), 1)


if __name__ == "__main__":
    unittest.main()
