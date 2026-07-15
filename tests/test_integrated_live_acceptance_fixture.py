from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import run_integrated_live_acceptance as acceptance  # noqa: E402


def _apply_change(repo_path: str, function_name: str, expression: str) -> None:
    target = Path(repo_path) / "calculator.py"
    target.write_text(
        target.read_text(encoding="utf-8")
        + f"\n\ndef {function_name}(a, b):\n    return {expression}\n",
        encoding="utf-8",
    )


def _synthetic_state(**overrides):
    state = {
        "status": "success",
        "cycle_count": 2,
        "codex_invoked_count": 2,
        "commit_tag_gate_observed_count": 2,
        "per_cycle_effect_verification_statuses": ["passed", "passed"],
        "commit_performed": False,
        "tag_performed": False,
    }
    state.update(overrides)
    return state


class IntegratedLiveAcceptanceFixtureTests(unittest.TestCase):
    def _validate(self, fixture, state, apply_changes=True):
        if apply_changes:
            for cycle in fixture["cycles"]:
                _apply_change(cycle["repo_path"], cycle["function_name"], cycle["expression"])
        return acceptance.validate_acceptance(
            state=state,
            fixture=fixture,
            main_repo_status_before=["?? something"],
            main_repo_status_after=["?? something"],
            main_repo_head_before="abc123",
            main_repo_head_after="abc123",
        )

    def test_fixture_creates_repos_files_manifest_and_specs(self):
        with tempfile.TemporaryDirectory() as raw:
            work_dir = Path(raw) / "acceptance_work"
            fixture = acceptance.create_fixture(work_dir)
            self.assertEqual(len(fixture["cycles"]), 2)
            manifest = json.loads(Path(fixture["manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["cycles"]), 2)
            for index, cycle in enumerate(fixture["cycles"]):
                repo = Path(cycle["repo_path"])
                self.assertTrue((repo / ".git").is_dir())
                self.assertTrue((repo / "calculator.py").is_file())
                self.assertTrue((repo / "test_calculator.py").is_file())
                self.assertTrue(Path(cycle["prompt_path"]).is_file())
                spec = json.loads(Path(cycle["effect_spec_path"]).read_text(encoding="utf-8"))
                self.assertEqual(spec["repo_path"], cycle["repo_path"])
                self.assertEqual(
                    manifest["cycles"][index]["generated_prompt_path"], cycle["prompt_path"]
                )
                self.assertEqual(
                    manifest["cycles"][index]["effect_spec_path"], cycle["effect_spec_path"]
                )
            self.assertTrue((Path(fixture["dirty_gate_repo"]) / ".git").is_dir())

    def test_validator_success_on_valid_state_and_diffs(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = acceptance.create_fixture(Path(raw) / "work")
            result = self._validate(fixture, _synthetic_state())
        self.assertEqual(result["acceptance_status"], "success")
        self.assertEqual(result["failures"], [])
        self.assertTrue(result["cycle_results"][0]["function_present"])
        self.assertTrue(result["cycle_results"][1]["function_present"])
        self.assertFalse(result["main_repo_source_modified"])
        self.assertFalse(result["runtime_commit_or_tag_performed"])

    def test_validator_fails_when_cycle_count_below_two(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = acceptance.create_fixture(Path(raw) / "work")
            result = self._validate(fixture, _synthetic_state(cycle_count=1))
        self.assertEqual(result["acceptance_status"], "blocked")
        self.assertTrue(any("cycle_count" in failure for failure in result["failures"]))

    def test_validator_fails_when_codex_invoked_count_below_two(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = acceptance.create_fixture(Path(raw) / "work")
            result = self._validate(fixture, _synthetic_state(codex_invoked_count=1))
        self.assertEqual(result["acceptance_status"], "blocked")
        self.assertTrue(any("codex_invoked_count" in failure for failure in result["failures"]))

    def test_validator_fails_when_expected_function_missing(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = acceptance.create_fixture(Path(raw) / "work")
            _apply_change(
                fixture["cycles"][0]["repo_path"],
                fixture["cycles"][0]["function_name"],
                fixture["cycles"][0]["expression"],
            )
            # cycle2 multiply intentionally not applied
            result = self._validate(fixture, _synthetic_state(), apply_changes=False)
        self.assertEqual(result["acceptance_status"], "blocked")
        self.assertTrue(any("multiply missing" in failure for failure in result["failures"]))
        self.assertTrue(result["cycle_results"][0]["function_present"])
        self.assertFalse(result["cycle_results"][1]["function_present"])

    def test_validator_fails_when_effect_status_not_passed(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture = acceptance.create_fixture(Path(raw) / "work")
            result = self._validate(
                fixture,
                _synthetic_state(per_cycle_effect_verification_statuses=["passed", "failed"]),
            )
        self.assertEqual(result["acceptance_status"], "blocked")
        self.assertTrue(any("effect verification" in failure for failure in result["failures"]))


if __name__ == "__main__":
    unittest.main()
