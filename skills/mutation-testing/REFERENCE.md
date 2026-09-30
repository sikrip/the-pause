# Mutation Testing Reference

## Tool comparison

| Feature | mutmut | cosmic-ray |
|---|---|---|
| Setup | One command | Config file required |
| Speed | Fast (in-process) | Slower (subprocess per mutant) |
| Distributed runs | No | Yes (Celery worker pool) |
| Pytest integration | Native | Via runner config |
| Output | CLI + cache file | SQLite session DB |
| Maintained | Active | Active |
| Best for | Single-machine, fast feedback | Large codebases, CI distributed |

Default: **mutmut**. Fall back to cosmic-ray when mutmut runs too slow (10k+ mutants) and a worker pool is available.

## Mutant types

Both tools inject similar mutations. Examples:

- **Comparison flips**: `==` → `!=`, `<` → `<=`, `>` → `>=`, `is` → `is not`
- **Boolean flips**: `and` → `or`, `True` → `False`
- **Arithmetic**: `+` → `-`, `*` → `/`, `x + 1` → `x - 1`
- **Constants**: `0` → `1`, `""` → `"XX"`, `None` → `""`
- **Return mutations**: `return x` → `return None`
- **Call removal**: `foo(); bar()` → `foo()` (removes second call)
- **Slice mutations**: `x[1:]` → `x[2:]`

## mutmut: full flag list

```bash
mutmut run \
  --paths-to-mutate <dir>          # required
  --tests-dir <dir>                 # default: tests/
  --runner "<test cmd>"             # default: python -m pytest -x
  --use-coverage                    # only mutate covered lines (faster)
  --use-patch-file <file>           # only mutate changed lines (PR mode)
  --simple-output                   # CI-friendly output
  --no-progress                     # silence progress bar

mutmut results                       # summary
mutmut show <id>                     # single mutant diff
mutmut show all                      # all mutants
mutmut show <file.py>                # mutants in one file
mutmut html                          # generate HTML report
mutmut junitxml > report.xml         # CI report
```

Cache lives in `.mutmut-cache` (SQLite). Delete to reset.

## cosmic-ray: minimal config

`config.toml`:

```toml
[cosmic-ray]
module-path = "src/project_name"
timeout = 30.0
excluded-modules = []
test-command = ".venv/bin/pytest -x"

[cosmic-ray.distributor]
name = "local"

[cosmic-ray.distributor.local]
worker-type = "subprocess"
```

Run:

```bash
cosmic-ray init config.toml session.sqlite
cosmic-ray exec config.toml session.sqlite
cr-report session.sqlite              # text report
cr-html session.sqlite > report.html  # HTML report
```

Distributed (Celery):

```toml
[cosmic-ray.distributor]
name = "celery4"
```

## CI integration

**PR-scoped runs** (only mutate changed lines):

```bash
git diff origin/main --name-only -- '*.py' > changed.txt
mutmut run --use-patch-file <(git diff origin/main)
```

Fail CI when survivor count exceeds threshold on changed files.

**Full nightly runs**: schedule mutmut on full `src/`, publish HTML report as artifact.

## Common pitfalls

- **Slow tests** → mutation run multiplies test time by mutant count. Always use `-x` and the fastest unit test subset.
- **Flaky tests** → mark as killed even when behavior unchanged. Fix flakes before mutation testing.
- **Module-level side effects** → mutmut may not detect them. Move side effects into functions.
- **Coverage gap masking** → if a line has no test coverage at all, every mutant on it survives. Run coverage first, fill gaps, then mutation test.
- **PySpark / heavy fixtures** → see PySpark caveat in SKILL.md. Refactor business logic out of transforms.

## Stop conditions

Do not chase 100% kill rate. Healthy targets:

- **Core business logic**: 85%+ kill rate
- **Boundary/validation code**: 90%+
- **Glue / orchestration**: 60% acceptable
- **Logging / observability**: don't measure

Each survivor decision is a judgment call. Document the decision when skipping.
