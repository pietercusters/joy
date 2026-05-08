---
phase: 21-ui-polish
reviewed: 2026-05-08T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - src/joy/widgets/project_list.py
  - src/joy/widgets/project_detail.py
  - src/joy/widgets/worktree_pane.py
  - src/joy/widgets/terminal_pane.py
  - src/joy/widgets/mr_pane.py
  - src/joy/app.py
findings:
  critical: 0
  warning: 5
  info: 6
  total: 11
status: issues_found
---

# Phase 21: Code Review Report

**Reviewed:** 2026-05-08
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Six widget and application files were reviewed. The codebase is well-structured overall: consistent cursor-restore patterns across all panes, non-focusable scroll containers used correctly, and background workers used consistently for I/O. No security vulnerabilities or data-loss bugs were found.

Five warnings were identified — two are logic bugs (a silent swallowed error in `_update_highlight`, and incorrect `emit` guard in `TerminalPane`), two are robustness gaps (bare-`except` swallowing all exceptions during rebuild and `_render_generation` initialized via `getattr`), and one is a layout calculation discrepancy in the ribbon-width formula. Six info items cover dead code, naming, and minor style patterns.

---

## Warnings

### WR-01: `_update_highlight` in `TerminalPane` ignores `emit` parameter — always emits

**File:** `src/joy/widgets/terminal_pane.py:378`
**Issue:** `_update_highlight` has an `emit: bool = True` parameter, but the guard at line 386 only checks `is_syncing` — it never checks `emit`. When `set_sessions` calls `self._update_highlight(emit=False)` at line 374, the intent is to suppress the `SessionHighlighted` message during a refresh rebuild. However, if `is_syncing` happens to be `False` at that moment (e.g., when called outside `_set_terminal_sessions`, such as from a direct `set_sessions` call in tests or future code paths), the message fires anyway, defeating the guard. The `WorktreePane` equivalent at `worktree_pane.py:415` has the same defect in the same position.

**Fix:**
```python
def _update_highlight(self, *, emit: bool = True) -> None:
    for row in self._rows:
        row.remove_class("--highlight")
    if 0 <= self._cursor < len(self._rows):
        self._rows[self._cursor].add_class("--highlight")
        self._rows[self._cursor].scroll_visible()
        if emit and not getattr(getattr(self.app, "_coordinator", None), "is_syncing", False):
            self.post_message(
                self.SessionHighlighted(self._rows[self._cursor].session_name)
            )
```
Apply the same fix to `WorktreePane._update_highlight` at `worktree_pane.py:415`.

---

### WR-02: Bare `except` in `ProjectList._rebuild` swallows all exceptions including app-level bugs

**File:** `src/joy/widgets/project_list.py:520`
**Issue:** The `try/except Exception: pass` block at the end of `_rebuild` calls `self.app.update_badges()` and silently ignores all failures. While the comment says "app not fully mounted yet", catching `Exception` broadly will also suppress genuine programming errors in `update_badges` (e.g., `AttributeError`, `TypeError`) making them invisible during development and production. The same pattern at `app.py:265` (MRPane mount guard) is more defensible since it is a narrow operation.

**Fix:** Narrow the exception to the specific Textual no-match exception, or at minimum log the error:
```python
from textual.css.query import NoMatches  # noqa: PLC0415
try:
    self.app.update_badges()
except (NoMatches, AttributeError):
    pass  # app not fully mounted yet — badges will come on next refresh
```

---

### WR-03: `_render_generation` initialized with `getattr` fallback — can mask missing `__init__` initialization

**File:** `src/joy/widgets/project_detail.py:134`
**Issue:** `set_project` initializes `_render_generation` via `getattr(self, "_render_generation", 0) + 1` (line 134), and `_render_project` reads it the same way (line 197). This pattern exists because `_render_generation` is never set in `__init__`. The `getattr` fallback silently handles the missing attribute, but if a subclass or test accidentally calls `_render_project` before `set_project`, the generation counter will always be 0/0 and the stale-render guard is defeated — every deferred callback will fire, potentially rendering stale data on top of fresh data. The same pattern is used in `_set_project_with_cursor` at line 335.

