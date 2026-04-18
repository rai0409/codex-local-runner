from __future__ import annotations

from datetime import datetime
import tempfile
import unittest
from pathlib import Path

from automation.scheduler.pause_state import PAUSE_STATE_CHECKS
from automation.scheduler.pause_state import PAUSE_STATE_HUMAN
from automation.scheduler.pause_state import PAUSE_STATE_PROVIDER_CAPACITY
from automation.scheduler.pause_state import PAUSE_STATE_RATE_LIMIT
from automation.scheduler.pause_state import build_pause_payload
from automation.scheduler.pause_state import classify_pause_condition
from automation.scheduler.pause_state import is_pause_active
from automation.scheduler.pause_state import is_pause_resume_eligible
from automation.scheduler.pause_state import load_pause_payload
from automation.scheduler.pause_state import mark_pause_resumed
from automation.scheduler.pause_state import persist_pause_payload


class PauseStateTests(unittest.TestCase):
    def _fixed_now(self) -> datetime:
        return datetime(2026, 4, 18, 15, 0, 0)

    def test_classify_provider_capacity_pause(self) -> None:
        pause = classify_pause_condition(
            next_action="same_prompt_retry",
            reason="provider capacity unavailable for codex",
            whether_human_required=False,
            now=self._fixed_now,
        )
        assert pause is not None
        self.assertEqual(pause["pause_state"], PAUSE_STATE_PROVIDER_CAPACITY)
        self.assertEqual(pause["provider_name"], "codex")

    def test_classify_rate_limit_pause_with_retry_after(self) -> None:
        pause = classify_pause_condition(
            next_action="same_prompt_retry",
            reason="rate limit reached retry_after_seconds=120",
            whether_human_required=False,
            now=self._fixed_now,
        )
        assert pause is not None
        self.assertEqual(pause["pause_state"], PAUSE_STATE_RATE_LIMIT)
        self.assertEqual(pause["retry_after_seconds"], 120)
        self.assertEqual(pause["next_eligible_at"], "2026-04-18T15:02:00")

    def test_classify_wait_for_checks_pause(self) -> None:
        pause = classify_pause_condition(
            next_action="wait_for_checks",
            reason="checks pending",
            whether_human_required=False,
            now=self._fixed_now,
        )
        assert pause is not None
        self.assertEqual(pause["pause_state"], PAUSE_STATE_CHECKS)

    def test_classify_human_required_pause(self) -> None:
        pause = classify_pause_condition(
            next_action="escalate_to_human",
            reason="needs review",
            whether_human_required=True,
            now=self._fixed_now,
        )
        assert pause is not None
        self.assertEqual(pause["pause_state"], PAUSE_STATE_HUMAN)
        self.assertIsNone(pause["next_eligible_at"])

    def test_pause_persistence_and_resume_eligibility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_root = Path(tmp_dir) / "job-1"
            payload = build_pause_payload(
                job_id="job-1",
                run_id="run-1",
                pause_state=PAUSE_STATE_RATE_LIMIT,
                pause_reason="rate limit",
                retry_after_seconds=60,
                next_eligible_at="2026-04-18T15:01:00",
                preserved_inputs_summary={"dry_run": False},
                now=self._fixed_now,
            )
            persist_pause_payload(run_root, payload)
            loaded = load_pause_payload(run_root)
            assert loaded is not None
            self.assertTrue(is_pause_active(loaded))
            self.assertFalse(is_pause_resume_eligible(loaded, now=self._fixed_now))

            def later_now() -> datetime:
                return datetime(2026, 4, 18, 15, 2, 0)

            self.assertTrue(is_pause_resume_eligible(loaded, now=later_now))
            resumed = mark_pause_resumed(run_root, now=later_now)
            assert resumed is not None
            self.assertEqual(resumed["lifecycle_state"], "resumed")
            self.assertEqual(resumed["resume_count"], 1)


if __name__ == "__main__":
    unittest.main()
