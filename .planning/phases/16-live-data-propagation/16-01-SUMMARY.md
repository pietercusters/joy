---
phase: 16-live-data-propagation
plan: "01"
subsystem: propagation
tags: [tdd, models, app, propagation, agents, mr]
dependency_graph:
  requires: []
  provides: [ObjectItem.stale, _propagate_changes, _propagate_mr_auto_add, _propagate_agent_stale]
  affects: [src/joy/app.py, src/joy/models.py]
tech_stack:
  added: []
  patterns: [tdd-red-green, transition-only-messages, batched-save]
key_files:
  created:
    - tests/test_propagation.py
  modified:
    - src/joy/models.py
    - src/joy/app.py
decisions:
  - "Propagation methods implemented as JoyApp instance methods accessing self._projects and self._current_sessions directly — no extraction to module-level functions needed since tests bind methods via JoyApp._propagate_mr_auto_add(ctx, mr_data) pattern"
  - "stale field excluded from ObjectItem.to_dict() by design — explicit key list in to_dict() means new fields are never accidentally serialized"
  - "_maybe_compute_relationships gates on both _worktrees_ready and _sessions_ready before running propagation — resets flags after each cycle"
  - "_propagate_changes saves to TOML only when MRs were added (not for stale-only changes since stale is runtime-only)"
metrics:
  duration: "178s"
  completed: "2026-04-15"
  tasks_completed: 2
  files_modified: 3
---

# Phase 16 Plan 01: Core Propagation Logic — TDD Summary

**One-liner:** ObjectItem.stale runtime field and JoyApp propagation methods (MR auto-add with URL dedup, agent stale marking with transition-only messages) implemented via TDD with 21 unit tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add ObjectItem.stale field and write propagation test scaffold (RED) | 2fe2a10 | src/joy/models.py, tests/test_propagation.py |
| 2 | Implement propagation methods on JoyApp and make all tests green | 64f0ce8 | src/joy/app.py |

## What Was Built

### ObjectItem.stale (models.py)

Added `stale: bool = False` runtime field to `ObjectItem` dataclass. The existing `to_dict()` method uses an explicit key list so `stale` is automatically excluded from TOML serialization — no change to `to_dict()` required. This satisfies PROP-07 (MR never auto-removed) and T-16-03 (stale never leaked to disk).

### _propagate_mr_auto_add(mr_data) (app.py)

Iterates `(repo_name, branch) -> MRInfo` pairs in `mr_data`. For each entry:
- Skips projects with `repo=None` (PROP-08)
- Skips projects where `project.repo != repo_name`
- Only proceeds if project has a BRANCH object with matching value (PROP-06: branches not modified)
- Deduplicates by checking if MR with same URL already exists (PROP-02 dedup)
- Appends `ObjectItem(kind=MR, value=url, label="PR #N", open_by_default=False)`
- Returns notification messages for each MR added

### _propagate_agent_stale() (app.py)

Computes `active_sessions = {s.session_name for s in self._current_sessions}`. For each AGENTS object across all projects:
- Sets `obj.stale = obj.value not in active_sessions`
- Emits message only on transitions: False->True ("offline"), True->False ("back online")
- True->True (still absent) and False->False (still present) emit no messages

### _propagate_changes(mr_data) (app.py)

Orchestrates both sub-methods:
1. Calls `_propagate_mr_auto_add(mr_data)`
2. Calls `_propagate_agent_stale()`
3. If any MR was added: calls `_save_projects_bg()` (batched, D-10)
4. Calls `self.notify()` per message (D-11)
5. If any changes: rebuilds ProjectList and ProjectDetail under `_is_syncing` guard (D-12)

### _maybe_compute_relationships() (app.py)

Gates on `_worktrees_ready and _sessions_ready`. Resets both flags (so next refresh cycle gates properly) then calls `_propagate_changes()`. Both `_set_worktrees` and `_set_terminal_sessions` now store their data and set their ready flags before calling this method.

## Verification Results

```
uv run pytest tests/test_propagation.py -x -q   # 21 passed
uv run pytest tests/test_models.py -x -q         # 35 passed
uv run pytest tests/ -x -q                       # 305 passed, 38 deselected
```

## Deviations from Plan

None — plan executed exactly as written. The test helper pattern using `JoyApp._propagate_mr_auto_add(ctx, mr_data)` with a `_PropContext` duck-type object matched the plan's recommended approach cleanly.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes were introduced. The `stale` field is runtime-only and explicitly excluded from `to_dict()` — T-16-03 mitigated as designed. The early-return `if not mr_data` guard addresses T-16-02 as specified.

## Self-Check: PASSED

- src/joy/models.py: FOUND stale field
- src/joy/app.py: FOUND _propagate_changes, _propagate_mr_auto_add, _propagate_agent_stale
- tests/test_propagation.py: FOUND (21 tests)
- Commits 2fe2a10, 64f0ce8: FOUND in git log
