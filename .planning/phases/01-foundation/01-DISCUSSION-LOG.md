# Phase 1: Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-10
**Phase:** 01-foundation
**Mode:** discuss
**Areas discussed:** Project identity / TOML schema, Package + pyproject.toml setup

## Gray Areas Presented

| Area | Selected for discussion |
|------|------------------------|
| Project identity / TOML schema | ✓ |
| Config coupling in operations | — |
| Testing strategy for macOS operations | — |
| Package + pyproject.toml setup | ✓ |
| iTerm2 implementation depth | — |

## Decisions Made

### Project Identity / TOML Schema

| Question | User answer |
|----------|-------------|
| How should projects be identified in projects.toml? | Name as table key |

- User confirmed the `[projects.my-project]` + `[[projects.my-project.objects]]` schema shown in the preview.

### Package Setup

| Question | User answer |
|----------|-------------|
| How much packaging setup should Phase 1 include? | Full pyproject.toml, src layout, entry point |

- User confirmed the full `src/joy/` layout with pyproject.toml and stub entry point from Phase 1.

## Carried Forward (Claude's Discretion)

- Config coupling: operations accept Config as parameter (standard practice, not discussed — built into D-11)
- Testing strategy: mock subprocess for unit tests + @pytest.mark.macos_integration for platform ops (standard pattern, built into D-13/D-14)
- iTerm2: full implementation with manual validation marker (built into D-12)

## No corrections made.
