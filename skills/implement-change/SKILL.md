---
name: implement-change
description: Serial, unattended implementation of a change as a sequence of commits on its change branch. Works for both lanes — a feature (work items are the issue stubs under ./docs/features/<name>/issues/) or a rework ticket (the numbered steps in ./docs/rework/<KEY>/ticket.md) — resolving the lane from which spec exists. Walks the items one at a time on the branch the planning session cut: one subagent per item, the item's new tests and the unit tier, commit on green. Integration and e2e tiers run once at the end. HITL items stop for a human. A second mode, --fix, answers a review round: it fixes the blocking findings (one commit each) and the nits (one commit) in-session behind the same gates, and skips re-grill findings. Use when the spec is frozen and the user wants batch implementation, or when a review round has come back with findings to fix.
---

# /implement-change

Drives **serial, fully-automated** execution of a change's work items as a sequence of commits on a dedicated branch. The implementer is the second leg of the workflow: **s1 plans**, **s2 implements**, **s3 reviews** (`review-change`), then `close-change` closes the branch and the merge request follows.

Two lanes share this skill. A **feature** is planned with `grill-change` → `to-prd` → `to-md-issues` and its work items are issue stubs. A **rework** (a refactor, cleanup or ticket-driven improvement that leaves behaviour unchanged) is planned with `grill-change <KEY>` → `to-rework <KEY>` and its work items are the numbered steps in one spec file. The loop, the halt conditions, the state file and the subagent discipline are identical; the lanes differ in where the items come from, how they are ordered, and what "green" means.

## Quick start

```
/implement-change                       # all items in the single auto-detected change
/implement-change <feature>             # all issue stubs under docs/features/<feature>/
/implement-change <feature> 01 03       # subset by issue number
/implement-change PROJ-123              # all steps in docs/rework/PROJ-123/ticket.md
/implement-change PROJ-123 2 3          # subset by step number
/implement-change --continue            # resume after a HITL or test-failure halt
/implement-change <name> --fix          # fix the findings of the latest review round
```

Zero-config for simple cases; fully configurable via `<repo-root>/.implement-change.config.json` (see [REFERENCE.md](REFERENCE.md)).

## Spec resolution — the change name and `<spec-dir>`

The change name is the first non-numeric positional arg, else `default_feature` from config, else single-change auto-detect (exactly one directory with `issues/` under `docs/features/`, or exactly one directory with `ticket.md` under `docs/rework/`; if both lanes have exactly one candidate, halt and ask). Resolve the spec from it, in this order:

1. `./docs/features/<name>/prd.md` exists → **feature lane**. `<spec-dir>` is `./docs/features/<name>/`. Work items = every `*.md` under `<spec-dir>/issues/`. Context doc = `prd.md`. Branch default `feature/<name>`.
2. `./docs/rework/<name>/ticket.md` exists → **rework lane**. `<spec-dir>` is `./docs/rework/<name>/`. Work items = the `### N. <title>` subsections under `## Steps` in `ticket.md` (parsing in REFERENCE.md). Context doc = `ticket.md` itself (its `## Acceptance` section is the bar). Branch default `rework/<name>`.
3. Neither exists → halt and print both paths checked and the current branch. The spec lives on the change branch, so running from the integration branch is the usual cause. Legacy fallbacks (`temp/issues/<name>/`, `temp/prds/<name>_prd.md`) are honoured for the feature lane only.

Numeric args filter the resolved items to that subset in either lane.

## Conventions

- **Commit messages:** `<NN>: <item title>` (e.g. `01: Fix X-pinch snap-back on the Lap Detail speed graph`, `00: Characterisation tests for the orders merge`). Override via `features.<name>.commit_template` in config.
- **Branch:** `feature/<name>` or `rework/<name>`, cut from `integration_branch` in the planning session, which committed the spec to it. This skill works on it and never creates it. Override the name via `features.<name>.feature_branch_template` / `rework_branch_template`.
- **HITL detection** applies to a step body exactly as to a stub (see REFERENCE.md).

## Commits without a per-commit OK

