---
phase: quick
plan: 260414-c4g
subsystem: test-infrastructure
tags: [pytest, slow-tests, developer-experience]
dependency_graph:
  requires: []
  provides: [fast-default-test-run, slow-marker-convention]
  affects: [tests/test_tui.py, tests/test_filter.py, pyproject.toml]
tech_stack:
  added: []
  patterns: [pytest-mark-slow, addopts-exclusion]
key_files:
  created: []
  modified:
    - tests/test_tui.py
    - tests/test_filter.py
    - pyproject.toml
decisions:
  - "Use module-level pytestmark assignment (not per-test decorator) to mark all tests in a file slow at once"
  - "Default addopts excludes both slow and macos_integration; opt-in with -m slow or -m 'slow or not slow'"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-14T06:50:49Z"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 3
---

# Quick 260414-c4g: Mark Slow Tests and Configure Pytest to Skip Them by Default — Summary

**One-liner:** Module-level `pytestmark = pytest.mark.slow` on TUI/filter tests plus `addopts` exclusion reduces default suite from ~264s to 25.84s with 38 tests deselected.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add pytestmark to test_tui.py and test_filter.py | a514155 | tests/test_tui.py, tests/test_filter.py |
| 2 | Register slow marker and update addopts in pyproject.toml | cf15821 | pyproject.toml |
| 3 | Verify fast suite runs and slow tests are deselected | (no commit — verification only) | — |

## Outcome

- `uv run pytest` — 260 passed, 38 deselected, 1 warning in **25.84s** (down from ~264s)
- `uv run pytest -m slow` — collects all 38 slow tests from test_tui.py (31) and test_filter.py (7)
- `uv run pytest -m 'slow or not slow'` — runs full suite including slow tests

## Changes Made

**tests/test_tui.py and tests/test_filter.py:**
Added `pytestmark = pytest.mark.slow` after the imports block in both files. This applies the `slow` marker to every test in each module without requiring per-test decorators.

**pyproject.toml `[tool.pytest.ini_options]`:**
- `addopts`: changed from `["-m", "not macos_integration"]` to `["-m", "not slow and not macos_integration"]`
- `markers`: added `"slow: tests using Textual pilot (async TUI driver, 6-12s each) -- run with -m slow"`

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- tests/test_tui.py contains `pytestmark = pytest.mark.slow` at line 10 — FOUND
- tests/test_filter.py contains `pytestmark = pytest.mark.slow` at line 11 — FOUND
- pyproject.toml `addopts` includes `not slow and not macos_integration` — FOUND
- Commit a514155 — FOUND
- Commit cf15821 — FOUND
- `uv run pytest` completed in 25.84s with 38 deselected — PASSED
