---
phase: 03-activation
reviewed: 2026-04-11T08:10:19Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - src/joy/app.py
  - src/joy/widgets/object_row.py
  - src/joy/widgets/project_detail.py
  - tests/test_object_row.py
  - tests/test_store.py
  - tests/test_tui.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-04-11T08:10:19Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the Phase 3 activation implementation: the `JoyApp` entry point, the `ObjectRow` widget, the `ProjectDetail` right pane, and the full test suite for store, object row, and TUI integration.

The implementation is clean and well-structured. All three activation actions (ACT-01 open, ACT-02 open-all-defaults, ACT-03 toggle) are correctly implemented with background worker threading. The test coverage is comprehensive and uses correct mocking patterns.

Three warnings and three info items were found. No critical/security issues in the reviewed files. The most actionable items are the non-hermetic `load_config` in TUI tests and the silent exception swallowing in `_open_defaults`.

---

## Warnings

### WR-01: `_open_defaults` silently discards the exception object

**File:** `src/joy/app.py:117`
**Issue:** The `except Exception` block in `_open_defaults` captures no exception information. Only the item's display name is stored for the error toast. When debugging open failures, there is no way to see the underlying error (e.g., subprocess exit code, OS error message) — it is fully discarded.
**Fix:** Capture the exception and include it in the error list or log it:
```python
except Exception as exc:
    display = _truncate(item.label if item.label else item.value)
    errors.append(f"{display}: {exc}")
```
Or at minimum use `self.app.notify(..., title=str(exc))` so the error surface is visible.

---

### WR-02: TUI tests are non-hermetic — `load_config` is not mocked

**File:** `tests/test_tui.py:50`
**Issue:** The `mock_store` fixture patches `joy.store.load_projects` but does not patch `joy.store.load_config`. The `_load_data` worker calls both `load_projects()` and `load_config()`. In CI or on a machine where `~/.joy/config.toml` exists with custom values, tests that depend on `app._config` defaults (e.g., the `_do_open` path that uses `self.app._config`) will pick up the real config rather than the test default. This can cause non-deterministic behavior.
**Fix:** Extend the `mock_store` fixture (or create a companion fixture) to also mock `load_config`:
```python
@pytest.fixture
def mock_store():
    with patch("joy.store.load_projects", return_value=_sample_projects()), \
         patch("joy.store.load_config", return_value=Config()):
        yield
```

---

### WR-03: Newline injection can silently break AppleScript in `_open_iterm`

**File:** `src/joy/operations.py:79`
**Issue:** The AppleScript escaping in `_open_iterm` escapes `\` and `"` but not newlines (`\n`) or carriage returns (`\r`). An `item.value` containing a newline (e.g., `"project\nname"`) would produce a multi-line AppleScript string literal, breaking the script syntax. This causes `osascript` to fail with a parse error rather than silently executing injected code (no injection risk here given `"` is escaped), but it is an unhandled edge case that will surface as an uncaught `CalledProcessError`.
**Fix:** Strip or replace newlines during escaping:
```python
name = item.value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")
```

---

## Info

### IN-01: `_render_generation` not initialized in `__init__`

**File:** `src/joy/widgets/project_detail.py:108`
**Issue:** `_project`, `_cursor`, and `_rows` are all initialized in `__init__`, but `_render_generation` is initialized lazily via `getattr(self, "_render_generation", 0)` inside `set_project`. This is inconsistent and makes the object's state surface harder to audit at a glance.
**Fix:** Add `self._render_generation: int = 0` to `__init__` alongside the other instance attributes:
```python
def __init__(self, **kwargs) -> None:
    super().__init__(**kwargs)
    self._project: Project | None = None
    self._cursor: int = -1
    self._rows: list[ObjectRow] = []
    self._render_generation: int = 0
```

---

### IN-02: `_config` class-level attribute on `JoyApp` is an unusual pattern

**File:** `src/joy/app.py:32`
**Issue:** `_config: Config = Config()` is declared as a class-level attribute. While `_set_projects` reassigns it as an instance attribute (shadowing the class attribute), the class attribute acts as an unintentional shared default. In tests, multiple `JoyApp` instances are created; if any test path modifies `JoyApp._config` (the class attribute rather than `self._config`), it would affect subsequent test instances. The pattern is also unusual enough to cause confusion for anyone reading the class.
**Fix:** Initialize `_config` as an instance attribute in `__init__` or `on_mount`:
```python
def __init__(self, **kwargs) -> None:
    super().__init__(**kwargs)
    self._config: Config = Config()
```

---

### IN-03: `PRESET_ICONS` fallback to space character is dead code

**File:** `src/joy/widgets/object_row.py:83`
**Issue:** `PRESET_ICONS.get(item.kind, " ")` falls back to a single space for any `PresetKind` not in the dict. Since `item.kind` is typed as `PresetKind` and `PRESET_ICONS` contains entries for all 9 `PresetKind` values, this fallback can never be reached. It also silently swallows any future `PresetKind` additions that are not reflected in `PRESET_ICONS`.
**Fix:** Replace the silent fallback with an explicit error or assertion to catch missing icons at development time:
```python
icon = PRESET_ICONS[item.kind]  # KeyError immediately flags missing entries
```
Or keep the fallback but use a visible placeholder (`"?"`) so missing icons are immediately obvious in the UI.

---

_Reviewed: 2026-04-11T08:10:19Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
