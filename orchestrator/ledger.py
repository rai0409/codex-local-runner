from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_LEDGER_DB_PATH = "state/jobs.db"


def _connect(db_path: str | Path = DEFAULT_LEDGER_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            repo TEXT NOT NULL,
            task_type TEXT NOT NULL,
            provider TEXT NOT NULL,
            accepted_status TEXT NOT NULL,
            declared_category TEXT NOT NULL,
            observed_category TEXT NOT NULL,
            merge_eligible INTEGER NOT NULL,
            merge_gate_passed INTEGER NOT NULL,
            created_at TEXT NULL,
            request_path TEXT NOT NULL,
            result_path TEXT NOT NULL,
            rubric_path TEXT NULL,
            merge_gate_path TEXT NULL,
            classification_path TEXT NULL
        )
        """
    )


def record_job_evaluation(
    *,
    job_id: str,
    repo: str,
    task_type: str,
    provider: str,
    accepted_status: str,
    declared_category: str,
    observed_category: str,
    merge_eligible: bool,
    merge_gate_passed: bool,
    created_at: str | None,
    request_path: str,
    result_path: str,
    rubric_path: str | None,
    merge_gate_path: str | None,
    classification_path: str | None = None,
    db_path: str | Path = DEFAULT_LEDGER_DB_PATH,
) -> None:
    with _connect(db_path) as conn:
        _ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO jobs (
                job_id,
                repo,
                task_type,
                provider,
                accepted_status,
                declared_category,
                observed_category,
                merge_eligible,
                merge_gate_passed,
                created_at,
                request_path,
                result_path,
                rubric_path,
                merge_gate_path,
                classification_path
            ) VALUES (
                :job_id,
                :repo,
                :task_type,
                :provider,
                :accepted_status,
                :declared_category,
                :observed_category,
                :merge_eligible,
                :merge_gate_passed,
                :created_at,
                :request_path,
                :result_path,
                :rubric_path,
                :merge_gate_path,
                :classification_path
            )
            ON CONFLICT(job_id) DO UPDATE SET
                repo=excluded.repo,
                task_type=excluded.task_type,
                provider=excluded.provider,
                accepted_status=excluded.accepted_status,
                declared_category=excluded.declared_category,
                observed_category=excluded.observed_category,
                merge_eligible=excluded.merge_eligible,
                merge_gate_passed=excluded.merge_gate_passed,
                created_at=excluded.created_at,
                request_path=excluded.request_path,
                result_path=excluded.result_path,
                rubric_path=excluded.rubric_path,
                merge_gate_path=excluded.merge_gate_path,
                classification_path=excluded.classification_path
            """,
            {
                "job_id": str(job_id).strip(),
                "repo": str(repo).strip(),
                "task_type": str(task_type).strip(),
                "provider": str(provider).strip(),
                "accepted_status": str(accepted_status).strip(),
                "declared_category": str(declared_category).strip(),
                "observed_category": str(observed_category).strip(),
                "merge_eligible": 1 if merge_eligible else 0,
                "merge_gate_passed": 1 if merge_gate_passed else 0,
                "created_at": created_at,
                "request_path": str(request_path),
                "result_path": str(result_path),
                "rubric_path": rubric_path,
                "merge_gate_path": merge_gate_path,
                "classification_path": classification_path,
            },
        )
        conn.commit()
