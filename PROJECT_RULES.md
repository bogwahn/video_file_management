# Project Rules

## Quick Actions

- All Finder Quick Actions live in `quickactions/`.
- Quick Actions are bash wrappers around Python components (no business logic in bash).

## Subprocess Commands

- Any operation that invokes external commands (via `subprocess.run` or shell) must have a named CLI entrypoint.

## Test-Driven Development (TDD) Mandate

- **Strict TDD for ALL Future Work:** Test-Driven Development is mandatory for all features, bug fixes, and modifications going forward.
- **Tests Must Fail First:** Before *any* effort is made to fix problems or write implementation code, you must first write a test that explicitly targets the bug or missing feature and prove that it fails. 
- **No AI assumptions:** Automation must never declare a feature "complete" without concrete, passing test logs proving its functionality.
- **Safe Synthetic Data:** Tests must *never* rely on user-provided or persistent production data (e.g., real NAS video files). Tests must generate their own isolated, ephemeral mock data (e.g., via `ffmpeg -f lavfi`) and clean up after themselves.
- **Prove the Fix:** Write the minimum code required to make the failing test pass. The test output is the only acceptable proof of success.
