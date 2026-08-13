from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from automation.orchestration.repository_multi_cycle_state import RepositoryMultiCycleStateError, load_latest_checkpoint, write_checkpoint


class StateTests(unittest.TestCase):
    def _write_json_only(self, root: Path, sequence: int, value: dict | None = None) -> Path:
        path = root / f"checkpoint-{sequence:06d}.json"
        payload = {"schema_version":"1","checkpoint_sequence":sequence,"cycle_run_id":"cycle-12345678901234567890"}
        if value: payload.update(value)
        path.write_bytes(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode())
        return path

    def _write_sha_only(self, root: Path, sequence: int) -> Path:
        path = root / f"checkpoint-{sequence:06d}.sha256"; path.write_text("0" * 64 + f"  checkpoint-{sequence:06d}.json\n"); return path

    def _assert_error(self, root: Path, reason: str) -> None:
        with self.assertRaises(RepositoryMultiCycleStateError) as caught: load_latest_checkpoint(root)
        self.assertEqual(caught.exception.reason_code, reason)

    def test_multiple_roundtrip_canonical_sidecar_and_immutability(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name); first=write_checkpoint(root,{"cycle_run_id":"cycle-12345678901234567890"}); second=write_checkpoint(root,{"cycle_run_id":"cycle-12345678901234567890","accepted_head_sha":"b"*40})
            value,fallback=load_latest_checkpoint(root); self.assertFalse(fallback); self.assertEqual(value["checkpoint_sequence"],1)
            self.assertEqual(second.with_suffix(".sha256").read_text(),f"{hashlib.sha256(second.read_bytes()).hexdigest()}  checkpoint-000001.json\n")
            before=first.read_bytes(); third=write_checkpoint(root,{"cycle_run_id":"cycle-12345678901234567890"})
            self.assertEqual(third.name,"checkpoint-000002.json"); self.assertEqual(first.read_bytes(),before)

    def test_latest_json_and_sha_only_fallback_cleanup_and_sequence_reuse(self):
        for kind in ("json","sha"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as name:
                root=Path(name); write_checkpoint(root,{"cycle_run_id":"cycle-12345678901234567890"}); orphan=self._write_json_only(root,1) if kind=="json" else self._write_sha_only(root,1)
                value,fallback=load_latest_checkpoint(root); self.assertTrue(fallback); self.assertEqual(value["checkpoint_sequence"],0); self.assertFalse(orphan.exists())
                next_path=write_checkpoint(root,{"cycle_run_id":"cycle-12345678901234567890"}); self.assertEqual(next_path.name,"checkpoint-000001.json"); self.assertTrue(next_path.with_suffix(".sha256").exists())

    def test_no_prior_and_non_latest_incomplete_fail_closed_without_mutation(self):
        for kind in ("json","sha"):
            with self.subTest(kind="zero-"+kind), tempfile.TemporaryDirectory() as name:
                root=Path(name); orphan=self._write_json_only(root,0) if kind=="json" else self._write_sha_only(root,0); before=orphan.read_bytes(); self._assert_error(root,"multi_cycle.resume.checkpoint_incomplete"); self.assertEqual(orphan.read_bytes(),before)
            with self.subTest(kind="nonlatest-"+kind), tempfile.TemporaryDirectory() as name:
                root=Path(name); write_checkpoint(root,{"cycle_run_id":"cycle-12345678901234567890"}); orphan=self._write_json_only(root,1) if kind=="json" else self._write_sha_only(root,1); self._write_json_only(root,2); p=root/"checkpoint-000002.json"; p.with_suffix(".sha256").write_text(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  checkpoint-000002.json\n"); before=orphan.read_bytes(); self._assert_error(root,"multi_cycle.resume.checkpoint_sequence_invalid"); self.assertEqual(orphan.read_bytes(),before)

    def test_gaps_corruption_and_invariants_fail_closed(self):
        cases=(
            ("gap", "multi_cycle.resume.checkpoint_sequence_invalid"),
            ("hash", "multi_cycle.resume.checkpoint_hash_mismatch"),
            ("json", "multi_cycle.resume.checkpoint_invalid"),
            ("schema", "multi_cycle.resume.checkpoint_invariant"),
            ("sequence", "multi_cycle.resume.checkpoint_invariant"),
        )
        for kind, reason in cases:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as name:
                root=Path(name); first=write_checkpoint(root,{"cycle_run_id":"cycle-12345678901234567890"})
                if kind=="gap": self._write_json_only(root,2); p=root/"checkpoint-000002.json"; p.with_suffix(".sha256").write_text(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  checkpoint-000002.json\n")
                else:
                    second=write_checkpoint(root,{"cycle_run_id":"cycle-12345678901234567890"})
                    if kind=="hash": second.with_suffix(".sha256").write_text("0"*64+"  checkpoint-000001.json\n")
                    elif kind=="json": second.write_text("{")
                    else:
                        value=json.loads(second.read_text()); value["schema_version" if kind=="schema" else "checkpoint_sequence"]="2" if kind=="schema" else 0; second.write_bytes(json.dumps(value,sort_keys=True,separators=(",",":")).encode()); second.with_suffix(".sha256").write_text(f"{hashlib.sha256(second.read_bytes()).hexdigest()}  checkpoint-000001.json\n")
                self._assert_error(root,reason); self.assertTrue(first.exists())

    def test_write_refuses_incomplete_or_gapped_history(self):
        for kind in ("json","sha","gap"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as name:
                root=Path(name); write_checkpoint(root,{"cycle_run_id":"cycle-12345678901234567890"})
                if kind=="json": self._write_json_only(root,1)
                elif kind=="sha": self._write_sha_only(root,1)
                else: self._write_json_only(root,2); p=root/"checkpoint-000002.json"; p.with_suffix(".sha256").write_text(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  checkpoint-000002.json\n")
                with self.assertRaises(RepositoryMultiCycleStateError) as caught: write_checkpoint(root,{"cycle_run_id":"cycle-12345678901234567890"})
                self.assertEqual(caught.exception.reason_code,"multi_cycle.state.history_invalid")

    def test_pair_write_interruption_recovers_and_reuses_sequence(self):
        import automation.orchestration.repository_multi_cycle_state as module
        with tempfile.TemporaryDirectory() as name:
            root=Path(name); write_checkpoint(root,{"cycle_run_id":"cycle-12345678901234567890"}); original=module._write; calls=[]
            def interrupted(path,payload):
                calls.append(path.suffix)
                if path.suffix==".sha256": raise OSError("interrupted")
                return original(path,payload)
            with patch.object(module,"_write",side_effect=interrupted):
                with self.assertRaises(OSError): write_checkpoint(root,{"cycle_run_id":"cycle-12345678901234567890"})
            orphan=root/"checkpoint-000001.json"; self.assertTrue(orphan.exists()); value,fallback=load_latest_checkpoint(root); self.assertTrue(fallback); self.assertEqual(value["checkpoint_sequence"],0); self.assertFalse(orphan.exists()); self.assertEqual(write_checkpoint(root,{"cycle_run_id":"cycle-12345678901234567890"}).name,"checkpoint-000001.json")
