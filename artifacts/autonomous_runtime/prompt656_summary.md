# Prompt656 — Minimal Safe Task-Kind Expansion (add_file)

**Status:** success · **Base:** fa1c91a (tag prompt655-project-prompt-batch-controller)
**New task kind:** `add_file` · **Live acceptance:** success

## What was added (minimal, additive)
- `task_spec.py`: `SUPPORTED_TASK_KINDS = ("add_function", "add_file")` + strict
  add_file validation — rejects absolute/`..`/empty paths, **secret-looking paths**
  (`.env`, `.env.*`, `*secret*`, `*token*`, `*credential*`, `id_rsa`, `id_ed25519`),
  **binary/NUL content**, and content **> 100 KB**; `allow_overwrite` defaults **false**;
  `create_parent_dirs` explicit. add_function validation is byte-for-byte unchanged.
- `task_planner.py`: add_file prompt (create file with exact content; no overwrite by
  default; explicit parent-dir behavior) + add_file effect spec (`expected_modified_files=[target]`,
  `required_text=[content]`, `allow_extra_files` default false); `plan_task` accepts both kinds.
- `project_plan.py` / `project_task_generator.py`: additive support so add_file flows
  through the whole project chain (descriptors → plan → queue spec).

## Why it's safe (no gate change, no new apply code)
add_file executes through the **existing Codex/effect-gated daemon path**: Codex creates
the file per the prompt, and the **unchanged strict effect gate** verifies it — a created
file satisfies `expected_modified_files`, `required_text` greps the content, and
`allow_extra_files=False` blocks any other created file. Validation rejects unsafe specs
before the prompt is ever built.

## Validation
- 20 new add_file tests (path/secret/binary/size/overwrite/parent-dir, planner effect
  spec, chain queue-spec validity, completion gate never marks failed add_file complete).
- **154 total tests green** (all existing project-layer + daemon + targeted-fix + gate suites).

## Live acceptance (real Codex, /tmp clone, 1/1/1)
Enqueued an add_file task on a /tmp clone and ran the daemon live: Codex **created** the
file with exact content, the effect gate **passed**, the clone got a real commit
(`5493639 sandbox auto commit: prompt656-add-file-live`) + sandbox tag. **Main repo HEAD
unchanged** (fa1c91a before==after); no source drift beyond scope; no marker file leaked
into the main repo; protected paths untouched.

## Result & next
The system now executes **two** task kinds (add_function + add_file), live-proven, under
the same strict safety gate. **Next:** `replace_text_task_kind`.