The project standards say every commit is audited, proposed and confirmed. A run of this skill is the named exception, in both modes. The plan the user confirms before the first item (workflow step 5, fix-mode step 3) authorises the run's commits; the test gate before each one stands in for the per-commit OK; and the audit the standards ask for is done by `review-change` on the whole branch, not per commit. Nothing else inherits the exception: outside a run, and for the spec and close commits, the standards' protocol applies.

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

**Resolving a tier's command.** The list above says which tier a test is in, not how to run it. The command is `tests.<tier>.all` / `tests.<tier>.select` from the config. For a tier the config gives no command for, draft one from what the project already documents (the project `CLAUDE.md` commands section, `package.json` scripts, `pyproject.toml`, the Gradle or Maven wrapper) and **ask the user once, at the plan step**, to confirm or correct it; never run a guessed command. A tier the user says the project does not have is reported as unrun, never as passing. Offer to save the answers to `.implement-change.config.json`, so a later session, `--fix` and `close-change` do not ask again. On yes, write the file and commit it by itself before the first item (`git add .implement-change.config.json`, `git commit -m "Add the implement-change test commands"`), so it is not swept into an item's commit; the plan covers that commit. On no, the answers last for this session.

*Legacy config:* with no `tests` block, `test_command` is the `select` command for an item's new tests, and `test_command_all` runs in place of the unit tier before every commit. Step 7 then has nothing to run and says so.

**When each tier runs** is set by the workflow, not here: the per-item gate is step 6, the deferred tiers are step 7. The per-item gate is deliberately narrow: it catches what is cheap to catch and defers the expensive tiers to a single gate at the end. An item that breaks an integration test is caught before `review-change`, not before its own commit — a trade of per-item precision for run-wide speed. The one slow thing that does run per item is a rework's step 0 tests, because they are what "unchanged" means.

## Workflow

1. **Resolve scope.** Resolve the spec (above), then read every in-scope item in full.
2. **Order the items.**
   - *Feature lane:* extract `## Blocked by` from every stub (`#03`, `03`, or a path), build a DAG, flatten it: level 0 first, then level 1, etc.; within a level, by `NN`. Parallelism is dropped entirely.
   - *Rework lane:* steps are already ordered by the planner; execute in numeric order, no DAG. **Step 0 must exist and must be the characterisation tests** that pin current behaviour. If `ticket.md` has no `### 0.` step, halt: a rework whose acceptance is "behaviour unchanged" cannot start without the tests that define "unchanged". Say so and point at `to-rework`.
3. **Pre-flight checks,** in this order.
   - The current branch must be `<branch>` (`feature/<name>` or `rework/<name>`). If it is not, **stop**: name the current branch and tell the user to check out `<branch>`, or, if it does not exist, to cut it from `<integration_branch>` and commit the spec to it as the planning session should have (with the cut sequence the freeze skill prints, which carries an uncommitted spec across). Never create the branch and never start on the integration branch. This check comes first so that a dirty tree on the wrong branch is never answered with "commit".
   - Verify the working tree is clean (`git status --porcelain` returns nothing). If not, **stop** and tell the user to stash or commit — the skill will not start on a dirty tree. A `--continue` after a halt is the exception: the halted item's work is in the tree by design, and it is verified and committed before anything else.
   - Resolve the integration branch the way `review-change` and `close-change` do, and use that one ref wherever a command below says `<integration_branch>`: the remote-tracking ref `<remote>/<integration_branch>` when `git rev-parse --verify -q` finds it, otherwise the local branch — where `<remote>` is `origin` if that remote exists, else the repo's only remote (with several remotes and no `origin`, ask), fetched explicitly with a best-effort `git fetch <remote>`. If neither exists, **stop**. A stale local branch makes other people's merged `NN:` commits look like this change's.
   - Verify the state file is ignored: `git check-ignore -q .claude/implement-change-state.json`. If not, **stop** and tell the user to add it to `.gitignore`; `git add -A` would commit it.
