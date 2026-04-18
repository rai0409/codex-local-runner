from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import unittest

from automation.github.write_idempotency import DEDUPE_CONFLICTING_PRIOR_INTENT
from automation.github.write_idempotency import DEDUPE_FIRST_ATTEMPT
from automation.github.write_idempotency import DEDUPE_REPLAY_SAME_INTENT
from automation.github.write_idempotency import evaluate_write_dedupe_status
from automation.github.write_receipts import FileWriteReceiptStore


class WriteIdempotencyTests(unittest.TestCase):
    def test_idempotency_key_is_deterministic_for_equivalent_input(self) -> None:
        kwargs = {
            "job_id": "job-1",
            "write_action": "create_draft_pr",
            "target_identifiers": {
                "repository": "rai0409/codex-local-runner",
                "head_branch": "feature/test",
                "base_branch": "main",
            },
            "intent_payload": {"title": "Draft", "body": "Body", "draft": True},
            "prior_records": [],
        }
        first = evaluate_write_dedupe_status(**kwargs)
        second = evaluate_write_dedupe_status(**kwargs)
        self.assertEqual(first["idempotency_key"], second["idempotency_key"])
        self.assertEqual(first["intent_fingerprint"], second["intent_fingerprint"])
        self.assertEqual(first["dedupe_status"], DEDUPE_FIRST_ATTEMPT)

    def test_replay_same_intent_is_detected_from_prior_record(self) -> None:
        first = evaluate_write_dedupe_status(
            job_id="job-1",
            write_action="create_draft_pr",
            target_identifiers={
                "repository": "rai0409/codex-local-runner",
                "head_branch": "feature/test",
                "base_branch": "main",
            },
            intent_payload={"title": "Draft", "body": "Body", "draft": True},
            prior_records=[],
        )
        replay = evaluate_write_dedupe_status(
            job_id="job-1",
            write_action="create_draft_pr",
            target_identifiers={
                "repository": "rai0409/codex-local-runner",
                "head_branch": "feature/test",
                "base_branch": "main",
            },
            intent_payload={"title": "Draft", "body": "Body", "draft": True},
            prior_records=[
                {
                    "idempotency_key": first["idempotency_key"],
                    "job_id": "job-1",
                    "write_action": "create_draft_pr",
                    "target_identifiers": {
                        "repository": "rai0409/codex-local-runner",
                        "head_branch": "feature/test",
                        "base_branch": "main",
                    },
                    "intent_fingerprint": first["intent_fingerprint"],
                    "final_classification": "applied",
                }
            ],
        )
        self.assertEqual(replay["dedupe_status"], DEDUPE_REPLAY_SAME_INTENT)

    def test_conflicting_prior_intent_is_detected(self) -> None:
        payload = evaluate_write_dedupe_status(
            job_id="job-1",
            write_action="create_draft_pr",
            target_identifiers={
                "repository": "rai0409/codex-local-runner",
                "head_branch": "feature/other",
                "base_branch": "main",
            },
            intent_payload={"title": "Other", "body": "Body", "draft": True},
            prior_records=[
                {
                    "idempotency_key": "prior",
                    "job_id": "job-1",
                    "write_action": "create_draft_pr",
                    "target_identifiers": {
                        "repository": "rai0409/codex-local-runner",
                        "head_branch": "feature/test",
                        "base_branch": "main",
                    },
                    "intent_fingerprint": "x",
                    "final_classification": "applied",
                }
            ],
        )
        self.assertEqual(payload["dedupe_status"], DEDUPE_CONFLICTING_PRIOR_INTENT)

    def test_receipt_persistence_and_reload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = FileWriteReceiptStore(Path(tmp_dir))
            first = store.persist_record(
                write_action="bounded_merge",
                idempotency_key="id-key",
                updated_at="2026-04-18T14:00:00",
                payload={
                    "job_id": "job-1",
                    "write_action": "bounded_merge",
                    "target_identifiers": {"repository": "rai0409/codex-local-runner", "pr_number": 42},
                    "intent_fingerprint": "abc",
                    "execution_status": "attempted",
                    "final_classification": "applied",
                },
            )
            second = store.persist_record(
                write_action="bounded_merge",
                idempotency_key="id-key",
                updated_at="2026-04-18T14:01:00",
                payload={
                    "job_id": "job-1",
                    "write_action": "bounded_merge",
                    "target_identifiers": {"repository": "rai0409/codex-local-runner", "pr_number": 42},
                    "intent_fingerprint": "abc",
                    "execution_status": "not_attempted",
                    "final_classification": "already_applied",
                },
            )
            loaded = store.get_record("bounded_merge", "id-key")
        self.assertEqual(first["attempt_count"], 1)
        self.assertEqual(second["attempt_count"], 2)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["attempt_count"], 2)
        self.assertEqual(loaded["final_classification"], "already_applied")

    def test_corrupted_receipt_file_fails_conservatively(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            action_path = root / "bounded_merge.json"
            action_path.write_text("{not valid json", encoding="utf-8")
            store = FileWriteReceiptStore(root)
            with self.assertRaises(ValueError):
                store.persist_record(
                    write_action="bounded_merge",
                    idempotency_key="id-key",
                    updated_at="2026-04-18T14:00:00",
                    payload={
                        "job_id": "job-1",
                        "write_action": "bounded_merge",
                        "target_identifiers": {"repository": "rai0409/codex-local-runner", "pr_number": 42},
                        "intent_fingerprint": "abc",
                        "execution_status": "attempted",
                        "final_classification": "applied",
                    },
                )

    def test_locked_persist_avoids_lost_updates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = FileWriteReceiptStore(Path(tmp_dir))

            def _write_once() -> None:
                store.persist_record(
                    write_action="update_existing_pr",
                    idempotency_key="same-key",
                    updated_at="2026-04-18T14:00:00",
                    payload={
                        "job_id": "job-1",
                        "write_action": "update_existing_pr",
                        "target_identifiers": {"repository": "rai0409/codex-local-runner", "pr_number": 42},
                        "intent_fingerprint": "abc",
                        "execution_status": "attempted",
                        "final_classification": "applied",
                    },
                )

            threads = [threading.Thread(target=_write_once) for _ in range(10)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            record = store.get_record("update_existing_pr", "same-key")
            on_disk = json.loads((Path(tmp_dir) / "update_existing_pr.json").read_text(encoding="utf-8"))

        self.assertIsNotNone(record)
        self.assertEqual(record["attempt_count"], 10)
        self.assertIn("records_by_key", on_disk)
        self.assertIn("same-key", on_disk["records_by_key"])


if __name__ == "__main__":
    unittest.main()
