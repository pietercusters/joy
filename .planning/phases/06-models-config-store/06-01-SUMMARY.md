---
phase: 06-models-config-store
plan: "01"
subsystem: models
tags: [models, dataclass, config, tdd]
dependency_graph:
  requires: []
  provides: [Repo dataclass, detect_forge function, Config.refresh_interval, Config.branch_filter]
  affects: [06-02-PLAN.md, Phase 7, Phase 9, Phase 10, Phase 11]
tech_stack:
  added: []
  patterns: [TDD red-green, dataclass field with default_factory, pure function]
key_files:
  created: []
  modified:
    - src/joy/models.py
    - tests/test_models.py
    - src/joy/store.py
    - tests/test_store.py
decisions:
  - "forge field is plain str (not Enum) per D-04 — simpler and sufficient for routing to gh/glab CLI"
  - "detect_forge uses simple substring match ('github.com' in url) per D-06 — avoids URL parsing complexity"
  - "Repo.to_dict() includes name field following Project.to_dict() pattern"
metrics:
  duration_minutes: 2
  tasks_completed: 2
  files_modified: 4
  completed_date: "2026-04-13"
---

# Phase 06 Plan 01: Models Config Store — Repo Dataclass and Config Extensions Summary

Repo dataclass + detect_forge pure function added to models.py; Config extended with refresh_interval (int, default 30) and branch_filter (list[str], default ["main","testing"]) with backward-compatible store layer.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add Repo dataclass and detect_forge function | 706e64c | src/joy/models.py, tests/test_models.py |
| 2 | Extend Config with refresh_interval and branch_filter | 43e7008 | src/joy/models.py, tests/test_models.py, src/joy/store.py, tests/test_store.py |

## What Was Built

### Task 1: Repo dataclass and detect_forge

Added to `src/joy/models.py`:

- `Repo` dataclass with 4 fields: `name: str`, `local_path: str`, `remote_url: str = ""`, `forge: str = "unknown"`
- `Repo.to_dict()` following same serialization pattern as `Project` and `ObjectItem`
- `detect_forge(remote_url: str) -> str` pure function — simple substring check for `"github.com"` and `"gitlab.com"`, returns `"unknown"` for all other URLs

Added to `tests/test_models.py`:
- `TestRepo` class (6 tests): minimal creation, full creation, to_dict serialization, equality, forge-is-str-not-enum
- `TestDetectForge` class (7 tests): github SSH, github HTTPS, gitlab SSH, gitlab HTTPS, unknown host, empty string, no-false-positive host

### Task 2: Config field extensions

Extended `Config` dataclass:
- `refresh_interval: int = 30` — configurable refresh frequency in seconds
- `branch_filter: list[str] = field(default_factory=lambda: ["main", "testing"])` — git branches to show in worktree pane

Updated `Config.to_dict()` to include both new fields.

Updated `store.load_config()` to read new fields with `data.get("refresh_interval", 30)` and `data.get("branch_filter", ["main", "testing"])` — backward compatible with existing config.toml files missing these fields.

Added tests:
- 6 new tests in `TestConfig` (defaults, custom values, list independence, to_dict inclusion)
- Updated `test_config_defaults` and `test_config_to_dict` to include new fields
- `test_config_round_trip_new_fields` in test_store.py
- `test_config_backward_compat_missing_new_fields` in test_store.py

## Verification

```
uv run pytest tests/test_models.py tests/test_store.py -x -q
67 passed in 0.06s

uv run pytest -x -q
152 passed, 1 deselected in 43.86s
```

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| forge as plain str, not Enum | D-04: simpler, sufficient for gh/glab CLI routing. No need for the type safety overhead of an Enum for a 3-value field that grows slowly. |
| detect_forge uses substring match | D-06: "github.com" in url is sufficient and readable. URL parsing would be overkill and more fragile. |
| Repo.to_dict() includes name | Follows Project.to_dict() pattern — consistent serialization. |
| branch_filter defaults to ["main", "testing"] | Plan spec. Covers the most common branch patterns. User-configurable via config.toml. |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None — all fields have real values, no placeholder data.

## Threat Flags

None — this plan adds pure data models with no I/O, no network endpoints, no auth paths, and no external input handling. No new threat surface introduced.

## Self-Check: PASSED

Files exist:
- FOUND: src/joy/models.py
- FOUND: src/joy/store.py
- FOUND: tests/test_models.py
- FOUND: tests/test_store.py

Commits exist:
- FOUND: 706e64c
- FOUND: 43e7008
