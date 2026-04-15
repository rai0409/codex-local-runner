# Archive Bundle Standard

## Purpose
Each archive bundle stores one implementation attempt in a re-evaluable format.

## Rule
One task = one archive bundle directory.

## Required files
- prompt.md
- codex_output.md
- diff.patch
- commands.txt
- test_results.txt
- evaluation.md
- decision.md

## Notes
- prompt.md may be a source note if the original prompt is embedded in another run-record file.
- diff.patch must contain real diff output from git, not a reconstructed summary.
- evaluation.md records scoring and analysis.
- decision.md records the final pass / revise / rollback judgment separately.

## Intended use
This archive format is the base unit for:
- good / bad example extraction
- prompt quality review
- retry prompt generation
- future semi-automation
