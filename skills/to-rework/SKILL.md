---
name: to-rework
description: Freeze a grilled rework ticket into a spec file at ./docs/rework/<KEY>/ticket.md — the rework-lane twin of to-prd. Synthesises from the current conversation (a grill-change session that has already read the ticket and agreed the approach); does NOT fetch the ticket or interview the user. Writes the ticket summary, the agreed plan, an Acceptance section (normally "observable behaviour unchanged") and numbered Steps starting with step 0, the characterisation tests. implement-change, review-change and close-change consume this file. Requires a ticket key as input.
---

# /to-rework

The rework lane's freeze step. A feature is planned with `grill-change` → `to-prd` → `to-md-issues`; a **rework** — a refactor, a cleanup, a dead-code removal, a ticket-driven improvement that leaves behaviour unchanged — is planned with `grill-change <KEY>` → `to-rework <KEY>`. Where to-prd produces a PRD plus issue stubs, to-rework produces **one file with numbered steps**, because a rework has no user stories to slice: it has a current behaviour to preserve and an ordered sequence of moves that preserve it.

This skill takes the current conversation context and codebase understanding and produces the spec. Do NOT interview the user — synthesise what the grilling already established. Do NOT fetch the ticket from a tracker: the grilling session read it, and its text is in the conversation.

## Required input

The user must provide a **ticket key** (`PROJ-123`, `LAP-42`, `#118`-style keys normalised to the tracker's own form). If invoked without one, ask before proceeding.

## Preconditions — halt on any failure

1. The ticket's text is in the conversation. If it is not, halt and say: run `grill-change <KEY>` first, then invoke this skill in the same session.
2. The grilling reached an agreed approach. If the conversation shows open decisions, list them and halt — a spec frozen over an open decision produces Re-grill findings at review.
3. The change is a rework: the agreed approach leaves observable behaviour unchanged. If the grilling concluded that behaviour *should* change, say so and route to the feature lane (`to-prd`); do not freeze a behaviour change as a rework.

## Output location

```
./docs/rework/<KEY>/ticket.md
```

Relative to the project root. Create `./docs/rework/<KEY>/` if it does not exist. The file is committed to the integration branch before the work branch is cut, so the cold reviewer can read it without a tracker. It is deleted by `close-change` when the ticket closes; git history and the tracker are the archive.

## Process

1. Explore the repo for the modules the rework touches, if the grilling has not already. Use the project's domain glossary vocabulary and respect ADRs in the area.

2. **Name the behaviour boundary.** Identify where "unchanged" will be measured: the public functions, CLI entry points, table schemas, API responses or rendered outputs whose observable results must be identical before and after. Check these boundaries with the user — they become step 0. A boundary the user did not agree to is a boundary nobody will test.

3. **Order the moves.** Break the agreed approach into steps that each leave the whole suite green and each fit one commit. Extract-a-helper, move-a-block, delete-dead-code, split-a-function are the right grain. A step that cannot be done without changing behaviour is not a step: either the rework's scope is wrong (go back to the grilling) or it is a feature in disguise (route to `to-prd`).

4. Write the spec using the template below. Confirm the path to the user once written, and remind them: commit it to the integration branch, then run `implement-change <KEY>` in a fresh session.

## Rules for the steps

- **Step 0 is always the characterisation tests** and is never optional. It pins the boundaries from process step 2 against the code as it is now. It touches no production code.
- Steps are numbered from 0 and executed in order by `implement-change`; there is no dependency graph.
- Each step body states what changes, what stays, and how the implementer knows it is done. Module and file names are fine here — unlike a PRD, a rework is *about* specific files and the spec lives days, not months. No code snippets.
- Mark a step `Type: HITL` only when a human must do or decide something *first* (a production data migration, a call the ticket does not settle). Prefer AFK. Mark `Verification: HITL` when green tests cannot confirm it (device, hardware, live environment).
- Six to ten steps is typical. More than fifteen means the ticket should have been split in the tracker.

<ticket-template>

# <KEY> — <ticket title>

**Ticket:** <KEY>
**Lane:** rework
**Frozen:** <YYYY-MM-DD>

## Ticket

The ticket's description, faithfully. Quote the acceptance criteria the ticket itself states, if any.

## Current behaviour

What the code does today at the boundaries this rework touches, in domain language. This is what step 0 pins. Include the known quirks that must survive — a rework that "fixes" an undocumented behaviour has changed behaviour.

## Plan

The approach the grilling agreed on, and the decisions taken along the way. One line per rejected alternative and why. Name the seams the split will follow.

## Acceptance

- Observable behaviour unchanged at: <the boundaries from Current behaviour>. Enforced by the characterisation tests in step 0 and by the existing suite staying green after every step.
- <Any structural criterion the ticket or grilling set: "no file over 500 lines", "no caller of X remains", "the docs grep for removed identifiers is clean".>

## Steps

### 0. Characterisation tests — <the boundaries>

Type: AFK

What to pin, at which boundary, with which fixtures (prefer captured production fixtures). What the tests must NOT do: assert internal structure, private helpers, or the exact shape of intermediate data.

### 1. <title>

Type: AFK

What changes. What stays. How the implementer knows it is done.

### 2. <title>

Type: AFK | HITL — <why, if HITL>
Verification: HITL — <why, if the tests cannot confirm it>

...

## Out of scope

What this rework deliberately leaves alone, especially the adjacent debt the grilling noticed and chose not to touch. Each item is a candidate ticket, not a step.

## Notes

Anything the implementer or reviewer needs that fits nowhere above.

</ticket-template>

## Hard constraints

- **Never fetch the ticket.** The grilling did. If it is not in context, halt.
- **Never write a spec whose acceptance changes behaviour.** Route to `to-prd`.
- **Never omit step 0.** `implement-change` refuses to start without it, by design.
- **Never commit.** Write the file, confirm the path, and hand the commit to the user.

## Output

Writes `./docs/rework/<KEY>/ticket.md` and nothing else.
