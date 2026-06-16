"""Prompt658 tests for the safe browser ChatGPT operator adapter."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from automation.orchestration.planned_runner.browser_chatgpt_operator_adapter import (
    BROWSER_RESPONSE_ENVELOPE_SCHEMA,
    HISTORICAL_CANDIDATE_COMMIT,
    HISTORICAL_CANDIDATE_PATH,
    create_browser_request_envelope,
    inspect_extension_files,
    normalize_browser_response_to_analysis_artifact,
    validate_and_convert_normalized_artifact,
    validate_browser_response_envelope,
)
from automation.orchestration.planned_runner.external_analysis_handoff import (
    validate_analysis_artifact,
)


def _analysis_request() -> dict:
    return {
        "request_id": "prompt658",
        "project_goal": "Wire browser ChatGPT analysis to Prompt657",
        "current_capability_boundary": "external_analysis_handoff_artifact_protocol_added_chatgpt_to_prompt_batch",
        "questions": ["What should happen next?"],
        "required_output_schema": "analysis_artifact_v1",
        "allowed_next_actions": ["generate_prompt_batch", "manual_review_required"],
        "context_files": ["artifacts/autonomous_runtime/prompt657_summary.md"],
    }


def _analysis_artifact(**overrides) -> dict:
    artifact = {
        "schema_version": "analysis_artifact_v1",
        "request_id": "prompt658",
        "source": "chatgpt_browser_operator_adapter",
        "status": "success",
        "current_state_summary": "Prompt657 is ready; Prompt658 should add the adapter.",
        "confirmed_completed": ["Prompt657 artifact protocol"],
        "missing_gaps": ["browser operator adapter"],
        "recommended_next_action": "generate_prompt_batch",
        "recommended_prompts": [
            {
                "prompt_id": "prompt659",
                "title": "Operator controlled browser live acceptance",
                "body": "Run an operator-controlled browser acceptance for the adapter.",
                "expected_tag": "prompt659-browser-live-acceptance",
                "expected_report_path": "artifacts/autonomous_runtime/prompt659_report.json",
                "expected_summary_path": "artifacts/autonomous_runtime/prompt659_summary.md",
                "required_tests": ["python -m unittest tests.test_browser_chatgpt_operator_adapter"],
                "pass_conditions": {"status_field": "prompt659_status", "status_value": "success"},
            }
        ],
        "evaluation_score_out_of_100": 91,
        "risk_notes": ["Keep browser credentials outside the repository."],
    }
    artifact.update(overrides)
    return artifact


def _response_envelope(**overrides) -> dict:
    envelope = {
        "schema_version": BROWSER_RESPONSE_ENVELOPE_SCHEMA,
        "adapter": "browser_chatgpt_operator_adapter",
        "request_id": "prompt658",
        "status": "artifact_ready",
        "chatgpt_output": json.dumps(_analysis_artifact()),
        "require_structured_artifact": True,
        "metadata": {"page_url": "https://chatgpt.com/c/example"},
        "errors": [],
    }
    envelope.update(overrides)
    return envelope


class BrowserChatgptOperatorAdapterTests(unittest.TestCase):
    def test_historical_candidate_is_documented(self):
        self.assertEqual(HISTORICAL_CANDIDATE_COMMIT, "d698389")
        self.assertEqual(HISTORICAL_CANDIDATE_PATH, "browser_extension/chatgpt_runner_bridge/content.js")

    def test_request_envelope_creation_works(self):
        result = create_browser_request_envelope(_analysis_request())
        self.assertEqual(result["status"], "success", msg=result["errors"])
        envelope = result["envelope"]
        self.assertEqual(envelope["request_id"], "prompt658")
        self.assertEqual(envelope["target_output_schema"], "analysis_artifact_v1")
        self.assertIn("analysis_artifact_v1", envelope["prompt_text"])
        self.assertTrue(envelope["safety"]["no_cookie_or_token_storage"])

    def test_response_envelope_validation_works(self):
        envelope, errors = validate_browser_response_envelope(
            _response_envelope(),
            expected_request_id="prompt658",
        )
        self.assertEqual(errors, [])
        self.assertEqual(envelope["status"], "artifact_ready")

    def test_wrong_request_id_rejected(self):
        _, errors = validate_browser_response_envelope(
            _response_envelope(request_id="wrong"),
            expected_request_id="prompt658",
        )
        self.assertTrue(any("does not match expected" in e for e in errors))

    def test_empty_response_rejected(self):
        _, errors = validate_browser_response_envelope(_response_envelope(chatgpt_output=" "))
        self.assertTrue(any("chatgpt_output" in e for e in errors))

    def test_malformed_response_rejected_when_structured_required(self):
        result = normalize_browser_response_to_analysis_artifact(
            _response_envelope(chatgpt_output="{not json", require_structured_artifact=True)
        )
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(any("not valid JSON" in e for e in result["errors"]))

    def test_normalized_artifact_validates_with_prompt657(self):
        result = normalize_browser_response_to_analysis_artifact(_response_envelope())
        self.assertEqual(result["status"], "success", msg=result["errors"])
        _, errors = validate_analysis_artifact(result["artifact"])
        self.assertEqual(errors, [])

    def test_raw_non_json_response_becomes_manual_review_required(self):
        result = normalize_browser_response_to_analysis_artifact(
            _response_envelope(
                chatgpt_output="This is a raw answer, not JSON.",
                require_structured_artifact=False,
            )
        )
        self.assertEqual(result["status"], "success", msg=result["errors"])
        self.assertEqual(result["artifact"]["recommended_next_action"], "manual_review_required")
        self.assertEqual(result["artifact"]["status"], "manual_review_required")

    def test_secret_like_fields_are_rejected(self):
        _, errors = validate_browser_response_envelope(
            _response_envelope(metadata={"api_token": "nope"})
        )
        self.assertTrue(any("prohibited secret-like fields" in e for e in errors))

    def test_no_network_subprocess_browser_execution_in_adapter(self):
        import automation.orchestration.planned_runner.browser_chatgpt_operator_adapter as mod

        src = Path(mod.__file__).read_text(encoding="utf-8")
        self.assertNotIn("subprocess", src)
        self.assertNotIn("requests", src)
        self.assertNotIn("urllib", src)
        self.assertNotIn("sync_playwright", src)
        self.assertNotIn("async_playwright", src)
        self.assertNotIn(".env", src)

    def test_extension_files_exist_and_include_safety_notes(self):
        result = inspect_extension_files()
        self.assertEqual(result["status"], "ok", msg=result["errors"])
        readme = Path("browser_extension/chatgpt_runner_bridge/README.md").read_text(encoding="utf-8")
        self.assertIn("Prompt658", readme)
        self.assertIn("does not store browser credentials", readme)

    def test_content_js_does_not_extract_credentials(self):
        content = Path("browser_extension/chatgpt_runner_bridge/content.js").read_text(encoding="utf-8")
        self.assertIn("reused_from_commit: d698389", content)
        self.assertNotIn("document.cookie", content)
        self.assertNotIn("localStorage", content)
        self.assertNotIn("sessionStorage", content)
        self.assertNotIn("querySelector(\"input[type=password", content)

    def test_prompt_batch_conversion_still_works_after_normalized_artifact(self):
        result = normalize_browser_response_to_analysis_artifact(_response_envelope())
        self.assertEqual(result["status"], "success", msg=result["errors"])
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            converted = validate_and_convert_normalized_artifact(
                result["artifact"],
                Path(raw) / "batch",
            )
            self.assertEqual(converted["status"], "success", msg=converted["errors"])
            self.assertTrue(converted["batch_result"]["prompt655_compatible"])


if __name__ == "__main__":
    unittest.main()