4. **Sync, and look for an earlier run.**
   - `git pull --ff-only` — best-effort; ignore when offline or when the branch has no upstream. If it cannot fast-forward, **stop** and let the user reconcile.
   - If the branch already has item commits (`git log <integration_branch>..<branch>` shows subjects matching the commit template), this is not a `--continue` or `--fix` run and no item numbers were given, **stop** and ask the user whether to resume (`--continue` semantics, requires a state file for this change) or to run only the remaining items. Never silently re-run an item that already has a commit. If no items remain, the run goes straight to step 7: that is the way back to the deferred tiers when a session ended on a red one and left no state file.
5. **Plan + confirm.** Show the user: lane, spec path, branch name, the serial order of items, which are HITL, and the command for each test tier — asking for any the config does not give (see "Resolving a tier's command"). Wait for explicit OK before launching the first item. On the OK, write the state file (shape in REFERENCE.md), replacing one left by a finished run or by another change; it is rewritten at every status change and every halt from here on.
6. **For each item, in order:**
   - **HITL?** Stop. Surface the item, quote the "why HITL" reason from it, tell the user to drive it manually on the branch (the main checkout is already on it), then resume when they say `done` (or `--continue`, which means the same here). What happens next depends on what the human's work left behind:
     - *A dirty tree.* Verify it as an item — auto-verify below, from the planning-files check on, with no agent report to read — and commit it under the item's `NN: <title>` subject. The skill commits, not the user: later skills find implemented items by that subject.
     - *A clean tree, with new commits since the halt.* The user committed it themselves. Run the unit tier and record `HEAD` as the item's commit. If none of the new commits carries the item's subject, say that the amend skills will not recognise the item as implemented.
     - *A clean tree, no new commits.* Ask the user to confirm the item was a decision or an action outside the repo. On yes, record it `done` with no commit and advance.
   - **AFK?** Note `git rev-parse HEAD` and `git branch --show-current`, then spawn **one** Agent subagent (prompt template in REFERENCE.md). No `isolation: "worktree"` — the subagent works in-place on the branch. It is told to leave changes **uncommitted** so the skill controls when and how to commit.
   - Wait for the subagent to return. Save its return message in the state file, so a halt can be resumed in another session.
   - **Auto-verify, in this order:**
     1. **The branch and `HEAD` are where they were.** Compare both with the values noted before the spawn. The prompt forbids commits and branch commands, and this is where that is checked. If the agent committed, **halt**: the user undoes it with `git reset --soft <noted-sha>`, which puts the work back in the tree, and continues. If the branch changed, **halt** and let the user sort it out.
     2. **The planning files are untouched.** `git status --porcelain -- <spec-dir> CONTEXT.md docs/adr` must print nothing. If the subagent edited the PRD, an issue stub, `ticket.md`, the glossary or an ADR — ticking its own acceptance boxes counts — **halt**: the implementer does not rewrite the bar it is measured against. The user restores the paths the check printed — `git restore --source=HEAD --staged --worktree -- <paths>` for every path not marked `??`, which also undoes a staged edit or a staged new file, then `git clean -fd -- <paths>` for the `??` ones — and continues, or takes the edit to the planning session.
     3. Surface the agent's summary, open questions, and any unsatisfied acceptance criteria. If any criterion is reported unsatisfied, or any open question is listed, **halt and ask the user** — do not auto-commit. The user's answer to an open question is what clears this halt: `continue` accepts the work as it stands, `push back: <answer>` sends the answer to a new attempt.
     4. **Run the item's new tests** — every test file the agent reported, whatever tier it belongs to, with that tier's `select` command. Check the tier the agent reported rather than trust it: a file that builds a real session or container is integration whatever it was called. Fast feedback, and proof the item actually added tests. A rework step after step 0 normally reports none; skip this run in that case and say so.
     5. *Rework lane, every step after step 0:* run **step 0's characterisation tests**, whatever tier they are in. Step 0's commit is found from the log, with or without a state file: `git log --format=%H --grep='^00: ' <integration_branch>..HEAD`; its files are `git show --name-only --format= <sha>` — the tests and their fixtures, since step 0 touches no production code. The tests are what "behaviour unchanged" means, and they are usually integration-tier, so the unit tier alone would let a behaviour-breaking step commit. Then check the step did not touch them: `git status --porcelain` must show none of step 0's files, fixtures included. If it does, **halt** — that is the refactor changing behaviour and hiding it.
     6. **Run the whole unit tier** with `tests.unit.all`. Do **not** run the integration or e2e tiers here — they run once at the end (see step 7). Both lanes commit only on a green unit tier.
     7. *Rework step 0 only:* the characterisation tests must pass against the **unrefactored** code, which is what the tree contains at this point. If they fail, they pin the wrong behaviour — halt; do not "fix" the code to make them pass.
     8. On green, surface `git diff --stat` and a one-line file-list summary as informational output (no approval gate).

     **A red run in 4, 5, 6 or 7 halts:** report the output verbatim. The user resumes with `--continue` (after fixing manually: the item is re-verified from the top of this list and committed, never carried uncommitted into the next item), `push back: <reason>` (respawn) or `skip` (abandon the item; not step 0). `merge anyway` is not offered when step 0's tests are what failed, in 5 or in 7 (see "Push-back / abandon flow").
   - **Auto-commit onto the branch:**
     ```
     git add -A
     git commit -m "<NN>: <item title>"
     ```
     Use the configured `commit_template` if present. If there is nothing to commit — the agent reported success but the tree is clean — **halt** and say so: it lost its work or did none. Record the SHA in the state file under the item's `commit` field and set its status: `pending-verification` if the item carries a verification gate (next bullet), otherwise `merged`.
   - **Verification gate.** If the item carries `Verification: HITL` (matched as REFERENCE.md says), it was implemented, tested and committed as normal (the code is complete and it is `Type: AFK`), but its status is `pending-verification`. Auto mode cannot perform on-device or real-hardware verification, so green tests do **not** mean confirmed. Do not halt the run for it.
   - **Advance.** Spawn the next item's subagent immediately: no user prompt, just a one-line "Advancing to <NN>: <slug>".
