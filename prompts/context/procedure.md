# codex-local-runner 手順書 — Prompt145 runner実行Runbook

## 0. 目的

この手順書は、Prompt144完了後に Prompt145 を runner 経由で実行するための手順をまとめる。

重要:
- この手順書には Prompt145 の全文は入れない。
- Prompt145全文は /tmp/codex-local-runner-intake/prompt145_source.md に保存する。
- この手順書では短縮例だけを示す。
- 実行時は prompt145_source.md の全文を prompt145_intake.json に埋め込む。

---

## 1. 現在の安全checkpoint

Prompt144完了地点:

    checkpoint-prompt144-candidate-safety-ready

戻し方:

    cd /home/rai/codex-local-runner
    git reset --hard checkpoint-prompt144-candidate-safety-ready

このcheckpointの意味:
- Prompt144 live 実行成功
- candidate safety fields 実装済み
- attempted=0 / completed=0 維持
- actual invocation なし
- new executor なし
- GitHub mutation なし
- py_compile 成功

---

## 2. Prompt145の目的

Prompt145の目的:

    Prompt144で candidate_safety_status=callable_candidate_safe になった場合だけ、
    既存call pathを1回だけ実際に呼ぶ。

Prompt145で初めて許可するもの:

    attempted=1

ただし、以下の場合だけ:

    実際に既存mapped call pathを1回だけ呼んだ場合

Prompt145で禁止するもの:

    completed=1
    max-two-launch
    second launch
    third launch
    loop
    retry loop
    daemon
    scheduler
    sleep loop
    queue drain
    new browser executor
    new Codex executor
    new ledger persistence
    GitHub mutation
    PR作成
    PR merge

completed=1 は Prompt146 で扱う。

---

## 3. Prompt145 sourceファイルを作る

Prompt145全文は長いため、この手順書内には全文を入れない。

次のように、別ファイルに保存する。

    cd /home/rai/codex-local-runner
    mkdir -p /tmp/codex-local-runner-intake

    cat > /tmp/codex-local-runner-intake/prompt145_source.md <<'PROMPT145'
    Prompt145 — execute exactly one bounded existing invocation only when Prompt144 candidate is safe / attempted may become 1 / completed remains 0

    Repository:
      /home/rai/codex-local-runner

    Read first:
      prompts/context/roadmap.md
      prompts/context/current_architecture_constraints.md
      prompts/context/pr_history_index.md
      prompts/context/procedure.md

    Edit only:
      automation/orchestration/planned_execution_runner.py

    Goal:
      Implement exactly one bounded existing invocation bridge for one_bounded_launch.

    Strict rules:
      attempted may become 1 only if a real selected existing mapped call path is actually invoked.
      completed must remain 0 in all Prompt145 branches.
      Reusing an already-built state object is not an actual invocation.
      Observing readiness is not an actual invocation.
      Mapping a state_ref is not an actual invocation.

    Do not add:
      completed=1
      max-two-launch execution
      second launch
      loop
      retry loop
      daemon
      scheduler
      sleep loop
      queue drain
      new browser executor
      new Codex executor
      new ledger persistence
      GitHub mutation
      PR creation
      PR merge

    Validation:
      Run only:
        python -m py_compile automation/orchestration/planned_execution_runner.py

    Report:
      1. changed sections
      2. whether any mapped existing invocation was actually called
      3. invocation_attempt_status
      4. invocation_result_status
      5. execution_mode
      6. execution_ref
      7. execution_receipt_status
      8. attempted behavior
      9. confirmation completed remains 0
      10. py_compile result
      11. confirmation no max-two-launch/no second launch/no new executor/no daemon/no scheduler/no queue drain/no GitHub mutation/no tests
    PROMPT145

上は短縮例。
実際に使うときは、この PROMPT145 ブロック内を、ChatGPTが生成したPrompt145全文に置き換える。

---

## 4. prompt145_intake.json を作る

