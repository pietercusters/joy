---
phase: 05-settings-search-distribution
fixed_at: 2026-04-12T00:00:00Z
review_path: .planning/phases/05-settings-search-distribution/05-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 05: Code Review Fix Report

**Fixed at:** 2026-04-12
**Source review:** .planning/phases/05-settings-search-distribution/05-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### WR-01: Bare `except` in `_exit_filter_mode` silently swallows all exceptions

**Files modified:** `src/joy/widgets/project_list.py`
**Commit:** 25b7177
**Applied fix:** Added `from textual.css.query import NoMatches` import and replaced `except Exception: pass` with `except NoMatches: pass  # already removed -- expected` in `_exit_filter_mode`. This narrows the handler to the single expected exception, letting genuine errors propagate.

---

### WR-02: `on_list_view_highlighted` can index into stale `_projects` after filter updates

**Files modified:** `src/joy/widgets/project_list.py`
**Commit:** 25b7177
**Applied fix:** Added label validation in `on_list_view_highlighted` — after bounds-checking the index, the handler now queries `event.item.query_one(Label)` and compares `str(label_widget.renderable) == project.name` before posting the message. If the label does not match (stale-index window), the event is silently dropped and recovers on the next highlight. Fix requires human verification of the logic.

---

### WR-03: `test_settings_save_returns_config` asserts a fragile internal default

**Files modified:** `tests/test_screens.py`
**Commit:** 3ffdafc
**Applied fix:** Removed `assert result_holder[0].ide == "PyCharm"` (line 249) and replaced it with a comment directing specific field assertions to `test_settings_prepopulated`. The `isinstance(result_holder[0], Config)` check remains as the meaningful assertion.

---

### WR-04: `test_filter_realtime` and `test_filter_enter_keeps_subset` count `ListView` children naively

**Files modified:** `tests/test_filter.py`
**Commit:** d36c30e
**Applied fix:** Added `from textual.widgets import ListItem` import. Replaced all 5 occurrences of `len(list(listview.children))` with `len(listview.query(ListItem))` — covering `test_filter_realtime` (line 61), `test_filter_escape_restores_full_list` (line 81), `test_filter_enter_keeps_subset` (line 105), `test_filter_clear_restores_list` (lines 122 and 128), and `test_filter_case_insensitive` (line 160). This makes the count Textual-version-safe by querying only `ListItem` descendants.

---

_Fixed: 2026-04-12_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
