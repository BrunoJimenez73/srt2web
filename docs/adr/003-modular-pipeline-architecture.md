# ADR 003: Modular Pipeline Architecture Refactoring

## Status

Deprecated — merged into ADR 001

## Context

This ADR originally duplicated ADR 001 (Pipeline Modular Architecture).
All architectural decisions, rationale, and consequences are documented there.

## Decision

Keep ADR 001 as the single source of truth for pipeline architecture decisions.

## Consequences

- **Maintainability**: One ADR to update when architecture changes
- **Clarity**: No confusion between duplicate documents
- **Traceability**: All references should point to ADR 001

## References

- `docs/adr/001-pipeline-modular-architecture.md` — canonical ADR
- `core/pipeline_manager.py` — current orchestrator
- `core/pipeline/strategies.py` — strategy implementations
- `core/pipeline/` — modular pipeline implementation

## Date

2026-04-14 (original), 2026-05-27 (deprecation)
