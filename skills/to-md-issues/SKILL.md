---
name: to-md-issues
description: Break a plan, spec, or PRD into independently-grabbable issues as markdown files under ./docs/features/<feature-name>/issues/ using tracer-bullet vertical slices. Use when user wants to convert a plan into local issue files (not pushed to GitHub or any issue tracker). Requires a feature name as input.
---

<!--
Derived from Matt Pocock's `to-issues` skill — reworked to emit local markdown
files under ./docs/features/<name>/issues/ instead of creating issues in a remote
tracker (GitHub/GitLab). Original `to-issues` authored by Matt Pocock. See ATTRIBUTION.md.
-->

# To Markdown Issues

Break a plan into independently-grabbable issues using vertical slices (tracer bullets), written as **markdown files on disk** — no issue tracker, no GitHub, no labels, no API calls.

## Required input

The user must provide a **feature name** (kebab-case, short, descriptive — e.g. `csv-export`, `rate-limit`, `lapser-anti-spam`). If the user invokes this skill without a feature name, ask for one before proceeding. The feature name is used as the parent directory under `./docs/features/`.

## Output location

Each issue is written as a separate markdown file under:

```
./docs/features/<feature-name>/issues/<NN>_<slug>.md
```

(relative to the project root, i.e. the current working directory). These files are committed to git alongside the code that implements them — they are not personal scratchpads.

- `NN` is a zero-padded two-digit ordinal (`01`, `02`, ...) reflecting dependency order — blockers first.
- `<slug>` is a kebab-case version of the issue title.
- Create the `./docs/features/<feature-name>/issues/` directory if it does not exist.

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes a path to a PRD or plan markdown file as an argument, read it. Do NOT fetch from any remote issue tracker.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code. Issue titles and descriptions should use the project's domain glossary vocabulary, and respect ADRs in the area you're touching.

### 3. Draft vertical slices

Break the plan into **tracer bullet** issues. Each issue is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

Each slice carries two independent classifications — keep them separate, they answer different questions:

**Type — who implements it?** `HITL` or `AFK`.
- `HITL` (a **decision gate**): the agent must NOT implement it as-is. A human has to do or decide something *first* — an architectural decision, a design review, a choice that changes what gets built. Orchestrators (`/implement-change`) hand these off to the human and do not run a subagent on them.
- `AFK`: the agent can implement it end-to-end with no human decision needed. Prefer AFK over HITL wherever possible.

**Verification — who confirms it works?** `AFK` (default) or `HITL`.
- A **verification gate** (`Verification: HITL`) means the agent implements the slice fully, but completion requires a *human* to confirm it — typically because it can't be verified in-loop: on-device behavior, a real permission prompt, real hardware, a native build, a visual/physical check on both platforms. The agent takes it to "ready for verification" and stops; it is NOT marked done/merged until the human verifies.
- Most slices are `Verification: AFK` (their own automated tests are sufficient) — omit the field in that case.

These are orthogonal. The common useful combination is **`Type: AFK` + `Verification: HITL`**: the agent builds it, then a human verifies on a device. That is NOT the same as `Type: HITL` (which means the agent shouldn't build it at all). Only set `Type: HITL` when a human must act *before* implementation; use the Verification gate when the human acts *after*.

<vertical-slice-rules>
- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
</vertical-slice-rules>

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**: short descriptive name
- **Type**: HITL / AFK (who implements)
- **Verification**: AFK / HITL (who confirms it works — only call out HITL)
- **Blocked by**: which other slices (if any) must complete first
- **User stories covered**: which user stories this addresses (if the source material has them)

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?
- Are the Type (HITL/AFK) and Verification (AFK/HITL) classifications right — in particular, is anything marked `Type: HITL` that's really `Type: AFK` + a verification gate?

Iterate until the user approves the breakdown.

### 5. Write the issues to markdown files

For each approved slice, write a new markdown file at `./docs/features/<feature-name>/issues/<NN>_<slug>.md` using the template below.

Write files in dependency order (blockers first) so the `NN` ordinal reflects the order, and the "Blocked by" field can reference real filenames (e.g. `01_schema-flatten.md`).

<issue-template>
# <Title>

**Type:** HITL | AFK

**Verification:** HITL — _only include this line when a human must confirm the slice works (on-device, real hardware, native build, visual check). Describe what the human checks and on which platforms. Omit entirely when automated tests suffice._

## Parent

A reference to the parent PRD or plan file (e.g. `docs/features/<feature-name>/prd.md`) if applicable. Otherwise omit this section.

## What to build

A concise description of this vertical slice. Describe the end-to-end behavior, not layer-by-layer implementation.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

When the slice has a `Verification: HITL` gate, split this into two labelled groups — "Agent-completable (no device required)" and "Human verification gate (HITL — …)" — so the boundary between what the agent finishes and what the human confirms is explicit.

**A criterion that is true once per change belongs on one slice, not on every slice.** Release chores — a version or build-number bump, a changelog entry, a migration applied, a feature flag flipped, a generated artifact regenerated — land once for the whole change. Put them on the slice that actually ships (usually the last, or the deploy slice) and leave them off the rest. Repeating one across slices makes each implementer redo it, produces a branch with the same line rewritten N times, and leaves N−1 of those values never built and never released. The test: *if this change ships once, how many times should this be true?* If the answer is once, it is one slice's criterion.

## Blocked by

- A reference to the blocking issue file (e.g. `01_schema-flatten.md`)

Or "None — can start immediately" if no blockers.

## User stories covered

- Story numbers / IDs from the parent PRD (if applicable). Omit if not applicable.

</issue-template>

Do NOT modify the parent PRD or any other source material. After all files are written, list the created paths back to the user as confirmation.
