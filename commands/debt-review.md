# /debt-review

Read the file `.claude/cognitive_debt.md` and produce a structured report.

## Open Assumptions
List all ASSUMPTION NEEDED entries — these are unresolved risks.
For each: file, line, question, and suggested owner to ask.

## High Priority Debt
List all DEBT entries with PRIORITY: high.

## Stale Thresholds
List all THRESHOLD entries older than 90 days that haven't been referenced as resolved. Flag for review.

## Decisions to Document
List DECISION entries that have no corresponding doc/ reference — these live only in code and are at risk of being forgotten.

## Rules

- Format as a prioritised action list, not a data dump.
- If `.claude/cognitive_debt.md` doesn't exist or is empty, say so and suggest running `/debt-check` on the current codebase first.
- Group by severity, not by date.
