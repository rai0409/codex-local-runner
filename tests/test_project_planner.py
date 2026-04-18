from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from automation.planning.project_planner import generate_planning_artifacts
from automation.planning.project_planner import write_planning_artifacts


class ProjectPlannerTests(unittest.TestCase):
    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _planner_script(self) -> Path:
        return self._repo_root() / "scripts" / "build_planning_artifacts.py"

    def _simple_intake(self) -> dict[str, object]:
        return {
            "project_id": "proj-planning-foundation",
            "objective": "Introduce planning artifacts for intake to PR slicing.",
            "success_definition": "Planning artifacts are deterministic and reviewable.",
            "constraints": [
                "No execution authority expansion",
                "Keep inspect/operator-summary compatibility untouched",
            ],
            "non_goals": [
                "No GitHub write behavior",
                "No scheduler loop",
            ],
            "allowed_risk_level": "conservative",
            "target_repo": "codex-local-runner",
            "target_branch": "main",
            "requested_by": "operator",
            "created_at": "2026-04-18T00:00:00+00:00",
            "requested_changes": [
                {
                    "summary": "Add deterministic planning artifacts",
                    "touched_files": [
                        "docs/reviewer_runbook.md",
                        "automation/planning/prompt_builder.py",
                        "orchestrator/merge_gate.py",
                        "tests/test_prompt_builder.py",
                    ],
                    "acceptance_criteria": [
                        "Artifacts include roadmap and ordered PR slices",
                    ],
                    "validation_commands": [
                        "python3 -m unittest tests.test_prompt_builder -v",
                    ],
                }
            ],
            "forbidden_files": [
                "orchestrator/merge_executor.py",
                "orchestrator/rollback_executor.py",
            ],
            "blocked_by": [
                "operator sign-off",
            ],
        }

    def test_artifact_schema_shape_contains_required_fields(self) -> None:
        artifacts = generate_planning_artifacts(self._simple_intake(), repo_root=self._repo_root())

        self.assertEqual(
            set(artifacts.keys()),
            {"project_brief", "repo_facts", "roadmap", "pr_plan"},
        )

        project_brief = artifacts["project_brief"]
        self.assertEqual(
            set(project_brief.keys()),
            {
                "project_id",
                "objective",
                "success_definition",
                "constraints",
                "non_goals",
                "allowed_risk_level",
                "target_repo",
                "target_branch",
                "requested_by",
                "created_at",
            },
        )

        repo_facts = artifacts["repo_facts"]
        self.assertEqual(
            set(repo_facts.keys()),
            {
                "repo",
                "default_branch",
                "relevant_paths",
                "entrypoints",
                "tests_available",
                "build_commands",
                "lint_commands",
                "current_branch_rules",
                "sensitive_paths",
                "source_of_truth_commit",
            },
        )

        roadmap = artifacts["roadmap"]
        self.assertEqual(
            set(roadmap.keys()),
            {
                "roadmap_id",
                "milestones",
                "dependency_edges",
                "blocked_by",
                "estimated_risk",
            },
        )

        pr_plan = artifacts["pr_plan"]
        self.assertIn("plan_id", pr_plan)
        self.assertIn("prs", pr_plan)
        for pr in pr_plan["prs"]:
            self.assertEqual(
                set(pr.keys()),
                {
                    "pr_id",
                    "title",
                    "exact_scope",
                    "touched_files",
                    "forbidden_files",
                    "acceptance_criteria",
                    "validation_commands",
                    "rollback_notes",
                    "tier_category",
                    "depends_on",
                    "bounded_step_contract",
                },
            )

    def test_generation_is_deterministic_for_same_input(self) -> None:
        intake = self._simple_intake()
        first = generate_planning_artifacts(intake, repo_root=self._repo_root())
        second = generate_planning_artifacts(intake, repo_root=self._repo_root())
        self.assertEqual(first, second)

    def test_simple_request_can_generate_multiple_pr_slices(self) -> None:
        artifacts = generate_planning_artifacts(self._simple_intake(), repo_root=self._repo_root())
        prs = artifacts["pr_plan"]["prs"]
        self.assertGreaterEqual(len(prs), 3)

        for pr in prs:
            touched_files = pr["touched_files"]
            has_docs = any(path.startswith("docs/") for path in touched_files)
            has_orchestrator = any(path.startswith("orchestrator/") for path in touched_files)
            self.assertFalse(has_docs and has_orchestrator)

    def test_bounded_step_contract_contains_required_fields(self) -> None:
        artifacts = generate_planning_artifacts(self._simple_intake(), repo_root=self._repo_root())
        first = artifacts["pr_plan"]["prs"][0]
        contract = first["bounded_step_contract"]

        self.assertEqual(contract["schema_version"], "v1")
        self.assertEqual(contract["step_id"], first["pr_id"])
        self.assertIn("title", contract)
        self.assertIn("purpose", contract)
        self.assertIn("scope_in", contract)
        self.assertIn("scope_out", contract)
        self.assertIn("files_or_areas_to_inspect", contract)
        self.assertIn("invariants_to_preserve", contract)
        self.assertIn("validation_expectations", contract)
        self.assertIn("progression_metadata", contract)
        self.assertIn("boundedness", contract)

    def test_atomic_overscoped_step_is_detected_by_boundedness_contract(self) -> None:
        intake = self._simple_intake()
        intake["requested_changes"] = [
            {
                "summary": "Keep this change atomic even when overscoped",
                "atomic": True,
                "touched_files": [
                    "docs/guide_01.md",
                    "docs/guide_02.md",
                    "docs/guide_03.md",
                    "docs/guide_04.md",
                    "docs/guide_05.md",
                    "docs/guide_06.md",
                    "docs/guide_07.md",
                ],
                "validation_commands": ["python3 -m unittest tests.test_project_planner -v"],
            }
        ]
        artifacts = generate_planning_artifacts(intake, repo_root=self._repo_root())
        statuses = [
            pr["bounded_step_contract"]["boundedness"]["status"]
            for pr in artifacts["pr_plan"]["prs"]
        ]

        self.assertIn("overscoped", statuses)
        self.assertTrue(
            any("bounded_step_overscoped" in warning for warning in artifacts["pr_plan"]["planning_warnings"])
        )

    def test_underspecified_step_is_detected_by_boundedness_contract(self) -> None:
        intake = self._simple_intake()
        intake["requested_changes"] = [{"summary": "No explicit files provided"}]
        artifacts = generate_planning_artifacts(intake, repo_root=self._repo_root())
        first = artifacts["pr_plan"]["prs"][0]
        boundedness = first["bounded_step_contract"]["boundedness"]

        self.assertEqual(boundedness["status"], "underspecified")
        self.assertIn("missing_scope_in", boundedness["issues"])
        self.assertTrue(
            any("bounded_step_underspecified" in warning for warning in artifacts["pr_plan"]["planning_warnings"])
        )

    def test_sensitive_path_detection_influences_tiering_and_separation(self) -> None:
        intake = self._simple_intake()
        intake["requested_changes"] = [
            {
                "summary": "Split docs and control-plane scope",
                "touched_files": [
                    "docs/reviewer_runbook.md",
                    "orchestrator/merge_gate.py",
                ],
            }
        ]
        artifacts = generate_planning_artifacts(intake, repo_root=self._repo_root())
        prs = artifacts["pr_plan"]["prs"]
        self.assertGreaterEqual(len(prs), 2)

        docs_pr = None
        sensitive_pr = None
        for pr in prs:
            files = pr["touched_files"]
            if "docs/reviewer_runbook.md" in files:
                docs_pr = pr
            if "orchestrator/merge_gate.py" in files:
                sensitive_pr = pr

        self.assertIsNotNone(docs_pr)
        self.assertIsNotNone(sensitive_pr)
        self.assertEqual(docs_pr["tier_category"], "docs_only")
        self.assertEqual(sensitive_pr["tier_category"], "runtime_fix_high_risk")
        self.assertNotEqual(docs_pr["pr_id"], sensitive_pr["pr_id"])

    def test_cli_writes_required_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            intake_path = tmp_root / "intake.json"
            out_dir = tmp_root / "artifacts"
            intake_path.write_text(
                json.dumps(self._simple_intake(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    str(self._planner_script()),
                    "--intake",
                    str(intake_path),
                    "--out-dir",
                    str(out_dir),
                    "--repo-root",
                    str(self._repo_root()),
                    "--json",
                ],
                capture_output=True,
                text=True,
                cwd=self._repo_root(),
            )

            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(
                payload["written_files"],
                [
                    "project_brief.json",
                    "repo_facts.json",
                    "roadmap.json",
                    "pr_plan.json",
                ],
            )
            for filename in payload["written_files"]:
                self.assertTrue((out_dir / filename).exists())

    def test_writer_is_deterministic_for_repeat_writes(self) -> None:
        artifacts = generate_planning_artifacts(self._simple_intake(), repo_root=self._repo_root())
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "artifacts"
            first = write_planning_artifacts(artifacts, out_dir)
            first_snapshot = {
                filename: (out_dir / filename).read_text(encoding="utf-8")
                for filename in first
            }

            second = write_planning_artifacts(artifacts, out_dir)
            second_snapshot = {
                filename: (out_dir / filename).read_text(encoding="utf-8")
                for filename in second
            }

        self.assertEqual(first, second)
        self.assertEqual(first_snapshot, second_snapshot)


if __name__ == "__main__":
    unittest.main()
