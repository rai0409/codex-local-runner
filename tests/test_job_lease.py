from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tempfile
import unittest

from automation.scheduler.job_lease import FileJobLease


class JobLeaseTests(unittest.TestCase):
    def _fixed_now(self) -> datetime:
        return datetime(2026, 4, 18, 17, 0, 0)

    def test_active_lease_blocks_duplicate_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "job_leases.json"
            lease = FileJobLease(path, now=self._fixed_now)
            claimed, _ = lease.claim(job_id="job-1", holder="holder-a", lease_seconds=60)
            self.assertTrue(claimed)
            claimed_other, existing = lease.claim(job_id="job-1", holder="holder-b", lease_seconds=60)
            self.assertFalse(claimed_other)
            assert existing is not None
            self.assertEqual(existing["holder"], "holder-a")

    def test_expired_lease_becomes_reclaimable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "job_leases.json"

            def now_a() -> datetime:
                return datetime(2026, 4, 18, 17, 0, 0)

            def now_b() -> datetime:
                return datetime(2026, 4, 18, 17, 2, 0)

            lease_a = FileJobLease(path, now=now_a)
            claimed, _ = lease_a.claim(job_id="job-1", holder="holder-a", lease_seconds=30)
            self.assertTrue(claimed)

            lease_b = FileJobLease(path, now=now_b)
            claimed_after_expiry, record = lease_b.claim(job_id="job-1", holder="holder-b", lease_seconds=30)
            self.assertTrue(claimed_after_expiry)
            assert record is not None
            self.assertEqual(record["holder"], "holder-b")

    def test_renew_and_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "job_leases.json"
            lease = FileJobLease(path, now=self._fixed_now)
            claimed, _ = lease.claim(job_id="job-1", holder="holder-a", lease_seconds=60)
            self.assertTrue(claimed)
            renewed, renewed_record = lease.renew(job_id="job-1", holder="holder-a", lease_seconds=120)
            self.assertTrue(renewed)
            assert renewed_record is not None
            self.assertEqual(renewed_record["holder"], "holder-a")
            self.assertTrue(lease.is_claimed(job_id="job-1"))
            released = lease.release(job_id="job-1", holder="holder-a")
            self.assertTrue(released)
            self.assertFalse(lease.is_claimed(job_id="job-1"))


if __name__ == "__main__":
    unittest.main()
