---
owner: platform-ops
status: consolidated
---

# Makefile Governance

## Purpose

The repository `Makefile` is a compatibility surface for operators, CI jobs, and phase validators. It must remain offline-first, deterministic, and portable across Linux and macOS shells already supported by the project.

## Structure

The main `Makefile` is organized around:

- operational targets such as `up`, `down`, `backup`, and `restore`
- canonical validation targets that execute one script or one focused test suite
- official aggregate validation groups declared through ordered `*_VALIDATION_TARGETS` variables
- legacy aliases that preserve historical entry points without redefining recipes

The official validation sections are:

- Core validation
- Governance validation
- Runtime validation
- Federation validation
- Plugin validation
- Compatibility validation
- Documentation validation
- Security validation

## Naming Conventions

- Use `validate-*` for validations.
- Use `validate-phase-*` only for phase-specific gates.
- Use singular canonical target names for executable recipes.
- Use alias targets only when preserving backward compatibility.
- Keep aggregate membership in uppercase list variables ending with `_VALIDATION_TARGETS`.

## Official Aggregators

The official deterministic aggregate targets are:

- `validate-architecture`
- `validate-governance`
- `validate-runtime`
- `validate-federation`
- `validate-plugin`
- `validate-compatibility`
- `validate-documentation`
- `validate-security`
- `validate-platform`
- `validate-all`

Policy:

- Aggregate targets must run members in explicit list order.
- Aggregate targets must call subtargets via `$(MAKE) --no-print-directory`.
- Aggregate targets must not redefine behavior already owned by canonical targets.

## New Target Policy

- Add a new validation target exactly once.
- Give the target a `##` help description when it is user-facing.
- Attach one canonical recipe to the target.
- Register new phase validations in `VALIDATE_PHASE_TARGETS`.
- Add the target to exactly the aggregate lists that own its domain.

## Legacy Alias Policy

- Prefer `alias: canonical-target` without a recipe.
- Keep aliases documented with a nearby compatibility comment.
- Do not promote aliases into aggregate lists unless the alias is itself the official public entry point.

## Anti-Shadowing Policy

- Never define the same target twice.
- Never split a recipe across adjacent targets.
- Never rely on silent prerequisite extension for `validate-*` targets.
- Keep `.PHONY` in one canonical block without duplicate entries.

## Anti-Redefinition Policy

- Do not override recipes later in the file.
- Do not add a second target definition to “append” behavior.
- If behavior must be shared, extract the shared command into the canonical target and point aliases to it.
- If an aggregate grows, update its ordered list variable instead of re-declaring the target.

## Deterministic Execution Expectations

- Aggregate execution order must come from the ordered list variables.
- Validation targets must remain offline-first.
- Avoid dynamic discovery, network downloads, or host-specific branching in aggregate targets.
- Aggregate recipes must avoid `eval`, `bash -c`, `sh -c`, and similar indirect execution patterns.
- Validation membership must be statically auditable by `scripts/validate_makefile_governance.py`.
