from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import run_daemon_candidate_acceptance as acceptance  # noqa: E402


class AcceptanceCleanlinessRequirementTests(unittest.TestCase):
    def test_dirty_sandbox_produces_failure(self):
        failures = acceptance.cleanliness_failures(
            {
                "sandbox_final_status_clean": False,
                "sandbox_final_status_short": ["?? __pycache__/"],
            }
        )
        self.assertEqual(len(failures), 1)
        self.assertIn("__pycache__", failures[0])

    def test_clean_sandbox_produces_no_failure(self):
        failures = acceptance.cleanliness_failures(
            {"sandbox_final_status_clean": True, "sandbox_final_status_short": []}
        )
        self.assertEqual(failures, [])

    def test_leftover_generated_artifacts_detected(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = Path(raw)
            (repo / "calculator.py").write_text("x = 1\n", encoding="utf-8")
            cache = repo / "__pycache__"
            cache.mkdir()
            (cache / "calculator.cpython-312.pyc").write_bytes(b"\x00")
            leftovers = acceptance.leftover_generated_artifacts(repo)
        self.assertIn("__pycache__", leftovers)
        self.assertTrue(any(item.endswith(".pyc") for item in leftovers))

    def test_no_leftovers_on_clean_repo(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = Path(raw)
            (repo / "calculator.py").write_text("x = 1\n", encoding="utf-8")
            leftovers = acceptance.leftover_generated_artifacts(repo)
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