prompt145_source.md の全文を JSON に埋め込む。

    cd /home/rai/codex-local-runner
    mkdir -p /tmp/codex-local-runner-intake

    python - <<'PY'
    from pathlib import Path
    import json

    prompt_path = Path("/tmp/codex-local-runner-intake/prompt145_source.md")
    prompt = prompt_path.read_text(encoding="utf-8").strip()

    intake = {
        "project_id": "prompt145-one-bounded-existing-invocation",
        "objective": (
            "Execute the attached Prompt145 exactly: perform exactly one bounded existing invocation "
            "only when Prompt144 candidate safety gates are satisfied. attempted may become 1 only after "
            "a real selected mapped call path is invoked. completed must remain 0 in all Prompt145 branches.\n\n"
            "FULL PROMPT145:\n"
            + prompt
        ),
        "success_definition": (
            "Prompt145 adds a one-bounded existing invocation bridge in "
            "automation/orchestration/planned_execution_runner.py; py_compile passes; "
            "attempted becomes 1 only if a real existing mapped invocation occurs; "
            "completed remains 0; no max-two-launch, second launch, new executor, daemon, scheduler, "
            "queue drain, GitHub mutation, PR creation, PR merge, or tests are added."
        ),
        "constraints": [
            "Implement the FULL PROMPT145 text embedded in objective and acceptance_criteria.",
            "Edit only automation/orchestration/planned_execution_runner.py.",
            "Read prompts/context/roadmap.md.",
            "Read prompts/context/current_architecture_constraints.md.",
            "Read prompts/context/pr_history_index.md.",
            "Read prompts/context/procedure.md.",
            "Do not set completed=1.",
            "Keep completed=0 in all Prompt145 branches.",
            "Set attempted=1 only after a real selected mapped existing invocation call path is actually invoked.",
            "If only an existing state dict is reused, attempted must remain 0.",
            "If only readiness is observed, attempted must remain 0.",
            "Do not add max-two-launch execution.",
            "Do not add a second launch.",
            "Do not add a third launch.",
            "Do not add a loop or retry loop.",
            "Do not add a new browser executor.",
            "Do not add a new Codex executor.",
            "Do not add new ledger persistence mechanism.",
            "Do not add daemon, scheduler, sleep loop, or queue drain.",
            "Do not mutate GitHub.",
            "Do not create or merge PRs.",
            "Do not run tests.",
            "Run only python -m py_compile automation/orchestration/planned_execution_runner.py."
        ],
        "non_goals": [
            "Do not implement Prompt146 completed evidence evaluation.",
            "Do not implement completed=1.",
            "Do not implement Prompt147 launch_1/launch_2 preparation.",
            "Do not implement Prompt148 max-two rolling execution.",
            "Do not implement Prompt149 result JSON accounting fix.",
            "Do not implement ChatGPT internal connection.",
            "Do not implement bounded autonomous loop.",
            "Do not push to GitHub.",
            "Do not merge."
        ],
        "allowed_risk_level": "conservative",
        "target_repo": "codex-local-runner",
        "target_branch": "main",
        "requested_by": "rai",
        "relevant_paths": [
            "automation/orchestration/planned_execution_runner.py",
            "prompts/context/roadmap.md",
            "prompts/context/current_architecture_constraints.md",
            "prompts/context/pr_history_index.md",
            "prompts/context/procedure.md"
        ],
        "validation_commands": [
            "python -m py_compile automation/orchestration/planned_execution_runner.py"
        ],
        "requested_changes": [
            {
                "summary": "Prompt145 one bounded existing invocation bridge with attempted=1 only on real invocation and completed=0 fixed",
                "touched_files": [
                    "automation/orchestration/planned_execution_runner.py"
                ],
                "acceptance_criteria": [
                    "FULL PROMPT145 TO IMPLEMENT:\n" + prompt,
                    "Use Prompt144 candidate_safety_status and candidate_risk_flags as required gates.",
                    "Invoke at most one selected existing mapped call path.",
                    "Do not loop, retry, or fall through to a second action.",
                    "Set attempted=1 only after a real selected mapped invocation call path is actually invoked.",
                    "Keep attempted=0 if only an existing state dict is reused.",
                    "Keep attempted=0 if only readiness is observed.",
                    "Keep completed=0 in all Prompt145 branches.",
                    "Do not set completed=1.",
                    "Do not add max-two-launch execution.",
                    "Do not add second launch.",
                    "Do not add new executor.",
                    "Do not mutate GitHub.",
                    "Expose new/updated Prompt145 fields in compact summary, supporting truth refs, and final approved restart payload.",
                    "python -m py_compile automation/orchestration/planned_execution_runner.py passes."
                ],
                "validation_commands": [
                    "python -m py_compile automation/orchestration/planned_execution_runner.py"
                ],
                "forbidden_files": [
                    "automation/execution/codex_executor_adapter.py",
                    "automation/execution/codex_live_transport.py",
                    "orchestrator/codex_execution.py"
                ],
                "depends_on": [],
                "atomic": True
            }
        ]
    }

    out = Path("/tmp/codex-local-runner-intake/prompt145_intake.json")
    out.write_text(json.dumps(intake, ensure_ascii=False, indent=2), encoding="utf-8")

    print(out)
    print("prompt_chars=", len(prompt))
    print("intake_bytes=", out.stat().st_size)
    print("objective_has_prompt145=", "Prompt145" in intake["objective"])
    print("acceptance_has_prompt145=", "Prompt145" in intake["requested_changes"][0]["acceptance_criteria"][0])
    PY

