---
name: 'Quality Gates'
description: 'Run the project-configured formatters, linters, type checkers and tests after code changes, and keep VS Code extensions aligned with the CLI tools.'
applyTo: '**'
---

# Quality Gates

## Before editing

- Read the project's tool configuration (for example `pyproject.toml`, `.golangci.yml`, `Cargo.toml`/`clippy.toml`, `checkstyle.xml`, `.editorconfig`, `.vscode/settings.json`) and write code that satisfies those rules from the start. "Appropriate linters" means the ones the project configures.

## After generating or changing code

Run in this order and rerun affected steps after every fix:

1. Formatter
2. Linter(s)
3. Type checker / compiler checks
4. The narrowest relevant tests, then the wider suite if shared components changed

Rules:

- Do not disable rules, add suppressions, or edit linter config to make code pass. Config changes need user approval.
- If a tool is missing or cannot run, report it and why. Do not skip it silently or invent a config.
- Do not present code for approval (Gate 2) until all checks pass.

## IDE and CLI alignment

- The VS Code extension for each tool must use the same config file, same tool version, and same rules as the CLI command you run. Prefer one tool per job (one formatter, one linter family).
- Before relying on the checks, compare `.vscode/settings.json` (and recommended extensions) with the CLI tools in use. Report any mismatch (different formatter, different line length, extension not installed, disabled language server) and propose a fix for approval.
- Keep tool versions pinned in the project's dev dependencies so the extension and CLI agree.
