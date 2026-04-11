---
phase: 03-activation
fixed_at: 2026-04-11T08:25:00Z
review_path: .planning/phases/03-activation/03-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 03: Code Review Fix Report

**Fixed at:** 2026-04-11T08:25:00Z
**Source review:** .planning/phases/03-activation/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: `_open_defaults` silently discards the exception object

**Files modified:** `src/joy/app.py`
**Commit:** 5ecc390
**Applied fix:** Changed `except Exception:` to `except Exception as exc:` and updated the error string appended to the list from `display` to `f"{display}: {exc}"`, so the underlying error message (subprocess exit code, OS error, etc.) is visible in the error toast.

### WR-02: TUI tests are non-hermetic — `load_config` is not mocked

**Files modified:** `tests/test_tui.py`
**Commit:** 7403c99
**Applied fix:** Extended the `mock_store` fixture to also patch `joy.store.load_config` returning a default `Config()`. The fixture now uses a two-context-manager `with` block and a plain `yield` (the mock object is no longer yielded, which is fine since no test uses it). Added an import of `Config` from `joy.models` inside the fixture and updated the docstring to document the new behaviour.

### WR-03: Newline injection can silently break AppleScript in `_open_iterm`

**Files modified:** `src/joy/operations.py`
**Commit:** 0a265d3
**Applied fix:** Added `.replace("\n", " ").replace("\r", " ")` to the escaping chain in `_open_iterm`, matching the suggestion exactly. Order is preserved: backslash, double-quote, newline, carriage-return — consistent with the existing injection-prevention logic (T-1-03-01).

---

_Fixed: 2026-04-11T08:25:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
