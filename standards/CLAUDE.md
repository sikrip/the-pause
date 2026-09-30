# CLAUDE.md — Engineering Standards (stack-agnostic core)

The **portable core** of the methodology: how we work with AI on a codebase — phased workflow, code
shape, decision hygiene, commit protocol — independent of language or platform.

Copy this file to the **root of your repo** as `CLAUDE.md` (or `AGENTS.md`), then copy the topic
rules you need from [`rules/`](./rules/) into `<repo>/.claude/rules/`: `testing.md` always;
`python-tooling.md` and `databricks-pipelines.md` for Python / Databricks teams. Rules load alongside
this file at session start. Keep every instruction file under ~200 lines — never concatenate them.

> The skills shipped in this repo (`grill-change`, `to-prd`, `to-md-issues`, `to-rework`,
> `implement-change`, `review-change`, `close-change`, `tdd`, `diagnose`, `handoff`,
> `mutation-testing`) assume the conventions below. See the repo `README.md` for the end-to-end workflow.

## Agent skills

> This block is pre-configured so the bundled skills work out of the box — **no setup step, no
> external install.** Edit the paths if your repo differs.

### Issue tracker

Issues live as **local markdown files** under `docs/features/<feature-name>/issues/<NN>_<slug>.md`,
authored by `to-md-issues`. No GitHub/GitLab/Jira API calls — the issue files are committed to git
alongside the code that implements them.

### Domain docs

**Single-context** repo: one `CONTEXT.md` (a glossary — domain language only, no implementation
detail) at the repo root, and architectural decision records under `docs/adr/`. `grill-change`
maintains both inline as decisions crystallise; `tdd` and `diagnose` read them for domain context.

### Planning artifacts

Per-feature planning artifacts live under `docs/features/<feature-name>/`:
`prd.md` (from `to-prd`), `issues/*.md` (from `to-md-issues`), and `reviews/round-NN.md`
(from `review-change`). See **After shipping** for what happens to them once the feature lands.

## Project structure

Use a **src layout**. Business logic lives in `src/`, never in `apps/` or `scripts/` — those are thin
wrappers that call into `src/`. If an app needs a computation the core also performs, expose it from
`src/` and call it; never reimplement it app-side.

```
project_name/
├── src/project_name/   # source code — all business logic
├── tests/              # unit tests; e2e under tests/e2e/; fixtures under tests/fixtures/
├── apps/               # thin UI wrappers (call into src/)
├── scripts/            # operational scripts (call into src/)
├── docs/               # specs, design docs, ADRs, per-feature planning artifacts
└── CONTEXT.md          # domain glossary (single-context repos)
```

Every project must have a proper `.gitignore` from day one.

## Working with AI on complex changes

Anything beyond a one-file fix goes through the four-session flow — understand, freeze the spec,
implement, review, close — with a **human decision at each boundary**. The lane depends on whether
behaviour changes, not on size:

- **Feature lane** — new behaviour, a contract change, or a decision an ADR would record:
  `grill-change` → `to-prd` + `to-md-issues` → `implement-change` → `review-change` →
  `close-change`. Spec: `docs/features/<name>/`.
- **Rework lane** — a refactor, cleanup or ticket-driven improvement that leaves behaviour unchanged:
  `grill-change <KEY>` (reads the ticket) → `to-rework <KEY>` → the same three skills. Spec:
  `docs/rework/<KEY>/ticket.md`; step 0 is always the characterisation tests that define "unchanged".

The shared skills infer the lane from which spec exists. Without the skills, the same phases by hand —
research, plan, implement — stopping after each. The value is in the pause, not the speed.

**Review checks two things:** does the diff conform to the spec, and does each touched file still read
as designed rather than accreted. A conforming slice that leaves a 300-line function is not done.

**Earn understanding before automating.** For refactors in unfamiliar or tightly-coupled code, migrate
one representative piece by hand first, then use it as the seed for the plan. If you can't explain the
change to someone else, you haven't earned enough understanding to automate it.

**Subagents** are for independent read-only research only — never more than six per task.
**Prefer enforcement over prose:** whenever a rule can be checked mechanically — a lint rule, a
type-checker setting, a pre-commit hook — configure the tool instead of writing the rule here.
Instruction files are context, not enforcement.

## Code shape

### Comments explain the code, not the review

One line of *why*, plus a pointer (an ADR id, a ticket) when a decision stands behind it. The
argument, the rejected alternatives and the history live in `docs/adr/`, not in the source. Never
paste the same justification at two sites — extract the helper and comment it once. No workflow
vocabulary in code or tests: no "slice 09", "round-01", "step-zero", "kills mutant".

