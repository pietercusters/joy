---
phase: 01-foundation
reviewed: 2026-04-10T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - pyproject.toml
  - src/joy/__init__.py
  - src/joy/app.py
  - src/joy/models.py
  - src/joy/operations.py
  - src/joy/store.py
  - tests/__init__.py
  - tests/conftest.py
  - tests/test_models.py
  - tests/test_operations.py
  - tests/test_store.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-04-10
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Foundation layer reviewed: data models, TOML persistence, subprocess-based openers, and their test suites. The code is well-structured and idiomatic Python. Two warnings concern error handling gaps that would surface as confusing runtime failures on malformed data. Three info items cover data consistency, a missing dependency, and a minor test coverage gap. No security issues found — the AppleScript injection escaping in `operations.py` is correctly implemented.

## Warnings

### WR-01: `PresetKind` deserialization raises unhandled `ValueError` on unknown kind strings

**File:** `src/joy/store.py:49`
**Issue:** `PresetKind(obj["kind"])` raises `ValueError` if a TOML object contains a kind string that does not exist in the enum (e.g., from a manually-edited file, a future migration, or a file written by a newer version of joy). The exception propagates through `load_projects` with no context about which project or which object caused the failure.
**Fix:**
```python
try:
    kind = PresetKind(obj["kind"])
except ValueError:
    # Skip or warn about unknown object kinds rather than aborting the whole load
    import warnings
    warnings.warn(
        f"Unknown object kind {obj['kind']!r} in project {name!r} — skipping object",
        UserWarning,
        stacklevel=2,
    )
    continue
```
Or, if strict loading is preferred, wrap the whole `load_projects` call at the call site and give the user a meaningful message.

---

### WR-02: Silent date fallback masks data corruption in `_toml_to_projects`

**File:** `src/joy/store.py:56-60`
**Issue:** When `created_raw` is not a `datetime.date` instance (e.g., the field is stored as a bare string like `"2026-01-15"` in a manually-edited TOML file, or as an integer), the code silently substitutes `date.today()`. The original value is lost without any warning, making data corruption invisible to the user.
```python
if isinstance(created_raw, date):
    created = created_raw
else:
    created = date.today()   # <-- silently discards the actual value
```
**Fix:** At minimum, log a warning with the project name and discarded value. If the value is a string in ISO format, attempt to parse it:
```python
from datetime import date
if isinstance(created_raw, date):
    created = created_raw
elif isinstance(created_raw, str):
    try:
        created = date.fromisoformat(created_raw)
    except ValueError:
        import warnings
        warnings.warn(
            f"Cannot parse created date {created_raw!r} for project {name!r}, using today",
            UserWarning,
        )
        created = date.today()
else:
    created = date.today()
```

---

## Info

### IN-01: Project `name` key in TOML value dict is ignored on load — silent divergence risk

**File:** `src/joy/store.py:38-61`
**Issue:** `project.to_dict()` writes `"name"` into the serialized value (line 81 of `models.py`), but `_toml_to_projects` derives the project name solely from the TOML dict key (`for name, proj_data in ...`). The `"name"` field inside `proj_data` is silently ignored. If a user manually edits `projects.toml` and changes only the inner `name` field without renaming the `[projects.key]` table header, the change is silently ignored on the next load.

The inner `"name"` field is unnecessary overhead. Two options:
1. Drop `"name"` from `project.to_dict()` serialization (since the key is the authoritative name), or
2. Assert consistency on load: `assert proj_data.get("name", name) == name`.

---

### IN-02: `textual` dependency not declared in `pyproject.toml`

**File:** `pyproject.toml:9-11`
**Issue:** CLAUDE.md declares Textual 8.x as the chosen TUI framework, but it is absent from `dependencies`. As a stub phase, this is expected — the `app.py` entry point is a placeholder. This is a reminder to add it before implementing the TUI layer so that `uv tool install` produces a working tool.
**Fix:** When implementing the TUI, add to `pyproject.toml`:
```toml
dependencies = [
    "textual>=8.2",
    "tomli-w>=1.0",
]
```

---

### IN-03: `test_open_iterm_creates_window` does not assert script contains window-management logic

**File:** `tests/test_operations.py:137-149`
**Issue:** The test verifies that `osascript -e <script>` is called and that the window name appears in the script, but does not assert that the script contains the key logic: the `repeat with w in windows` loop (find existing window) or `create window with default profile` (create new window). A refactor that removes the find-or-create logic but still embeds the name would pass this test. The security escape tests (WR-03, WR-04) are solid.
**Fix:** Add lightweight structural assertions:
```python
assert "repeat with w in windows" in script
assert "create window with default profile" in script
```

---

_Reviewed: 2026-04-10_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
