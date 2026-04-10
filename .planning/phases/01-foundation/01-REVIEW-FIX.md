---
phase: 01-foundation
fixed_at: 2026-04-10T00:00:00Z
review_path: .planning/phases/01-foundation/01-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 01: Code Review Fix Report

**Fixed at:** 2026-04-10
**Source review:** .planning/phases/01-foundation/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2
- Fixed: 2
- Skipped: 0

## Fixed Issues

### WR-01: `PresetKind` deserialization raises unhandled `ValueError` on unknown kind strings

**Files modified:** `src/joy/store.py`
**Commit:** ca09db8
**Applied fix:** Converted the list comprehension in `_toml_to_projects` to an explicit for-loop. Unknown `PresetKind` values are now caught with `try/except ValueError`, emit a `UserWarning` with the project name and offending kind string, and `continue` to skip the object — leaving the rest of the project's objects intact. Added `import warnings` at the top of the module.

### WR-02: Silent date fallback masks data corruption in `_toml_to_projects`

**Files modified:** `src/joy/store.py`
**Commit:** ca09db8
**Applied fix:** Extended the `created_raw` type check to handle `str` values by attempting `date.fromisoformat()`. A failed parse now emits a `UserWarning` with the project name and the unparseable value before falling back to `date.today()`. Unrecognised non-string, non-date values still fall back to `date.today()` silently (no data to warn about).

---

_Fixed: 2026-04-10_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
