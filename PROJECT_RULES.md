# Project Rules

## Scope Immutability

- **Two commands, forever:** Only `chapterize` and `remux` are in scope. No new commands will be added.
- **Refactoring only:** Within those two commands, work falls into two categories:
  - **Bug fixes & minor enhancements:** Shipped directly in feature PRs.
  - **Refactoring (OOP/SOLID improvement, test coverage, architecture redesign):** Must be a *separate* PR from feature work. Do not mix refactoring and features.
- **Plugin architecture (future):** When `remux` gains variants (e.g., remux to MKV, WebM), implement as a plugin system *in a separate, scoped refactor PR*. Do not expand scope before that refactor exists.

## Quick Actions

- All Finder Quick Actions live in `quickactions/`.
- Quick Actions are bash wrappers around Python components (no business logic in bash).
- Current Quick Actions: `chapterize.sh`, `remux.sh`.

## Subprocess Commands

- Any operation that invokes external commands (via `subprocess.run` or shell) must have a named CLI entrypoint.
- CLIs live in `chapterize/cli.py` and `remux/cli.py`.

## Test-Driven Development (TDD) Mandate

- **Strict TDD for ALL Future Work:** Test-Driven Development is mandatory for all features, bug fixes, and modifications going forward.
- **Tests Must Fail First:** Before *any* effort is made to fix problems or write implementation code, you must first write a test that explicitly targets the bug or missing feature and prove that it fails.
- **No AI assumptions:** Automation must never declare a feature "complete" without concrete, passing test logs proving its functionality.
- **Safe Synthetic Data:** Tests must *never* rely on user-provided or persistent production data (e.g., real NAS video files). Tests must generate their own isolated, ephemeral mock data (e.g., via `ffmpeg -f lavfi`) and clean up after themselves.
- **Prove the Fix:** Write the minimum code required to make the failing test pass. The test output is the only acceptable proof of success.
