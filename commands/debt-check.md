# /debt-check

Review the current task or file for cognitive debt.

## What to check

- Magic numbers or thresholds without documented origin
- Business rules that exist only in code (not in comments or docs)
- Unvalidated assumptions
- What would silent failure look like here?
- What would someone need to know in 6 months to safely modify this?

## Output

Rate overall: **LOW** / **MEDIUM** / **HIGH**

Output as a bullet list with severity per item. Example:

- **HIGH**: `pricing.py:58` — discount threshold 0.15 has no documented origin
- **MEDIUM**: `client.py:27` — retry delay should be configurable
- **LOW**: `parser.py:15` — keyword list could be incomplete

## Rules

- If no file is specified, check all files modified in the current session.
- Focus on business logic and pipeline code in `src/`, not scripts or tests.
- Be honest — flag real issues, don't pad the list.