**Fix:** Initialize `_render_generation` in `__init__`:
```python
def __init__(self, **kwargs) -> None:
    super().__init__(**kwargs)
    self._project: Project | None = None
    self._cursor: int = -1
    self._rows: list[ObjectRow] = []
    self._render_generation: int = 0          # add this line
    self._resolver_worktrees: list[WorktreeInfo] = []
    self._resolver_terminals: list[TerminalSession] = []
    self._readonly_items: set[int] = set()
    self.border_title = "Details"
```
Then replace the `getattr` usages with direct attribute access.

---

### WR-04: Ribbon-width formula does not account for emoji/wide-char icon width

**File:** `src/joy/widgets/project_list.py:189`
**Issue:** `ribbon_width = 2 * len(ribbon_icons) - 1` computes 11 for 6 icons and assumes each icon is exactly 1 terminal column wide. The icons (`ICON_BRANCH`, `ICON_TICKET`, etc.) are Nerd Font codepoints from `joy/widgets/icons.py` and are typically rendered as 2-column-wide glyphs by most terminal emulators. If they render as double-width, the actual ribbon occupies 17 columns, not 11. This would cause the name truncation budget (`name_budget`) to be 6 characters too large, making the row overflow the available width and the text to be clipped by the terminal rather than by the carefully built ellipsis logic. Whether this manifests depends on the terminal and font, but it is worth an explicit comment or correction.

**Fix:** Verify measured width of the icons in practice. If they are double-width, update:
```python
# Each Nerd Font icon occupies 2 terminal columns; 6 icons + 5 single-space separators = 17
ribbon_width = 2 * len(ribbon_icons) + (len(ribbon_icons) - 1)  # = 17 for 6 icons
```
At minimum, add a comment documenting the assumption so a future contributor knows to re-check when icons change.

---

### WR-05: `action_force_delete_object` accesses `self._project.objects` without None guard

**File:** `src/joy/widgets/project_detail.py:410`
**Issue:** `action_force_delete_object` calls `self._project.objects.index(item)` at line 410 without first checking `self._project is not None`. While `highlighted_object` returns `None` when `self._project` is `None` (line 431), the early-return check at line 401 only tests `item is None`, not `self._project is None`. In theory these are equivalent because `highlighted_object` requires `self._project` to be set before returning a non-None item. However, if `self._project` is cleared between the `highlighted_object` call and the `objects.index` call (e.g., via a concurrent refresh), this will raise `AttributeError: 'NoneType' object has no attribute 'objects'`. The same gap exists in `action_delete_object` at line 380.

**Fix:**
```python
def action_force_delete_object(self) -> None:
    item = self.highlighted_object
    if item is None or self._project is None:   # guard both
        self.app.notify("No object selected", severity="error", markup=False)
        return
    ...
```

---

## Info

### IN-01: `GroupHeader` is duplicated across four files without a shared base

**File:** `src/joy/widgets/project_list.py:50`, `src/joy/widgets/project_detail.py:32`, `src/joy/widgets/worktree_pane.py:92`, `src/joy/widgets/terminal_pane.py:68`, `src/joy/widgets/mr_pane.py:49`
**Issue:** `GroupHeader` — an identical `Static` subclass with the same `DEFAULT_CSS` — is copy-pasted five times. Comments in the files acknowledge this as intentional to avoid "cross-widget coupling," but the CSS block is now a maintenance burden: a future style change must be made in five places. The rationale makes sense for widget coupling, but the CSS could be moved to a shared constants module without introducing widget coupling.
**Fix:** Extract the CSS string to a shared location (e.g., `joy/widgets/group_header.py`) and import it. Alternatively, accept the duplication and add a `# noqa: duplicate` note so a reviewer does not mistake it for a mistake.