7. **Run the deferred tiers once.** After the last item is committed or skipped, and before declaring the branch ready. If every item was skipped the run made no commit and there is nothing to gate: say so and stop.
   - **Run the whole integration tier** with `tests.integration.all`.
   - On green, **run the whole e2e tier** with `tests.e2e.all`.
   - If either fails, **halt and report verbatim**, naming the tier and which item most plausibly introduced the failure (`git log -S` on the failing symbol narrows it). The branch keeps its commits, so `push back` and `skip` do not apply here: they only discard uncommitted work. The fix is a new commit, made in this session like a fix-mode finding — unit tier green, then `git add -A` and `git commit -m "Fix: <what failed>"`, covered by the run's plan — and then this gate runs again. In a later session, `--continue` on a state file whose items are all finished resumes here.
   - If a tier is not configured and cannot be resolved by convention, say so explicitly and name it as unrun. Never report a tier as passing when it was skipped. Record each tier's result in the state file.
8. **End state.** Once the deferred tiers are green:
   - Surface the final `git log <branch> --not <integration_branch> --oneline` showing every commit.
   - Tell the user: "Branch `<branch>` is ready. Review it with `review-change <name>` in a fresh session, and answer each round's findings here with `implement-change <name> --fix`. When a round is clean (`merge-ready`), merge `<integration_branch>` into this branch if it has moved; a merge with a conflict, or one that touches a file this branch changed, needs one more round. Then run `close-change <name>` on this branch and open the merge request."
   - **List any `pending-verification` items** with their commit SHAs and the human-verification criteria, flagged as requiring real-device verification before merge.
   - The skill **never** auto-merges the branch into the integration branch.

## Fix mode — `--fix`

The return leg of the review loop: `review-change` writes `round-NN.md`, `--fix` answers it, `review-change` runs again. Run it in the session that implemented the change.

```
/implement-change <name> --fix
```

Unlike a normal run it spawns **no subagents**. The fixes are small and the session that built the change already holds the context they need. In a fresh session, read the spec and every file a finding names before touching it.

