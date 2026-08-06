from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

from automation.orchestration.repository_profile import APPROVAL_ACTIONS
from automation.orchestration.repository_profile import FORBIDDEN_GIT_OPERATION_IDS
from automation.orchestration.repository_profile import validate_repository_profile
from automation.orchestration.repository_profile_binding import RepositoryProfileBindingError
from automation.orchestration.repository_profile_binding import bind_repository_profile_to_worktree


def _profile(root: Path, *, artifact_path: str | None = None):
    return validate_repository_profile({
        "schema_version": "1", "profile_id": "profile", "repository_root": str(root),
        "base_branch": "main", "python_executable": sys.executable,
        "validation_commands": [
            {"command_id": kind, "kind": kind, "argv": [sys.executable, "-m", "py_compile", "x.py"],
             "cwd": str(root / "nested"), "timeout_seconds": 10, "required": True,
             "stop_on_failure": True}
            for kind in ("focused", "related_regression", "full", "compile", "diff_check")
        ],
        "artifact_requirements": [] if artifact_path is None else [{
            "artifact_id": "inside", "path": artifact_path, "required": True,
            "expected_type": "json", "minimum_size_bytes": 1, "parse_json": True,
            "required_keys": ["x"], "readback_required": True,
            "checksum_required": True, "allow_outside_repository": False,
        }],
        "forbidden_git_operations": list(FORBIDDEN_GIT_OPERATION_IDS), "max_changed_files": 2,
        "approval_boundary": {action: "automatic" for action in APPROVAL_ACTIONS},
        "environment_allowlist": [],
    })


class RepositoryProfileBindingTests(unittest.TestCase):
    def test_rebinds_repository_paths_without_mutating_source(self) -> None:
        with tempfile.TemporaryDirectory() as source_raw, tempfile.TemporaryDirectory() as worktree_raw:
            source, worktree = Path(source_raw), Path(worktree_raw)
            for root in (source, worktree):
                (root / "nested").mkdir()
                (root / "artifact.json").touch()
                (root / ".git").touch()
            profile = _profile(source, artifact_path=str(source / "artifact.json"))
            bound = bind_repository_profile_to_worktree(profile, worktree)
            self.assertEqual(bound.repository_root, str(worktree.resolve()))
            self.assertTrue(all(item.cwd.startswith(str(worktree.resolve())) for item in bound.validation_commands))
            self.assertEqual(bound.artifact_requirements[0].path, str((worktree / "artifact.json").resolve()))
            self.assertEqual(profile.repository_root, str(source.resolve()))

    def test_rejects_non_worktree_and_mapped_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as source_raw, tempfile.TemporaryDirectory() as worktree_raw:
            source, worktree = Path(source_raw), Path(worktree_raw)
            (source / "nested").mkdir()
            (worktree / ".git").touch()
            profile = _profile(source)
            with self.assertRaisesRegex(RepositoryProfileBindingError, "not_found"):
                bind_repository_profile_to_worktree(profile, worktree)
            (worktree / "nested").symlink_to(Path(tempfile.gettempdir()))
            with self.assertRaisesRegex(RepositoryProfileBindingError, "symlink_escape"):
                bind_repository_profile_to_worktree(profile, worktree)
