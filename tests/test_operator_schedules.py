from __future__ import annotations

from datetime import datetime
from datetime import timezone
import unittest

from orchestrator.operator_schedules import get_due_operator_schedules
from orchestrator.operator_schedules import is_schedule_due_now
from orchestrator.operator_schedules import load_operator_schedules


class OperatorScheduleTests(unittest.TestCase):
    def _base_schedule(self) -> dict:
        return {
            "schedule_id": "test_schedule",
            "enabled": True,
            "timezone": "UTC",
            "target": {"repo": "codex-local-runner"},
            "job_selector": {"accepted_status": "accepted"},
            "delivery": {"method": "placeholder"},
            "decision": {"mode": "human_review_required"},
            "trigger": {
                "type": "daily_times",
                "times": ("09:00",),
                "daily_minutes": (9 * 60,),
            },
        }

    def test_schedule_with_one_daily_time(self) -> None:
        schedule = self._base_schedule()
        due_now = datetime(2026, 4, 13, 9, 0, tzinfo=timezone.utc)
        not_due_now = datetime(2026, 4, 13, 9, 1, tzinfo=timezone.utc)

        self.assertTrue(is_schedule_due_now(schedule, now_utc=due_now))
        self.assertFalse(is_schedule_due_now(schedule, now_utc=not_due_now))

    def test_schedule_with_multiple_daily_times(self) -> None:
        schedule = self._base_schedule()
        schedule["trigger"]["times"] = ("09:00", "17:30")
        schedule["trigger"]["daily_minutes"] = ((9 * 60), (17 * 60) + 30)

        due_evening = datetime(2026, 4, 13, 17, 30, tzinfo=timezone.utc)
        not_due = datetime(2026, 4, 13, 17, 31, tzinfo=timezone.utc)

        self.assertTrue(is_schedule_due_now(schedule, now_utc=due_evening))
        self.assertFalse(is_schedule_due_now(schedule, now_utc=not_due))

    def test_disabled_schedule_is_never_due(self) -> None:
        schedule = self._base_schedule()
        schedule["enabled"] = False
        due_time = datetime(2026, 4, 13, 9, 0, tzinfo=timezone.utc)

        self.assertFalse(is_schedule_due_now(schedule, now_utc=due_time))

    def test_timezone_aware_due_evaluation(self) -> None:
        schedule = self._base_schedule()
        schedule["timezone"] = "Asia/Tokyo"
        schedule["trigger"]["times"] = ("09:30",)
        schedule["trigger"]["daily_minutes"] = ((9 * 60) + 30,)

        # 00:30 UTC == 09:30 Asia/Tokyo
        due_in_tokyo = datetime(2026, 4, 13, 0, 30, tzinfo=timezone.utc)
        not_due_in_tokyo = datetime(2026, 4, 13, 0, 31, tzinfo=timezone.utc)

        self.assertTrue(is_schedule_due_now(schedule, now_utc=due_in_tokyo))
        self.assertFalse(is_schedule_due_now(schedule, now_utc=not_due_in_tokyo))

    def test_load_operator_schedules_contains_required_fields(self) -> None:
        policy = load_operator_schedules()
        self.assertIn("schedules", policy)
        self.assertGreaterEqual(len(policy["schedules"]), 1)
        schedule = policy["schedules"][0]
        self.assertIn("schedule_id", schedule)
        self.assertIn("enabled", schedule)
        self.assertIn("timezone", schedule)
        self.assertIn("target", schedule)
        self.assertIn("repo", schedule["target"])
        self.assertIn("job_selector", schedule)
        self.assertIn("delivery", schedule)
        self.assertIn("decision", schedule)
        self.assertIn("trigger", schedule)
        self.assertEqual(schedule["decision"]["mode"], "human_review_required")

    def test_get_due_operator_schedules_filters_due_now(self) -> None:
        policy = {
            "schedules": (
                {
                    "schedule_id": "due",
                    "enabled": True,
                    "timezone": "UTC",
                    "target": {"repo": "codex-local-runner"},
                    "job_selector": {"accepted_status": "accepted"},
                    "delivery": {"method": "placeholder"},
                    "decision": {"mode": "human_review_required"},
                    "trigger": {
                        "type": "daily_times",
                        "times": ("10:00",),
                        "daily_minutes": (10 * 60,),
                    },
                },
                {
                    "schedule_id": "not_due",
                    "enabled": True,
                    "timezone": "UTC",
                    "target": {"repo": "codex-local-runner"},
                    "job_selector": {"accepted_status": "accepted"},
                    "delivery": {"method": "placeholder"},
                    "decision": {"mode": "human_review_required"},
                    "trigger": {
                        "type": "daily_times",
                        "times": ("11:00",),
                        "daily_minutes": (11 * 60,),
                    },
                },
            )
        }
        now = datetime(2026, 4, 13, 10, 0, tzinfo=timezone.utc)

        due = get_due_operator_schedules(now_utc=now, schedule_policy=policy)

        self.assertEqual(len(due), 1)
        self.assertEqual(due[0]["schedule_id"], "due")

    def test_legacy_shape_is_accepted_with_compatibility_normalization(self) -> None:
        policy = {
            "schedules": (
                {
                    "name": "legacy_schedule",
                    "enabled": True,
                    "timezone": "UTC",
                    "target_repo": "codex-local-runner",
                    "job_selector": {"accepted_status": "accepted"},
                    "delivery": {"method": "placeholder"},
                    "decision": {"mode": "advisory_only"},
                    "trigger": {
                        "type": "daily_times",
                        "times": ("10:00",),
                        "daily_minutes": (10 * 60,),
                    },
                },
            )
        }
        now = datetime(2026, 4, 13, 10, 0, tzinfo=timezone.utc)

        due = get_due_operator_schedules(now_utc=now, schedule_policy=policy)

        self.assertEqual(len(due), 1)
        self.assertEqual(due[0]["schedule_id"], "legacy_schedule")
        self.assertEqual(due[0]["target"]["repo"], "codex-local-runner")
        self.assertEqual(due[0]["decision"]["mode"], "human_review_required")


if __name__ == "__main__":
    unittest.main()
