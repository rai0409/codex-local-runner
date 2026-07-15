# Prompt650 — Minimal-Safe Task-Kind Expansion: DEFERRED (blocked by safety scope)

**Status:** blocked (deliberate) · **Base:** 53966a1 · **Implementation performed:** no

## Decision
Do **not** implement a new executable task kind in this offline loop. A new kind
(add_file/modify_file) must be wired into the Codex-facing prompt + effect-spec
generation and `task_spec` validation — a NEW path on the safety-critical live
execution surface. Per project precedent, `add_function` was only accepted after a
live, effect-verified /tmp runtime acceptance (638d/639/644a). Doing that for a new
kind requires live Codex + bounded daemon runtime, which is **outside this loop's
offline, no-uncontrolled-daemon, no-Codex scope**. The meta prompt permits marking
this blocked if too risky/broad.

## Why this does not block the goal
All project-orchestration layers above `task_spec` are kind-agnostic;
`add_function` already drives the entire offline chain. Task-kind breadth is a
breadth feature, not a prerequisite for proving project-level orchestration offline.

## Recommended follow-up
A dedicated prompt implementing `add_file` with strict path validation (no
traversal/secrets/shell/deletion) **plus** a bounded live /tmp effect-verified
acceptance, before tagging.

Proceeding to the higher-value, offline-safe target: **project_level_e2e_acceptance**.
