# /implement-change — reference

## Configuration

The skill reads a project-level config file. **Every field is optional** — without a config the skill falls back to the defaults listed below.

### Path

`<repo-root>/.implement-change.config.json`

(or `<repo-root>/.claude/implement-change.config.json` if the repo keeps `.claude/` un-gitignored). The repo-root path wins if both exist.

The state file at `.claude/implement-change-state.json` stays gitignored — it's per-developer-per-session and must never be committed.

### Schema

```json
{
  "default_feature": "graph-improvements",
  "integration_branch": "develop",
  "tests": {
    "unit":        { "all": ".venv/bin/pytest -m 'not integration and not e2e' -q",
                     "select": ".venv/bin/pytest {tests} -q" },
    "integration": { "all": ".venv/bin/pytest -m integration -q",
                     "select": ".venv/bin/pytest {tests} -q" },
    "e2e":         { "all": ".venv/bin/pytest tests/e2e -q",
                     "select": ".venv/bin/pytest {tests} -q" }
  },
  "features": {
    "graph-improvements": {
      "issue_dir": "docs/features/graph-improvements/issues/",
      "context_docs": [
        "docs/features/graph-improvements/prd.md"
      ],
      "feature_branch_template": "feature/{feature}",
      "rework_branch_template": "rework/{feature}",
      "commit_template": "{nn}: {title}"
    }
  }
}
```

The `features` map is keyed by change name in both lanes — a rework ticket key (`PROJ-123`) is a valid key.

### Field semantics + defaults

