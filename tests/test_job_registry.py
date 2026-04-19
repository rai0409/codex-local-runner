from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tempfile
import unittest

from automation.scheduler.job_registry import FileJobRegistry
from automation.scheduler.job_registry import STATE_PENDING
from automation.scheduler.job_registry import STATE_RETRY_SCHEDULED
from automation.scheduler.job_registry import STATE_RUNNABLE


class JobRegistryTests(unittest.TestCase):
    def _fixed_now(self) -> datetime:
        return datetime(2026, 4, 18, 17, 0, 0)

    def test_registry_create_load_update_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "job_registry.json"
            registry = FileJobRegistry(path, now=self._fixed_now)
            created = registry.upsert(
                {
                    "job_id": "job-1",
                    "current_state": STATE_PENDING,
                    "artifact_root": "/tmp/planning/job-1",
                    "run_root": "/tmp/executions/job-1",
                    "retry_budget_remaining": 2,
                }
            )
            self.assertEqual(created["current_state"], STATE_PENDING)
            self.assertEqual(created["retry_budget_remaining"], 2)

            updated = registry.upsert(
                {
                    "job_id": "job-1",
                    "current_state": STATE_RUNNABLE,
                    "retry_budget_remaining": 1,
                }
            )
            self.assertEqual(updated["current_state"], STATE_RUNNABLE)
            self.assertEqual(updated["retry_budget_remaining"], 1)

            reloaded = FileJobRegistry(path, now=self._fixed_now)
            record = reloaded.get("job-1")
            assert record is not None
            self.assertEqual(record["current_state"], STATE_RUNNABLE)
            self.assertEqual(record["retry_budget_remaining"], 1)
            self.assertEqual(record["created_at"], "2026-04-18T17:00:00")

    def test_registry_list_filter_and_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "job_registry.json"
            registry = FileJobRegistry(path, now=self._fixed_now)
            registry.upsert({"job_id": "job-b", "current_state": STATE_PENDING})
            registry.upsert({"job_id": "job-a", "current_state": STATE_RETRY_SCHEDULED})
            registry.upsert({"job_id": "job-c", "current_state": STATE_RUNNABLE})

            all_records = registry.list()
            self.assertEqual([item["job_id"] for item in all_records], ["job-a", "job-b", "job-c"])

            pending = registry.list(current_state=STATE_PENDING)
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["job_id"], "job-b")


if __name__ == "__main__":
    unittest.main()
