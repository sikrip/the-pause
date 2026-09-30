---
name: close-change
description: Close a shipped change so the repo matches reality. Works for both lanes — a feature (spec ./docs/features/<name>/prd.md) or a rework ticket (spec ./docs/rework/<KEY>/ticket.md). Greps the docs for identifiers the change removed or renamed, confirms test fixtures are tracked and the whole suite passes, runs the debt check, then in the feature lane sets a Status header on the PRD and touched ADRs and deletes the issue stubs and review rounds, and in the rework lane deletes the whole docs/rework/<KEY>/ directory (the tracker is the record). Use at the merge or version-bump commit, once the branch is on the integration branch. Requires a change name as input. Never commits.
---

# /close-change

The last step of the workflow: **s1 plans**, **s2 implements**, **s3 reviews**, and then someone
closes. Without this step the planning artifacts outlive the change: PRDs stay "planned" for shipped
code, issue stubs and rework specs pile up with no status, review rounds describe a branch that no
longer exists, and docs keep naming tables and hosts the release removed. A change is not done until
this skill has run clean.

This is the **local-files-only** variant, like `review-change`. It edits files under the spec
directory and `docs/adr/`, runs the project's test command, and never talks to a tracker.

## Required input — the change name, and how the spec is resolved

The user must provide a **change name**: a kebab-case feature name or a ticket key (`PROJ-123`,
`LAP-42`). If invoked without one, ask before proceeding. Resolve the spec from it, in this order:

1. `./docs/features/<name>/prd.md` exists → **feature lane**. `<spec-dir>` is
   `./docs/features/<name>/`.
2. `./docs/rework/<name>/ticket.md` exists → **rework lane**. `<spec-dir>` is
   `./docs/rework/<name>/`.
3. Neither exists → halt and print both paths checked. Nothing to close.

`<spec-dir>` is used below for everything the skill reads, edits or deletes.

Optional positional args (in order):

- **Release ref.** A version, tag or commit that shipped the change (e.g. `1.4.0`, `v2.3.0`, a
  merge SHA). Recorded in the feature-lane Status line and in the closing summary. Default: the
  current `HEAD` short SHA and today's date.
- **Integration branch.** Default: `develop`.

## Preconditions — halt on any failure

1. The spec resolves (above).
2. The current branch is the integration branch, and the change's commits are reachable from it
   (`git branch --merged <integration_branch>` lists `feature/<name>` or `rework/<name>`, or that
   branch is already deleted and the spec is present on the integration branch). If the branch is
   unmerged, halt: closing unshipped work is what this skill exists to prevent.
3. The working tree is clean apart from files this skill will touch. Do not close on top of
   unrelated uncommitted work.

## Process

### 1. Inventory — read, then report

Read, in full:

- Everything under `<spec-dir>`: the PRD and `issues/*.md`, or `ticket.md`; every
  `reviews/round-*.md`; anything under `release/` or `notes/` if present.
- `docs/adr/*.md` files that name the change or that the spec cites.
- The change's commits: `git log <integration_branch> --grep="<name>" --oneline`, plus any commits
  the spec or release notes name. If none are found, ask the user for the commit range rather than
  guessing.

Post one short message to the conversation: change name, lane, spec path, release ref, number of
issue stubs or steps, number of review rounds, ADRs touched, commit range identified, and the test
command you intend to run (see step 3). Under 10 lines.

### 2. Docs drift — grep for what the change removed or renamed

From the change's diff (`git diff <merge-base>..<last-change-commit>`), collect identifiers that
were **deleted or renamed**: function and class names, table and column names, env vars, config
keys, hostnames, file paths, CLI flags, version strings. Ignore identifiers that were only added.
This step matters most for rework tickets that remove dead code — the docs are where its names
survive.

Grep for each across `docs/`, `README*`, `CLAUDE.md`, `CONTEXT.md` and `.env.example`, excluding
`<spec-dir>` itself and `docs/adr/`. Every hit is a stale claim. List them with file and line; do
not fix them silently. The user decides which to fix now (`fix`) and which to file.

Separately, grep the same paths for **unfilled template placeholders** — angle-bracket markers a
slice left for a human to complete, e.g. `<to measure`, `<deploy date`, `<run id`, `<TBD`, `<owner`.
A change whose spec deferred a figure to deploy day closes over them silently otherwise, because
they are additions and so invisible to the removed-identifier grep above. Report every hit; an
unfilled marker means the change is not closed.

### 3. Fixtures and the full suite

- **Fixtures:** grep `tests/` for references to files under `tests/fixtures/` (or the project's
  equivalent) and check each against `git ls-files`. Report every referenced fixture that is
  untracked or missing. This is the failure that silently disables e2e suites after a refactor.
