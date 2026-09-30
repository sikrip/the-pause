# Testing

Stack-agnostic testing standards. Copy to `<repo>/.claude/rules/testing.md` in every repo. Runner
commands and fixture idioms for a specific stack belong in that stack's rule file
(see `python-tooling.md`).

## Tests verify plausible real-life scenarios, not the implementation

Tests describe what the system does for the business or data consumer, in language a domain
reader recognises. They do not mirror the production code's structure, internal constants, or
branch shape.

- A lookup-client test asserts "returns not_found for an ID the upstream API doesn't know" — not
  "calls `_parse_response` with an empty list".
- A re-run/idempotency test asserts "re-running with the same input produces identical output" —
  not "calls the write function once".
- A cache test asserts "a transient error is not cached so the next run retries" — not
  "sets `status = 'transient'`".

Why: implementation-mirroring tests pass when the production code is wrong (they test the same
logic) and fail spuriously on refactors. Scenario tests catch genuine bugs and survive refactors.

Concretely not allowed: asserting a config constant equals its literal, asserting a default equals
its default, testing private helpers one literal at a time, pinning the exact key set of an output
object.

- Prefer real captured fixtures over synthetic per-test inputs when the scenario is "what happens in
  production". Synthetic inputs are fine when the scenario is genuinely abstract (empty input,
  missing field raises).
- If you don't know the right scenario to verify, **stop and ask.** Don't invent one by reading the
  production code — that is the failure mode this rule prevents.
- One test = one scenario. A name that needs "and" or commas describes two tests. A docstring
  longer than the test body belongs in `docs/`. No ADR history or planning-slice numbers in test
  docstrings.

If a failure ever produces "I'll just update the test to match the new code" without asking whether
the new behaviour is correct for users, the test was implementation-mirroring. Replace it with a
scenario test.

## Structure

- **Unit tests**: fast, no external dependencies. Mock at the boundary (HTTP clients, DB calls) —
  never a sibling module's own functions when an environment variable or a client mock is the real
  boundary.
- **E2E tests** (`tests/e2e/`): real but local infrastructure; session-scoped shared resources to
  avoid startup cost.
- Group by unit under test (`class TestFunctionName:` in pytest, `describe(...)` in Jest/JUnit
  nesting), one scenario per test.
- Factory helpers take named/keyword-only arguments, one factory per shape, defined once in the
  shared fixtures file and never redefined per test file.

## Coverage follows risk

Every module that touches external IO (databases, file transfer, cloud SDKs, HTTP) gets at least
one boundary-mocked scenario test before any pure function gets its twentieth. Before adding tests,
check which source modules have none.

## Baselines and pinned numbers

- One characterisation baseline (e.g. published outputs for a fixed input set) lives in exactly one
  file. Every other test asserts relative behaviour — "a penalty lowers the result below the
  clean case" — not an absolute value copied from the baseline.
- When a recalibration moves the baseline, the diff touches that one file. If it touches three, the
  pins were duplicated.
- Tests written to kill a mutation-testing mutant are kept only if they read as a scenario.
  Parametrize boundary cases instead of three copies differing by one literal.
- No assertion-free tests. "Does not throw" is a scenario only if the test also says what happens
  instead.

## Fixtures and moves

- Fixtures are committed, never gitignored. A test that skips because a local-only file is absent
  never runs in CI — track the file or delete the test.
- A move or extraction across repos (modules leaving for a sibling package) runs the whole suite,
  e2e included, from a clean checkout before the commit. Deleted fixtures and orphaned e2e tests
  are the classic casualty.
