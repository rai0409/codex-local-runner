# Prompt678 Codex No-Confirmation Execution Profile

This acceptance adds an explicit safe no-confirmation profile for dry-run verified Codex command construction.

- profile_name: no_confirmation_workspace_write
- command_family: codex exec
- sandbox: workspace-write
- approval_policy: never
- yolo_mode_rejected: true
- danger_full_access_rejected: true
- sandbox_bypass_flags_rejected: true

The profile is not a default. It is available only through the explicit `no_confirmation_workspace_write` profile after preapproval and safety validation.