### No speculative surface

No parameters, config keys, CLI flags, config blocks or interfaces for a caller that does not exist
yet. Add them in the commit that adds the caller. "Stable surface for a future slice" is not a
reason.

### No guards for states upstream rules out

Before adding a null check, a try/catch, a "does this field exist" check, a re-validation of an
already-validated argument, or a "(safety)" dedup: name the caller that can produce that state. If
you cannot, do not add the check — document the upstream guarantee once, where it is provided.

### Entry points orchestrate only

A `main()`, controller, handler or job entry reads config, decides which path applies, and calls one
function per path. Metrics assembly, persistence scaffolding and field mapping live in helpers. An
entry point over roughly 50 lines or three levels of nesting gets split.

### File and function size

Files stay under ~500 lines and functions under ~50 statements. Crossing either is a prompt to
propose a split at a seam the module docstring can name, never a mechanical cut at the line. A test
file over ~500 lines means the unit under test is too big or the tests duplicate each other. The
linter holds the numbers where it can: ESLint `max-lines` / `max-lines-per-function`, Checkstyle
`FileLength` / `MethodLength`, ruff `C90` / `PLR0915` plus pylint `C0302`.

### Code duplication

Extract shared helpers, constants, and factory functions rather than copying code — in both
production code and tests. But don't over-abstract: if the extraction requires acrobatic
workarounds, duplication is acceptable, and a comment at the second site says so. Either way,
**ask the question** during review; don't skip it.

## Decision hygiene

**No magic numbers without origin.** If a value encodes a business rule, threshold, or tuning
parameter, annotate where it came from:
`if score > 0.7:   # threshold from <where/when> — revalidate if inputs change`

**No silent assumptions on business logic.** If you're choosing a default, window size, threshold,
or weight and don't know the rationale — say so explicitly, with an owner and a date, rather than
picking a plausible number:

```
# ASSUMPTION NEEDED (<owner>, <date>): what's the right cache TTL? Using 7 days as placeholder.
```

Markers have a lifecycle: at every release each one is resolved into an ADR decision, converted
into a ticket, or retired. "Inherited unchanged" is only written after checking history — values
drift. A marker older than one release with no owner is a defect.

**Configurable over hardcoded.** Values someone might want to tune (thresholds, batch sizes,
delays, feature flags) should be configuration with sensible defaults, not buried in business logic.
Never hardcode API URLs, service endpoints, or environment-specific values in business code.

## Testing

Lives in [`rules/testing.md`](./rules/testing.md) — install it in every repo. In one line: tests
verify plausible real-life scenarios in domain language, never the implementation; coverage follows risk.

## Commits

When the user asks to commit, follow a two-step protocol — never collapse it.

### 1. Audit the diff before drafting the message

An explicit audit pass on the actual diff, to catch what the linter and type checker cannot:

- **Residual duplication** that should be extracted — or that should stay duplicated. Either way,
  ask the question.
- **Dead leftovers**: unused imports, helpers, branches, comments from earlier iterations.
- **Inconsistencies**: mixed naming, formats, or conventions across files in the same commit.
- **Scope creep**: changes that don't fit the commit's stated focus and should be split off.
- **Removed surface**: if the change retires a feature, tier, flag or provider, its config keys,
  CLI flags, tests, scripts and docs go in the same commit. Grep the name before claiming done.
- **Missed cleanup**: anything the linter wouldn't flag but a careful reviewer would.

Surface findings even when minor. Don't skip the audit on "small" commits — that's where most
half-finished work hides.

### 2. Propose, then wait

Only after the audit, draft a short commit message — a single subject line (≤72 chars), imperative
mood, no body unless the *why* is non-obvious. No enumerated bullets. Ask for confirmation. Do not
run `git commit` until the user says yes.

### No message trailers

Commit messages must not include `Co-Authored-By`, `Generated with …`, or any other attribution
footer. Plain message body, nothing after it.

### Each commit needs a fresh OK

A previous "go ahead" does not extend to a follow-up commit later in the same session — unless the
user has explicitly said "you can commit without asking from now on" in the current session.

## After shipping

Per-diff review cannot see cross-commit rot. A change is closed by `/close-change <name>` at the
merge or version-bump commit; until it has run clean, the change is not done. It sets the PRD and
ADR status, deletes the issue stubs and review rounds (git is the archive), greps the docs for
identifiers the release removed or renamed, confirms fixtures are tracked and the full suite passes,
and runs `/debt-check`. The fixture and suite steps stand in for CI until CI exists.
