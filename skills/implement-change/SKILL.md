---
name: implement-change
description: Serial, unattended implementation of a change as a sequence of commits on a dedicated branch. Works for both lanes — a feature (work items are the issue stubs under ./docs/features/<name>/issues/) or a rework ticket (work items are the numbered steps in ./docs/rework/<KEY>/ticket.md) — resolving the lane from which spec exists. Cuts the branch from the integration branch, walks the items one at a time, spawning one subagent per item, running the item's new tests and then the unit tier when it returns, and committing on green before advancing. The integration and e2e tiers run once at the end of the run, not per item. HITL items still stop for human action. No worktrees, no parallelism. Use when the spec is frozen and the user wants batch implementation that lands as one commit per item.
---

# /implement-change

Drives **serial, fully-automated** execution of a change's work items as a sequence of commits on a dedicated branch. The implementer is the second leg of the workflow: **s1 plans**, **s2 implements**, **s3 reviews** (`review-change`), then `close-change` closes.

Two lanes share this skill. A **feature** is planned with `grill-change` → `to-prd` → `to-md-issues` and its work items are issue stubs. A **rework** (a refactor, cleanup or ticket-driven improvement that leaves behaviour unchanged) is planned with `grill-change <KEY>` → `to-rework <KEY>` and its work items are the numbered steps in one spec file. The loop, the halt conditions, the state file and the subagent discipline are identical; the lanes differ in where the items come from, how they are ordered, and what "green" means.

## Quick start

```
/implement-change                       # all items in the single auto-detected change
/implement-change <feature>             # all issue stubs under docs/features/<feature>/
/implement-change <feature> 01 03       # subset by issue number
/implement-change PROJ-123              # all steps in docs/rework/PROJ-123/ticket.md
/implement-change PROJ-123 2 3          # subset by step number
/implement-change --continue            # resume after a HITL or test-failure halt
```

Zero-config for simple cases; fully configurable via `<repo-root>/.implement-change.config.json` (see [REFERENCE.md](REFERENCE.md)).

## Spec resolution — the change name and `<spec-dir>`

The change name is the first non-numeric positional arg, else `default_feature` from config, else single-change auto-detect (exactly one directory with `issues/` under `docs/features/`, or exactly one directory with `ticket.md` under `docs/rework/`; if both lanes have exactly one candidate, halt and ask). Resolve the spec from it, in this order:

1. `./docs/features/<name>/prd.md` exists → **feature lane**. `<spec-dir>` is `./docs/features/<name>/`. Work items = every `*.md` under `<spec-dir>/issues/`. Context doc = `prd.md`. Branch default `feature/<name>`.
2. `./docs/rework/<name>/ticket.md` exists → **rework lane**. `<spec-dir>` is `./docs/rework/<name>/`. Work items = the `### N. <title>` subsections under `## Steps` in `ticket.md`; the step body is everything up to the next `###`. Context doc = `ticket.md` itself (its `## Acceptance` section is the bar). Branch default `rework/<name>`.
3. Neither exists → halt and print both paths checked. Legacy fallbacks (`temp/issues/<name>/`, `temp/prds/<name>_prd.md`) are honoured for the feature lane only.

Numeric args filter the resolved items to that subset in either lane.

## Conventions

- **Commit messages:** `<NN>: <item title>` (e.g. `01: Fix X-pinch snap-back on the Lap Detail speed graph`, `00: Characterisation tests for the orders merge`). Override via `features.<name>.commit_template` in config.
- **Branch:** `feature/<name>` or `rework/<name>` cut from `integration_branch` at the start of the run. Override via `features.<name>.feature_branch_template` / `rework_branch_template`.
- **HITL detection** applies to a step body exactly as to a stub (see REFERENCE.md).

## Test tiers

Tests are ranked into three tiers. The ranking decides what runs per commit and what runs once at the end, so a slow tier cannot tax every item in the run.

| Tier | Definition | Typical cost |
|---|---|---|
| **unit** | No process boundary. No real IO, database, JVM, container, browser or network. Mocked at the boundary. | milliseconds |
| **integration** | Real but local infrastructure — database, Spark/JVM, docker, message broker, filesystem fixtures. No external network. | seconds to minutes |
| **e2e** | Full stack. External services, real credentials, deployed environments. | minutes and up |

**Resolving a test's tier**, in precedence order:

1. **Config.** `tests.<tier>.all` / `tests.<tier>.select` in `.implement-change.config.json` (schema in REFERENCE.md). Where a project declares these they are authoritative and nothing is inferred.
2. **Project convention.** A path segment (`tests/unit/`, `tests/integration/`, `tests/e2e/`) or a marker the project already uses (`@pytest.mark.integration`, `@Tag("e2e")`, a build target).
3. **The behavioural definition above**, applied by inspection when neither of the first two exists. A test that constructs a real session, container, driver or connection is integration however it is filed.

