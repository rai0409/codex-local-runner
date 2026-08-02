from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from automation.orchestration import repository_state_analyzer as analyzer
from automation.orchestration.repository_state_analyzer import (
    OPERATION_ORDER, REPOSITORY_STATE_SCHEMA_VERSION, WORKTREE_STATES,
    RepositoryStateAnalyzerError, RepositoryStateSnapshot, analyze_repository_state,
    repository_state_to_mapping, serialize_repository_state,
)


class RepositoryStateAnalyzerTests(unittest.TestCase):
    def git(self, repo: str, *args: str) -> str:
        return subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, text=True).stdout.strip()

    def init(self, repo: str, *, commit: bool = True) -> None:
        self.git(repo, "init", "-q", "-b", "main")
        self.git(repo, "config", "user.name", "Test User")
        self.git(repo, "config", "user.email", "test@example.com")
        if commit:
            Path(repo, "base.txt").write_text("base\n", encoding="utf-8")
            self.git(repo, "add", "base.txt")
            self.git(repo, "commit", "-qm", "base")

    def marker(self, repo: str, name: str, *, directory: bool = False) -> None:
        path = Path(self.git(repo, "rev-parse", "--git-path", name))
        if not path.is_absolute():
            path = Path(repo, path)
        if directory:
            path.mkdir()
        else:
            path.write_text("marker\n", encoding="ascii")

    def test_clean_mapping_serialization_frozen_and_exports(self):
        with tempfile.TemporaryDirectory() as repo:
            self.init(repo)
            snapshot = analyze_repository_state(repo)
        self.assertEqual(snapshot.schema_version, REPOSITORY_STATE_SCHEMA_VERSION)
        self.assertEqual(snapshot.worktree_state, "known_clean")
        self.assertEqual(snapshot.branch, "main")
        self.assertFalse(snapshot.detached_head)
        self.assertEqual(snapshot.tracked_modified_files, ())
        self.assertEqual(snapshot.operations_in_progress, ())
        with self.assertRaises(Exception):
            snapshot.branch = "other"  # type: ignore[misc]
        mapped = repository_state_to_mapping(snapshot)
        self.assertEqual(set(mapped), {field.name for field in __import__("dataclasses").fields(RepositoryStateSnapshot)})
        serialized = serialize_repository_state(snapshot)
        self.assertEqual(serialized, serialize_repository_state(snapshot))
        self.assertEqual(json.loads(serialized), mapped)
        self.assertEqual(WORKTREE_STATES, ("known_clean", "known_dirty"))
        self.assertEqual(analyzer.__all__, ["RepositoryStateAnalyzerError", "RepositoryStateSnapshot", "analyze_repository_state", "repository_state_to_mapping", "serialize_repository_state"])

    def test_dirty_status_classes_stable_order_and_duplicates(self):
        with tempfile.TemporaryDirectory() as repo:
            self.init(repo)
            Path(repo, "z.txt").write_text("z\n", encoding="utf-8")
            Path(repo, "a.txt").write_text("a\n", encoding="utf-8")
            self.git(repo, "add", "z.txt", "a.txt")
            Path(repo, "z.txt").write_text("z changed\n", encoding="utf-8")
            Path(repo, "base.txt").write_text("changed\n", encoding="utf-8")
            Path(repo, "u.txt").write_text("u\n", encoding="utf-8")
            snapshot = analyze_repository_state(repo)
        self.assertEqual(snapshot.staged_files, ("a.txt", "z.txt"))
        self.assertEqual(snapshot.tracked_modified_files, ("base.txt", "z.txt"))
        self.assertEqual(snapshot.untracked_files, ("u.txt",))
        self.assertEqual(snapshot.worktree_state, "known_dirty")

    def test_rename_conflict_and_operations_have_contract_order(self):
        with tempfile.TemporaryDirectory() as repo:
            self.init(repo)
            self.git(repo, "mv", "base.txt", "renamed.txt")
            self.marker(repo, "sequencer", directory=True)
            self.marker(repo, "BISECT_LOG")
            self.marker(repo, "REVERT_HEAD")
            self.marker(repo, "CHERRY_PICK_HEAD")
            self.marker(repo, "rebase-apply", directory=True)
            self.marker(repo, "MERGE_HEAD")
            snapshot = analyze_repository_state(repo)
        self.assertEqual(snapshot.staged_files, ("renamed.txt",))
        self.assertEqual(snapshot.tracked_modified_files, ())
        self.assertEqual(snapshot.operations_in_progress, OPERATION_ORDER)

    def test_real_conflict_is_not_duplicated_into_other_statuses(self):
        with tempfile.TemporaryDirectory() as repo:
            self.init(repo)
            self.git(repo, "checkout", "-qb", "feature")
            Path(repo, "base.txt").write_text("feature\n", encoding="utf-8")
            self.git(repo, "commit", "-am", "feature")
            self.git(repo, "checkout", "-q", "main")
            Path(repo, "base.txt").write_text("main\n", encoding="utf-8")
            self.git(repo, "commit", "-am", "main")
            subprocess.run(["git", "-C", repo, "merge", "feature"], capture_output=True, check=False)
            snapshot = analyze_repository_state(repo)
        self.assertEqual(snapshot.conflicted_files, ("base.txt",))
        self.assertNotIn("base.txt", snapshot.staged_files)
        self.assertNotIn("base.txt", snapshot.tracked_modified_files)

    def test_detached_subdirectory_unborn_and_no_upstream(self):
        with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as unborn:
            self.init(repo)
            head = self.git(repo, "rev-parse", "HEAD")
            self.git(repo, "checkout", "-q", head)
            detached = analyze_repository_state(Path(repo, "nested")) if False else analyze_repository_state(repo)
            self.init(unborn, commit=False)
            unborn_snapshot = analyze_repository_state(unborn)
        self.assertIsNone(detached.branch)
        self.assertTrue(detached.detached_head)
        self.assertEqual(detached.head_sha, head)
        self.assertIsNone(detached.upstream_ref)
        self.assertEqual(unborn_snapshot.branch, "main")
        self.assertIsNone(unborn_snapshot.head_sha)

    def test_subdirectory_linked_worktree_and_non_utf8_filename(self):
        with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as parent:
            self.init(repo)
            Path(repo, "sub").mkdir()
            self.assertEqual(analyze_repository_state(Path(repo, "sub")).repository_root, repo)
            linked = Path(parent, "linked")
            self.git(repo, "worktree", "add", "-q", "-b", "linked", str(linked))
            self.assertTrue((linked / ".git").is_file())
            self.assertEqual(analyze_repository_state(linked).repository_root, str(linked))
            raw_name = os.fsencode(repo) + b"/bad-\xff-name"
            descriptor = os.open(raw_name, os.O_CREAT | os.O_WRONLY, 0o600)
            os.close(descriptor)
            snapshot = analyze_repository_state(repo)
        self.assertIn("bad-\udcff-name", snapshot.untracked_files)
        self.assertIn("\\udcff", serialize_repository_state(snapshot))

    def test_local_upstream_ahead_behind_and_deleted_upstream(self):
        with tempfile.TemporaryDirectory() as remote, tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as peer:
            subprocess.run(["git", "init", "--bare", "-q", remote], check=True)
            self.init(repo)
            self.git(repo, "remote", "add", "origin", remote)
            self.git(repo, "push", "-qu", "origin", "main")
            self.git(repo, "clone", "-q", remote, peer)
            self.git(peer, "checkout", "-q", "main")
            self.git(peer, "config", "user.name", "Peer")
            self.git(peer, "config", "user.email", "peer@example.com")
            Path(repo, "ahead.txt").write_text("a\n", encoding="utf-8")
            self.git(repo, "add", "ahead.txt")
            self.git(repo, "commit", "-qm", "ahead")
            ahead = analyze_repository_state(repo)
            Path(peer, "behind.txt").write_text("b\n", encoding="utf-8")
            self.git(peer, "add", "behind.txt")
            self.git(peer, "commit", "-qm", "behind")
            self.git(peer, "push", "-q")
            self.git(repo, "fetch", "-q", "origin")
            diverged = analyze_repository_state(repo)
            self.git(repo, "update-ref", "-d", "refs/remotes/origin/main")
            deleted = analyze_repository_state(repo)
        self.assertEqual(ahead.upstream_ref, "origin/main")
        self.assertEqual(ahead.ahead_count, 1)
        self.assertEqual(ahead.behind_count, 0)
        self.assertEqual((diverged.ahead_count, diverged.behind_count), (1, 1))
        self.assertEqual(deleted.upstream_ref, "origin/main")
        self.assertIsNone(deleted.ahead_count)

    def test_local_submodule_modification_is_tracked_as_dirty(self):
        with tempfile.TemporaryDirectory() as child, tempfile.TemporaryDirectory() as repo:
            self.init(child)
            self.init(repo)
            self.git(repo, "-c", "protocol.file.allow=always", "submodule", "add", "-q", child, "vendor/child")
            self.git(repo, "commit", "-qm", "add submodule")
            Path(repo, "vendor/child/base.txt").write_text("modified\n", encoding="utf-8")
            snapshot = analyze_repository_state(repo)
        self.assertEqual(snapshot.tracked_modified_files, ("vendor/child",))
        self.assertEqual(snapshot.worktree_state, "known_dirty")

    def test_invalid_paths_mapping_type_and_stable_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            file_path = Path(directory, "file")
            file_path.write_text("x", encoding="utf-8")
            cases = [(True, "repository_path.invalid_type"), ("", "repository_path.invalid_type"), (Path(directory, "none"), "repository_path.not_found"), (file_path, "repository_path.not_directory"), (directory, "repository.invalid_git_repository")]
            for value, code in cases:
                with self.subTest(value=value):
                    with self.assertRaises(RepositoryStateAnalyzerError) as raised:
                        analyze_repository_state(value)  # type: ignore[arg-type]
                    self.assertEqual(raised.exception.reason_code, code)
        with self.assertRaises(TypeError):
            repository_state_to_mapping(object())  # type: ignore[arg-type]

    def test_read_only_and_git_failures(self):
        with tempfile.TemporaryDirectory() as repo:
            self.init(repo)
            self.marker(repo, "MERGE_HEAD")
            marker = Path(self.git(repo, "rev-parse", "--git-path", "MERGE_HEAD"))
            if not marker.is_absolute():
                marker = Path(repo, marker)
            before = (self.git(repo, "rev-parse", "HEAD"), self.git(repo, "branch", "--show-current"), self.git(repo, "status", "--porcelain"), Path(repo, "base.txt").read_text(encoding="utf-8"), marker.read_text(encoding="ascii"))
            self.assertEqual(analyze_repository_state(repo).operations_in_progress, ("merge",))
            after = (self.git(repo, "rev-parse", "HEAD"), self.git(repo, "branch", "--show-current"), self.git(repo, "status", "--porcelain"), Path(repo, "base.txt").read_text(encoding="utf-8"), marker.read_text(encoding="ascii"))
        self.assertEqual(before, after)
        with mock.patch.object(analyzer.subprocess, "run", side_effect=FileNotFoundError):
            with self.assertRaises(RepositoryStateAnalyzerError) as raised:
                analyze_repository_state("/")
        self.assertEqual(raised.exception.reason_code, "git.executable_not_found")

    def test_nonzero_git_command_has_stable_reason_code(self):
        with tempfile.TemporaryDirectory() as repo:
            self.init(repo)
            original = analyzer.subprocess.run

            def fail_status(argv, **kwargs):
                if "status" in argv:
                    return subprocess.CompletedProcess(argv, 7, b"", b"failure")
                return original(argv, **kwargs)

            with mock.patch.object(analyzer.subprocess, "run", side_effect=fail_status):
                with self.assertRaises(RepositoryStateAnalyzerError) as raised:
                    analyze_repository_state(repo)
        self.assertEqual(raised.exception.reason_code, "git.command_failed")


if __name__ == "__main__":
    unittest.main()
