---
phase: 04-crud
reviewed: 2026-04-11T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - src/joy/screens/__init__.py
  - src/joy/screens/name_input.py
  - src/joy/screens/preset_picker.py
  - src/joy/screens/value_input.py
  - src/joy/screens/confirmation.py
  - tests/test_screens.py
  - src/joy/app.py
  - src/joy/widgets/project_detail.py
  - src/joy/widgets/project_list.py
  - tests/test_tui.py
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-04-11
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

This phase delivers CRUD operations for projects and objects: four modal screens (`NameInputModal`, `PresetPickerModal`, `ValueInputModal`, `ConfirmationModal`), wired into `JoyApp` and `ProjectDetail`/`ProjectList` widgets. The modal screens are clean and well-structured. The main concerns are a cursor-positioning logic bug on object deletion, a missing user feedback path in the preset picker, and a `None`-safety gap in the delete confirmation closure. Test coverage is solid with good use of `mock_store`/`mock_save` fixtures.

## Warnings

### WR-01: Delete-object cursor moves backward when it should stay in place

**File:** `src/joy/widgets/project_detail.py:287`

**Issue:** After deleting an object at cursor position N, the cursor is set to `max(0, prev_cursor - 1)`. When the deleted item is not the last in the list, the item that was at position N+1 slides into position N — so the cursor should remain at `prev_cursor` (clamped to the new length). The current code moves one step earlier than necessary, skipping the item that is now at the deletion slot. Only when deleting the very last item should the cursor decrement.

**Fix:**
```python
def on_confirm(confirmed: bool) -> None:
    if not confirmed:
        return
    try:
        idx = self._project.objects.index(item)
        self._project.objects.pop(idx)
    except ValueError:
        return
    self._save_toggle()
    # Stay at prev_cursor unless it was the last item; then step back
    total_after = len(self._project.objects)
    target_cursor = min(prev_cursor, total_after - 1) if total_after > 0 else -1
    self._set_project_with_cursor(self._project, max(0, target_cursor))
    self.app.notify(f"Deleted: {kind_val} '{value_display}'", markup=False)
```

### WR-02: `on_confirm` closure accesses `self._project` without a None guard

**File:** `src/joy/widgets/project_detail.py:281`

**Issue:** The `on_confirm` closure inside `action_delete_object` is called after the user interacts with the `ConfirmationModal`. Between the time the guard check runs (line 268) and the closure executes, `self._project` could theoretically be set to `None` (e.g., all projects deleted from another code path). Line 281 calls `self._project.objects.index(item)` without checking `self._project is not None`, which would raise `AttributeError`.

**Fix:**
```python
def on_confirm(confirmed: bool) -> None:
    if not confirmed:
        return
    if self._project is None:
        return  # project was cleared while confirmation was open
    try:
        idx = self._project.objects.index(item)
        self._project.objects.pop(idx)
    except ValueError:
        return
    ...
```

### WR-03: `PresetPickerModal` gives no feedback when Enter is pressed with an empty filter result

**File:** `src/joy/screens/preset_picker.py:104-110`

**Issue:** `on_input_submitted` handles two cases: exactly one match (auto-select) and multiple matches (focus list). When `self._filtered` is empty (the user typed something that matches nothing), the method silently does nothing — no toast, no focus shift. The user sees no response to their Enter key press.

**Fix:**
```python
def on_input_submitted(self, event: Input.Submitted) -> None:
    if len(self._filtered) == 1:
        self.dismiss(self._filtered[0])
    elif self._filtered:
        listview = self.query_one("#preset-list", ListView)
        listview.focus()
    else:
        self.app.notify("No matches", severity="warning", markup=False)
```

## Info

### IN-01: `_save_toggle` is misleadingly named — it is used as a general persistence method

**File:** `src/joy/widgets/project_detail.py:299-304`

**Issue:** `_save_toggle` was originally introduced for the space-bar toggle-default action, but it is now also called from `action_edit_object` (line 255) and `action_delete_object` (line 285). The method body is a correct general-purpose save, but its name implies toggle-specific behaviour. This creates reader confusion.

**Fix:** Rename to `_save_projects_bg` (matching the pattern already used in `JoyApp`) or `_persist_bg`:
```python
@work(thread=True, exit_on_error=False)
def _persist_bg(self) -> None:
    """Persist project changes to TOML in background thread."""
    from joy.store import save_projects  # noqa: PLC0415
    if hasattr(self.app, "_projects"):
        save_projects(self.app._projects)
```

### IN-02: `_DetailScroll` class is defined before module-level imports it depends on

**File:** `src/joy/widgets/project_detail.py:12-21`

**Issue:** `_DetailScroll` is declared at lines 12-18, then the module imports `ObjectItem`, `PresetKind`, `Project`, and `ObjectRow` at lines 20-21. Python's dynamic import resolution means this works at runtime, but the split creates an unusual ordering: class definition appears before the imports that support the rest of the module. Any reader scanning top-to-bottom must mentally re-order to understand the module.

**Fix:** Move the `_DetailScroll` class definition to after the import block, or move the imports above it.

### IN-03: `ConfirmationModal` hardcodes "delete" in the hint line

**File:** `src/joy/screens/confirmation.py:50`

**Issue:** The hint text `"Enter to delete, Escape to cancel"` is unconditional. The modal is reused for both object deletion and project deletion, and the caller already provides a `title` and `prompt`. If the modal were ever used for a non-destructive confirmation (e.g., "Enter to confirm"), this hint would be misleading. Accept a `confirm_label` parameter or generalise to "Enter to confirm".

**Fix:**
```python
def __init__(self, title: str, prompt: str, confirm_label: str = "delete") -> None:
    super().__init__()
    self._title = title
    self._prompt = prompt
    self._confirm_label = confirm_label

def compose(self) -> ComposeResult:
    with Vertical():
        yield Static(self._title, classes="modal-title")
        yield Static(self._prompt)
        yield Static(f"Enter to {self._confirm_label}, Escape to cancel", classes="modal-hint")
```

### IN-04: `JoyApp._config` defined as a class variable then shadowed by instance assignment

**File:** `src/joy/app.py:34`

**Issue:** `_config: Config = Config()` at class level creates a shared class variable. `_set_projects` then assigns `self._config = config` which shadows it with an instance variable. For a single-instance app this is harmless, but the pattern is unusual and will not survive a multi-instance scenario (the class variable would be shared across all instances). Using `__init__` for initialization is safer.

**Fix:** Add `__init__` and initialise `_config` as an instance attribute:
```python
def __init__(self) -> None:
    super().__init__()
    self._config: Config = Config()
    self._projects: list[Project] = []
```
Then remove `_config: Config = Config()` from the class body.

---

_Reviewed: 2026-04-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
