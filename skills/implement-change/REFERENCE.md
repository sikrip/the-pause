# /implement-change — reference

Lookup material only: the config schema, how a rework spec is parsed, the subagent prompt, the state file and HITL detection. The procedure — what runs when, what halts, what each user answer does — lives in [SKILL.md](SKILL.md) and is not restated here. A rule that appears in both files will drift; if you find one, SKILL.md is right and this copy is deleted.

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
| `integration_branch` | `develop` | The branch the change branch was cut from in the planning session and the merge request will target. How it is resolved to a ref is in SKILL.md's pre-flight. |
| `tests.<tier>.all` | see below | Runs the whole tier. |
| `tests.<tier>.select` | the tier's `all` with `{tests}` appended | Runs named test files in that tier. `{tests}` is replaced by the space-separated paths. |
| `test_command` / `test_command_all` *(legacy)* | unset | Pre-tier config, read only when `tests` is absent so existing configs keep working. What each runs is in SKILL.md's "Test tiers" section. |
| `features.<name>.issue_dir` | `docs/features/<name>/issues/` (falls back to `temp/issues/<name>/`) | Feature lane only. Directory containing the issue stubs. |
| `features.<name>.context_docs` | feature lane: auto-discover `docs/features/<name>/prd.md`, falling back to `temp/prds/<name>_prd.md` and `docs/<name>*.md`; rework lane: `docs/rework/<name>/ticket.md` | Paths attached to every subagent prompt. |
| `features.<name>.feature_branch_template` | `feature/{feature}` | Branch template in the feature lane. Placeholder: `{feature}` (the change name). |
| `features.<name>.rework_branch_template` | `rework/{feature}` | Branch template in the rework lane. Placeholder: `{feature}` (the change name, i.e. the ticket key). |
| `features.<name>.commit_template` | `{nn}: {title}` | Template for the per-item commit subject line. Placeholders: `{nn}` (zero-padded item number), `{slug}` (kebab-cased title), `{title}` (the item's title), `{feature}` (change name). |

**No built-in test command.** With no `tests` block and no legacy keys, and for any tier a `tests` block leaves out, the user is asked for the command as SKILL.md's "Test tiers" section says.

With no config file at all: the integration branch is `develop`, the branch is `feature/<name>` or `rework/<name>`, the commit subject is `<NN>: <item title>`, and the change name comes from the argument or single-change auto-detect.

## Rework spec: step parsing

`docs/rework/<KEY>/ticket.md` is written by `to-rework`. The parts this skill reads:

- `## Acceptance` — the bar for the whole change. For rework it normally states that observable behaviour is unchanged and names the characterisation tests that define "unchanged". Attached to every subagent prompt.
- `## Steps` — one `### N. <title>` subsection per work item, `N` starting at 0. The body runs to the next `###` or the end of the section. `### 0.` is always the characterisation tests and must be present.

Each step body may carry the same markers as an issue stub (matched as "HITL detection" below says): `Type: HITL`, `Verification: HITL`, a `## Blocked by` line (ignored in the rework lane — steps are already ordered). Steps are never inferred from the ticket prose.

## Subagent prompt template

Tool call shape, one call per message:

```
Agent(
  subagent_type   = "general-purpose",
  run_in_background = false,
  description     = "Implement <NN>: <slug>",
  prompt          = <bundle>,
)
```

The `description` field stays short. The heavy briefing goes in `prompt`.

The `<bundle>` is assembled in this exact order:

1. **The work item.** Feature lane: the full issue stub text, inline. Rework lane: the spec's title line (`# <KEY> — <ticket title>`), the full `## Acceptance` section, then the full text of the current step, inline — in that order, so the subagent reads the bar before the task.
2. A context line. Resolve `<context_docs>` from config or auto-discovery. If non-empty, emit:
   ```
   Context: read <comma-separated paths> before starting. Read the project root CLAUDE.md too if present.
   ```
   If there are no context docs, just emit `Context: read the project root CLAUDE.md if present.`
3. The full scenario-test guidance, inline:

   ```
   Use the /tdd skill for the red-green-refactor loop. You are unattended: where it
   says to confirm or get approval from the user, decide from the work item and name
   the decision in your return message. Write scenario tests first.

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
   modify, weaken or delete them. Run them before you finish, whatever tier they
   are in: <step-0 test files>. If one fails, the refactor is wrong, not the
   test. Their fixtures are protected the same way. A step after step 0
   normally adds no tests of its own. Do not widen
   scope beyond this step. If the step cannot be completed without changing
   behaviour, stop and report that as an unsatisfied acceptance criterion rather
   than changing it.
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

   DO NOT edit the planning files — the PRD, the issue stubs, the rework ticket,
   CONTEXT.md, the ADRs — not even to tick an acceptance checkbox. Report which
   criteria you satisfied in your return message instead. If one of them is wrong
   or cannot be met, say so there; do not change it.

   Hold your own diff to the project CLAUDE.md code-shape rules and name anything
   you left unresolved in your return message. DO NOT COMMIT. Leave all changes
   uncommitted in the working tree. The orchestrator runs the tests and commits
   on your behalf when they pass.
   ```
8. The return-message directive:
   ```
   Return in your final message: (1) one-paragraph summary of what was built,
   (2) the list of files you changed (paths only), (3) the list of new test files
   you wrote (paths only), (4) open questions, (5) any acceptance criteria you
   could not satisfy. Do NOT report a branch name or commit — the orchestrator
   owns those.
   ```

### Push-back extension

When an item is respawned after `push back: <reason>`, the original bundle is extended with:

```
Previous attempt was rejected. Reason: <user's reason verbatim>.
Address this specifically before proceeding. Re-read the work item and the
relevant context docs. Start fresh — the working tree has been reset.
```

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
    "01": { "status": "in-review",     "halt_reason": "unit tier: 2 failures in test_orders_merge.py",
            "report": "<the agent's return message, verbatim>" },
    "02": { "status": "pending" }
  },
  "current_issue": "01",
  "updated_at": "2026-09-04T11:30:00Z"
}
```

`lane` is `feature` or `rework`; `spec` is the resolved spec path. The `issues` map holds items in both lanes (the key name is kept for compatibility with existing state files). Statuses: `pending` | `running` | `in-review` | `merged` (committed) | `done` (a HITL decision or out-of-repo action, no commit) | `skipped` | `hitl-pending` | `blocked-on-hitl` | `pending-verification`.

Optional fields: `report` holds the agent's return message for the item being verified, so its new test files, open questions and unsatisfied criteria survive into another session; an item committed with `merge anyway` carries `"override": "<reason>"`; once the end-of-run gate has run the file carries `"tiers": {"integration": "passed", "e2e": "failed"}`, and a red tier there is the halt `--continue` resumes at when every item is finished. Otherwise `--continue` resumes at `current_issue`. Fix mode does not use this file.

## HITL detection

Both markers are matched at the start of a line, with or without bold on the label — the issue template writes `**Type:** HITL`, the rework template `Type: HITL`:

- **Decision gate:** `grep -E '^\*{0,2}Type:\*{0,2} +HITL'`
- **Verification gate:** `grep -E '^\*{0,2}Verification:\*{0,2} +HITL'`

An item is also a decision gate if its stub or step body contains `**HITL**` as a literal token, or a `## HITL` section header (a `#### HITL` header inside a step body counts too).
