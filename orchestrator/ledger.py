from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_LEDGER_DB_PATH = "state/jobs.db"


def _connect(db_path: str | Path = DEFAULT_LEDGER_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _connect_readonly(db_path: str | Path = DEFAULT_LEDGER_DB_PATH) -> sqlite3.Connection | None:
    path = Path(db_path)
    if not path.exists():
        return None
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS execution_targets (
            candidate_idempotency_key TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            target_ref TEXT NOT NULL,
            source_sha TEXT NOT NULL,
            base_sha TEXT NOT NULL,
            created_at TEXT NULL,
            declared_category TEXT NULL,
            observed_category TEXT NULL,
            accepted_status TEXT NULL,
            merge_gate_passed INTEGER NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS merge_receipts (
            receipt_id TEXT PRIMARY KEY,
            attempt_identity_key TEXT UNIQUE NOT NULL,
            candidate_idempotency_key TEXT NOT NULL,
            job_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            target_ref TEXT NOT NULL,
            source_sha TEXT NOT NULL,
            base_sha TEXT NOT NULL,
            merge_attempt_status TEXT NOT NULL,
            merge_attempted_at TEXT NULL,
            merge_result_sha TEXT NULL,
            merge_error TEXT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS merge_executions (
            candidate_idempotency_key TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            target_ref TEXT NOT NULL,
            source_sha TEXT NOT NULL,
            base_sha TEXT NOT NULL,
            execution_status TEXT NOT NULL,
            executed_at TEXT NULL,
            pre_merge_sha TEXT NULL,
            post_merge_sha TEXT NULL,
            merge_result_sha TEXT NULL,
            merge_error TEXT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rollback_traces (
            rollback_trace_id TEXT PRIMARY KEY,
            candidate_idempotency_key TEXT UNIQUE NOT NULL,
            job_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            target_ref TEXT NOT NULL,
            source_sha TEXT NOT NULL,
            base_sha TEXT NOT NULL,
            merge_execution_status TEXT NOT NULL,
            merge_execution_executed_at TEXT NULL,
            pre_merge_sha TEXT NULL,
            post_merge_sha TEXT NULL,
            merge_result_sha TEXT NULL,
            merge_receipt_id TEXT NULL,
            rollback_eligible INTEGER NOT NULL,
            ineligible_reason TEXT NULL,
            recorded_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rollback_executions (
            rollback_trace_id TEXT PRIMARY KEY,
            candidate_idempotency_key TEXT NOT NULL,
            job_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            target_ref TEXT NOT NULL,
            pre_merge_sha TEXT NOT NULL,
            post_merge_sha TEXT NOT NULL,
            execution_status TEXT NOT NULL,
            attempted_at TEXT NULL,
            current_head_sha TEXT NULL,
            rollback_result_sha TEXT NULL,
            rollback_error TEXT NULL,
            consistency_check_passed INTEGER NOT NULL,
            recorded_at TEXT NOT NULL
        )
        """
    )


def build_candidate_idempotency_key(
    *,
    repo: str,
    target_ref: str,
    source_sha: str,
    base_sha: str,
) -> str:
    identity = "\n".join(
        [
            str(repo).strip(),
            str(target_ref).strip(),
            str(source_sha).strip(),
            str(base_sha).strip(),
        ]
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def build_merge_attempt_identity_key(
    *,
    candidate_idempotency_key: str,
    merge_attempt_status: str,
    merge_attempted_at: str | None,
    merge_result_sha: str | None,
    merge_error: str | None,
) -> str:
    identity = "\n".join(
        [
            str(candidate_idempotency_key).strip(),
            str(merge_attempt_status).strip(),
            str(merge_attempted_at or "").strip(),
            str(merge_result_sha or "").strip(),
            str(merge_error or "").strip(),
        ]
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def build_merge_receipt_id(*, attempt_identity_key: str) -> str:
    material = "receipt\n" + str(attempt_identity_key).strip()
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def build_rollback_trace_id(
    *,
    candidate_idempotency_key: str,
    pre_merge_sha: str | None,
    post_merge_sha: str | None,
) -> str:
    identity = "\n".join(
        [
            "rollback_trace",
            str(candidate_idempotency_key).strip(),
            str(pre_merge_sha or "").strip(),
            str(post_merge_sha or "").strip(),
        ]
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


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


def record_execution_target(
    *,
    job_id: str,
    repo: str,
    target_ref: str,
    source_sha: str,
    base_sha: str,
    created_at: str | None,
    declared_category: str | None = None,
    observed_category: str | None = None,
    accepted_status: str | None = None,
    merge_gate_passed: bool | None = None,
    db_path: str | Path = DEFAULT_LEDGER_DB_PATH,
) -> str:
    candidate_idempotency_key = build_candidate_idempotency_key(
        repo=repo,
        target_ref=target_ref,
        source_sha=source_sha,
        base_sha=base_sha,
    )
    with _connect(db_path) as conn:
        _ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO execution_targets (
                candidate_idempotency_key,
                job_id,
                repo,
                target_ref,
                source_sha,
                base_sha,
                created_at,
                declared_category,
                observed_category,
                accepted_status,
                merge_gate_passed
            ) VALUES (
                :candidate_idempotency_key,
                :job_id,
                :repo,
                :target_ref,
                :source_sha,
                :base_sha,
                :created_at,
                :declared_category,
                :observed_category,
                :accepted_status,
                :merge_gate_passed
            )
            ON CONFLICT(candidate_idempotency_key) DO UPDATE SET
                job_id=excluded.job_id,
                repo=excluded.repo,
                target_ref=excluded.target_ref,
                source_sha=excluded.source_sha,
                base_sha=excluded.base_sha,
                created_at=excluded.created_at,
                declared_category=excluded.declared_category,
                observed_category=excluded.observed_category,
                accepted_status=excluded.accepted_status,
                merge_gate_passed=excluded.merge_gate_passed
            """,
            {
                "candidate_idempotency_key": candidate_idempotency_key,
                "job_id": str(job_id).strip(),
                "repo": str(repo).strip(),
                "target_ref": str(target_ref).strip(),
                "source_sha": str(source_sha).strip(),
                "base_sha": str(base_sha).strip(),
                "created_at": created_at,
                "declared_category": (
                    str(declared_category).strip() if declared_category is not None else None
                ),
                "observed_category": (
                    str(observed_category).strip() if observed_category is not None else None
                ),
                "accepted_status": (
                    str(accepted_status).strip() if accepted_status is not None else None
                ),
                "merge_gate_passed": (
                    None if merge_gate_passed is None else (1 if merge_gate_passed else 0)
                ),
            },
        )
        conn.commit()
    return candidate_idempotency_key


def record_merge_attempt_receipt(
    *,
    job_id: str,
    repo: str,
    target_ref: str,
    source_sha: str,
    base_sha: str,
    merge_attempt_status: str,
    merge_attempted_at: str | None,
    merge_result_sha: str | None,
    merge_error: str | None,
    db_path: str | Path = DEFAULT_LEDGER_DB_PATH,
) -> str:
    normalized_repo = str(repo).strip()
    normalized_target_ref = str(target_ref).strip()
    normalized_source_sha = str(source_sha).strip()
    normalized_base_sha = str(base_sha).strip()
    normalized_status = str(merge_attempt_status).strip()
    normalized_attempted_at = (
        str(merge_attempted_at).strip() if merge_attempted_at is not None else None
    )
    normalized_result_sha = str(merge_result_sha).strip() if merge_result_sha is not None else None
    normalized_error = str(merge_error).strip() if merge_error is not None else None

    if not normalized_repo:
        raise ValueError("repo is required for merge receipt linkage")
    if not normalized_target_ref:
        raise ValueError("target_ref is required for merge receipt linkage")
    if not normalized_source_sha:
        raise ValueError("source_sha is required for merge receipt linkage")
    if not normalized_base_sha:
        raise ValueError("base_sha is required for merge receipt linkage")
    if not normalized_status:
        raise ValueError("merge_attempt_status is required for merge receipt persistence")

    candidate_idempotency_key = build_candidate_idempotency_key(
        repo=normalized_repo,
        target_ref=normalized_target_ref,
        source_sha=normalized_source_sha,
        base_sha=normalized_base_sha,
    )
    attempt_identity_key = build_merge_attempt_identity_key(
        candidate_idempotency_key=candidate_idempotency_key,
        merge_attempt_status=normalized_status,
        merge_attempted_at=normalized_attempted_at,
        merge_result_sha=normalized_result_sha,
        merge_error=normalized_error,
    )
    receipt_id = build_merge_receipt_id(attempt_identity_key=attempt_identity_key)

    with _connect(db_path) as conn:
        _ensure_schema(conn)
        linked_row = conn.execute(
            """
            SELECT candidate_idempotency_key
            FROM execution_targets
            WHERE candidate_idempotency_key = :candidate_idempotency_key
              AND repo = :repo
              AND target_ref = :target_ref
              AND source_sha = :source_sha
              AND base_sha = :base_sha
            LIMIT 1
            """,
            {
                "candidate_idempotency_key": candidate_idempotency_key,
                "repo": normalized_repo,
                "target_ref": normalized_target_ref,
                "source_sha": normalized_source_sha,
                "base_sha": normalized_base_sha,
            },
        ).fetchone()
        if linked_row is None:
            raise ValueError(
                "execution target linkage not found for merge receipt persistence"
            )

        conn.execute(
            """
            INSERT INTO merge_receipts (
                receipt_id,
                attempt_identity_key,
                candidate_idempotency_key,
                job_id,
                repo,
                target_ref,
                source_sha,
                base_sha,
                merge_attempt_status,
                merge_attempted_at,
                merge_result_sha,
                merge_error
            ) VALUES (
                :receipt_id,
                :attempt_identity_key,
                :candidate_idempotency_key,
                :job_id,
                :repo,
                :target_ref,
                :source_sha,
                :base_sha,
                :merge_attempt_status,
                :merge_attempted_at,
                :merge_result_sha,
                :merge_error
            )
            ON CONFLICT(attempt_identity_key) DO UPDATE SET
                receipt_id=excluded.receipt_id,
                candidate_idempotency_key=excluded.candidate_idempotency_key,
                job_id=excluded.job_id,
                repo=excluded.repo,
                target_ref=excluded.target_ref,
                source_sha=excluded.source_sha,
                base_sha=excluded.base_sha,
                merge_attempt_status=excluded.merge_attempt_status,
                merge_attempted_at=excluded.merge_attempted_at,
                merge_result_sha=excluded.merge_result_sha,
                merge_error=excluded.merge_error
            """,
            {
                "receipt_id": receipt_id,
                "attempt_identity_key": attempt_identity_key,
                "candidate_idempotency_key": candidate_idempotency_key,
                "job_id": str(job_id).strip(),
                "repo": normalized_repo,
                "target_ref": normalized_target_ref,
                "source_sha": normalized_source_sha,
                "base_sha": normalized_base_sha,
                "merge_attempt_status": normalized_status,
                "merge_attempted_at": normalized_attempted_at,
                "merge_result_sha": normalized_result_sha,
                "merge_error": normalized_error,
            },
        )
        conn.commit()
    return receipt_id


def record_merge_execution_outcome(
    *,
    job_id: str,
    repo: str,
    target_ref: str,
    source_sha: str,
    base_sha: str,
    execution_status: str,
    executed_at: str | None,
    pre_merge_sha: str | None,
    post_merge_sha: str | None,
    merge_result_sha: str | None,
    merge_error: str | None,
    db_path: str | Path = DEFAULT_LEDGER_DB_PATH,
) -> str:
    normalized_repo = str(repo).strip()
    normalized_target_ref = str(target_ref).strip()
    normalized_source_sha = str(source_sha).strip()
    normalized_base_sha = str(base_sha).strip()
    normalized_status = str(execution_status).strip()

    if not normalized_repo:
        raise ValueError("repo is required for merge execution persistence")
    if not normalized_target_ref:
        raise ValueError("target_ref is required for merge execution persistence")
    if not normalized_source_sha:
        raise ValueError("source_sha is required for merge execution persistence")
    if not normalized_base_sha:
        raise ValueError("base_sha is required for merge execution persistence")
    if not normalized_status:
        raise ValueError("execution_status is required for merge execution persistence")

    candidate_idempotency_key = build_candidate_idempotency_key(
        repo=normalized_repo,
        target_ref=normalized_target_ref,
        source_sha=normalized_source_sha,
        base_sha=normalized_base_sha,
    )

    with _connect(db_path) as conn:
        _ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO merge_executions (
                candidate_idempotency_key,
                job_id,
                repo,
                target_ref,
                source_sha,
                base_sha,
                execution_status,
                executed_at,
                pre_merge_sha,
                post_merge_sha,
                merge_result_sha,
                merge_error
            ) VALUES (
                :candidate_idempotency_key,
                :job_id,
                :repo,
                :target_ref,
                :source_sha,
                :base_sha,
                :execution_status,
                :executed_at,
                :pre_merge_sha,
                :post_merge_sha,
                :merge_result_sha,
                :merge_error
            )
            ON CONFLICT(candidate_idempotency_key) DO UPDATE SET
                job_id=excluded.job_id,
                repo=excluded.repo,
                target_ref=excluded.target_ref,
                source_sha=excluded.source_sha,
                base_sha=excluded.base_sha,
                execution_status=excluded.execution_status,
                executed_at=excluded.executed_at,
                pre_merge_sha=excluded.pre_merge_sha,
                post_merge_sha=excluded.post_merge_sha,
                merge_result_sha=excluded.merge_result_sha,
                merge_error=excluded.merge_error
            """,
            {
                "candidate_idempotency_key": candidate_idempotency_key,
                "job_id": str(job_id).strip(),
                "repo": normalized_repo,
                "target_ref": normalized_target_ref,
                "source_sha": normalized_source_sha,
                "base_sha": normalized_base_sha,
                "execution_status": normalized_status,
                "executed_at": (
                    str(executed_at).strip() if executed_at is not None else None
                ),
                "pre_merge_sha": (
                    str(pre_merge_sha).strip() if pre_merge_sha is not None else None
                ),
                "post_merge_sha": (
                    str(post_merge_sha).strip() if post_merge_sha is not None else None
                ),
                "merge_result_sha": (
                    str(merge_result_sha).strip() if merge_result_sha is not None else None
                ),
                "merge_error": str(merge_error).strip() if merge_error is not None else None,
            },
        )
        conn.commit()
    return candidate_idempotency_key


def get_execution_target_by_identity(
    *,
    repo: str,
    target_ref: str,
    source_sha: str,
    base_sha: str,
    db_path: str | Path = DEFAULT_LEDGER_DB_PATH,
) -> dict[str, Any] | None:
    conn = _connect_readonly(db_path)
    if conn is None:
        return None
    with conn:
        try:
            row = conn.execute(
                """
                SELECT *
                FROM execution_targets
                WHERE repo = :repo
                  AND target_ref = :target_ref
                  AND source_sha = :source_sha
                  AND base_sha = :base_sha
                LIMIT 1
                """,
                {
                    "repo": str(repo).strip(),
                    "target_ref": str(target_ref).strip(),
                    "source_sha": str(source_sha).strip(),
                    "base_sha": str(base_sha).strip(),
                },
            ).fetchone()
        except sqlite3.OperationalError:
            return None
    if row is None:
        return None
    return _row_to_dict(row)


def get_merge_execution_by_candidate_idempotency_key(
    candidate_idempotency_key: str,
    *,
    db_path: str | Path = DEFAULT_LEDGER_DB_PATH,
) -> dict[str, Any] | None:
    conn = _connect_readonly(db_path)
    if conn is None:
        return None
    with conn:
        try:
            row = conn.execute(
                """
                SELECT *
                FROM merge_executions
                WHERE candidate_idempotency_key = ?
                LIMIT 1
                """,
                (str(candidate_idempotency_key).strip(),),
            ).fetchone()
        except sqlite3.OperationalError:
            return None
    if row is None:
        return None
    return _row_to_dict(row)


def record_rollback_traceability_for_candidate(
    *,
    candidate_idempotency_key: str,
    merge_receipt_id: str | None = None,
    db_path: str | Path = DEFAULT_LEDGER_DB_PATH,
) -> dict[str, Any]:
    normalized_candidate_key = str(candidate_idempotency_key).strip()
    if not normalized_candidate_key:
        raise ValueError("candidate_idempotency_key is required for rollback traceability")

    normalized_receipt_id = (
        str(merge_receipt_id).strip() if merge_receipt_id is not None else None
    )
    if normalized_receipt_id == "":
        normalized_receipt_id = None

    with _connect(db_path) as conn:
        _ensure_schema(conn)
        execution_target_row = conn.execute(
            """
            SELECT *
            FROM execution_targets
            WHERE candidate_idempotency_key = :candidate_idempotency_key
            LIMIT 1
            """,
            {"candidate_idempotency_key": normalized_candidate_key},
        ).fetchone()
        if execution_target_row is None:
            raise ValueError("execution target linkage not found for rollback traceability")

        merge_execution_row = conn.execute(
            """
            SELECT *
            FROM merge_executions
            WHERE candidate_idempotency_key = :candidate_idempotency_key
            LIMIT 1
            """,
            {"candidate_idempotency_key": normalized_candidate_key},
        ).fetchone()
        if merge_execution_row is None:
            raise ValueError("merge execution outcome not found for rollback traceability")

        merge_execution_status = str(merge_execution_row["execution_status"]).strip()
        pre_merge_sha = (
            str(merge_execution_row["pre_merge_sha"]).strip()
            if merge_execution_row["pre_merge_sha"] is not None
            else None
        )
        post_merge_sha = (
            str(merge_execution_row["post_merge_sha"]).strip()
            if merge_execution_row["post_merge_sha"] is not None
            else None
        )
        merge_result_sha = (
            str(merge_execution_row["merge_result_sha"]).strip()
            if merge_execution_row["merge_result_sha"] is not None
            else None
        )
        merge_execution_executed_at = (
            str(merge_execution_row["executed_at"]).strip()
            if merge_execution_row["executed_at"] is not None
            else None
        )

        rollback_eligible = False
        ineligible_reason: str | None = None
        if merge_execution_status != "succeeded":
            ineligible_reason = "merge_execution_not_succeeded"
        elif not pre_merge_sha or not post_merge_sha:
            ineligible_reason = "merge_execution_linkage_incomplete"
        else:
            rollback_eligible = True

        rollback_trace_id = build_rollback_trace_id(
            candidate_idempotency_key=normalized_candidate_key,
            pre_merge_sha=pre_merge_sha,
            post_merge_sha=post_merge_sha,
        )
        recorded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

        conn.execute(
            """
            INSERT INTO rollback_traces (
                rollback_trace_id,
                candidate_idempotency_key,
                job_id,
                repo,
                target_ref,
                source_sha,
                base_sha,
                merge_execution_status,
                merge_execution_executed_at,
                pre_merge_sha,
                post_merge_sha,
                merge_result_sha,
                merge_receipt_id,
                rollback_eligible,
                ineligible_reason,
                recorded_at
            ) VALUES (
                :rollback_trace_id,
                :candidate_idempotency_key,
                :job_id,
                :repo,
                :target_ref,
                :source_sha,
                :base_sha,
                :merge_execution_status,
                :merge_execution_executed_at,
                :pre_merge_sha,
                :post_merge_sha,
                :merge_result_sha,
                :merge_receipt_id,
                :rollback_eligible,
                :ineligible_reason,
                :recorded_at
            )
            ON CONFLICT(candidate_idempotency_key) DO UPDATE SET
                rollback_trace_id=excluded.rollback_trace_id,
                job_id=excluded.job_id,
                repo=excluded.repo,
                target_ref=excluded.target_ref,
                source_sha=excluded.source_sha,
                base_sha=excluded.base_sha,
                merge_execution_status=excluded.merge_execution_status,
                merge_execution_executed_at=excluded.merge_execution_executed_at,
                pre_merge_sha=excluded.pre_merge_sha,
                post_merge_sha=excluded.post_merge_sha,
                merge_result_sha=excluded.merge_result_sha,
                merge_receipt_id=excluded.merge_receipt_id,
                rollback_eligible=excluded.rollback_eligible,
                ineligible_reason=excluded.ineligible_reason,
                recorded_at=excluded.recorded_at
            """,
            {
                "rollback_trace_id": rollback_trace_id,
                "candidate_idempotency_key": normalized_candidate_key,
                "job_id": str(execution_target_row["job_id"]).strip(),
                "repo": str(execution_target_row["repo"]).strip(),
                "target_ref": str(execution_target_row["target_ref"]).strip(),
                "source_sha": str(execution_target_row["source_sha"]).strip(),
                "base_sha": str(execution_target_row["base_sha"]).strip(),
                "merge_execution_status": merge_execution_status,
                "merge_execution_executed_at": merge_execution_executed_at,
                "pre_merge_sha": pre_merge_sha,
                "post_merge_sha": post_merge_sha,
                "merge_result_sha": merge_result_sha,
                "merge_receipt_id": normalized_receipt_id,
                "rollback_eligible": 1 if rollback_eligible else 0,
                "ineligible_reason": ineligible_reason,
                "recorded_at": recorded_at,
            },
        )
        row = conn.execute(
            """
            SELECT *
            FROM rollback_traces
            WHERE candidate_idempotency_key = :candidate_idempotency_key
            LIMIT 1
            """,
            {"candidate_idempotency_key": normalized_candidate_key},
        ).fetchone()
        conn.commit()

    if row is None:
        raise RuntimeError("rollback trace write did not produce a row")
    return _row_to_dict(row)


def get_rollback_trace_by_job_id(
    job_id: str,
    *,
    db_path: str | Path = DEFAULT_LEDGER_DB_PATH,
) -> dict[str, Any] | None:
    conn = _connect_readonly(db_path)
    if conn is None:
        return None
    with conn:
        try:
            row = conn.execute(
                """
                SELECT *
                FROM rollback_traces
                WHERE job_id = ?
                ORDER BY recorded_at DESC, rowid DESC
                LIMIT 1
                """,
                (str(job_id).strip(),),
            ).fetchone()
        except sqlite3.OperationalError:
            return None
    if row is None:
        return None
    return _row_to_dict(row)


def get_rollback_trace_by_id(
    rollback_trace_id: str,
    *,
    db_path: str | Path = DEFAULT_LEDGER_DB_PATH,
) -> dict[str, Any] | None:
    conn = _connect_readonly(db_path)
    if conn is None:
        return None
    with conn:
        try:
            row = conn.execute(
                """
                SELECT *
                FROM rollback_traces
                WHERE rollback_trace_id = ?
                LIMIT 1
                """,
                (str(rollback_trace_id).strip(),),
            ).fetchone()
        except sqlite3.OperationalError:
            return None
    if row is None:
        return None
    return _row_to_dict(row)


def record_rollback_execution_outcome(
    *,
    rollback_trace_id: str,
    execution_status: str,
    attempted_at: str | None,
    current_head_sha: str | None,
    rollback_result_sha: str | None,
    rollback_error: str | None,
    consistency_check_passed: bool,
    db_path: str | Path = DEFAULT_LEDGER_DB_PATH,
) -> dict[str, Any]:
    normalized_trace_id = str(rollback_trace_id).strip()
    normalized_execution_status = str(execution_status).strip()
    if not normalized_trace_id:
        raise ValueError("rollback_trace_id is required for rollback execution persistence")
    if not normalized_execution_status:
        raise ValueError("execution_status is required for rollback execution persistence")

    with _connect(db_path) as conn:
        _ensure_schema(conn)
        trace_row = conn.execute(
            """
            SELECT *
            FROM rollback_traces
            WHERE rollback_trace_id = :rollback_trace_id
            LIMIT 1
            """,
            {"rollback_trace_id": normalized_trace_id},
        ).fetchone()
        if trace_row is None:
            raise ValueError("rollback trace linkage not found for rollback execution persistence")

        recorded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        conn.execute(
            """
            INSERT INTO rollback_executions (
                rollback_trace_id,
                candidate_idempotency_key,
                job_id,
                repo,
                target_ref,
                pre_merge_sha,
                post_merge_sha,
                execution_status,
                attempted_at,
                current_head_sha,
                rollback_result_sha,
                rollback_error,
                consistency_check_passed,
                recorded_at
            ) VALUES (
                :rollback_trace_id,
                :candidate_idempotency_key,
                :job_id,
                :repo,
                :target_ref,
                :pre_merge_sha,
                :post_merge_sha,
                :execution_status,
                :attempted_at,
                :current_head_sha,
                :rollback_result_sha,
                :rollback_error,
                :consistency_check_passed,
                :recorded_at
            )
            ON CONFLICT(rollback_trace_id) DO UPDATE SET
                candidate_idempotency_key=excluded.candidate_idempotency_key,
                job_id=excluded.job_id,
                repo=excluded.repo,
                target_ref=excluded.target_ref,
                pre_merge_sha=excluded.pre_merge_sha,
                post_merge_sha=excluded.post_merge_sha,
                execution_status=excluded.execution_status,
                attempted_at=excluded.attempted_at,
                current_head_sha=excluded.current_head_sha,
                rollback_result_sha=excluded.rollback_result_sha,
                rollback_error=excluded.rollback_error,
                consistency_check_passed=excluded.consistency_check_passed,
                recorded_at=excluded.recorded_at
            """,
            {
                "rollback_trace_id": normalized_trace_id,
                "candidate_idempotency_key": str(trace_row["candidate_idempotency_key"]).strip(),
                "job_id": str(trace_row["job_id"]).strip(),
                "repo": str(trace_row["repo"]).strip(),
                "target_ref": str(trace_row["target_ref"]).strip(),
                "pre_merge_sha": str(trace_row["pre_merge_sha"]).strip(),
                "post_merge_sha": str(trace_row["post_merge_sha"]).strip(),
                "execution_status": normalized_execution_status,
                "attempted_at": str(attempted_at).strip() if attempted_at is not None else None,
                "current_head_sha": (
                    str(current_head_sha).strip() if current_head_sha is not None else None
                ),
                "rollback_result_sha": (
                    str(rollback_result_sha).strip() if rollback_result_sha is not None else None
                ),
                "rollback_error": str(rollback_error).strip() if rollback_error is not None else None,
                "consistency_check_passed": 1 if consistency_check_passed else 0,
                "recorded_at": recorded_at,
            },
        )
        row = conn.execute(
            """
            SELECT *
            FROM rollback_executions
            WHERE rollback_trace_id = :rollback_trace_id
            LIMIT 1
            """,
            {"rollback_trace_id": normalized_trace_id},
        ).fetchone()
        conn.commit()

    if row is None:
        raise RuntimeError("rollback execution write did not produce a row")
    return _row_to_dict(row)


def get_rollback_execution_by_trace_id(
    rollback_trace_id: str,
    *,
    db_path: str | Path = DEFAULT_LEDGER_DB_PATH,
) -> dict[str, Any] | None:
    conn = _connect_readonly(db_path)
    if conn is None:
        return None
    with conn:
        try:
            row = conn.execute(
                """
                SELECT *
                FROM rollback_executions
                WHERE rollback_trace_id = ?
                LIMIT 1
                """,
                (str(rollback_trace_id).strip(),),
            ).fetchone()
        except sqlite3.OperationalError:
            return None
    if row is None:
        return None
    return _row_to_dict(row)


def get_rollback_execution_by_job_id(
    job_id: str,
    *,
    db_path: str | Path = DEFAULT_LEDGER_DB_PATH,
) -> dict[str, Any] | None:
    conn = _connect_readonly(db_path)
    if conn is None:
        return None
    with conn:
        try:
            row = conn.execute(
                """
                SELECT *
                FROM rollback_executions
                WHERE job_id = ?
                ORDER BY recorded_at DESC, rowid DESC
                LIMIT 1
                """,
                (str(job_id).strip(),),
            ).fetchone()
        except sqlite3.OperationalError:
            return None
    if row is None:
        return None
    return _row_to_dict(row)


def get_job_by_id(
    job_id: str, db_path: str | Path = DEFAULT_LEDGER_DB_PATH
) -> dict[str, Any] | None:
    conn = _connect_readonly(db_path)
    if conn is None:
        return None
    with conn:
        try:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        except sqlite3.OperationalError:
            return None
    if row is None:
        return None
    return _row_to_dict(row)


def get_latest_job(db_path: str | Path = DEFAULT_LEDGER_DB_PATH) -> dict[str, Any] | None:
    conn = _connect_readonly(db_path)
    if conn is None:
        return None
    with conn:
        try:
            row = conn.execute(
                """
                SELECT *
                FROM jobs
                ORDER BY
                    CASE WHEN created_at IS NULL THEN 1 ELSE 0 END ASC,
                    created_at DESC,
                    rowid DESC
                LIMIT 1
                """
            ).fetchone()
        except sqlite3.OperationalError:
            return None
    if row is None:
        return None
    return _row_to_dict(row)


def list_recorded_jobs(
    *,
    db_path: str | Path = DEFAULT_LEDGER_DB_PATH,
    limit: int | None = None,
) -> tuple[dict[str, Any], ...]:
    conn = _connect_readonly(db_path)
    if conn is None:
        return ()

    query = """
        SELECT *
        FROM jobs
        ORDER BY
            CASE WHEN created_at IS NULL THEN 1 ELSE 0 END ASC,
            created_at DESC,
            rowid DESC
    """
    params: tuple[Any, ...] = ()
    if limit is not None:
        query += "\nLIMIT ?"
        params = (int(limit),)

    with conn:
        try:
            rows = conn.execute(query, params).fetchall()
        except sqlite3.OperationalError:
            return ()

    return tuple(_row_to_dict(row) for row in rows)
