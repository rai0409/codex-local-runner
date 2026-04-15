# Bad Example: Skip retry_metadata then expand inspect layers

## Pattern
Move directly to advisory / execution_bridge / mode_visibility before retry_metadata is fixed and contract-stabilized.

## Why this is bad
- advisory and execution_bridge lose grounding
- inspect-derived layers become less trustworthy
- later compatibility handling becomes messy
- the sequence of deterministic control-plane construction breaks

## Typical symptoms
- recommendation exists but retry basis is unclear
- inspect fields become present but weakly justified
- tests check shape only, not deterministic derivation basis

## Corrective action
- return to machine-review payload
- add retry_metadata first
- verify old-payload compatibility
- then add advisory
- then execution_bridge
- then mode_visibility