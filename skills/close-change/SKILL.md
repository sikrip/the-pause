---
name: close-change
description: Close a reviewed change on its own branch, before the merge request, so that what merges already matches reality. Works for both lanes — a feature (spec ./docs/features/<name>/prd.md) or a rework ticket (spec ./docs/rework/<KEY>/ticket.md). Greps the docs for identifiers the change removed or renamed, confirms test fixtures are tracked and the whole suite passes, runs the debt check, then in the feature lane sets a Status header on the PRD and touched ADRs and deletes the issue stubs, and in the rework lane deletes the whole docs/rework/<KEY>/ directory (the tracker is the record). Also drafts the merge request description. Use on the change branch after review-change returns a clean round and before the merge request is opened. Requires a change name as input. Commits only on the user's OK; never pushes or opens the merge request.
---

# /close-change

The last step before the merge request: **s1 plans**, **s2 implements**, **s3 reviews**, and then
someone closes. Without this step the planning artifacts outlive the change: PRDs stay "planned" for
merged code, issue stubs and rework specs pile up with no status, and docs keep naming tables and
hosts the change removed. A change is not ready for its merge request until this skill has run
clean.

It runs **on the change branch**, and its output is the branch's last commit. That way the checks
below can still hold the merge, the merge request carries the code and its closed-out docs together,
and nothing is committed to the integration branch outside a merge request.

This is the **local-files-only** variant, like `review-change`. It edits files under the spec
directory and `docs/adr/`, runs the project's test command, and never talks to a tracker.

## Required input — the change name, and how the spec is resolved

The user must provide a **change name**: a kebab-case feature name or a ticket key (`PROJ-123`,
`LAP-42`). If invoked without one, ask before proceeding. Resolve the spec from it, in this order:

1. `./docs/features/<name>/prd.md` exists → **feature lane**. `<spec-dir>` is
   `./docs/features/<name>/`.
2. `./docs/rework/<name>/ticket.md` exists → **rework lane**. `<spec-dir>` is
   `./docs/rework/<name>/`.
3. Neither exists → halt and print both paths checked and the current branch. The spec lives only
   on the change branch, so being on another branch is the usual cause; on a branch that is already
   closed, the rework spec is gone and there is nothing to close.

`<spec-dir>` is used below for everything the skill reads, edits or deletes.

Optional positional arg:

- **Integration branch.** The merge request's target, used as the diff base. Default:
  `integration_branch` in the `implement-change` config file (`.implement-change.config.json`, or
  `.claude/implement-change.config.json`) when one exists, else `develop`.
  Resolve it once and use that one ref wherever a command below
  says `<integration_branch>`: the remote-tracking ref `<remote>/<integration_branch>` when
  `git rev-parse --verify -q` finds it, otherwise the local branch — where `<remote>` is `origin` if
  that remote exists, else the repo's only remote (with several remotes and no `origin`, ask),
  fetched explicitly with a best-effort `git fetch <remote>`. A local integration branch that nobody
  fast-forwarded is stale, and a stale base makes other people's merged work look like this
  change's.

## Preconditions — halt on any failure

1. The spec resolves (above), and the change is not closed already: a PRD that carries
   `> Status: implemented` means the close commit is on this branch. Halt and point at "After the
   close commit" below; this skill is not re-run on a closed branch.
2. The current branch is not the integration branch. The branch that is checked out, and on which
   the spec resolved, is the change branch; the close is a commit on it.