A repo whose slow tests are unlabelled has no cheap unit tier. Say so once at the start of the run and name the cost, rather than silently paying it on every item.

**When each tier runs:**

- **Per item, before its commit:** the item's own new tests (whatever tier they are), then the **whole unit tier**. Nothing else.
- **Once at the end of the run,** after the last item commits: the **whole integration tier**, then the **whole e2e tier**. A failure in either halts before the branch is declared ready.

The per-item gate is deliberately narrow: it catches what is cheap to catch and defers the expensive tiers to a single gate at the end. An item that breaks an integration test is caught before `review-change`, not before its own commit — a trade of per-item precision for run-wide speed.

## Workflow

1. **Resolve scope.** Resolve the spec (above), then read every in-scope item in full.
2. **Order the items.**
   - *Feature lane:* extract `## Blocked by` from every stub (`#03`, `03`, or a path), build a DAG, flatten it: level 0 first, then level 1, etc.; within a level, by `NN`. Parallelism is dropped entirely.
   - *Rework lane:* steps are already ordered by the planner; execute in numeric order, no DAG. **Step 0 must exist and must be the characterisation tests** that pin current behaviour. If `ticket.md` has no `### 0.` step, halt: a rework whose acceptance is "behaviour unchanged" cannot start without the tests that define "unchanged". Say so and point at `to-rework`.
3. **Pre-flight checks.**
   - Verify the working tree is clean (`git status --porcelain` returns nothing). If not, **stop** and tell the user to stash or commit — the skill will not start on a dirty tree.
   - Verify the integration branch exists locally.
4. **Create the branch.**
   ```
   git fetch                                          # best-effort; ignore if no remote
   git checkout <integration_branch>
   git pull --ff-only                                 # best-effort; ignore on offline / no upstream
   git checkout -b <branch>                           # feature/<name> or rework/<name>
   ```
   If `<branch>` already exists locally, **stop** and ask the user whether to resume on it (`--continue` semantics, requires a non-empty state file) or rename / delete it and start fresh. Never silently reuse a pre-existing branch.
5. **Plan + confirm.** Show the user: lane, spec path, branch name, the serial order of items, and which are HITL. Wait for explicit OK before launching the first item.
6. **For each item, in order:**
   - **HITL?** Stop. Surface the item, quote the "why HITL" reason from it, tell the user to drive it manually on the branch (the main checkout is already on it), then resume with `--continue` after they say `done`.
   - **AFK?** Spawn **one** Agent subagent (prompt template in REFERENCE.md). No `isolation: "worktree"` — the subagent works in-place on the branch. It is told to leave changes **uncommitted** so the skill controls when and how to commit.
   - Wait for the subagent to return.
   - **Auto-verify, in this order:**
     1. Surface the agent's one-line summary, open questions, and any unsatisfied acceptance criteria. If any criterion is reported unsatisfied, **halt and ask the user** — do not auto-commit.
     2. **Run the item's new tests** — every test file the agent reported, whatever tier it belongs to, with that tier's `select` command. Fast feedback, and proof the item actually added tests. A rework step after step 0 normally reports none; skip this run in that case and say so.
     3. **Run the whole unit tier** with `tests.unit.all`. Do **not** run the integration or e2e tiers here — they run once at the end (see step 8). Both lanes commit only on a green unit tier. If either run fails, **halt and report** verbatim. The user resumes with `--continue` (after fixing manually), `push back: <reason>` (respawn) or `skip` (abandon the item).
     4. *Rework step 0 only:* the characterisation tests must pass against the **unrefactored** code, which is what the tree contains at this point. If they fail, they pin the wrong behaviour — halt; do not "fix" the code to make them pass.
     5. On green, surface `git diff --stat` and a one-line file-list summary as informational output (no approval gate).
   - **Auto-commit onto the branch:**
     ```
     git add -A
     git commit -m "<NN>: <item title>"
     ```
     Use the configured `commit_template` if present. Record the SHA in the state file under the item's `commit` field.
   - **Verification gate.** If the item carries `Verification: HITL`, implement, test and commit it as normal (the code is complete and it is `Type: AFK`), but mark it `pending-verification` in state. Auto mode cannot perform on-device or real-hardware verification, so green tests do **not** mean confirmed. Do not halt the run for it.
   - **Advance.** Spawn the next item's subagent immediately.
7. **Run the deferred tiers once.** After the last item commits, and before declaring the branch ready:
   - **Run the whole integration tier** with `tests.integration.all`.
   - On green, **run the whole e2e tier** with `tests.e2e.all`.
   - If either fails, **halt and report verbatim**, naming the tier and which item most plausibly introduced the failure (`git log -S` on the failing symbol narrows it). The branch keeps its commits — the fix is a new commit or a `push back` on the offending item, not a silent pass.
   - If a tier is not configured and cannot be resolved by convention, say so explicitly and name it as unrun. Never report a tier as passing when it was skipped.
