---
phase: 01-foundation
plan: "01"
subsystem: core
tags: [scaffold, models, dataclasses, enums, tdd, packaging]

dependency_graph:
  requires: []
  provides:
    - joy Python package installable via uv
    - ObjectType and PresetKind str-enums
    - PRESET_MAP with all 9 kind-to-type mappings
    - ObjectItem, Project, Config dataclasses with to_dict()
    - pytest test suite with 35 passing model tests
  affects:
    - 01-02: store.py imports from joy.models
    - 01-03: operations.py imports from joy.models and uses Config
    - Phase 2: TUI imports Project, ObjectItem, Config from joy.models

tech_stack:
  added:
    - hatchling 1.29.0 (build backend)
    - tomli-w 1.2.0 (TOML writing, runtime dependency)
    - pytest 9.0.3 (dev dependency)
    - Python >=3.11 (tomllib stdlib, modern type hints)
  patterns:
    - src/ layout with hatchling wheel packages
    - str-Enum for TOML-transparent serialization
    - Plain dataclasses for pure data (no Pydantic)
    - TDD: RED commit then GREEN commit per task
    - PRESET_MAP dict for two-level type dispatch

key_files:
  created:
    - pyproject.toml
    - src/joy/__init__.py
    - src/joy/app.py
    - src/joy/models.py
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_models.py
    - uv.lock
  modified:
    - .gitignore (added Python runtime patterns)

decisions:
  - "Used [dependency-groups] for dev deps (uv native) instead of [project.optional-dependencies]"
  - "TDD protocol: failing test commit (8e84482) before implementation commit (eb1543f)"
  - "app.py stub intentional: prints 'Not yet implemented' until Phase 2 wires TUI"

metrics:
  duration_minutes: 22
  completed_date: "2026-04-10"
  tasks_completed: 2
  files_created: 8
  files_modified: 1
  tests_added: 35
  tests_passing: 35
---

# Phase 1 Plan 1: Package Scaffold and Data Models Summary

Python package scaffold and pure data model layer: hatchling-backed uv package with ObjectType/PresetKind str-enums, PRESET_MAP, and ObjectItem/Project/Config dataclasses, all verified by 35 passing TDD tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create package scaffold | a8d56a9 | pyproject.toml, src/joy/__init__.py, src/joy/app.py, tests/__init__.py, uv.lock |
| 2 (RED) | Add failing model tests | 8e84482 | tests/test_models.py |
| 2 (GREEN) | Implement data models | eb1543f | src/joy/models.py, tests/conftest.py |
| chore | Add Python gitignore patterns | 6c526b3 | .gitignore |

## Verification Results

1. `uv sync` - PASS: resolves 8 packages, builds joy 0.1.0
2. `uv run joy` - PASS: prints "Not yet implemented"
3. `uv run pytest tests/test_models.py -x -v` - PASS: 35/35 tests passed
4. `uv run pytest --co -q` - PASS: 35 tests collected, no import errors

## Implementation Notes

### Two-Level Type System

The plan uses a clean two-level design:
- `PresetKind` (user-facing): mr, branch, ticket, thread, file, note, worktree, agents, url
- `ObjectType` (operation-facing): string, url, obsidian, file, worktree, iterm
- `PRESET_MAP` bridges them: `PresetKind.MR -> ObjectType.URL`, etc.

Both enums inherit from `(str, Enum)` so their values serialize transparently as plain strings to TOML — `item.kind.value == "mr"`, no special encoder needed.

### Serialization Design

`to_dict()` on `ObjectItem`, `Project`, and `Config` explicitly use `.value` for enum fields, returning plain `str` instead of `Enum` instances. This is important for TOML writers which may not recognize Enum types.

### Package Structure

Using `[tool.hatch.build.targets.wheel] packages = ["src/joy"]` for the src-layout. `uv add --dev pytest` added a `[dependency-groups]` section (the modern uv approach); the original `[project.optional-dependencies]` section was removed to avoid duplication.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] Added Python gitignore patterns**
- **Found during:** Post-task 2 git status check
- **Issue:** `__pycache__/` and `.pytest_cache/` directories were untracked after running tests
- **Fix:** Extended .gitignore with standard Python runtime patterns
- **Files modified:** .gitignore
- **Commit:** 6c526b3

**2. [Rule 1 - Deviation] uv native dependency-groups**
- **Found during:** Task 1, running `uv add --dev pytest`
- **Issue:** uv adds dev deps as `[dependency-groups]` (uv-native PEP 735 style), not `[project.optional-dependencies]`
- **Fix:** Removed the redundant `[project.optional-dependencies]` section, kept uv's `[dependency-groups]`
- **Files modified:** pyproject.toml
- **Impact:** No functional change; both approaches install dev deps with `uv sync --dev`

## Known Stubs

| File | Stub | Reason |
|------|------|--------|
| src/joy/app.py | `print("Not yet implemented")` | Intentional Phase 1 stub. Plan 01-02 (TUI Shell) will replace this with the Textual app entry point. |

## Self-Check: PASSED

Files created exist:
- pyproject.toml: FOUND
- src/joy/__init__.py: FOUND
- src/joy/app.py: FOUND
- src/joy/models.py: FOUND
- tests/__init__.py: FOUND
- tests/conftest.py: FOUND
- tests/test_models.py: FOUND

Commits verified:
- a8d56a9: FOUND (feat: package scaffold)
- 8e84482: FOUND (test: failing model tests)
- eb1543f: FOUND (feat: data models)
- 6c526b3: FOUND (chore: gitignore)