3. The change has been reviewed as it stands: the highest `<spec-dir>/reviews/round-NN.md` carries
   a `**Verdict:**` of `merge-ready`, and its `**Head reviewed:**` SHA is `HEAD` — or everything
   after it is a trivial sync (below). If there is no round, the verdict is anything else, or other
   commits landed after the reviewed head, halt and name which: closing unreviewed work is what this
   precondition prevents. The user can override with `close anyway`. Rounds are local, gitignored
   files, so a checkout that never ran the review has none.

   **A trivial sync needs no round.** The commits after the reviewed head are acceptable when all
   three hold, and the merge request description then says "synced after review: clean, no overlap":
   - every commit in `git log --first-parent <head-reviewed>..HEAD` is a merge of the integration
     branch;
   - `git show --remerge-diff --format= <merge-sha>` is empty for each, i.e. no conflict was
     resolved;
   - no file is in both `git diff --name-only <integration_branch>...<head-reviewed>` (what the
     branch changed) and `git diff --name-only <mb-before>..<mb-after>` (what arrived), the merge
     bases being `git merge-base <integration_branch> <head-reviewed>` and
     `git merge-base <integration_branch> HEAD`. `CONTEXT.md` and `docs/adr/` do not count: nearly
     every planned change edits them, and a conflict in them is caught by the bullet above.

   A conflict or a shared file means the merge could have changed what the reviewer approved, so it
   gets the sync round.
4. The branch is up to date with the integration branch:
   `git merge-base --is-ancestor <integration_branch> HEAD` succeeds. If it does not, halt: the user
   merges the integration branch in — merge, never rebase — and re-runs this skill. Precondition 3
   then accepts a clean, non-overlapping merge as it is and asks for one more `review-change` round,
   the sync round, only otherwise. That keeps this skill's suite and docs grep honest about what
   will land, and puts the conflict resolutions in front of the cold reviewer. The user can override
   with `close anyway`.
5. The working tree is clean. Do not close on top of uncommitted work.

## Process

### 1. Inventory — read, then report

Read, in full:

- Everything under `<spec-dir>`: the PRD and `issues/*.md`, or `ticket.md`; every
  `reviews/round-*.md`; anything under `release/` or `notes/` if present.
- `docs/adr/*.md` files that name the change or that the spec cites.
- The change's commits: `git log <integration_branch>..HEAD --oneline`.

Post one short message to the conversation: change name, lane, spec path, change branch, number of
issue stubs or steps, number of review rounds, ADRs touched, number of commits, and the test
command you intend to run (see step 3). Under 10 lines.

### 2. Docs drift — grep for what the change removed or renamed

From the change's diff (`git diff <integration_branch>...HEAD`), collect identifiers that
were **deleted or renamed**: function and class names, table and column names, env vars, config
keys, hostnames, file paths, CLI flags, version strings. Ignore identifiers that were only added.
This step matters most for rework tickets that remove dead code — the docs are where its names
survive.

Grep for each across `docs/`, `README*`, `CLAUDE.md`, `CONTEXT.md` and `.env.example`, excluding
`<spec-dir>` itself and `docs/adr/`. Every hit is a stale claim. List them with file and line; do
not fix them silently. The user decides which to fix now (`fix`) and which to file.

Separately, grep the same paths except `CLAUDE.md` — the standards write their own examples with
placeholders, so it would report one on every close — for **unfilled template placeholders**:
angle-bracket markers a slice left for a human to complete, e.g. `<to measure`, `<deploy date`,
`<run id`, `<TBD`, `<owner`.
A change whose spec deferred a figure to deploy day closes over them silently otherwise, because
they are additions and so invisible to the removed-identifier grep above. Report every hit. A
marker that can be filled now means the change is not closed. One that can only be filled after the
merge — a deploy date, a run id — cannot hold a close that runs before it: list it under Follow-ups
in the merge request description, with who fills it.

### 3. Fixtures and the full suite

- **Fixtures:** grep `tests/` for references to files under `tests/fixtures/` (or the project's
  equivalent) and check each against `git ls-files`. Report every referenced fixture that is
  untracked or missing. This is the failure that silently disables e2e suites after a refactor.
- **Suite:** run **every tier**, e2e included. This is the merge gate, and it is not a repeat of
  `implement-change`'s gates: the sync merge, and any commit made outside that skill, are code no
  full gate has seen. The command for each tier is `tests.<tier>.all` in
  `.implement-change.config.json`. For a tier the config gives no command for, do as
  `implement-change` does: draft one from what the project documents (the project `CLAUDE.md`
  commands section, `package.json` scripts, `pyproject.toml` / pytest, Gradle or Maven wrapper) and
  ask the user to confirm or correct it before running anything. Name the commands in step 1's
  message, and report each tier with its own result and count.
  The trap on a tiered repo is a discovered command that quietly covers the fast tier only — a bare
  `pytest` can deselect every slow test and come back green in a second. If the counts do not add up
  to the whole suite, you ran the wrong thing: say so rather than reporting a pass.
  If e2e needs local services (Docker), say so and run it only if they are up; otherwise report the
  e2e suite as **not run**, never as passed. A tier that is declared but has no tests is reported as
  **empty**, never as passed.
