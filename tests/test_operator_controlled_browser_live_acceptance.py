"""Prompt659 tests for operator-controlled browser live acceptance harness."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from automation.orchestration.planned_runner.browser_chatgpt_operator_adapter import (
    BROWSER_RESPONSE_ENVELOPE_SCHEMA,
)
from automation.orchestration.planned_runner.browser_live_acceptance import (
    DEFAULT_REQUEST_ID,
    build_live_acceptance_analysis_request,
    operator_steps,
    prepare_live_acceptance,
    run_if_response_present,
    validate_live_response,
)
from automation.orchestration.planned_runner.external_analysis_handoff import (
    validate_analysis_artifact,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _artifact(**overrides):
    artifact = {
        "schema_version": "analysis_artifact_v1",
        "request_id": DEFAULT_REQUEST_ID,
        "source": "chatgpt_browser",
        "status": "success",
        "current_state_summary": "The browser adapter produced a response envelope that can be validated locally.",
        "confirmed_completed": ["Prompt658 browser adapter", "Prompt659 response validation path"],
        "missing_gaps": ["Run the next full browser-to-Codex cycle."],
        "recommended_next_action": "generate_prompt_batch",
        "recommended_prompts": [
            {
                "prompt_id": "prompt660",
                "title": "Browser to Codex full cycle acceptance",
                "body": "Implement a small report-only follow-up that validates the browser-to-Codex handoff artifacts without executing generated prompts.",
                "expected_tag": "prompt660-browser-to-codex-full-cycle-acceptance",
                "expected_report_path": "artifacts/autonomous_runtime/prompt660_report.json",
                "expected_summary_path": "artifacts/autonomous_runtime/prompt660_summary.md",
                "required_tests": ["python -m unittest tests.test_operator_controlled_browser_live_acceptance"],
                "pass_conditions": {"status_field": "prompt660_status", "status_value": "success"},
            }
        ],
        "evaluation_score_out_of_100": 88,
        "risk_notes": ["Keep credentials and browser profile data outside repository artifacts."],
    }
    artifact.update(overrides)
    return artifact


def _response(**overrides):
    payload = {
        "schema_version": BROWSER_RESPONSE_ENVELOPE_SCHEMA,
        "adapter": "browser_chatgpt_operator_adapter",
        "request_id": DEFAULT_REQUEST_ID,
        "status": "artifact_ready",
        "chatgpt_output": json.dumps(_artifact()),
        "require_structured_artifact": True,
        "captured_at": "2026-06-17T00:00:00Z",
        "metadata": {"page_url": "https://chatgpt.com/c/prompt659"},
        "errors": [],
        "test_only": True,
    }
    payload.update(overrides)
    return payload


class OperatorControlledBrowserLiveAcceptanceTests(unittest.TestCase):
    def test_prepare_writes_request_envelope_under_work_root_only(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            work = Path(raw)
            result = prepare_live_acceptance(repo_root=REPO_ROOT, work_root=work)
            self.assertEqual(result["status"], "success", msg=result["errors"])
            request_path = Path(result["request_envelope_path"])
            self.assertTrue(request_path.is_file())
            self.assertTrue(request_path.is_relative_to(work))
            self.assertEqual(json.loads(request_path.read_text())["request_id"], DEFAULT_REQUEST_ID)

    def test_request_id_is_deterministic_or_explicitly_supplied(self):
        default_request = build_live_acceptance_analysis_request()
        explicit_request = build_live_acceptance_analysis_request(request_id="custom_prompt659")
        self.assertEqual(default_request["request_id"], DEFAULT_REQUEST_ID)
        self.assertEqual(explicit_request["request_id"], "custom_prompt659")

    def test_print_steps_include_extension_and_response_paths(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            steps = "\n".join(operator_steps(repo_root=REPO_ROOT, work_root=raw))
            self.assertIn("browser_extension/chatgpt_runner_bridge", steps)
            self.assertIn("live_response_envelope.json", steps)
            self.assertIn("validate-response", steps)

    def test_validate_response_rejects_missing_file(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = validate_live_response(
                repo_root=REPO_ROOT,
                work_root=raw,
                response_envelope=Path(raw) / "missing.json",
            )
            self.assertEqual(result["status"], "partial")
            self.assertFalse(result["browser_live_run_performed"])
            self.assertTrue(any("file not found" in e for e in result["errors"]))

    def test_validate_response_rejects_wrong_request_id(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            path = Path(raw) / "response.json"
            path.write_text(json.dumps(_response(request_id="wrong")), encoding="utf-8")
            result = validate_live_response(repo_root=REPO_ROOT, work_root=raw, response_envelope=path)
            self.assertEqual(result["status"], "partial")
            self.assertFalse(result["browser_live_run_performed"])
            self.assertTrue(any("request_id" in e for e in result["errors"]))

    def test_validate_response_rejects_empty_captured_response(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            path = Path(raw) / "response.json"
            path.write_text(json.dumps(_response(chatgpt_output=" ")), encoding="utf-8")
            result = validate_live_response(repo_root=REPO_ROOT, work_root=raw, response_envelope=path)
            self.assertEqual(result["status"], "partial")
            self.assertFalse(result["browser_live_run_performed"])
            self.assertTrue(any("chatgpt_output" in e for e in result["errors"]))

    def test_validate_response_rejects_credential_like_fields(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            path = Path(raw) / "response.json"
            path.write_text(json.dumps(_response(metadata={"page_url": "https://chatgpt.com", "api_token": "x"})), encoding="utf-8")
            result = validate_live_response(repo_root=REPO_ROOT, work_root=raw, response_envelope=path)
            self.assertEqual(result["status"], "partial")
            self.assertFalse(result["browser_live_run_performed"])
            self.assertTrue(any("secret-like" in e for e in result["errors"]))

    def test_validate_response_normalizes_valid_test_response_but_not_live_success(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            path = Path(raw) / "response.json"
            path.write_text(json.dumps(_response()), encoding="utf-8")
            result = validate_live_response(repo_root=REPO_ROOT, work_root=raw, response_envelope=path)
            self.assertEqual(result["status"], "partial", msg=result["errors"])
            self.assertTrue(result["mocked_only"])
            self.assertFalse(result["browser_live_run_performed"])
            self.assertTrue(result["response_envelope_validated"], msg=result["errors"])
            self.assertTrue(result["analysis_artifact_normalized"], msg=result["errors"])
            self.assertTrue(result["prompt657_validation_compatibility_verified"], msg=result["errors"])
            self.assertTrue(result["prompt655_batch_conversion_compatibility_verified"], msg=result["errors"])
            self.assertTrue(result["next_prompt_selection_verified"], msg=result["errors"])
            artifact = json.loads((Path(raw) / "live_analysis_artifact.json").read_text())
            _, errors = validate_analysis_artifact(artifact)
            self.assertEqual(errors, [])

    def test_run_if_response_present_returns_not_ready_without_response(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = run_if_response_present(repo_root=REPO_ROOT, work_root=raw)
            self.assertEqual(result["status"], "partial")
            self.assertIn("not_ready", result["reason"])
            self.assertFalse(result["browser_live_run_performed"])

    def test_no_network_subprocess_browser_execution_or_env_read(self):
        import automation.orchestration.planned_runner.browser_live_acceptance as mod

        src = Path(mod.__file__).read_text(encoding="utf-8")
        self.assertNotIn("subprocess", src)
        self.assertNotIn("requests", src)
        self.assertNotIn("urllib", src)
        self.assertNotIn("sync_playwright", src)
        self.assertNotIn("async_playwright", src)
        self.assertNotIn(".env", src)

    def test_no_cookie_token_password_persistence_in_harness(self):
        import automation.orchestration.planned_runner.browser_live_acceptance as mod

        src = Path(mod.__file__).read_text(encoding="utf-8")
        self.assertNotIn("document.cookie", src)
        self.assertNotIn("localStorage", src)
        self.assertNotIn("sessionStorage", src)
        self.assertNotIn("input[type=password", src)


if __name__ == "__main__":
    unittest.main()
