# Bad Example: Expand scheduler/notifier/runtime before contract fix

## Pattern
Add notifier-triggered actions, scheduler-driven decisions, or runtime automation before inspect/read-only contracts are fixed.

## Why this is bad
- automation outruns visibility guarantees
- debugging and operator trust degrade
- future rollback of semantics becomes harder

## Red flags
- webhook-triggered decision behavior
- scheduler starts interpreting advisory fields
- notification success becomes prerequisite for review

## Corrective action
- first fix payload contract
- then fix inspect-derived contract
- then keep explicit operator gate
- only after that design bounded execution separately