- If the suite is red, **stop here** and report the failures. Do not write a status or delete
  anything over a red suite; the user decides whether the failures are pre-existing.

These two checks stand in for CI. When the repo has CI that runs every tier, e2e included, on the
merge request, delete this step from the skill.

### 4. Debt pass

Invoke `/debt-check` on the change's diff (`git diff <integration_branch>...HEAD`) if it is
installed. Otherwise, do a bounded manual pass over that diff only: `ASSUMPTION NEEDED` markers with
no owner or date, `TODO`/`FIXME` added by the change, parameters or config keys the diff added that
nothing reads. Report, do not fix.

### 5. Status headers — feature lane only

- **PRD:** insert or replace a line at the very top of the file (under the H1 if it has one):
  `> Status: implemented — <YYYY-MM-DD>`. If the PRD already carries a `Status:` line
  saying `planned`, `in progress` or similar, replace it. Never append a second one.
- **ADRs the change introduced or amended:** ensure a `Status:` line exists under the H1. Use
  `Status: Accepted — <YYYY-MM-DD>`. If an ADR states that it supersedes
  another, make sure the superseded ADR carries `Status: Superseded by ADR-NNNN`. Do not rewrite
  any other part of an ADR.

The status describes the branch, so it becomes true of the integration branch at the merge and not
before; the merge commit is the record of when. Show the exact header lines you intend to write
before writing them.

**Rework lane:** skip this step. The tracker holds the ticket's status; this skill does not post to
it. Remind the user in step 7 to close the ticket there once the merge request has merged.

### 6. Prune

**Feature lane:** list every file under `<spec-dir>/issues/` and ask for confirmation. On `close`
(or `prune`), `git rm` them. Keep `prd.md`, `release/`, `notes/`. The branch's history and the merge
request are the archive — under a squash merge, the merge request alone; do not create an `archive/`
directory. If the user answers `keep issues`, leave `issues/` in place.

**Rework lane:** list every tracked file under `<spec-dir>` and ask for confirmation. On `close`,
`git rm -r <spec-dir>`. Nothing survives in the repo: the ticket and the merge request are the
record, which is why step 7 copies the spec's bar into the description.

**Review rounds, both lanes:** leave `<spec-dir>/reviews/` on disk. The rounds were never committed,
so there is nothing to prune from the branch, and this skill needs them again if the close is
reverted and redone. They are deleted by hand once the merge request has merged; say so in step 7.

Any `Status:` field inside an issue stub or ticket file is moot once it is deleted, so do not edit
those files before deleting them.

### 7. Report, propose the commit, draft the merge request description

Post a closing summary: lane, stale doc claims found, fixture and suite results, debt findings,
status lines written (feature lane), files pruned. Then draft **one** commit message covering the
status headers and the prune, in the project's commit style — single subject line, imperative, ≤72
chars, no trailers — in the form `Close <name>`, and wait for the user's confirmation. Doc fixes
from step 2 are a separate commit if the user chose to make them.

Then draft the **merge request description**, from what step 1 read. The review rounds are never
committed, and in the rework lane the prune removes the spec from the branch tip, so this
description is where the human reviewer sees them:

- **What the change does** — two or three lines from the PRD's problem and solution, or the ticket's
  summary. Rework lane: the ticket key.
- **What stays unchanged** — rework lane only: the spec's `## Acceptance` and `## Current behaviour`
  sections, copied verbatim, not summarised. They are the bar the reviewer judges the refactor
  against, and after the prune this is the only place they can read it.
