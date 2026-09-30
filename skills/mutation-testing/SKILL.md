---
name: mutation-testing
description: Run mutation testing on Python codebases using mutmut (default) or cosmic-ray (fallback) to find gaps in test suite quality. Use only when explicitly invoked — e.g. user says "run mutation testing", "kill mutants", "check test quality with mutation", or "/mutation-testing".
---

# Mutation Testing

Validates test suite quality by injecting code mutations and checking which ones tests catch. Surviving mutant = test gap.

## Before running: ask the user

Always ask these before executing. Do not guess.

1. **Tool**: `mutmut` (default, fast) or `cosmic-ray` (configurable, distributed)?
2. **Source paths**: which directories to mutate? (e.g. `src/`, `src/project_name/core/`)
3. **Exclusions**: any modules to skip? Default candidates to suggest:
   - PySpark transform code (`df.select(...)` chains — overhead too high)
   - Logging-only modules
   - Config/constants files
   - Generated code
4. **Test command**: how to run tests? (e.g. `.venv/bin/pytest tests/ --ignore=tests/e2e -x`)
   - Use `-x` (fail fast) — mutmut kills mutant on first failure, no need for full suite per mutant
5. **Time budget**: full run (can take hours) or scoped to a single module/function first?
6. **Python env**: venv path? (`.venv/bin/python` in a typical venv layout)

## Quick start — mutmut

```bash
pip install mutmut
mutmut run \
  --paths-to-mutate src/project_name/<module> \
  --tests-dir tests/ \
  --runner ".venv/bin/pytest -x --ignore=tests/e2e"
mutmut results            # list killed/survived/timeout
mutmut show <id>          # show mutant diff
mutmut show all           # show all survivors
```

## Quick start — cosmic-ray

```bash
pip install cosmic-ray
cosmic-ray init config.toml session.sqlite
cosmic-ray exec config.toml session.sqlite
cr-report session.sqlite
```

See [REFERENCE.md](REFERENCE.md) for cosmic-ray config example and full mutmut flag list.

## Workflow

1. **Verify green baseline**: run full test suite first. Mutation testing on a red suite is meaningless.
2. **Scope tight first**: run on one module before whole codebase. Validates setup, gives signal fast.
3. **Run**: `mutmut run ...`
4. **Triage survivors**: use `scripts/prioritize_survivors.py` to group by file and filter low-value paths.
5. **For each prioritized survivor**:
   - `mutmut show <id>` → read the diff
   - Decide: real gap (write test) or equivalent mutant / dead code (skip)
   - If real gap: write a scenario test (not implementation-mirroring) that fails on the mutated version
   - Re-run: `mutmut run <id>` confirms kill
6. **Stop condition**: not 100% kill rate. Stop when survivors are all equivalent / low-value. Aim ~80%+ on core business logic.

## Judgment: survivors worth fixing

**Fix**:
- Survivors in core business logic (calculations, conditionals on business rules, data transformations)
- Survivors in error-handling branches that are reachable
- Boundary mutations on thresholds (`>` ↔ `>=`)

**Skip** (equivalent or low-value):
- Logging statements (`logger.info(...)` removed → no behavior change)
- Defensive guards on impossible inputs
- Performance optimizations (caching, memoization — mutation doesn't change correctness)
- Constants only used in one place (test would just re-assert the constant)
- Dead code (mark for deletion instead of writing a test)

## Helper script

`scripts/prioritize_survivors.py` — parses mutmut results, groups by file, filters out user-supplied excluded paths, ranks files by survivor count. Run after `mutmut run`:

```bash
python ~/.claude/skills/mutation-testing/scripts/prioritize_survivors.py \
  --exclude "**/spark/**" --exclude "**/logging.py"
```

## PySpark caveat

Skip mutation testing on Spark DataFrame transform code. Reason: each mutant runs the full test suite; Spark session startup + job overhead = hours per module. Instead:

1. Refactor business logic out of Spark transforms into pure Python functions.
2. Run mutation testing on the pure functions only.
3. Keep Spark transforms covered by E2E tests, not mutation tests.
