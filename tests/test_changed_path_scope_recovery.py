from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from automation.orchestration.repository_resolved_single_task_controller import (
    MAX_SAFE_SCOPE_AUTO_EXPANSIONS,
    _recover_safe_changed_path_scope,
)


class ChangedPathScopeRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _create(self, *paths: str) -> None:
        for path in paths:
            candidate = self.root / path
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.write_text("x\n", encoding="utf-8")

    def _recover(self, *actual: str):
        self._create(*actual)
        return _recover_safe_changed_path_scope(self.root, ("src/feature.py",), actual)

    def test_no_unexpected_files_is_not_needed(self):
        result = self._recover("src/feature.py")
        self.assertFalse(result.scope_recovery_attempted)
        self.assertEqual(result.scope_recovery_status, "not_needed")
        self.assertEqual(result.effective_allowed_changed_paths, ("src/feature.py",))

    def test_root_and_nested_support_paths_are_accepted(self):
        paths = (
            "tests/test_feature.py", "apps/foo/tests/test_feature.py",
            "packages/a/b/tests/test_feature.py", "docs/feature.md",
        )
        result = self._recover(*paths)
        self.assertTrue(result.scope_recovery_attempted)
        self.assertEqual(result.scope_recovery_status, "accepted")
        self.assertEqual(result.auto_expanded_paths, tuple(sorted(paths)))
        self.assertEqual(result.effective_allowed_changed_paths, tuple(sorted(("src/feature.py", *paths))))

    def test_nested_docs_and_two_tests_plus_two_docs_are_accepted_atomically(self):
        paths = (
            "tests/test_one.py", "apps/foo/tests/test_two.py",
            "docs/one.md", "apps/foo/docs/two.md",
        )
        result = self._recover(*paths)
        self.assertEqual(len(result.auto_expanded_paths), MAX_SAFE_SCOPE_AUTO_EXPANSIONS)
        self.assertEqual(result.auto_expanded_paths, tuple(sorted(paths)))

    def test_more_than_four_safe_paths_blocks_without_partial_expansion(self):
        paths = tuple(f"tests/test_{number}.py" for number in range(5))
        result = self._recover(*paths)
        self.assertEqual(result.scope_recovery_status, "blocked")
        self.assertEqual(result.auto_expanded_paths, ())
        self.assertEqual(result.original_unexpected_changed_files, paths)

    def test_hard_block_categories_and_non_support_source_are_blocked(self):
        paths = (
            "src/foo.py", "src/tests.py", ".github/workflows/ci.yml",
            "migrations/001.py", "alembic/versions/001.py", ".env",
            "tests/secret.txt", "pyproject.toml", "requirements.txt", "package.json",
            "poetry.lock", "tests/data/fixture.json", "docs/archive.zip", "docs/schema.sql",
        )
        for path in paths:
            with self.subTest(path=path):
                result = self._recover(path)
                self.assertEqual(result.scope_recovery_status, "blocked")
                self.assertEqual(result.auto_expanded_paths, ())

    def test_absolute_and_traversal_paths_are_blocked(self):
        for path in ("/tmp/outside.py", "C:/outside.py", "../tests/test_feature.py", "tests\\test_feature.py"):
            with self.subTest(path=path):
                result = _recover_safe_changed_path_scope(self.root, ("src/feature.py",), (path,))
                self.assertEqual(result.scope_recovery_status, "blocked")

    def test_misleading_component_names_and_git_metadata_are_blocked(self):
        for path in ("contest/test_feature.py", "tests_backup/test_feature.py", ".git/config", "tests/.git/config"):
            with self.subTest(path=path):
                result = self._recover(path)
                self.assertEqual(result.scope_recovery_status, "blocked")

    def test_symlink_escape_is_blocked(self):
        outside = self.root.parent / "outside.py"
        outside.write_text("x\n", encoding="utf-8")
        link = self.root / "tests" / "escape.py"
        link.parent.mkdir(parents=True)
        link.symlink_to(outside)
        result = _recover_safe_changed_path_scope(self.root, ("src/feature.py",), ("tests/escape.py",))
        self.assertEqual(result.scope_recovery_status, "blocked")

    def test_mixed_safe_and_unsafe_set_is_atomically_blocked(self):
        result = self._recover("tests/test_feature.py", "src/foo.py")
        self.assertEqual(result.scope_recovery_status, "blocked")
        self.assertEqual(result.auto_expanded_paths, ())
        self.assertEqual(result.original_unexpected_changed_files, ("src/foo.py", "tests/test_feature.py"))


if __name__ == "__main__":
    unittest.main()
