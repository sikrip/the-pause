<!--
⚠️ DEPRECATED — superseded by the `grill-with-docs` skill.
Kept for historical reference only. Do NOT use in the current workflow.
See README.md → "Evolution of the planning phase".
-->

# /research

> **⚠️ DEPRECATED.** Superseded by `grill-with-docs`. Kept for historical reference — see README → "Evolution of the planning phase". Do not use in the current workflow.

Analyze the relevant code and context before planning or implementing a change.

## Research: $ARGUMENTS

### Step 1 — Setup

Create the output file:
- Slugify `$ARGUMENTS` (lowercase, hyphens, no special chars)
- Write to `docs/research/<slug>-RESEARCH.md`
- Create `docs/research/` if it doesn't exist

### Step 2 — Scope

Identify which files, modules, and external dependencies are relevant to the change.
Map the boundaries: what's in scope, what's adjacent, what must not be touched.

### Step 3 — Analysis

For each relevant component:
- **What it does** — purpose, inputs, outputs
- **How it connects** — dependencies, callers, data flow
- **What constraints exist** — invariants, implicit assumptions, coupling

### Step 4 — Risk surface

- What will this change affect beyond the obvious?
- Where is the accidental complexity? (workarounds, shims, legacy patterns to preserve vs remove)
- What edge cases or failure modes exist?
- What context is missing? (flag as **ASSUMPTION NEEDED**)

## Output

Write the research document to `docs/research/<slug>-RESEARCH.md` with these sections:

1. **Components involved** — table of file/module, purpose, relevance to change
2. **Dependency map** — what connects to what
3. **Constraints & invariants** — things that must remain true
4. **Risk areas** — where things are likely to break
5. **Open questions** — what needs human input before proceeding

End the document with:
```
---
*Findings ready for review. Do not proceed to /spec or implementation until validated.*
```

Also print a summary to the conversation with the file path and key findings.

## Rules

- Do not write code. Do not produce a plan. Research only.
- Do not skip to solutions — the goal is understanding, not implementation.
- If the scope is too broad, narrow it and state what was excluded.
- Probe actively: check tests, config, imports, callers — don't rely on surface reading.
- Stop and present findings for human validation before moving to /spec or implementation.
- The research file is a project artifact — it should be committed with the related work.