- **Suite:** run **every tier**, e2e included. This is the merge gate, and it is not a repeat of
  `implement-change`'s end-of-run gate: the review fixes that landed since then are new code no gate
  has seen. Discover the command in this order: `tests.<tier>.all` in
  `.implement-change.config.json` (run each of the three tiers it declares), then the project
  `CLAUDE.md` commands section, `package.json` scripts, `pyproject.toml` / pytest, Gradle or Maven
  wrapper. Say which you picked, and report each tier with its own result and count.
  The trap on a tiered repo is a discovered command that quietly covers the fast tier only — a bare
  `pytest` can deselect every slow test and come back green in a second. If the counts do not add up
  to the whole suite, you ran the wrong thing: say so rather than reporting a pass.
  If e2e needs local services (Docker), say so and run it only if they are up; otherwise report the
  e2e suite as **not run**, never as passed. A tier that is declared but has no tests is reported as
  **empty**, never as passed.
- If the suite is red, **stop here** and report the failures. Do not write a shipped status or
  delete anything over a red suite; the user decides whether the failures are pre-existing.

These two checks stand in for CI. When the repo has CI that runs e2e on the integration branch,
delete this step from the skill.

### 4. Debt pass

Invoke `/debt-check` if it is installed. Otherwise, do a bounded manual pass over the change's diff
only: `ASSUMPTION NEEDED` markers with no owner or date, `TODO`/`FIXME` added by the change,
parameters or config keys the diff added that nothing reads. Report, do not fix.

### 5. Status headers — feature lane only

- **PRD:** insert or replace a line directly under the H1:
  `> Status: shipped — <release-ref>, <YYYY-MM-DD>`. If the PRD already carries a `Status:` line
  saying `planned`, `in progress` or similar, replace it. Never append a second one.
- **ADRs the change introduced or amended:** ensure a `Status:` line exists under the H1. Use
  `Status: Accepted — shipped <release-ref>, <YYYY-MM-DD>`. If an ADR states that it supersedes
  another, make sure the superseded ADR carries `Status: Superseded by ADR-NNNN`. Do not rewrite
  any other part of an ADR.

Show the exact header lines you intend to write before writing them.

**Rework lane:** skip this step. The tracker holds the ticket's status; this skill does not post to
it. Remind the user in step 7 to close the ticket there.

### 6. Prune

**Feature lane:** list every file under `<spec-dir>/issues/` and `<spec-dir>/reviews/` and ask for
confirmation. On `close` (or `prune`), `git rm` them. Keep `prd.md`, `release/`, `notes/`. Git
history is the archive; do not create an `archive/` directory. If the user answers `keep issues`,
leave `issues/` in place and prune only `reviews/`.

**Rework lane:** list every file under `<spec-dir>` and ask for confirmation. On `close`,
`git rm -r <spec-dir>`. Nothing survives in the repo: the ticket is the record and git history holds
the spec and the rounds.

Any `Status:` field inside an issue stub or ticket file is moot once it is deleted, so do not edit
those files before deleting them.

### 7. Report and propose

Post a closing summary: lane, stale doc claims found, fixture and suite results, debt findings,
status lines written (feature lane), files pruned. Then draft **one** commit message covering the
status headers and the prune, in the project's commit style — single subject line, imperative, ≤72
chars, no trailers — in the form `Close <name>`, and wait for the user's confirmation. Doc fixes
from step 2 are a separate commit if the user chose to make them. In the rework lane, end with a
one-line reminder to close the ticket in the tracker.

## Hard constraints

- **Never modify code.** This skill touches `<spec-dir>`, `docs/adr/` status lines, and nothing
  else. Stale doc claims are reported, not edited, unless the user says `fix`.
- **Never commit, push or tag.** Draft the message; the user commits.
- **Never delete without the confirmation in step 6.**
- **Never mark shipped or prune over a red or unrun suite** without the user explicitly overriding
  with `status <text>` (feature lane) or `close anyway` (either lane).
- **Never invent a commit range.** If the change's commits cannot be identified, ask.

## Cheat sheet

| User input | Skill action |
|---|---|
| `close` / `prune` | Confirm step 6: `git rm` the listed files or directory. |
| `keep issues` | Feature lane: prune review rounds only; leave `issues/` in place. |
| `skip tests` | Skip step 3's suite run; record `suite: not run` in the PRD status line and the summary. |
| `status <text>` | Feature lane: override the Status line text (e.g. to record a known-red suite). |
| `close anyway` | Proceed to steps 5–6 despite a red or unrun suite; the summary records the override. |
| `fix` | After step 2, edit the listed stale doc claims in place. |
| `show <file>` | Read and surface a file's contents. |
| `hold` / `stop` | Stop after the current step; nothing further is written. |
| `abort` | Discard; restore any status lines already written with `git checkout -- <file>`. |

## Output

Feature lane: edits `<spec-dir>/prd.md` and `docs/adr/*.md` status lines, removes
`<spec-dir>/issues/` and `<spec-dir>/reviews/`. Rework lane: removes `<spec-dir>`. Both: prints a
summary plus a proposed `Close <name>` commit message. Nothing else.