- **Review** — how many rounds ran; one line per Re-grill and Blocking finding with how it was
  resolved; nits and questions as counts.
- **Tests** — each tier with its result and count, exactly as step 3 reported them, `not run` and
  `empty` included.
- **Human verification** — every item marked `Verification: HITL`, with what a human still has to
  confirm before the merge.
- **Follow-ups** — `pre-existing` findings from the rounds, stale doc claims the user chose to file
  and debt findings.

Print it to the conversation for the user to paste. End by naming what is left: the close commit,
which this skill makes on the user's OK; then the user's own steps — push the branch, open the
merge request, and delete the local `<spec-dir>/reviews/` once it has merged. In the rework lane,
add a one-line reminder to close the ticket in the tracker then too.

## After the close commit

This skill is finished, and it is not re-run on a closed branch: the merge request is now the review
loop. What the human
reviewers ask for takes one of two routes, and the test is whether it changes what is being built.

- **A fix** — a bug, a name, a missed case; the spec still describes the change. It is fixed on the
  branch like on any merge request and reviewed by the humans who asked. The close commit's suite
  result does not cover it, so the tiers are re-run by CI or with the project's own test command,
  not by this skill.
- **A change to what is built** — new or different behaviour, a different boundary, a reversed
  decision. That is a planning change and the spec has to say it before any code does, or the next
  cold review will flag the requested change as a deviation. One route, in this order:
  1. `git revert` the close commit. It restores the spec and removes the status line; the rounds are
     still on disk. Planning cannot be re-entered on a closed branch: the amend skills recognise a
     change in progress by the files the close removed.
  2. `grill-change <name>` on the branch, with the feedback pasted, then the freeze skills, which
     amend the spec in place.
  3. `implement-change <name> <NN>` for the new items, `review-change` (a full sweep, because the
     spec changed), the sync, and this skill again.

  **Rework lane:** feedback that asks a rework to change behaviour is not an amendment, and the
  close commit is **not** reverted for it. A rework in
  progress is never converted into a feature. It is finished and merged as the behaviour-preserving
  change it is, or abandoned, and the behaviour change is planned afterwards as a separate feature.

## Hard constraints

- **Never modify code.** This skill touches `<spec-dir>`, `docs/adr/` status lines, and nothing
  else. Stale doc claims are reported, not edited, unless the user says `fix`.
- **Never commit without the user's OK on the drafted message,** as the standards' commit protocol
  says. **Never push, tag or open the merge request:** those are the user's.
- **Never delete without the confirmation in step 6.**
- **Never write a status or prune over a red or unrun suite** without the user explicitly overriding
  with `skip tests`, `status <text>` (feature lane) or `close anyway` (either lane).
- **Never close on the integration branch.** The close reaches it through the merge request.

## Cheat sheet

| User input | Skill action |
|---|---|
| `close` / `prune` | Confirm step 6: `git rm` the listed files or directory. |
| `keep issues` | Feature lane: leave `issues/` in place; the close commit is the status headers only. |
| `skip tests` | Skip step 3's suite run. An explicit override: record `suite: not run` in the PRD status line, the summary and the merge request description. |
| `status <text>` | Feature lane: override the Status line text (e.g. to record a known-red suite). |
| `close anyway` | Proceed despite a missing or non-`merge-ready` review round, or code that landed after the reviewed head (precondition 3), or a branch behind the integration branch (precondition 4), or to steps 5–6 despite a red or unrun suite; the summary and the merge request description record the override. |
| `fix` | After step 2, edit the listed stale doc claims in place. |
| `show <file>` | Read and surface a file's contents. |
| `hold` / `stop` | Stop after the current step; nothing further is written. |
| `abort` | Discard everything this skill did: `git reset --hard HEAD`. The tree was clean at precondition 5, so only the skill's own edits and staged removals go. |

## Output

Feature lane: edits `<spec-dir>/prd.md` and `docs/adr/*.md` status lines, removes
`<spec-dir>/issues/`. Rework lane: removes the tracked files under `<spec-dir>`. Both: prints a
summary, a proposed `Close <name>` commit message and a draft merge request description. Nothing
else.
