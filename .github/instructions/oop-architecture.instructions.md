---
name: 'OOP Architecture'
description: 'Componentized, thin-wrapper, OOP/OOD/SOLID design rules for object-oriented or interface/trait-based projects (Python, Java, C#, Go, Rust).'
applyTo: '**/*.{py,java,cs,go,rs}'
---

# Architecture and Design Rules

Applies to object-oriented or interface/trait-based code. In Go and Rust, read "class" as struct/type plus its interfaces/traits.

## Componentization

- Build every capability as a small, single-purpose component with an explicit interface.
- Before writing a component, search the project for an existing one. Reuse or extend by composition before creating a new one.
- Components do the work. Entry points (CLI `main`, handlers, controllers, scripts) are thin wrappers that parse input, select and wire components, and report results. They contain no business logic.
- Prefer composition over inheritance. Inject dependencies; do not construct them inside components.

## Design standards

- Follow the language's official style guide and idioms, and the project's configured linters (see quality-gates).
- Apply OOP (encapsulation, abstraction, polymorphism) and OOD. Keep the public surface of each component minimal and typed.
- Follow SOLID as described by Robert C. Martin (*Agile Software Development: Principles, Patterns, and Practices*; *Clean Architecture*):
  - SRP: one reason to change per component.
  - OCP: extend through new components, not by editing existing ones.
  - LSP: substitutes honor the base contract.
  - ISP: small, role-specific interfaces.
  - DIP: depend on abstractions, not concretions.

## Patterns

Use a pattern only when it removes a concrete problem in the current code. Name the pattern and the problem in the design outline. Do not add speculative abstraction.

Sources, in order of preference:

1. Gang of Four, *Design Patterns*.
2. Martin Fowler, *Patterns of Enterprise Application Architecture* and *Refactoring*.
3. Hohpe and Woolf, *Enterprise Integration Patterns*.
4. Domain-Driven Design (Evans), Hexagonal and Clean Architecture.
5. Cloud and operations: Azure Architecture Center patterns, AWS Well-Architected, Twelve-Factor App, *Release It!*.

## Released code

"Released" means tagged, published, or running in production. Do not modify released code except as part of a planned refactor (see tdd-change-control). Add new behavior by adding components.
