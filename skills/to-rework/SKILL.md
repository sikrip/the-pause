---
name: to-rework
description: Freeze a grilled rework ticket into a spec file at ./docs/rework/<KEY>/ticket.md — the rework-lane twin of to-prd. Synthesises from the current conversation (a grill-change session that has already read the ticket and agreed the approach); does NOT fetch the ticket or interview the user. Writes the ticket summary, the agreed plan, an Acceptance section (normally "observable behaviour unchanged") and numbered Steps starting with step 0, the characterisation tests. If the spec already exists, amends it without renumbering implemented steps. implement-change, review-change and close-change consume this file. Requires a ticket key as input.
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

Relative to the project root. Create `./docs/rework/<KEY>/` if it does not exist. Before writing a new spec, run the state checks in `grill-change`'s step 1 for `<KEY>` — merged, in flight on another branch, closed (its spec deleted by the close). Each is handled here as it is there, so a rework is never planned twice. The file is committed as the first commit on the change branch `rework/<KEY>`, not to the integration branch, so the cold reviewer can read it without a tracker and it reaches the integration branch only through the merge request. It is deleted by `close-change` as the branch's last commit, which copies its Acceptance and Current behaviour sections into the merge request description; the tracker and the merge request are the archive.

## If the spec already exists — amend it, do not re-freeze from scratch

A `ticket.md` already at that path means the rework is in progress and its plan was reopened. Read
it in full, and find which steps are already implemented: `implement-change` leaves one commit per
step with the subject its commit template gives, zero-padded `NN: <title>` by default (`00:`, `01:`, ...). In a re-grill the ticket text is the spec's own `## Ticket` section, which `grill-change` has read; that satisfies precondition 1.

- **A rework in progress is never converted into a feature.** If the amendment changes observable
  behaviour, or widens the boundary step 0 pinned, it is not an amendment: say so and stop. The
  rework is finished and merged as the behaviour-preserving change it is, or abandoned, and the rest
  is planned afterwards — a behaviour change as a separate feature, a wider refactor as a new
  ticket. Do not add either as a step, and do not add a second characterisation step:
  `implement-change` treats step 0 alone as the tests that define "unchanged".
- **Implemented steps are never edited or renumbered, and step 0 is never edited.** New steps are
  numbered after the last existing one and run after it. A step not yet implemented may be edited or
  removed.
- Change **Plan**, **Acceptance** and **Current behaviour** only where the reopened decision touches
  them, and add an `**Amended:** <YYYY-MM-DD> — <one line>` under `**Frozen:**`.
- Show the user the intended edits as a diff and wait for an explicit OK before writing.

Afterwards the amended spec is committed on the change branch, which already exists, and the new
steps are implemented with `implement-change <KEY> <N> ...`.

## Process

1. Explore the repo for the modules the rework touches, if the grilling has not already. Use the project's domain glossary vocabulary and respect ADRs in the area.

2. **Name the behaviour boundary.** Identify where "unchanged" will be measured: the public functions, CLI entry points, table schemas, API responses or rendered outputs whose observable results must be identical before and after. Check these boundaries with the user — they become step 0. A boundary the user did not agree to is a boundary nobody will test.

3. **Order the moves.** Break the agreed approach into steps that each leave the whole suite green and each fit one commit. Extract-a-helper, move-a-block, delete-dead-code, split-a-function are the right grain. A step that cannot be done without changing behaviour is not a step: either the rework's scope is wrong (go back to the grilling) or it is a feature in disguise (route to `to-prd`).

4. Write the spec using the template below. Confirm the path to the user once written, and remind them: cut `rework/<KEY>` from the up-to-date integration branch and commit the planning files there. If `rework/<KEY>` is already checked out — it was cut before the spec was written — there is nothing to cut: commit the planning files on it. Otherwise, the sequence that survives a planning file a teammate also changed: `git fetch <remote>` (best-effort) first; then confirm `rework/<KEY>` does not exist, locally or on the remote (`git branch -a --list '*rework/<KEY>'` prints nothing), so nothing is stashed for a checkout that will fail; then `git stash -u`, `git checkout --no-track -b rework/<KEY> <remote>/<integration_branch>`, `git stash pop`. `<integration_branch>` is the one in the `implement-change` config file, else `develop`; `<remote>` is `origin` if it exists, else the repo's only remote; with no remote, cut from the local `<integration_branch>`, then commit the spec and any `CONTEXT.md` / ADR updates. A conflict on `git stash pop` — `CONTEXT.md` is the usual one — is a real collision with a plan that merged meanwhile: resolve it before committing, then `git stash drop`. Then run `implement-change <KEY>` on that branch in a fresh session.

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
- **Never commit without the user's OK.** Write the file and confirm the path; the spec commit follows the standards' commit protocol.

## Output

Writes `./docs/rework/<KEY>/ticket.md` and nothing else.
