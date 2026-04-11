---
phase: 02-tui-shell
fixed_at: 2026-04-11T06:47:26Z
review_path: .planning/phases/02-tui-shell/02-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-04-11T06:47:26Z
**Source review:** .planning/phases/02-tui-shell/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: `mock_store` fixture patches the wrong target

**Files modified:** `tests/test_tui.py`
**Commit:** 66cc5a5
**Applied fix:** Added a multi-line docstring to `mock_store` explaining why `joy.store.load_projects` is the correct patch target (lazy import re-executes on each `_load_data` call, so the binding is resolved from `joy.store` at call time). Replaced the timing-dependent `await pilot.pause(0.2)` in `test_first_project_auto_selected` with `await pilot.pause()` (processes all pending messages) followed by `await app.workers.wait_for_complete()` to reliably wait for the background worker.

### WR-02: Stale `_rows` reference possible during rapid project switching

**Files modified:** `src/joy/widgets/project_detail.py`
**Commit:** 23e717b
**Applied fix:** Added a `_render_generation` counter to `set_project`. Each call increments the counter, captures the current value in `gen`, and schedules a lambda that passes `gen` to `_render_project`. At the top of `_render_project`, if `gen` does not match the current `_render_generation`, the render was superseded and returns immediately. Also updated the `_render_project` signature to accept `gen: int = 0` and added docstrings explaining the generation guard.

### WR-03: `pytest-asyncio` mode not configured — tests may silently collect but not run

**Files modified:** `pyproject.toml`
**Commit:** 75e62cc
**Applied fix:** Added `asyncio_mode = "auto"` to `[tool.pytest.ini_options]` so that pytest-asyncio 0.25 processes `@pytest.mark.asyncio`-decorated tests correctly without deprecation warnings or silent skips.

---

_Fixed: 2026-04-11T06:47:26Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