---

### IN-02: `_do_rename_session` notification message uses f-string without interpolation

**File:** `src/joy/widgets/terminal_pane.py:505`
**Issue:** `self.app.call_from_thread(self.app.notify, f"Renamed session", markup=False)` uses an f-string with no interpolated values. The new name is available in the `new_name` parameter.
**Fix:**
```python
self.app.call_from_thread(self.app.notify, f"Renamed to: '{new_name}'", markup=False)
```

---

### IN-03: Dead `import` of `RelationshipIndex` in `update_badges` is unused

**File:** `src/joy/widgets/project_list.py:814`
**Issue:** `from joy.resolver import RelationshipIndex` is imported inside `update_badges` but the type is only referenced in a `# type: ignore` comment. The actual `index` parameter is typed as `object`. The import adds startup cost to every `update_badges` call and the annotation is non-functional.
**Fix:** Remove the import; the `# type: ignore[union-attr]` comments work without it:
```python
def update_badges(self, index: object, mr_data: dict | None = None, mr_authored: list | None = None) -> None:
    avail_width = self._get_available_width()
    for row in self._rows:
        ...
```

---

### IN-04: `action_edit_object` calls `self.set_project(self._project)` without None check

**File:** `src/joy/widgets/project_detail.py:353`
**Issue:** Inside the `on_value` callback at line 353, `self.set_project(self._project)` is called. `self._project` could theoretically be `None` if focus moved away between the modal being pushed and the user confirming. `set_project` does accept `None` implicitly (it just stores it), and `_render_project` guards against it at line 199, so this will not crash. But the re-render will clear the pane rather than show the updated value. Worth a guard for correctness.
**Fix:**
```python
def on_value(new_value: str | None) -> None:
    if new_value is None:
        return
    item.value = new_value
    self._save_toggle()
    if self._project is not None:
        self.set_project(self._project)
    ...
```

---

### IN-05: `MRRow.build_content` computes `prefix` string but never uses it

**File:** `src/joy/widgets/mr_pane.py:115`
**Issue:** `prefix = f"XX !{detail.mr_number}  "` is computed at line 115 for use as a length reference for `title_budget`, but the value `"XX"` is a placeholder that does not match the actual rendered prefix. The actual prefix rendered is `ICON_ACTIONABLE` or `" "` (1 char) plus the MR icon (1 char) plus ` !{number}  ` (variable). The `title_budget` calculation using `len(prefix)` is therefore wrong for any MR number > 9, and the `prefix` variable is never used in rendering — only its `len()` is used.
**Fix:** Replace with an accurate length computation:
```python
# dot/space (1) + MR icon (1) + " !" (2) + number digits + "  " (2)
prefix_len = 1 + 1 + 2 + len(str(detail.mr_number)) + 2
title_budget = max(max_width - prefix_len, 5)
```
And remove the unused `prefix` variable.

---

### IN-06: `app.py` BINDINGS declares duplicate `"x"` key entries — one is always hidden

**File:** `src/joy/app.py:61`
**Issue:** Two `Binding` entries for `"x"` exist in `BINDINGS` (lines 61-62): one for `"toggle_sync"` and one for `"disable_sync"`. Textual resolves this via `check_action`, which is correctly implemented. However, having two bindings for the same key in the class-level `BINDINGS` list is unusual and may confuse future maintainers who assume each key maps to exactly one action. A comment explaining the intentional dual-binding pattern would help.
**Fix:** Add an explanatory comment:
```python
# Two bindings for 'x': only one is shown at a time via check_action() (D-13, SYNC-09)
Binding("x", "toggle_sync",  "Sync: on"),   # shown when sync is ON
Binding("x", "disable_sync", "Sync: off"),  # shown when sync is OFF
```

---

_Reviewed: 2026-05-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