| Field | Default | Notes |
|---|---|---|
| `default_feature` | unset | When unset, the skill uses single-change auto-detect or requires a positional change-name arg. |
| `integration_branch` | `develop` | The branch the work branch is **cut from** at the start of the run, and the branch the skill diffs against in informational output. The skill never merges into it. |
| `tests.<tier>.all` | see below | Runs the whole tier. `unit` runs before **every** commit; `integration` and `e2e` run **once**, at the end of the run, in that order. |
| `tests.<tier>.select` | the tier's `all` with `{tests}` appended | Runs named test files in that tier. `{tests}` is replaced by the space-separated paths the subagent reported. Used for the item's own new tests. |
| `test_command` *(legacy)* | `.venv/bin/pytest {tests} -v` | Pre-tier config. When `tests` is absent this is used for the item's new tests, unchanged. |
| `test_command_all` *(legacy)* | `.venv/bin/pytest tests/ --ignore=tests/e2e -v` | Pre-tier config. When `tests` is absent this runs before every commit and there is no end-of-run gate — the old behaviour, preserved so existing configs keep working. |
| `features.<name>.issue_dir` | `docs/features/<name>/issues/` (falls back to `temp/issues/<name>/`) | Feature lane only. Directory containing the issue stubs. |
| `features.<name>.context_docs` | feature lane: auto-discover `docs/features/<name>/prd.md`, falling back to `temp/prds/<name>_prd.md` and `docs/<name>*.md`; rework lane: `docs/rework/<name>/ticket.md` | Paths attached to every subagent prompt. |
| `features.<name>.feature_branch_template` | `feature/{feature}` | Branch template in the feature lane. Placeholder: `{feature}` (the change name). |
| `features.<name>.rework_branch_template` | `rework/{feature}` | Branch template in the rework lane. Placeholder: `{feature}` (the change name, i.e. the ticket key). |
| `features.<name>.commit_template` | `{nn}: {title}` | Template for the per-item commit subject line. Placeholders: `{nn}` (zero-padded item number), `{slug}` (kebab-cased title), `{title}` (the item's title), `{feature}` (change name). |

**Tier command defaults.** When `tests` is absent entirely, the skill falls back to the legacy pair above. When `tests` is present but a tier is missing, that tier is resolved by convention (`tests/unit/`, `tests/integration/`, `tests/e2e/`, or the project's own marker); if convention yields nothing, the tier is **unrun** and must be reported as such — never as passing.

A project with no tier separation at all has no cheap unit tier. State the cost once at the start of the run — *"the unit tier is the whole suite, N minutes, and runs before every commit"* — so the user can choose to tier the repo before continuing.

### Fallback behaviour (no config file)

- Integration branch is `develop`.
- Branch is `feature/<name>` or `rework/<name>` cut from `develop`.
- No tiers are declared, so the legacy pair applies: new tests via `.venv/bin/pytest {tests} -v`, then `.venv/bin/pytest tests/ --ignore=tests/e2e -v` before every commit, and no end-of-run tier gate.
- Commit message is `<NN>: <item title>`.
- Change name must come from a positional arg or single-change auto-detect.
- Feature lane: issue dir is `docs/features/<name>/issues/`; context docs auto-discovered as above. Rework lane: the spec is `docs/rework/<name>/ticket.md` and is the only context doc.

## Rework spec: step parsing

`docs/rework/<KEY>/ticket.md` is written by `to-rework`. The parts this skill reads:

- `## Acceptance` — the bar for the whole change. For rework it normally states that observable behaviour is unchanged and names the characterisation tests that define "unchanged". Attached to every subagent prompt.
- `## Steps` — one `### N. <title>` subsection per work item, `N` starting at 0. The body runs to the next `###` or the end of the section. `### 0.` is always the characterisation tests and must be present.

Each step body may carry the same markers as an issue stub: `Type: HITL`, `Verification: HITL`, a `## Blocked by` line (ignored in the rework lane — steps are already ordered). If `## Steps` or `### 0.` is missing, halt and point the user at `to-rework <KEY>`; do not infer steps from the ticket prose.

## Subagent prompt template

For each AFK item, spawn **one** Agent subagent. Spawns are strictly serial — never bundle multiple Agent tool calls in one message.

Tool call shape:

```
Agent(
  subagent_type   = "general-purpose",
  run_in_background = false,
  description     = "Implement <NN>: <slug>",
  prompt          = <bundle>,
)
```

**Notice: no `isolation: "worktree"`.** The subagent works in-place in the main checkout, which is already on the branch.

The `description` field stays short. The heavy briefing goes in `prompt`.

The `<bundle>` is assembled in this exact order:

1. **The work item.** Feature lane: the full issue stub text, inline. Rework lane: the ticket's one-paragraph summary, the full `## Acceptance` section, then the full text of the current step, inline — in that order, so the subagent reads the bar before the task.
2. A context line. Resolve `<context_docs>` from config or auto-discovery. If non-empty, emit:
   ```
   Context: read <comma-separated paths> before starting. Read the project root CLAUDE.md too if present.
   ```
   If there are no context docs, just emit `Context: read the project root CLAUDE.md if present.`
3. The full scenario-test guidance, inline:

   ```
   Use the /tdd skill. Write scenario tests first.

   Tests must describe plausible domain scenarios in language a domain reader
   would recognise — never the production code's structure, internal constants,
   or branch shape.

   BAD: test_calls_parse_response_with_empty_list  (names an internal helper)
   GOOD: test_returns_not_found_for_unknown_id  (names a domain outcome)

   BAD: test_calls_spark_createDataFrame_once  (names an internal Spark call)
   GOOD: test_rerunning_with_same_input_produces_identical_output  (names idempotency)

   BAD: test_sets_status_to_transient_on_timeout  (names an internal field)
   GOOD: test_transient_error_is_not_cached_so_next_run_retries  (names cache behavior)

   Rules:
   - Prefer real captured fixtures (PDFs, JSON, HTML) over synthetic per-test
     inputs whenever the scenario is "what happens in production". Synthetic
     inputs are fine only for genuinely abstract scenarios (empty input, missing
     required field).
   - One test = one scenario. If the test name needs "and" or commas, split it.
   - If a test failure ever invites "I'll just update the test to match the new
     code", that test was implementation-mirroring. Replace it with a scenario test.
   - If you cannot name a scenario in domain language, do NOT invent one by
     reading the production code. List the unclear scenarios under "open questions"
     in your final summary; the orchestrator will halt for the user to resolve them.
   ```
4. A dependency-hygiene directive, inline:
   ```
   If this item adds or upgrades a dependency, do NOT hand-pick a version
   string. Use the project's SDK/framework install resolver so the version
   matches the installed runtime — e.g. `npx expo install <pkg>` for Expo
   projects (never `npm install <pkg>@<ver>`); the framework's own add command
   otherwise. A hand-pinned version even one SDK too new can install,
   type-check, and bundle cleanly, yet silently fail native autolinking and
   crash at runtime ("Cannot find native module ..."). After adding, confirm
   the installed version matches the SDK's expected version before claiming
   done — and flag a verification gate if the dependency is native (it needs a
   real device/build to confirm).
   ```
5. The test-tier directive, inline. Substitute the resolved tier commands for this project:
   ```
   Tests are ranked into three tiers. Put each test you write in the right one,
   and run only what this directive tells you to run.

   - unit        — no process boundary: no real IO, database, JVM, container,
                   browser or network. Mocked at the boundary. Milliseconds.
   - integration — real but local infrastructure: database, Spark/JVM, docker,
                   message broker, filesystem fixtures. No external network.
   - e2e         — full stack, external services, real credentials.

   Decide a test's tier by: this project's config or existing markers/paths
   first; otherwise the behavioural definition above. A test that constructs a
   real session, container, driver or connection is integration however it is
   filed — if you write one, mark or place it so the tier commands select it.

   Prefer the cheapest tier that can express the scenario. Do not reach for real
   infrastructure to test logic that a boundary mock covers; do not fake away a
   boundary the scenario is actually about.

   Run, while you work:
     - your own new tests:  <tests.<tier>.select>
     - the whole unit tier: <tests.unit.all>

   Do NOT run the whole integration or e2e tier. They are slow and the
   orchestrator runs them once at the end of the whole change, not per item.
   Report which tier each new test file belongs to in your final summary.
   ```
6. **Rework lane only** — the rework directive, inline (omit in the feature lane):
   ```
   This is a rework step. Observable behaviour must not change. The
   characterisation tests from step 0 are the definition of "unchanged": never
   modify, weaken or delete them. If one fails, the refactor is wrong, not the
   test. Do not widen scope beyond this step. If the step cannot be completed
   without changing behaviour, stop and report that as an unsatisfied acceptance
   criterion rather than changing it.
   ```
   For step 0 itself, replace the directive with:
   ```
   This is step 0 of a rework: write characterisation tests that pin the CURRENT
   behaviour of the code the later steps will refactor, at the boundaries the
   Acceptance section names. Do not modify production code. The tests must pass
   against the code as it is now; a failing test here means you have described
   behaviour the code does not have.
   ```
7. The in-place workflow directive:
   ```
   You are working in-place on the current checkout. The branch is already checked out
   by the orchestrator — DO NOT create or switch branches. DO NOT run `git checkout`,
   `git switch`, `git branch`, or any other branch-mutating command.

   Follow the global CLAUDE.md commit/audit protocol BUT DO NOT COMMIT. Leave all
   changes uncommitted in the working tree. The orchestrator runs the tests and
   commits on your behalf when they pass.
   ```
8. The return-message directive:
   ```
   Return in your final message: (1) one-paragraph summary of what was built,
   (2) the list of files you changed (paths only), (3) the list of new test files
   you wrote (paths only), (4) open questions, (5) any acceptance criteria you
   could not satisfy. Do NOT report a branch name or commit — the orchestrator
   owns those.
   ```

## Post-subagent actions (Claude-driven, in the same conversation)

When the subagent returns, execute these steps without prompting the user — this is the "fully auto" loop. Halt and surface only on the conditions listed under "Halt conditions" below.

### 1. Surface the agent's output

In one short message: one-paragraph summary, file list (changed + new test files), open questions, unsatisfied acceptance criteria. If unsatisfied criteria are reported, **halt** — do not proceed.

### 2. Run the item's new tests

Group the new test file paths the agent reported by tier, and run each group with that tier's `select` command (legacy: `test_command`). The agent reports the tier of each file; verify rather than trust it — a file that builds a real session or container is integration whatever the agent called it. If the agent reported none (normal for a rework step after 0), say so and go to step 3. If tests fail, **halt** and report the output verbatim.

### 3. Run the unit tier

Run `tests.unit.all` (legacy: `test_command_all`). Both lanes commit only on a green unit tier: a feature may break something cheap to check, and a rework must leave everything green by definition. If it fails, **halt** and report verbatim.

Do **not** run the whole integration or e2e tier here. They run once, at the end of the run — see "End-of-run tier gate" below.

*Rework step 0:* the new characterisation tests have just run against the unrefactored code in step 2. If they failed there, halt without touching production code — the tests pin the wrong behaviour.

*Rework later steps:* additionally check `git diff --stat` against the branch head for any file under the test paths step 0 created. If step 0's tests were modified, **halt** — that is the refactor changing behaviour and hiding it.

### 4. Auto-commit on green

```
git add -A
git commit -m "<rendered commit_template>"
```

`<rendered commit_template>` substitutes `{nn}`, `{slug}`, `{title}`, `{feature}` from the current item. Default rendering: `01: Fix X-pinch snap-back on the Lap Detail speed graph`.

If there are no changes to commit (the agent reported success but the working tree is clean), **halt** and surface the inconsistency — the agent either lost its work or didn't actually do anything.

### 5. Update state and advance

- Read the new commit SHA: `git rev-parse HEAD`.
- Update `.claude/implement-change-state.json`: `"01": { "status": "merged", "commit": "<sha>" }`.
- Immediately spawn the next item's subagent. No user prompt, no review message — just a one-line "Advancing to <NN>: <slug>" log.

### End-of-run tier gate

After the last item commits, and before the branch is declared ready:

1. Run `tests.integration.all`. On failure, **halt and report verbatim**, naming the tier. Narrow the likely culprit with `git log -S <failing symbol> <branch> --not <integration_branch>` and name the item — do not guess without that evidence.
2. On green, run `tests.e2e.all`. Same halt behaviour.
3. Record both results in the state file under `tiers`: `{"integration": "passed", "e2e": "failed"}`.

A tier with no configured command and no resolvable convention is reported as **unrun**, explicitly, in the end-state message. Never let an unrun tier read as a pass.

Recovery from a failure here is a new commit on the branch (or `push back` on the item that `git log -S` identified), then re-run the gate. The branch keeps its per-item commits either way — the gate does not rewind them.

### Push-back

User says `push back: <reason>` (or close paraphrase):
1. `git reset --hard HEAD` to wipe the rejected uncommitted changes.
2. Respawn the item's subagent with the original prompt extended with:
   ```
   Previous attempt was rejected. Reason: <user's reason verbatim>.
   Address this specifically before proceeding. Re-read the work item and the
   relevant context docs. Start fresh — the working tree has been reset.
   ```
3. Status stays `in-review` until the respawned subagent returns and passes auto-verify.

### Skip

User says `skip`: `git reset --hard HEAD`; mark the item `skipped` in state; advance. Not available for rework step 0 — refuse and say why.

### Merge anyway

User says `merge anyway` (when halted on failing tests or unsatisfied criteria):
1. `git add -A && git commit -m "<rendered commit_template> [merge-anyway: <reason>]"`.
2. Record the override in state: `"01": { "status": "merged", "commit": "<sha>", "override": "<reason>" }`.
3. Advance.

## Halt conditions

The skill halts (surfaces the reason, persists state, awaits user input) on any of:

1. **HITL item.** Surface the item, quote the HITL reason. User drives manually; resumes with `done`.
2. **Subagent reports unsatisfied acceptance criteria.** User chooses `continue`, `push back: <reason>`, `skip`, or `merge anyway`.
3. **The item's new tests fail.** Same options.
4. **The unit tier fails.** Same options.
5. **The integration or e2e tier fails at the end-of-run gate.** The branch keeps its commits; the user fixes forward with a new commit, or `push back`s the item `git log -S` identifies, then the gate re-runs.
6. **Rework: step 0 tests fail against current code, or a later step modified step 0's tests.** `push back` or `abort`; `merge anyway` is available but recorded as a behaviour-change override.
7. **Working tree clean after subagent return.** Surface the inconsistency. Same options as 2.
8. **Merge conflict during pull/rebase pre-flight.** User resolves, resumes.
9. **Dirty working tree at start of run.** Pre-flight halt.
10. **Branch already exists at start of run.** Pre-flight halt; user picks resume vs fresh start.
11. **Rework spec has no `## Steps` or no `### 0.`.** Pre-flight halt; point at `to-rework <KEY>`.
12. **User says `hold` / `stop` / `abort`.** Persist state; do nothing further.

## State file

Path: `.claude/implement-change-state.json` (gitignored).

```json
{
  "feature": "PROJ-123",
  "lane": "rework",
  "spec": "docs/rework/PROJ-123/ticket.md",
  "feature_branch": "rework/PROJ-123",
  "integration_branch": "develop",
  "issues": {
    "00": { "status": "merged",        "commit": "abc123" },
    "01": { "status": "in-review",     "halt_reason": "full suite: 2 failures in test_orders_merge.py" },
    "02": { "status": "pending" }
  },
  "current_issue": "01",
  "updated_at": "2026-09-04T11:30:00Z"
}
```

`lane` is `feature` or `rework`; `spec` is the resolved spec path. The `issues` map holds items in both lanes (the key name is kept for compatibility with existing state files). Statuses: `pending` | `running` | `in-review` | `merged` | `skipped` | `hitl-pending` | `blocked-on-hitl` | `pending-verification`.

`--continue` reads this file and picks up at `current_issue`. If its status is `in-review` or `blocked-on-hitl`, re-evaluate the halt condition and either advance (if cleared) or re-surface the halt reason.

## HITL detection

An item is HITL if its stub or step body contains any of:

- `Type: HITL` in the body
- `**HITL**` as a literal token
- A `## HITL` section header (a `#### HITL` header inside a step body counts too)

When the skill stops at a HITL item, it must quote the HITL reason when surfacing — so the user immediately sees *why* the skill refused to automate it.

## Caveats baked into the procedure

1. **Subagent /tdd quality varies.** Tests passing is necessary but not sufficient — tests can pass while still being implementation-mirroring. Auto-commit on green is a deliberate trade-off: faster throughput, at the cost of reviewing the branch before merging.
2. **No mid-run steering.** Each subagent runs to completion. Bad output means `push back`, not patch in-flight.
3. **Skill never auto-merges the branch into the integration branch.** That's the user's call after review.
4. **Skill never pushes branches.** Push policy is per-branch and the user's decision.
5. **Working tree is the only place rejected work lives.** `git reset --hard HEAD` is destructive of uncommitted changes — the skill confirms before `abort` if the tree is non-empty.
6. **No `isolation: "worktree"` on subagent spawn.** The subagent has full access to the main checkout. This is the cost of dropping worktrees in exchange for serial simplicity.
7. **Serial spawning.** Spawn one subagent per message, never bundle.
8. **One unit-tier run per commit; integration and e2e once at the end.** The per-item gate stays cheap so it can run every time. A repo whose slow tests are unlabelled has no cheap tier to run — tier it, rather than dropping the gate or narrowing it to something that no longer means anything.
9. **The end-of-run tiers are the last gate before review.** An item that breaks an integration test is found there, not at its own commit. That is the deliberate trade: run-wide speed for per-item precision. Never report a tier that did not run as passing.
