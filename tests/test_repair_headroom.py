from automation.orchestration.repair_headroom import repair_headroom_evidence


def test_headroom_evidence_is_deterministic_and_diagnostic_only():
    paths = ("alembic/versions/1_x.py", "packages/common/src/model.py", "apps/x/tests/test_x.py")
    first = repair_headroom_evidence(task_id="task", task_index=1, allowed_changed_paths=paths, max_changed_files=18, min_repair_headroom=2)
    second = repair_headroom_evidence(task_id="task", task_index=1, allowed_changed_paths=paths, max_changed_files=18, min_repair_headroom=2)
    assert first == second
    assert first["repair_headroom"] == 15
    assert first["migration_present"] is True
    assert first["test_path_count"] == 1
    assert "allowed" not in first and "blocked" not in first


def test_headroom_boundary_math_for_18_path_profile():
    for count, expected in ((18, 0), (17, 1), (16, 2), (9, 9), (19, -1)):
        evidence = repair_headroom_evidence(task_id="task", task_index=0, allowed_changed_paths=tuple(f"src/{i}.py" for i in range(count)), max_changed_files=18, min_repair_headroom=2)
        assert evidence["repair_headroom"] == expected
        assert (evidence["repair_headroom"] >= evidence["min_repair_headroom"]) is (count <= 16)