8. **End state.** Once the deferred tiers are green:
   - Surface the final `git log <branch> --not <integration_branch> --oneline` showing every commit.
   - Tell the user: "Branch `<branch>` is ready. Review it with `review-change <name>` in a fresh session, merge when a round comes back clean, then run `close-change <name>` on `<integration_branch>`."
   - **List any `pending-verification` items** with their commit SHAs and the human-verification criteria, flagged as requiring real-device verification before merge.
   - The skill **never** auto-merges the branch into the integration branch.

## Push-back / abandon flow

Because there are no per-item branches or worktrees, abandoning an item's work is a single `git reset --hard HEAD` against the branch:

- **`push back: <reason>`** — `git reset --hard HEAD` to discard the rejected changes; respawn the subagent with the user's reason appended; loop back to auto-verify when it returns.
- **`skip`** — `git reset --hard HEAD`; mark the item `skipped` in state; advance. The branch is left without that item's work. *Rework lane:* step 0 cannot be skipped.
- **`merge anyway`** — commit despite failing tests / unsatisfied criteria. Record the SHA *and* the override reason in state. Use sparingly; in the rework lane it means committing a behaviour change, which the reviewer will treat as Blocking.

Because the working tree is the only place rejected work lives, an `abort` while changes are uncommitted will discard them. The skill confirms before `abort` if the working tree is non-empty.

## Hard constraints

- **Never auto-merge the branch into the integration branch.** Always stop at the branch.
- **Never push** any branch.
- **Never run subagents on HITL items.** Stop and hand off to the user.
- **Never auto-commit when the item's new tests or the unit tier fail, or acceptance criteria are unsatisfied,** without explicit `merge anyway`. Halt instead.
- **Never declare the branch ready before the deferred tiers have run.** Integration and e2e run once at the end; a tier that was skipped is reported as unrun, never as passing.
- **Never run the full integration or e2e tier per item.** That is the cost this ranking exists to avoid.
- **Never start on a dirty working tree.** Pre-flight check halts before any branch creation.
- **Never start a rework without step 0.** Characterisation tests come first or the run does not begin.
- **Never let a subagent modify, weaken or delete step 0's tests.** If the diff of a later step touches them, halt — that is the refactor changing behaviour and hiding it.
- **Serial, never parallel.** Even when multiple AFK items sit at the same dependency level, spawn them one at a time — each subagent must start from the *post-commit* state of the previous item.

## Soft rules (skim each before proceeding)

- Subagent /tdd quality varies. On the first sign of test cheating (tests-that-pass-rather-than-tests-that-capture-scenarios), halt and let the user push back. Don't auto-commit through obvious shortcuts.
- No mid-run steering of subagents — bad output means respawn with a corrected prompt, not patch in-flight.
- Surface unsatisfied acceptance criteria loudly. Halt rather than auto-committing.
- The skill is "fully auto" between halt conditions, but every halt is a real handoff. State the halt reason in plain language, quote the relevant item or test output, and name the resume command.
- Shape is part of done. If a step's diff leaves a touched file longer, more nested or more duplicated than it found it, say so in the informational summary; the reviewer will flag it, and the user may prefer to `push back` now.

## Cheat sheet

UX tokens during a halt.

| User input                              | Skill action                                                                                              |
|-----------------------------------------|-----------------------------------------------------------------------------------------------------------|
| `continue` / `--continue`               | Resume from the persisted state. Re-evaluate the halt condition and advance if cleared.                   |
| `push back: <reason>` / `redo: <reason>`| `git reset --hard HEAD`, respawn the halted item's subagent with the user's reason appended.              |
| `merge anyway`                          | Auto-commit the working-tree changes despite failing tests / unsatisfied criteria. Record the override reason in state. |
| `skip`                                  | `git reset --hard HEAD`, mark the halted item `skipped`, advance. Not available for rework step 0.        |
| `show <file>` / `cat <file>`            | `Read` the file and surface contents.                                                                     |
| `run tests`                             | Re-run the halted item's own new tests against the working tree.                                           |
| `run unit` / `run all tests`            | Run the whole unit tier (`tests.unit.all`) against the working tree.                                      |
| `run integration`                       | Run the whole integration tier (`tests.integration.all`) on demand, ahead of the end-of-run gate.          |
| `run e2e`                               | Run the whole e2e tier (`tests.e2e.all`) on demand.                                                       |
| `hold` / `stop`                         | Persist state, do nothing further. User resumes with `--continue` later.                                  |
| `done` (after manual HITL work)         | Verify the HITL changes are committed on the branch; mark the item `merged`; advance.                     |
| `abort`                                 | Stop the run. The branch is left in place at its current state; the user decides what to do with it.     |

## Advanced

See [REFERENCE.md](REFERENCE.md) for the subagent prompt template (including the rework directive), post-subagent commands, state-file shape, HITL detection rules, step parsing, and the configuration schema.
