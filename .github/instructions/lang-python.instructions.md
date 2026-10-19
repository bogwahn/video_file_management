---
name: 'Python Tooling'
description: 'Python formatter, linter, type-checker, test and VS Code extension expectations.'
applyTo: '**/*.py'
---

# Python

- Python 3.14 (tool targets use `3.14`/`py314`). Change the pin only as a planned, approved update. Type hints on all public functions and methods, PEP 8/PEP 257, `abc.ABC` or `typing.Protocol` for component interfaces.
- Tests: `pytest` (`tests/`), run with `.venv/bin/python -m pytest`.
- Config lives in `pyproject.toml`; line length is 120.

## Tools to run (use `.venv/bin/`)

1. Format: `ruff format`
2. Lint and import sorting: `ruff check`
3. Types: `mypy` (the single gating type checker)
4. Tests: `pytest`
5. Markdown changes: `markdownlint`

Do not reintroduce Black, isort, flake8, pylint or Pyright without an approved change.

## VS Code alignment

Expected extensions (see `.vscode/extensions.json`): Python, Ruff, Mypy Type Checker, Markdownlint. Each must read `pyproject.toml` and use the `.venv` tools (`importStrategy: fromEnvironment`). Ruff is the only formatter. The tool list is in `docs/policies/linters.md`.
