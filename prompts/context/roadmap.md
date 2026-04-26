# codex-local-runner Roadmap — Prompt144後の完全自律開発フロー化

最終更新:
- Prompt144完了後
- checkpoint-prompt144-candidate-safety-ready 作成済み
- 現在地点: one_bounded_launch の candidate safety validation まで完了
- 次: Prompt145

---

## 0. 現在地

現在、以下までは完了している。

### Prompt143まで

- action-specific input wiring classification
- selected next_action ごとの required_inputs / available_inputs / missing_inputs の分類
- actual local variables から available_inputs を算出
- callable_candidate_inputs_ready になれる状態の追加
- actual invocation はまだ実行しない
- attempted=0
- completed=0

### Prompt144完了

Prompt144で、one_bounded_launch に candidate safety 判定層を追加した。

追加済みフィールド:

- `project_browser_autonomous_one_bounded_launch_candidate_safety_status`
- `project_browser_autonomous_one_bounded_launch_candidate_safety_reason`
- `project_browser_autonomous_one_bounded_launch_candidate_safety_evidence`
- `project_browser_autonomous_one_bounded_launch_candidate_risk_flags`
- `project_browser_autonomous_one_bounded_launch_candidate_receipt_evidence_status`
- `project_browser_autonomous_one_bounded_launch_candidate_completion_evidence_status`

分類可能な状態:

- `callable_candidate_safe`
- `unsafe_to_reinvoke`
- `state_only`
- `missing_inputs`
- `terminal_stop`
- `insufficient_truth`

Prompt144の重要な制約:

- actual invocation は実行しない
- attempted=0
- completed=0
- new executor なし
- daemon / scheduler / sleep loop / queue drain なし
- GitHub mutation なし
- max-two-launch なし
- second launch なし

Prompt144の実行確認:

- runner経由 live 実行成功
- py_compile 成功
- `automation/orchestration/planned_execution_runner.py` のみ変更
- checkpoint tag:
  - `checkpoint-prompt144-candidate-safety-ready`

戻し方:

```bash
git reset --hard checkpoint-prompt144-candidate-safety-ready
1. 目標

最終目標は、現在の手動開発フローをローカルrunner内で自動化すること。

現在の手動フロー:

ChatGPTが次Promptを作る
ユーザーがCodexへ渡す
Codexが実装する
ユーザーが結果をChatGPTへ貼る
ChatGPTが評価する
次Promptへ進むか判断する
必要ならfix Promptを生成する

目標フロー:

runnerが現在状態を読む
runnerが次Promptを生成または選択する
runnerがCodexへ渡す
Codexが実装する
runnerがresult JSON / git diff / validationを読む
runnerがChatGPT内部接続へ判断を依頼する
ChatGPTがdecision JSONを返す
runnerが次Prompt / fix / stop / human_reviewを選ぶ
bounded条件内で繰り返す
危険時は停止またはrollbackする
2. ロードマップ概要

最短・安全ルート:

Prompt145
one actual invocation
attempted=1
completed=0固定
Prompt146
completion evidence評価
completed=1の厳密判定
Prompt149
Codex result JSON accounting修正
changed_files / additions / deletions を実diffと一致させる
Prompt147
launch_1 / launch_2 準備
最大2 launchの状態分離
Prompt148
max-two rolling execution
最大2回までのbounded実行
Prompt150
ChatGPT decision JSON schema
Prompt151
runner → ChatGPT internal call
Prompt152
decision → next prompt generator
Prompt153
bounded autonomous loop controller
Prompt154
rollback / checkpoint / human review gate
Prompt155
local autonomous development loop
Prompt156以降
GitHub PR作成 / CI / merge
3. Prompt145 — one actual invocation / attempted=1
目的

Prompt144で candidate_safety_status=callable_candidate_safe になった場合だけ、既存call pathを1回だけ実際に呼ぶ。

許可すること
実際に既存call pathを1回呼んだ場合だけ:
project_browser_autonomous_one_bounded_launch_attempted=1
禁止すること
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
厳格ルール
既存state dictを再利用しただけなら attempted=0
実際にmapped call pathを呼んだ場合だけ attempted=1
呼べなかった場合は attempted=0
Prompt145では completed=0 固定を推奨
completed=1はPrompt146に任せる
成功条件
py_compile成功
candidate_safety_status=callable_candidate_safe の場合のみ実行候補
hard risk flags があれば実行しない
actual invocationできた場合だけ attempted=1
completed=0
new executorなし
GitHub mutationなし
4. Prompt146 — completion evidence / completed=1判定
目的

Prompt145で attempted=1 になった後、本当に完了したかを判定する。

判定対象
receipt_status
receipt_kind
result evidence
action-specific completion evidence
validation result
state transition evidence
ledger evidence, if already existing and safe
厳格ルール
attempted=1 だけでは completed=1 にしない
receipt_status=ready だけでは completed=1 にしない
state存在だけでは completed=1 にしない
explicit completion evidence がある場合のみ completed=1
evidenceが曖昧なら completed=0
成功条件
completion evidence available and confirmed:
completed=1
completion evidence unavailable / ambiguous:
completed=0
5. Prompt149 — Codex result JSON accounting修正
目的

Codex実行後の result JSON が実際のgit diffを正しく表すようにする。

背景

Prompt144実行時に以下の不整合が発生した。

実際の git diff --stat
automation/orchestration/planned_execution_runner.py
571 insertions / 11 deletions
result.json
changed_files=[]
additions=0
deletions=0

これは完全自律loopでは危険。

修正対象
changed_files
additions
deletions
diff_stat
validation_status
commands_run
stdout_path
stderr_path
worktree_dirty
generated_patch_summary
必須ルール
git diff --name-only を反映
git diff --numstat を反映
py_compile結果を反映
result.json と実worktree差分を一致させる
Codexが変更した場合、changed_filesが空にならないようにする
成功条件

実際にファイル変更がある場合:

changed_files に対象ファイルが入る
additions/deletions が0ではない
worktree_dirty が正しく反映される
6. Prompt147 — launch_1 / launch_2 準備
目的

最大2 launchへ進む前に、1回目と2回目の状態を分離する。

追加・整理する状態
launch_1_attempted
launch_1_completed
launch_1_status
launch_1_result_status
launch_1_stop_reason
launch_2_allowed
launch_2_block_reason
launch_2_candidate_status
launch_2_required_inputs
launch_2_missing_inputs
Prompt147でやらないこと
2回目のactual execution
max-two-launch actual execution
loop
daemon
scheduler
sleep loop
queue drain
GitHub mutation
成功条件
1回目結果から2回目へ進めるか分類できる
2回目が許可されない理由を明示できる
7. Prompt148 — max-two rolling execution
目的

最大2回までの bounded rolling execution を実装する。

許可すること
最大2回までの実行
1回目の結果に応じて2回目へ進む
failure_budget内で停止判断する
禁止すること
3回目
unbounded loop
daemon
scheduler
sleep loop
queue drain
GitHub mutation
PR作成
PR merge
成功条件
最大2 launchまで実行可能
2回を超えない
失敗時は止まる
risk時は止まる
missing inputs時は止まる
8. Prompt150 — ChatGPT decision JSON schema
目的

ChatGPT内部接続時の入出力JSONを固定する。

入力JSON例
{
  "current_prompt_id": "Prompt145",
  "codex_result": {},
  "git_diff_summary": {},
  "validation": {},
  "risk_flags": [],
  "current_state": {},
  "allowed_next_actions": []
}
出力JSON例
{
  "decision": "proceed | fix | stop | human_review",
  "next_prompt_id": "Prompt146",
  "reason": "...",
  "required_constraints": [],
  "risk_flags": [],
  "confidence": "high | medium | low"
}
成功条件
ChatGPTの判断をJSONとして機械的に読める
自由文依存を減らせる
fix / proceed / stop / human_review の分岐が可能
9. Prompt151 — runner → ChatGPT internal call
目的

runnerからChatGPTへ内部問い合わせできるようにする。

処理
Codex result JSONを読む
git diff JSONを読む
validation結果を読む
current stateを読む
ChatGPT decision schemaへ詰める
ChatGPTへ問い合わせる
decision JSONを保存する
成功条件
runnerがChatGPT判断をJSONとして受け取れる
ユーザーが毎回Codex結果をChatGPTへ貼らなくてよくなる
10. Prompt152 — decision → next prompt generator
目的

ChatGPT decision JSONから次Promptを生成または選択する。

分岐
decision=proceed
次Promptへ進む
decision=fix
fix Promptを生成する
decision=stop
停止する
decision=human_review
人間確認へ回す
成功条件
Codex結果 → ChatGPT判断 → 次Prompt生成 が自動でつながる
ユーザーが毎回Promptを手で作らなくてよい
11. Prompt153 — bounded autonomous loop controller
目的

以下のサイクルをboundedに回す。

prompt生成
Codex実行
result JSON取得
git diff取得
ChatGPT判断
次prompt生成
再実行または停止
初期制限
max_prompts=3
max_codex_runs=2
failure_budget=1
unsafe時はhuman_review
unexpected diff時は停止
GitHub mutationは禁止
成功条件
bounded範囲で自律的に開発サイクルを回せる
無限loopしない
失敗時に止まる
12. Prompt154 — rollback / checkpoint / human review gate
目的

自律loopで壊れたときに戻れるようにする。

必須機能
checkpoint commit/tag
rollback command
dirty worktree検出
unexpected file changes検出
human_review_required
stop_reason明示
rollback_reason明示
成功条件
自律loopが失敗しても安全に戻れる
危険時に人間確認へ止められる
13. Prompt155 — local autonomous development loop
目的

ローカルで現在の開発フローを完全自律に近づける。

実現する流れ
runnerが現在状態を読む
ChatGPTに次prompt判断を聞く
promptを生成する
Codexへ渡す
Codexが実装する
result JSONを保存する
git diff / validation を読む
ChatGPTに評価させる
次prompt / fix / stop / human_review を決める
上限内で繰り返す
成功条件
人間が毎回promptを貼らなくてよい
人間が毎回Codex結果をChatGPTへ貼らなくてよい
runnerがboundedに回す
危険時は止まる
rollback可能
14. Prompt156以降 — GitHub PR作成 / CI / merge

GitHub mutationは影響が大きいため、ローカル自律loopが安定してから行う。

Prompt156
branch作成
commit作成
push
draft PR作成
Prompt157
CI結果取得
status check確認
Prompt158
PR comment作成
review summary作成
Prompt159
merge可能判定
human approval gate
Prompt160
auto-mergeまたはmanual merge support
15. 完了基準
Prompt146後
1回の実行単位が成立
attempted/completedを正しく分けられる
Prompt148後
最大2回までのbounded自動実行が成立
Prompt152後
ChatGPT内部接続による次prompt判断が成立
Prompt155後
ローカル完全自律開発loopが成立
Prompt160以降
GitHub PR/merge込みの完全自律に近づく
16. 最短見積もり

ローカル完全自動化まで:

Prompt145
Prompt146
Prompt149
Prompt147
Prompt148
Prompt150
Prompt151
Prompt152
Prompt153
Prompt154
Prompt155

合計:

あと11 Prompt

fix込みの現実的見積もり:

あと12〜14 Prompt

GitHub PR/merge込み:

あと15〜18 Prompt程度
17. 厳格な禁止事項

次の段階に進むまで禁止:

unbounded loop
常駐daemon
scheduler
sleep loop
queue drain
3回以上のlaunch
new browser executor
new Codex executor
new ledger persistence mechanism
GitHub mutation
PR作成
PR merge
CI auto-fix loop
18. 次の一手

次に実行すべきPrompt:

Prompt145 — execute exactly one bounded existing invocation only when Prompt144 candidate is safe / attempted may become 1 / completed remains 0

Prompt145の厳格方針:

actual invocationは1回だけ
attempted=1は実際に呼んだ場合だけ
completed=0固定
completed=1はPrompt146へ回す
max-two-launchはまだしない
second launchはまだしない
new executorは作らない
GitHub mutationはしない

---

## Current checkpoint update after Prompt149

Current checkpoint:

checkpoint-prompt149-result-json-accounting-ready

Completed:

- Prompt145: one bounded existing invocation attempt bridge.
- Prompt146: completion evidence evaluator.
- Prompt149: runner result JSON accounting correction.

Next:

Prompt147 — launch_1 / launch_2 state separation

Prompt147 must prepare launch_2 as candidate-only metadata. It must not execute launch_2, must not implement max-two rolling execution, and must not change Prompt149 accounting behavior.

---

## Current checkpoint update after Prompt147

Current checkpoint:

checkpoint-prompt147-launch-state-separation-ready

Completed:

- Prompt144: callable candidate safety validation.
- Prompt145: one bounded existing invocation attempt bridge.
- Prompt146: completion evidence evaluator.
- Prompt149: runner result JSON accounting correction.
- Prompt147: launch_1 / launch_2 state separation.

Next:

Prompt148 — execute bounded max-two rolling launch from Prompt147 launch_2 candidate.

Prompt148 must:
- execute at most one second bounded launch
- stop at max_launches=2
- not create a third launch
- not add unbounded loop / daemon / scheduler / queue drain
- not mutate GitHub
- not change Prompt149 accounting