期待:

    objective_has_prompt145= True
    acceptance_has_prompt145= True

---

## 5. planning artifactsを生成する

    cd /home/rai/codex-local-runner

    rm -rf /tmp/codex-local-runner-artifacts-prompt145
    mkdir -p /tmp/codex-local-runner-artifacts-prompt145

    python scripts/build_planning_artifacts.py \
      --intake /tmp/codex-local-runner-intake/prompt145_intake.json \
      --out-dir /tmp/codex-local-runner-artifacts-prompt145 \
      --repo-root /home/rai/codex-local-runner \
      --json

確認:

    python - <<'PY'
    from pathlib import Path
    import json

    p = Path("/tmp/codex-local-runner-artifacts-prompt145/pr_plan.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    text = json.dumps(data, ensure_ascii=False)

    print("has_prompt145=", "Prompt145" in text)
    print("prs=", len(data.get("prs", [])))
    print("title=", data.get("prs", [{}])[0].get("title"))
    print("touched_files=", data.get("prs", [{}])[0].get("touched_files"))
    print("validation_commands=", data.get("prs", [{}])[0].get("validation_commands"))
    PY

期待:

    has_prompt145=True
    prs=1
    touched_files=['automation/orchestration/planned_execution_runner.py']
    validation_commands=['python -m py_compile automation/orchestration/planned_execution_runner.py']

---

## 6. dry-run実行

    cd /home/rai/codex-local-runner

    rm -rf /tmp/codex-local-runner-dry-run-prompt145
    mkdir -p /tmp/codex-local-runner-dry-run-prompt145

    set +e

    timeout 180s python scripts/run_planned_execution.py \
      --artifacts-dir /tmp/codex-local-runner-artifacts-prompt145 \
      --out-dir /tmp/codex-local-runner-dry-run-prompt145 \
      --job-id prompt145-dry-run \
      --transport-mode dry-run \
      --json \
      > /tmp/codex-local-runner-dry-run-prompt145/stdout.json \
      2> /tmp/codex-local-runner-dry-run-prompt145/stderr.txt

    CODE=$?
    echo "exit_code=$CODE"

    echo
    echo "==== stderr ===="
    sed -n '1,160p' /tmp/codex-local-runner-dry-run-prompt145/stderr.txt

    echo
    echo "==== stdout summary ===="
    python - <<'PY'
    from pathlib import Path
    import json

    p = Path("/tmp/codex-local-runner-dry-run-prompt145/stdout.json")
    text = p.read_text(errors="ignore").strip()
    print("stdout_bytes=", len(text))

    if text:
        data = json.loads(text)
        print("job_id=", data.get("job_id"))
        print("run_status=", data.get("run_status"))
        print("processed_units=", len(data.get("pr_units", [])))
        print("next_action=", data.get("decision_summary", {}).get("next_action"))
    PY

成功条件:

    exit_code=0
    run_status=dry_run_completed
    processed_units=1

Prompt本文が入っているか確認:

    grep -RIn "Prompt145" /tmp/codex-local-runner-dry-run-prompt145 | head -n 20

---

## 7. live実行

dry-run成功後のみ実行する。

    cd /home/rai/codex-local-runner

    rm -rf /tmp/codex-local-runner-live-prompt145
    mkdir -p /tmp/codex-local-runner-live-prompt145

    set +e

    timeout 1200s python scripts/run_planned_execution.py \
      --artifacts-dir /tmp/codex-local-runner-artifacts-prompt145 \
      --out-dir /tmp/codex-local-runner-live-prompt145 \
      --job-id prompt145-live \
      --transport-mode live \
      --enable-live-transport \
      --repo-path /home/rai/codex-local-runner \
      --live-timeout-seconds 900 \
      --stop-on-failure \
      --json \
      > /tmp/codex-local-runner-live-prompt145/stdout.json \
      2> /tmp/codex-local-runner-live-prompt145/stderr.txt

    CODE=$?
    echo "exit_code=$CODE"

    echo
    echo "==== stderr ===="
    sed -n '1,220p' /tmp/codex-local-runner-live-prompt145/stderr.txt

    echo
    echo "==== stdout summary ===="
    python - <<'PY'
    from pathlib import Path
    import json

    p = Path("/tmp/codex-local-runner-live-prompt145/stdout.json")
    text = p.read_text(errors="ignore").strip()
    print("stdout_bytes=", len(text))

    if text:
        data = json.loads(text)
        print("job_id=", data.get("job_id"))
        print("run_status=", data.get("run_status"))
        print("processed_units=", len(data.get("pr_units", [])))
        print("next_action=", data.get("decision_summary", {}).get("next_action"))
    PY

    echo
    echo "==== repo status after Prompt145 live ===="
    git status --short

---

## 8. live後の確認

    cd /home/rai/codex-local-runner

    echo "==== py_compile ===="
    python -m py_compile automation/orchestration/planned_execution_runner.py

    echo
    echo "==== git status ===="
    git status --short

    echo
    echo "==== diff stat ===="
    git diff --stat

    echo
    echo "==== Prompt145 grep ===="
    grep -n -E "invocation_attempt_status|invocation_result_status|existing_invocation_call_path_invoked|prepared_only_invocation_not_callable|one_bounded_launch_attempted|one_bounded_launch_completed|candidate_safety_status|candidate_risk_flags" \
      automation/orchestration/planned_execution_runner.py | sed -n '1,260p'

    echo
    echo "==== codex stdout report ===="
    STDOUT_FILE=$(find /tmp/codex-local-runner-live-prompt145 -path '*execution_runs*/stdout.txt' -type f | sort | tail -n 1)
    echo "stdout_file=$STDOUT_FILE"
    sed -n '1,320p' "$STDOUT_FILE"

    echo
    echo "==== codex stderr report ===="
    STDERR_FILE=$(find /tmp/codex-local-runner-live-prompt145 -path '*execution_runs*/stderr.txt' -type f | sort | tail -n 1)
    echo "stderr_file=$STDERR_FILE"
    sed -n '1,180p' "$STDERR_FILE"

---

## 9. 成功判定

成功条件:

    py_compile成功
    automation/orchestration/planned_execution_runner.py のみ変更
    completed=0固定
    attempted=1 は実際に既存mapped call pathを呼んだ場合のみ
    呼べなかった場合 attempted=0
    new executorなし
    GitHub mutationなし
    daemon/scheduler/sleep-loop/queue-drainなし
    max-two-launchなし
    second launchなし

Prompt145-fixが必要な条件:

    py_compile失敗
    completed=1が入った
    new executorを追加した
    second launch / max-two-launchを追加した
    actual invocationなしなのに attempted=1
    既存state dict再利用だけで attempted=1
    GitHub mutationあり

---

## 10. 成功後のcommit/tag

Prompt145成功後:

    cd /home/rai/codex-local-runner

    python -m py_compile automation/orchestration/planned_execution_runner.py
    git status --short
    git diff --stat

    git add automation/orchestration/planned_execution_runner.py prompts/context/procedure.md
    git commit -m "Prompt145: execute one bounded existing invocation attempt"
    git tag checkpoint-prompt145-one-invocation-attempt-ready

    git log --oneline --decorate -n 6

壊れた場合の戻し方:

    git reset --hard checkpoint-prompt144-candidate-safety-ready

未追跡ファイルも消す場合のみ:

    git clean -fd

---

## 11. Prompt145後の次

Prompt145成功後は Prompt146。

Prompt146の目的:

    completion evidenceを評価する
    attempted=1だけでcompleted=1にしない
    receipt_status=readyだけでcompleted=1にしない
    明示的completion evidenceがある場合だけ completed=1