1. **Pre-flight.** As steps 3 and 4 of the workflow: on the change branch, clean tree, pulled. Then read the highest `<spec-dir>/reviews/round-NN.md` — the round is found, not passed as a path. Halt if there is none: rounds are local to the checkout that wrote them, so either that checkout's `reviews/` directory is copied here or there is nothing to fix. If the round's `**Head reviewed:**` SHA is not `HEAD`, say which commits landed since and ask before going on. A finding listed under "Carried over" is a one-line pointer: read its full text in the round it names, and refer to it by round and id (`round-01 B2`).
2. **Sort the findings.**
   - **Fix:** every finding under the round's Blocking and Nits sections, including still-open ones under "Carried over from prior rounds" — whatever its provenance. A `pre-existing` finding sits under Blocking only when a rework ticket targets it, and then it is this branch's job.
   - **Skip:** every Re-grill finding, and every finding marked `downstream-of` one — its foundation is about to change, and a patch now is reviewed twice. Also the items that appear only under "Follow-up, outside this branch".
   - **Hand back:** the Questions. They are for the user to answer; do not guess an answer and code to it.
3. **Plan + confirm.** Show the three lists and the command for each test tier, asking for any the config does not give, and wait for explicit OK. The user can drop a finding (`skip B2: <reason>`); it is reported as declined. Say then that this session cannot settle it: a declined finding and the answer to a Question count only once the user gives them in the reviewer session (`skip blocking #N`, `answer Q#: …`), because the next round re-checks every prior finding and this session never writes where the reviewer reads.
4. **Fix each Blocking finding, in the round's order, one commit each.**
   - Make the fix. Where the finding is wrong behaviour, write the failing test first, as `tdd` does.
   - If the right fix turns out to change a decision — a glossary term, an ADR clause, behaviour a rework must preserve — stop work on that finding, discard the attempt (`git reset --hard HEAD && git clean -fd`) and report it as `needs re-grill`; the round file is already written and this session may not edit it, so the user carries it: to `grill-change <name>`, pasting this report, and to the reviewer at the start of the next round. Do not patch it.
   - Verify as a normal item: the planning files are untouched, the tests the fix added or changed pass, a rework fix passes step 0's characterisation tests, then the **whole unit tier** passes.
   - On red, **halt and report** verbatim, and stay in this step. The user answers `continue` (they fixed it by hand: re-verify, then commit under this finding's subject), `skip <id>: <reason>` (discard with `git reset --hard HEAD && git clean -fd`, report as declined, go on) or `abort` (discard the same way and stop). Fix mode keeps no state file, so `--continue` does not apply to it; `hold` leaves the halt as it is, to be answered in this session; and there is no `merge anyway` — a red fix is never committed.
   - On green: `git add -A`, then `git commit -m "Fix: <finding title>"`.
5. **Fix all the Nits, one commit.** Fix and verify them one at a time, uncommitted, then `git add -A` and `git commit -m "Fix: review nits"`. Here `skip <id>` must not reset the tree — that would throw away the nits already fixed. Reverse that one nit's edits by hand, report it as declined, and carry on.
6. **Run the deferred tiers once** — integration, then e2e — as step 7 of the workflow, halting on red, except that nothing is recorded: fix mode keeps no state file. A tier that could not run is named as unrun in the report.
7. **Report.** One line per finding in the round: `B1 fixed <sha>`, `N3 declined — <reason>`, `B4 needs re-grill`, `R1 skipped — re-grill`, `Q1 open — for the user`. Then name the next step: `review-change <name>` in the reviewer session, or `grill-change` first if a Re-grill finding is open. The report goes to the conversation only. Never write it into the round file or anywhere the reviewer preloads: the next round re-verifies each finding at its recorded location, cold.

Re-running `--fix` on the same round is safe once the tree is clean: a Blocking finding whose `Fix: <finding title>` commit already sits after the round's reviewed head is done, and so are the Nits once `Fix: review nits` sits there. Only what is left is fixed, and the deferred tiers run again only if this run made a commit. A finding that was declined or reported as needing a re-grill left no commit, so a re-run lists it again; the user skips it again.

The hard constraints below apply unchanged — above all, step 0's tests are never weakened to make a rework fix pass. Two more hold in this mode: **never patch a Re-grill finding**, and **never edit a round file**.

## Push-back / abandon flow

Because there are no per-item branches or worktrees, abandoning an item's uncommitted work is `git reset --hard HEAD && git clean -fd` against the branch. The `clean` matters: `reset` alone leaves the item's new files — its tests, usually — to be swept into the next item's commit. Ignored files (review rounds, the state file) survive both.

- **`push back: <reason>`** (or `redo: <reason>`) — discard the rejected changes as above; respawn the subagent with the original prompt plus the push-back extension in REFERENCE.md; loop back to auto-verify when it returns.
- **`skip`** — discard as above; mark the item `skipped` in state; advance. Step 7 still runs for whatever the run did commit. An item **Blocked by** a skipped one cannot be built: name it, and skip it too unless the user says otherwise. The branch is left without that item's work. *Rework lane:* step 0 cannot be skipped.
- **`merge anyway`** — commit despite failing tests / unsatisfied criteria, with ` [merge-anyway: <reason>]` appended to the subject. Record the SHA *and* the override reason in state. Use sparingly. It is **not available** at three halts, where it would commit exactly what the hard constraints forbid: a planning file the subagent edited, step 0's tests failing (in step 0 itself or after a later step), and a step that touched step 0's files.

Because the working tree is the only place rejected work lives, an `abort` while changes are uncommitted will discard them. The skill confirms before `abort` if the working tree is non-empty.

## Hard constraints

- **Never auto-merge the branch into the integration branch.** Always stop at the branch.
- **Never push** any branch.
- **Never run subagents on HITL items.** Stop and hand off to the user.
- **Never auto-commit when the item's new tests or the unit tier fail, acceptance criteria are unsatisfied, or the agent left an open question,** without the user's explicit answer. Halt instead.
- **Never commit a rework step over failing step 0 tests.** `merge anyway` does not apply; a rework that changes behaviour is not a rework.
- **Never declare the branch ready before the deferred tiers have run.** Integration and e2e run once at the end; a tier that was skipped is reported as unrun, never as passing.
- **Never run the full integration or e2e tier per item.** That is the cost this ranking exists to avoid.
- **Never start on a dirty working tree, and never on the integration branch.** Pre-flight halts before the first item.
- **Never create the branch.** The planning session cut it; if it is missing, so is the spec.
- **Never start a rework without step 0.** Characterisation tests come first or the run does not begin.
- **Never commit a subagent's edit to a planning file.** The PRD, the issue stubs, `ticket.md`, `CONTEXT.md` and the ADRs change only in the planning session.
- **Never let a subagent modify, weaken or delete step 0's tests or their fixtures.** If the diff of a later step touches them, halt — that is the refactor changing behaviour and hiding it.
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
| `continue` / `--continue`               | Resume from the persisted state. Re-evaluate the halt condition; if cleared, verify and commit the halted item, then advance. With every item finished, resume at step 7. |
| `push back: <reason>` / `redo: <reason>`| Discard and respawn the halted item — see "Push-back / abandon flow". |
| `merge anyway`                          | Commit despite the failure, recording the override — same section. Not available in fix mode, nor at the planning-file and step 0 halts. |
| `skip`                                  | Discard the halted item and advance — same section. Not available for rework step 0. |
| `show <file>` / `cat <file>`            | `Read` the file and surface contents.                                                                     |
| `run tests`                             | Re-run the halted item's own new tests against the working tree.                                           |
| `run unit` / `run all tests`            | Run the whole unit tier (`tests.unit.all`) against the working tree.                                      |
| `run integration`                       | Run the whole integration tier (`tests.integration.all`) on demand, ahead of the end-of-run gate.          |
| `run e2e`                               | Run the whole e2e tier (`tests.e2e.all`) on demand.                                                       |
| `hold` / `stop`                         | Persist state, do nothing further. User resumes with `--continue` later.                                  |
| `done` (after manual HITL work)         | Same as `continue` at a HITL halt: commit a dirty tree as the item, record the user's own commits, or record a decision as `done` with no commit — see step 6. |
| `abort`                                 | Stop the run. Uncommitted work is discarded after confirmation; the branch keeps its commits and the user decides what to do with it. |

## Reference

See [REFERENCE.md](REFERENCE.md) for lookup material only: the configuration schema, rework step parsing, the subagent prompt template (with the rework directive and the push-back extension), the state-file shape and HITL detection. The procedure is this file; REFERENCE.md does not restate it.
