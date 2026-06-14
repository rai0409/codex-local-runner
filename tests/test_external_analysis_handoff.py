"""Prompt657: tests for the external analysis handoff controller (offline, safe)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from automation.orchestration.planned_runner.external_analysis_handoff import (
    MAX_RECOMMENDED_PROMPTS,
    analysis_artifact_to_prompt_batch,
    create_analysis_request,
    evaluate_analysis_artifact,
    prepare_next_chatgpt_instruction,
    validate_analysis_artifact,
    validate_analysis_request,
)
from automation.orchestration.planned_runner.project_prompt_batch import load_and_validate
import run_external_analysis_handoff as cli  # noqa: E402


def _request():
    return {
        "request_id": "analysis001",
        "project_goal": "Advance toward autonomy",
        "current_capability_boundary": "two_kinds_live_proven",
        "questions": ["What is complete?", "What is next?"],
        "required_output_schema": "analysis_artifact_v1",
        "allowed_next_actions": ["generate_prompt_batch", "manual_review_required"],
        "context_files": ["artifacts/autonomous_runtime/prompt656_summary.md"],
    }


def _artifact(**over):
    a = {
        "schema_version": "analysis_artifact_v1",
        "request_id": "analysis001",
        "source": "chatgpt_browser",
        "status": "success",
        "current_state_summary": "Two task kinds live-proven; planner stack complete.",
        "confirmed_completed": ["add_function", "add_file", "prompt batch controller"],
        "missing_gaps": ["replace_text task kind"],
        "recommended_next_action": "generate_prompt_batch",
        "recommended_prompts": [
            {
                "prompt_id": "prompt658", "title": "Add replace_text kind",
                "body": "Implement replace_text task kind with strict validation.",
                "expected_tag": "prompt658-replace-text",
                "expected_report_path": "artifacts/autonomous_runtime/prompt658_report.json",
                "expected_summary_path": "artifacts/autonomous_runtime/prompt658_summary.md",
                "pass_conditions": {"status_field": "prompt658_status", "status_value": "success"},
            }
        ],
        "evaluation_score_out_of_100": 92,
        "risk_notes": ["keep strict path validation"],
    }
    a.update(over)
    return a


class AnalysisRequestTests(unittest.TestCase):
    def test_valid_request(self):
        req, errors = validate_analysis_request(_request())
        self.assertEqual(errors, [])
        self.assertEqual(req["request_id"], "analysis001")

    def test_invalid_request_fails_safely(self):
        req, errors = validate_analysis_request({"request_id": "BAD ID"})
        self.assertTrue(errors)
        self.assertTrue(any("project_goal" in e for e in errors))

    def test_non_object_request(self):
        _, errors = validate_analysis_request("nope")  # type: ignore[arg-type]
        self.assertTrue(errors)

    def test_instruction_deterministic(self):
        a = prepare_next_chatgpt_instruction(_request())
        b = prepare_next_chatgpt_instruction(_request())
        self.assertEqual(a, b)
        self.assertIn("analysis001", a)
        self.assertIn("analysis_artifact_v1", a)

    def test_create_request_writes_file(self):
        import os
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            prev = os.getcwd()
            os.chdir(raw)
            try:
                # repo-relative output path (absolute is rejected by design)
                res = create_analysis_request(_request(), "analysis_requests/req.md")
                self.assertEqual(res["status"], "success", msg=res.get("errors"))
                self.assertTrue((Path(raw) / "analysis_requests" / "req.md").is_file())
            finally:
                os.chdir(prev)

    def test_create_request_rejects_absolute_output(self):
        res = create_analysis_request(_request(), "/etc/evil.md")
        self.assertEqual(res["status"], "blocked")

    def test_create_request_rejects_traversal_output(self):
        res = create_analysis_request(_request(), "../../evil.md")
        self.assertEqual(res["status"], "blocked")


class AnalysisArtifactTests(unittest.TestCase):
    def test_valid_artifact(self):
        art, errors = validate_analysis_artifact(_artifact())
        self.assertEqual(errors, [])
        self.assertEqual(art["recommended_next_action"], "generate_prompt_batch")

    def test_missing_required_fields_rejected(self):
        _, errors = validate_analysis_artifact({"schema_version": "analysis_artifact_v1"})
        self.assertTrue(any("request_id" in e for e in errors))
        self.assertTrue(any("source" in e for e in errors))
        self.assertTrue(any("current_state_summary" in e for e in errors))

    def test_wrong_schema_rejected(self):
        _, errors = validate_analysis_artifact(_artifact(schema_version="v0"))
        self.assertTrue(any("schema_version" in e for e in errors))

    def test_empty_prompt_body_rejected(self):
        bad = _artifact()
        bad["recommended_prompts"][0]["body"] = "   "
        _, errors = validate_analysis_artifact(bad)
        self.assertTrue(any("body must be a non-empty string" in e for e in errors))

    def test_generate_prompt_batch_requires_prompts(self):
        _, errors = validate_analysis_artifact(_artifact(recommended_prompts=[]))
        self.assertTrue(any("requires recommended_prompts" in e for e in errors))

    def test_max_prompts_cap_enforced(self):
        many = [dict(_artifact()["recommended_prompts"][0], prompt_id=f"p{i}") for i in range(MAX_RECOMMENDED_PROMPTS + 1)]
        _, errors = validate_analysis_artifact(_artifact(recommended_prompts=many))
        self.assertTrue(any("exceeds cap" in e for e in errors))

    def test_score_out_of_range_rejected(self):
        _, errors = validate_analysis_artifact(_artifact(evaluation_score_out_of_100=150))
        self.assertTrue(any("evaluation_score" in e for e in errors))

    def test_evaluate_artifact_breakdown(self):
        ev = evaluate_analysis_artifact(_artifact())
        self.assertTrue(ev["passed"])
        self.assertEqual(ev["score"], 100)
        for k in ("structure_valid", "state_summary", "gaps_or_completed", "actionable_recommendation", "risk_notes"):
            self.assertIn(k, ev["breakdown"])

    def test_evaluate_invalid_artifact(self):
        ev = evaluate_analysis_artifact({"schema_version": "v0"})
        self.assertEqual(ev["status"], "invalid")
        self.assertFalse(ev["passed"])


class ArtifactToBatchTests(unittest.TestCase):
    def test_converts_to_prompt655_batch(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            bd = Path(raw) / "batch"
            res = analysis_artifact_to_prompt_batch(_artifact(), bd.as_posix())
            self.assertEqual(res["status"], "success", msg=res["errors"])
            self.assertTrue(res["prompt655_compatible"])
            self.assertTrue(Path(res["manifest_path"]).is_file())
            # the produced manifest validates under the Prompt655 validator
            batch, errors = load_and_validate(bd)
            self.assertEqual(errors, [])
            self.assertEqual(batch["batch_id"], "analysis001")
            self.assertEqual(len(batch["prompts"]), 1)
            # generated prompt file is inside the batch dir
            for f in res["prompt_files"]:
                self.assertTrue(Path(f).resolve().is_relative_to(bd.resolve()))

    def test_blocked_when_not_generate_prompt_batch(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            res = analysis_artifact_to_prompt_batch(
                _artifact(recommended_next_action="manual_review_required", recommended_prompts=[]),
                (Path(raw) / "b").as_posix(),
            )
            self.assertEqual(res["status"], "blocked")

    def test_blocked_invalid_artifact(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            res = analysis_artifact_to_prompt_batch({"schema_version": "v0"}, (Path(raw) / "b").as_posix())
            self.assertEqual(res["status"], "blocked")

    def test_missing_expected_tag_blocks_conversion(self):
        bad = _artifact()
        bad["recommended_prompts"][0]["expected_tag"] = ""
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            res = analysis_artifact_to_prompt_batch(bad, (Path(raw) / "b").as_posix())
            self.assertEqual(res["status"], "blocked")

    def test_no_module_executes_prompts(self):
        from automation.orchestration.planned_runner import external_analysis_handoff as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        self.assertNotIn("exec(", src)
        self.assertNotIn("eval(", src)
        self.assertNotIn("subprocess", src)
        self.assertNotIn("requests", src)
        self.assertNotIn("urllib", src)

    def test_no_side_effects_for_validation(self):
        before = set(Path(".").iterdir())
        validate_analysis_artifact(_artifact())
        evaluate_analysis_artifact(_artifact())
        self.assertEqual(before, set(Path(".").iterdir()))


class CliTests(unittest.TestCase):
    def test_cli_create_validate_tobatch_evaluate(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            art_path = Path(raw) / "art.json"
            art_path.write_text(json.dumps(_artifact()), encoding="utf-8")
            self.assertEqual(cli.main(["validate-artifact", "--artifact", art_path.as_posix()]), 0)
            self.assertEqual(cli.main(["evaluate", "--artifact", art_path.as_posix()]), 0)
            self.assertEqual(cli.main(["next-instruction"]), 0)
            self.assertEqual(
                cli.main(["to-batch", "--artifact", art_path.as_posix(), "--batch-dir", (Path(raw) / "b").as_posix()]),
                0,
            )


if __name__ == "__main__":
    unittest.main()
