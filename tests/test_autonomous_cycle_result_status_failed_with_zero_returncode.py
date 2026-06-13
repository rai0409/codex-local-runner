"""Prompt638B regression: a Codex-like success/returncode-0 result that FAILED
effect verification must never classify as success.

Closes the Prompt638A bug where _result_status evaluated the returncode==0
shortcut before the explicit failed status/classification, promoting an
effect_verification_failed cycle to success.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from automation.orchestration.planned_runner.autonomous_cycle import (
    AUTONOMOUS_CYCLE_ENABLE_TOKEN,
    _result_status,
    run_autonomous_cycle_metadata,
)


class ResultStatusFailedWithZeroReturncodeTests(unittest.TestCase):
    def test_result_status_failed_status_beats_zero_returncode(self):
        payload = {
            "status": "failed",
            "returncode": 0,
            "returncode_classification": "failed",
            "stop_reason": "effect_verification_failed",
            "effect_verification_status": "failed",
        }
        self.assertEqual(_result_status(payload, "assimilated"), "failed")

    def test_result_status_effect_failed_beats_zero_returncode(self):
        # Even if the explicit status field were missing, a non-passed effect
        # verification status with returncode 0 must still be a failure.
        payload = {
            "returncode": 0,
            "effect_verification_status": "failed",
        }
        self.assertEqual(_result_status(payload, "assimilated"), "failed")

    def test_result_status_plain_zero_returncode_still_success(self):
        # No failure signals and no effect verification details -> success preserved.
        payload = {"status": "success", "returncode": 0}
        self.assertEqual(_result_status(payload, "assimilated"), "success")

    def test_cycle_metadata_effect_failed_not_classified_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            prompt_path = tmp_path / "prompt.md"
            prompt_path.write_text("do the thing\n", encoding="utf-8")
            result_path = tmp_path / "codex_execution_result.json"
            # Mirrors the Prompt638 Task1 codex_execution_result.json exactly.
            result_path.write_text(
                json.dumps(
                    {
                        "status": "failed",
                        "returncode": 0,
                        "returncode_classification": "failed",
                        "stop_reason": "effect_verification_failed",
                        "next_action": "inspect_missing_expected_effects",
                        "effect_verification_enabled": True,
                        "effect_verification_status": "failed",
                        "effect_required_text_verified": False,
                    }
                ),
                encoding="utf-8",
            )

            state = run_autonomous_cycle_metadata(
                generated_prompt_path=prompt_path,
                codex_result_path=result_path,
                output_dir=tmp_path / "out",
                cycle_index=1,
                max_cycles=1,
                autonomous_enable_token=AUTONOMOUS_CYCLE_ENABLE_TOKEN,
            )

            self.assertEqual(state["codex_result_status"], "failed")
            self.assertNotEqual(state["classification"], "codex_result_success")
            self.assertNotEqual(state["status"], "success")
            self.assertNotEqual(state["next_action"], "commit_tag_gate")


if __name__ == "__main__":
    unittest.main()
