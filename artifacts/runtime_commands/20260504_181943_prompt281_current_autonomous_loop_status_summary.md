# Prompt281までの現在地: local自律loop確認状況

## 結論

Prompt281までで、GitHubを除いたlocal自律開発loopの中核部品はかなり揃った。

現在できていることは次の通り。

- ChatGPT bridge / Chrome auto-run / task lifecycle / dedupe
- ChatGPT response assimilation
- Codex向けprompt routing
- Codex execution gate
- Codex execution connector
- Codex diff capture gate
- ChatGPT diff review request生成
- ChatGPT diff review decision branching
- fix prompt route
- safe revert gate
- local commit/tag gate
- explicit local commit/tag execution
- local PR queue state
- bounded local autonomous loop coordinator

Prompt281では、これらをまとめる bounded local autonomous loop coordinator が追加され、function-level smoke は成功した。

## Prompt281で確認済みのこと

Prompt281は commit/tag 済み。

- commit: `8d4b179 Add bounded local loop coordinator`
- tag: `prompt281-bounded-local-loop-coordinator`

Prompt281 smokeでは以下を確認済み。

### decision-only

- status: `bounded_local_loop_decision_only`
- next_action: `set_continue_enabled_for_next_local_step`
- iteration: `0`
- selected_component: `local_loop`
- blocked_reason: `continue_not_enabled`

意味:
- bounded loopは有効だが、continueがfalseなので実行せず判断だけに留まる。
- 副作用なしで次step確認ができる。

### one-step continue

- status: `bounded_local_loop_ready_continue`
- next_action: `run_codex_implementation`
- iteration: `1`
- selected_component: `local_loop`
- blocked_reason: `none`

意味:
- continue_enabled=true のとき、1 stepだけ進める判断ができる。
- iterationが1だけ増える。
- ただし coordinator自体はCodexを直接実行しない。

### duplicate/no-progress

- status: `bounded_local_loop_blocked_duplicate_or_no_progress`
- next_action: `manual_review_required`
- iteration: `1`
- blocked_reason: `duplicate_or_no_progress_fingerprint`

意味:
- 同じprogress fingerprintで再実行した場合、無限loopせず停止できる。

### project complete

- status: `bounded_local_loop_project_complete`
- next_action: `project_complete`
- selected_component: `pr_queue_state`

意味:
- PR queueがproject complete状態なら、loopは完了として停止できる。

## real runner dry-runで進んだこと

`run_planned_execution.py` のCLI入口を確認した。

必須入力は次の4ファイル。

- `project_brief.json`
- `repo_facts.json`
- `roadmap.json`
- `pr_plan.json`

最初の最小 `pr_plan.json` では `pr_units` を使ったため、runnerはPR unitを見つけられず失敗した。

エラー:

```text
no pr units found in planning artifacts

原因:

runner内部では compile_prompt_units(artifacts) を使い、pr_plan.prs を期待する。
pr_plan.json は pr_units ではなく prs を使う必要がある。

修正:

pr_plan.json を prs schemaに変更した。

その後、dry-runを再実行し、以下のartifact生成まで進んだ。

next_action.json
objective_contract.json
execution_result_contract.json
bounded_execution_bridge.json
approval_transport.json
completion_contract.json
endgame_closure_contract.json
execution_authorization_gate.json
failure_bucket_rollup.json
pr-smoke-1/compiled_prompt.md
pr-smoke-1/bounded_step_contract.json
pr-smoke-1/pr_implementation_prompt_contract.json
pr-smoke-1/checkpoint_decision.json
pr-smoke-1/commit_decision.json
pr-smoke-1/commit_execution.json
pr-smoke-1/merge_decision.json
pr-smoke-1/merge_execution.json
pr-smoke-1/pr_execution.json
pr-smoke-1/push_execution.json
pr-smoke-1/rollback_decision.json
pr-smoke-1/rollback_execution.json
pr-smoke-1/unit_progression.json

意味:

run_planned_execution.py のdry-run入口は動いた。
最小planning artifactからrunner artifactを生成できるところまで進んだ。
ただし、まだ bounded_local_loop_* fields がrun outputに出ているかは未確認。
まだ未確認のこと

次に確認すべきことは、latest dry-run output内に以下のfieldが出ているか。

project_browser_autonomous_bounded_local_loop_status
project_browser_autonomous_bounded_local_loop_next_action
project_browser_autonomous_bounded_local_loop_iteration
project_browser_autonomous_bounded_local_loop_progress_fingerprint
project_browser_autonomous_bounded_local_loop_selected_component
project_browser_autonomous_bounded_local_loop_blocked_reason

理想:

project_browser_autonomous_bounded_local_loop_status=bounded_local_loop_decision_only
project_browser_autonomous_bounded_local_loop_next_action=set_continue_enabled_for_next_local_step

もし出ていない場合:

Prompt281 coordinatorが壊れているとは限らない。
approved_restart flags が pr_plan.json からrunner内のapproved restart payload経路へ入っていない可能性が高い。
次に retry-context、policy_snapshot、または別contract path経由でflagsを投入する方法を確認する。
現時点の到達度
GitHubを除いたlocal自律loop

かなり完成に近い。

できているもの:

bounded loop coordinator
function-level smoke
dry-run runner入口確認
minimal planning artifact作成
pr_plan schema修正
dry-run artifact生成

未確認:

real runner output内の bounded_local_loop_* field露出
real payload decision-only
real payload one-step continue
Codex connectorのlive実行
capture → ChatGPT review → decision → fix/revert/commit のE2E
こまめなlocal commit/tag

仕組みはできている。

commit/tag gate
explicit local commit/tag execution
PR queue update
next PR pointer

ただし、real E2E連続運用はまだ未確認。

GitHub

低優先度として後回し。

未実装/未確認:

GitHub upload decision gate
push
GitHub PR作成
merge
local main最新化
branch削除
次にやるべき確認

次は、latest dry-run outputから bounded_local_loop_* fields を探す。

期待:

fieldsが見つかる
statusがdecision-onlyになる
next_actionが出る
dry-runなので副作用なし

その後、もしfieldsが出れば:

continue_enabled=true
max_iterations=1
dry-run再実行
iterationが最大+1になるか確認
同じpayloadでduplicate/no-progress stopを確認

もしfieldsが出なければ:

approved_restart flagsの投入経路を特定
retry-context / policy_snapshot / contract overrideのどれで渡すべきか確認
real payload decision-onlyを再試行
安全性

ここまでの確認では、以下は行っていない。

live Codex execution
git restore
git commit/tag
git push/fetch/pull/merge/rebase
GitHub PR作成
branch deletion
untracked file削除
ChatGPT/OpenAI API call
Playwright
CAPTCHA/Verify bypass
cookie/token/session storage

