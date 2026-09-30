<!--
⚠️ DEPRECATED — superseded by the `grill-with-docs` + `to-prd` skills.
Kept for historical reference only. Do NOT use in the current workflow.
See README.md → "Evolution of the planning phase".
-->

# /spec

> **⚠️ DEPRECATED.** Superseded by `grill-with-docs` + `to-prd`. Kept for historical reference — see README → "Evolution of the planning phase". Do not use in the current workflow.

Before any implementation, produce a structured spec and wait for approval.

## Spec: $ARGUMENTS

**Input schema** — column names, types, source table (with catalog.schema.table)
**Output schema** — what changes, what's added
**Business rules applied** — with stakeholder or ticket reference
**Edge cases handled**
**Edge cases NOT handled** — and why
**Data quality checks** — what will catch silent failures
**ASSUMPTION NEEDED** — list any unresolved questions

## Rules

- Do not write code until this spec is acknowledged by the user.
- If the task is too vague to spec, ask clarifying questions first.
- Keep it concise — tables and bullet points, not paragraphs.
