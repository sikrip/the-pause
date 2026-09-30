# Python tooling and conventions

Stack rule for **Python** projects (pytest, ruff, pyright, bandit, setuptools src layout). Copy to
`<repo>/.claude/rules/python-tooling.md`. Pair with `databricks-pipelines.md` on Databricks.

## Project setup

### `.gitignore`

Critical on Databricks: Asset Bundles uses `.gitignore` to decide which files to upload, and a
missing or thin one uploads `.venv/` and `build/` and makes deploys hang. Standard ignores:
`__pycache__/`, `*.py[cod]`, `.venv/ venv/ env/`, `build/ dist/ *.egg-info/ src/*.egg-info/`,
`.DS_Store`, `*.log`, `.idea/ .vscode/`, `.env`, `.metastore_db/ spark-warehouse/`,
`.claude/ .mcp.json`, `*.local.md`.

### Build and tooling config

All in `pyproject.toml` — no `setup.cfg`, `setup.py`, or separate tool configs.

- **Build**: setuptools with `package-dir = {"" = "src"}`
- **Ruff**: `line-length = 100`, `target-version = "py39"`,
  `select = ["E", "F", "W", "I", "B", "N", "ARG", "RUF100", "C90", "PLR0915"]`. `ARG` catches
  parameters kept for a caller that never came; `RUF100` catches `noqa` comments for rules that never
  fire; `C90`/`PLR0915` hold function complexity and length. Ruff has no file-length rule — use pylint
  `C0302` (`max-module-lines=500`) or a pre-commit check.
  Per-file: `"apps/*" = ["E402"]` (apps load `.env` before imports).
- **Pyright**: `basic` mode, `reportMissingImports = "warning"` for runtime-only deps (pyspark, etc.)
- **Bandit**: skip `B101` (assert), exclude `tests/`, `apps/`, `scripts/`
- **Pytest**: `testpaths = ["tests"]`, `pythonpath = ["src", "tests"]`
- **Pre-commit**: ruff (lint + format), pyright on `src/`, bandit.

Setup: `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]" && .venv/bin/pre-commit install`.
Always run tools via `.venv/bin/` (`.venv/bin/pytest`, `.venv/bin/ruff`), never `python3 -m pytest`.

## Tooling

- **Ruff**: after creating or modifying files, check unused imports (`F401`), import ordering
  (`I001`), naming (`N817`). Run `ruff check --fix src/` then `ruff format src/`.
- **Imports and formatter hooks**: when adding a new symbol from a module, the import AND at least
  one usage must land in the **same** edit. Otherwise Ruff (on PostToolUse) strips the orphan import
  and the follow-up edit ships a `NameError`. After any edit touching an import block, grep for the
  symbol or run `.venv/bin/python -c "import module"` before claiming done.
- **Pyright**: prefer narrowing (early return, `if x is None`) over `# type: ignore`. Use
  `# type: ignore[specific-code]` only when narrowing is impractical. All function signatures have
  type hints; internal variables don't need them if pyright can infer.
- **Bandit**: when suppressing with `# nosec BXXX`, add a comment above explaining why it's safe.
  Use `defusedxml` for untrusted XML. Use `usedforsecurity=False` on `hashlib.md5`/`sha1` used for
  checksums.
- Every `noqa`, `nosec` or `type: ignore` names a rule that is actually enabled. A suppression for
  a disabled rule is noise; delete it.

## Coding conventions

### Packages

Every `__init__.py` contains only `__all__ = []`. Packages are namespaces — no re-exports. Import
from the specific module, not the package. `__all__` appears nowhere else; ordinary modules do not
declare it.

### File structure

1. Module docstring → 2. `from __future__ import annotations` → 3. stdlib imports →
4. third-party imports → 5. local imports → 6. `logger = logging.getLogger(__name__)` →
7. constants → 8. classes / functions. (Exception: `__init__.py` files with only `__all__`.)
Imports live at the top; an import inside a function is only for an optional or heavy dependency,
with a comment saying so.

### Type hints

3.10+ syntax (via `from __future__ import annotations`): `str | None`, `list[int]`, `dict[str, str]`.
Never `Optional`, `Dict`, `List` from `typing`.

### Docstrings

Short and natural. No `Args:` / `Returns:` / `Raises:` blocks. Multi-line only for non-obvious
context. A docstring longer than the function body is a sign the content belongs in `docs/`.

### Logging

`%`-style for lazy evaluation: `logger.info("Found %d items", count)`. Levels: `debug` (detail),
`info` (progress), `warning` (recoverable), `exception` (unexpected). No `print()` in `src/`.

**Databricks `python_wheel_task` logging:** Databricks configures no logging handler for
`python_wheel_task` entry points — without explicit setup, all `logger.*()` calls are silently
dropped. Define `setup_logging()` in `config/env.py` and call it first in every `main()`:

```python
def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    logging.getLogger("py4j").setLevel(logging.WARNING)
```

### Shell and operational scripts

Scripts in `scripts/` must be Linux-compatible (CI, cloud): no macOS-specific `sed -i ''`, no
`brew`-only tools. Every script must run — one that calls a module that moved or was deleted is
fixed or removed in the same commit. Scripts are thin wrappers over `src/`; spec content (field
tables, business rules) does not live in a script.

## Pytest conventions

- Class-based grouping: `class TestFunctionName:` with `def test_scenario(self):`
- Section headers: `# ── section_name ──────────`
- Factory fixtures with keyword-only args: `def _make_thing(*, key: str = "default") -> dict:`
- Mock HTTP: `unittest.mock.patch("requests.get", return_value=mock_resp)`
- JSON fixtures in `tests/fixtures/` for realistic API responses; root `conftest.py` for shared
  fixtures and session-scoped resources, `tests/e2e/conftest.py` for mock wiring and factories.
- Run: `.venv/bin/pytest tests/ -v` (all), `--ignore=tests/e2e` (unit only), `tests/e2e/ -v`
  (e2e only).
