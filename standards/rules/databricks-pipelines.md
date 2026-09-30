# Databricks pipelines: configuration, patterns, deployment

Stack rule for **PySpark / Delta Lake / Unity Catalog** pipelines deployed with Databricks Asset
Bundles, with local dev on MinIO as S3-compatible storage. Copy to
`<repo>/.claude/rules/databricks-pipelines.md`. Pairs with `python-tooling.md`.

## Configuration

### Environment helpers (`config/env.py`)

`_required()` raises on missing, `_optional()` returns a default, `_secret_or_env()` tries
Databricks secrets first then falls back to env vars. Feature flags via
`_optional("FLAG", "false").lower() == "true"`. Every env function has a caller in `src/`, `apps/`
or `scripts/`; a function only tests call is dead.

### Configuration over hardcoding

Never hardcode API URLs, endpoints, or env-specific values in client/business code. Define them as
`_optional()` functions in `config/env.py` with sensible prod defaults; accept them as optional
constructor params. Secrets go through `_secret_or_env()`. Defaults live in `env.py` only — not
restated in scripts or local run helpers.

### Project-prefixed env vars for shared resources

Env vars controlling shared resources (UC catalog/schema, storage roots, DB names) **must be
prefixed with the project name** so two pipelines on one cluster cannot collide: `UC_SCHEMA` will
collide; `MY_PIPELINE_UC_SCHEMA` won't. Use the prefix consistently in `config/env.py`,
`resources/jobs.yml`, `.env.example`, and scripts.

### No config reads at module level

Never call `env.*()` at module level — module code runs at import time, before
`load_job_parameters()` has loaded job parameters into `os.environ`, so it reads the default and
ignores the job parameter. Read config inside the function that uses it.

## Pipeline patterns

### API clients that never raise

External API clients return a `Result` dataclass instead of raising. Three tiers: success, permanent
failure (not_found), transient failure (timeout, rate limit). Callers decide how to handle each.

### Cache with MERGE hierarchy

Cache successes and permanent failures (e.g. "not found"). Exclude transient errors so they retry
next run. MERGE priority: success overwrites everything; not_found overwrites only transient/null;
transient never overwrites success or not_found.

### Environment-aware resource resolution

A single `resolve_table()` returns a local path or UC table name depending on environment. Same code
runs locally (MinIO/Delta) and on Databricks (Unity Catalog) — no scattered if/else. Delta-table
access (`forName`/`forPath`, exists, read, write) goes through the helpers in `spark/session.py`;
call sites do not re-branch on environment.

### Idempotent pipeline design

Every stage must be safely re-runnable. **Bronze**: append-only snapshots partitioned by batch ID;
never update/delete. **Silver/Gold**: Delta MERGE keyed on entity ID; same input, same output.
**Sync**: overwrite or MERGE to serving tables; no side effects from duplicate runs.

### Long-running pipelines and memory

- **Never accumulate unbounded lists** in long-running loops — flush in batches (e.g. MERGE every
  500 items, then clear).
- Check caches before external API calls; re-authenticate on 401/403 (long jobs outlive tokens).
- Write results incrementally so progress survives crashes.
- **Never do single-row Spark operations in a loop.** Each `spark.createDataFrame` + MERGE is a full
  Spark job; thousands accumulate JVM overhead and are orders of magnitude slower. Collect into a
  Python list, then MERGE the batch in one job. Aim for **tens of Spark jobs per run, not thousands**.

### Delta MERGE for upserts

Match on composite keys; separate UPDATE/INSERT logic. With open-source Delta, explicitly add new
columns before MERGE (`autoMerge` doesn't add columns) and reload the `DeltaTable` reference after
schema changes.

### Shared frame idioms

A recurring DataFrame idiom gets one helper with the explanation on it — e.g. a `count_if(cond)`
wrapper around `count(when(cond, lit(1)))`, which yields 0 rather than NULL on an empty frame. The
reason is written once, on the helper, never re-pasted at each call site. Metadata stamping,
metrics dicts and fail-fast ladders that appear in more than one layer are helpers too.

### Spark session factory

Environment-aware session in `spark/session.py`. Local: build with Delta, S3A (MinIO), JDBC.
Databricks: `SparkSession.builder.getOrCreate()`. Always set `spark.sql.session.timeZone` to UTC.
Never call `spark.stop()` on shared Databricks clusters. No smoke tests or `print()` inside library
modules; smoke checks live under `scripts/`.

## Databricks deployment

- **Wheel packaging**: `pip wheel --no-deps -w dist .`, deploy to a shared Workspace path. Classic
  clusters cache wheels by version — **bump the version in `pyproject.toml` for every code change.**
- **Wheel upload path**: always under the team workspace
  (`/Workspace/<team folder>/<project>/libs/`), never `/Workspace/Shared/`
  or user-scoped paths.
- **Job task libraries**: each `python_wheel_task` on an existing cluster must declare the wheel as a
  `libraries` entry pointing to the shared workspace path.
- **Job parameters → env vars**: use `load_job_parameters()` to bridge `--KEY=VALUE` CLI args into
  `os.environ`; use `setdefault` so existing env vars aren't overwritten.
- **Deploy script** (`scripts/deploy.sh`): build wheel → sed-update wheel version in
  `resources/jobs/*.yml` → `databricks bundle deploy` → upload wheel to team workspace path.
- Every bundle variable and job parameter is consumed by some task. One nothing reads is deleted.

### Databricks Asset Bundles (DAB)

- Deploy under a team workspace path, not user paths or `/Workspace/Shared/`.
- Avoid `mode: development` (prefixes job names with `[dev USERNAME]`). Control naming with a
  variable (e.g. `env_prefix: "[dev] "` for dev, `""` for prod).
- Job definitions in `resources/jobs/*.yml`. Use `existing_cluster_id` for shared clusters; pass
  config via `parameters`.

## Bundled commands tied to this stack

`/check` is **Python/Databricks-specific**: it runs `.venv/bin/ruff` (lint + format), pyright,
bandit, and pytest. `/debt-check` and `/debt-review` are stack-agnostic in spirit but assume the
`.claude/cognitive_debt.md` convention written by `hooks/capture_decisions.sh`.
