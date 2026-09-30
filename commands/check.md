# /check

Run all code quality checks and tests for the current project.

## Steps

1. **Ruff lint**: `.venv/bin/ruff check --fix src/`
2. **Ruff format**: `.venv/bin/ruff format src/`
3. **Pyright**: `.venv/bin/python -m pyright src/`
4. **Bandit**: `.venv/bin/bandit -c pyproject.toml -r src/`
5. **Tests**: `.venv/bin/pytest tests/ --ignore=tests/e2e -v`

## Rules

- Run all 5 steps in order. Do not skip any.
- If ruff --fix modifies files, report which files were changed.
- If any step fails, continue running the remaining steps so the user gets the full picture.
- At the end, provide a summary: which steps passed, which failed, and the specific errors.
- Do not attempt to auto-fix pyright or bandit issues — just report them.
