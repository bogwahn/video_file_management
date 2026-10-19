---
name: 'TDD and Change Control'
description: 'Test-first workflow with user approval gates, and change control for existing, released code and tests.'
applyTo: '**'
---

# TDD and Change Control

## Workflow (applies to every code change)

1. **Outline.** Present which objects will be created or changed and how. Wait for approval before generating or changing any code.
2. **Write tests first.** Cover the agreed behavior only. Run them and confirm they fail for the expected reason.
3. **Gate 1: user approves the tests.** Do not write production code until approved.
4. **Implement.** Write only the code needed to pass the approved tests.
5. **Iterate.** All tests must pass before proceeding. If tests still fail after 3 iterations, stop and ask the user to review the code and help resolve it.
6. **Quality checks.** Run the checks in quality-gates. All must pass.
7. **Gate 2: user approves the remaining code changes.** Only then is the work complete.

If an executable test is not feasible, say why and get approval for the alternative validation.

## Existing code and tests

- Do not retroactively change existing code or tests unless it is part of a planned refactor or a planned workaround approved by the user.
- Either way, present a clear outline of what changes, per object, and get approval before any code is generated or changed.
- A refactor is worked in isolation: no feature work or other changes are deployed concurrently.
- Exception: an urgent security fix to released code may be made with explicit user approval, and must be followed by a planned refactor if the design needs correcting.
