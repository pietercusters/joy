# Phase 17: Fix iTerm2 Integration Bugs - Pattern Map

**Mapped:** 2026-04-16
**Files analyzed:** 6 (4 modified, 1 removed, 1 modified test)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/joy/app.py` (modify) | controller | event-driven | `src/joy/app.py` itself | self (surgical edits) |
| `src/joy/terminal_sessions.py` (modify) | service | request-response | `src/joy/terminal_sessions.py:close_session` | exact (same module, same pattern) |
| `src/joy/widgets/project_list.py` (modify) | component | request-response | `src/joy/widgets/project_list.py:action_delete_project` | exact (same widget, same pattern) |
| `src/joy/screens/archive_modal.py` (DELETE) | screen | — | `src/joy/screens/confirmation.py` | replacement pattern |
| `src/joy/screens/__init__.py` (modify) | config | — | `src/joy/screens/__init__.py` itself | self |
| `tests/conftest.py` (modify) | test | — | `tests/test_store.py` (monkeypatch + tmp_path) | role-match |

## Pattern Assignments

---

### `src/joy/app.py` — remove auto-create branch in `_set_terminal_sessions`, add `_close_tab_bg`, modify `action_new_project` and `action_open_terminal`

**Analog:** `src/joy/app.py` (existing patterns in the same file)

**Background worker pattern** (`_close_sessions_bg`, lines 889–899 — COPY for `_close_tab_bg`):
```python
@work(thread=True, exit_on_error=False)
def _close_sessions_bg(self, sessions: list[TerminalSession]) -> None:
    """Close iTerm2 sessions gracefully in a background thread."""
    from joy.terminal_sessions import close_session  # noqa: PLC0415
    for session in sessions:
        close_session(session.session_id, force=False)
```
`_close_tab_bg` mirrors this exactly: same decorator, same lazy import, same silent-fail (no try/except needed because `close_tab` handles it internally). Replace the loop with a single `close_tab(tab_id, force=False)` call.

**Tab-create worker pattern** (`_do_create_tab_for_project`, lines 670–684 — reference for `call_from_thread` idiom):
```python
@work(thread=True, exit_on_error=False)
def _do_create_tab_for_project(self, project: Project) -> None:
    from joy.terminal_sessions import create_tab  # noqa: PLC0415
    project_name = project.name
    tab_id = create_tab(project_name)

    def _apply(tab_id: str | None = tab_id) -> None:
        self._tabs_creating.discard(project_name)
        if tab_id:
            project.iterm_tab_id = tab_id
            self._save_projects_bg()
            self._load_terminal()

    self.app.call_from_thread(_apply)
```

**Stale-heal block to KEEP** (inside `_set_terminal_sessions`, lines 246–259 — delete only the `elif` branch):
```python
# KEEP:
if project.iterm_tab_id and project.iterm_tab_id not in live_tab_ids:
    project.iterm_tab_id = None
    needs_save = True
    # ADD: self.notify(f"'{project.name}' tab closed — press h to relink", markup=False)

# DELETE this entire elif block:
elif project.iterm_tab_id is None and project.name not in self._tabs_creating:
    self._tabs_creating.add(project.name)
    self._do_create_tab_for_project(project)
```

**Notification pattern** (used throughout `app.py` — e.g., line 626, 640, 696):
```python
self.notify(f"'{project.name}' tab closed — press h to relink", markup=False)
# For warnings:
self.app.call_from_thread(self.notify, "Tab session not found", severity="warning", markup=False)
```

**`action_new_project` auto-create line to DELETE** (line 642):
```python
# DELETE this line:
self._do_create_tab_for_project(project)
```

**`action_open_terminal` — replace the else-notify with create logic** (lines 815–829):
```python
def action_open_terminal(self) -> None:
    # existing guard code unchanged (lines 817-825) ...
    if project.iterm_tab_id:
        self._do_activate_tab(project.iterm_tab_id)
    else:
        # CHANGE: was self.notify("No terminal tab linked...")
        # NEW: create if not already in-flight
        if project.name not in self._tabs_creating:
            self._tabs_creating.add(project.name)
            self._do_create_tab_for_project(project)
```

---

### `src/joy/terminal_sessions.py` — add `close_tab(tab_id, force=False) -> bool`

**Analog:** `src/joy/terminal_sessions.py:close_session` (lines 196–222) — exact same structure

**Import pattern** (lines 1–6, 70–71 — lazy imports inside function body):
```python
# Module-level: only stdlib + project imports
import subprocess
from joy.models import TerminalSession

# Inside each function body — lazy iTerm2 imports:
import iterm2
from iterm2.connection import Connection
```

**`close_session` — copy and adapt for `close_tab`** (lines 196–222):
```python
def close_session(session_id: str, force: bool = False) -> bool:
    """Close an iTerm2 session. Returns True on success, False on failure.

    force=False for graceful close, force=True to skip iTerm2's confirmation.
    If session is already gone (None), returns True.
    All iterm2 imports are lazy to avoid startup overhead.
    """
    import iterm2
    from iterm2.connection import Connection

    success = False

    async def _close(connection):
        nonlocal success
        app = await iterm2.async_get_app(connection)
        session = app.get_session_by_id(session_id)
        if session is None:
            success = True  # already gone
            return
        await session.async_close(force=force)
        success = True

    try:
        Connection().run_until_complete(_close, retry=False)
    except Exception:
        pass
    return success
```

For `close_tab`, the inner `_close` coroutine must iterate `app.terminal_windows` → `window.tabs` to find the tab by `tab_id` (same loop as `fetch_sessions` lines 79–87), then call `tab.async_close(force=force)`. If no matching tab is found, return `True` (already gone — mirrors the `session is None` guard).

**Tab iteration pattern** (from `fetch_sessions`, lines 79–88 — reference for finding a tab by tab_id):
```python
for window in app.terminal_windows:
    for tab in window.tabs:
        if tab.tab_id == tab_id:
            await tab.async_close(force=force)
            success = True
            return
# If we fall through: tab already gone
success = True
```

---

### `src/joy/widgets/project_list.py` — modify `action_delete_project` and `action_archive_project`

**Analog:** `action_delete_project` (lines 471–517) — exact reference for `_close_tab_bg` call placement

**`action_delete_project` — where to add tab-close call** (inside `on_confirm`, after confirmed check, lines 481–509):
```python
def on_confirm(confirmed: bool) -> None:
    if not confirmed:
        return
    # ADD before _save_projects_bg:
    if project.iterm_tab_id:
        self.app._close_tab_bg(project.iterm_tab_id)
    projects = self.app._projects
    try:
        projects.remove(project)
    except ValueError:
        return
    self.app._save_projects_bg()
    # ... rest unchanged
```

**`action_archive_project` — REPLACE ArchiveModal with ConfirmationModal** (lines 550–612):

Current import to REMOVE:
```python
from joy.screens.archive_modal import ArchiveChoice, ArchiveModal  # noqa: PLC0415
```

New import (matches `action_delete_project` pattern, line 473):
```python
from joy.screens import ConfirmationModal  # noqa: PLC0415
```

New callback signature — replaces `on_archive(choice: ArchiveChoice)`:
```python
def on_archive(confirmed: bool) -> None:
    if not confirmed:
        return
    # Always close tab (D-10, D-12):
    if project.iterm_tab_id:
        self.app._close_tab_bg(project.iterm_tab_id)
    # Strip WORKTREE + TERMINALS objects (keep this logic from current code, lines 566-570)
    stripped_objects = [
        obj for obj in project.objects
        if obj.kind not in (PresetKind.WORKTREE, PresetKind.TERMINALS)
    ]
    # ... rest of archive logic unchanged (build ArchivedProject, remove from list, etc.)
```

New `push_screen` call — matches `action_delete_project` pattern (lines 511–517):
```python
self.app.push_screen(
    ConfirmationModal(
        title="Archive Project",
        prompt=f"Archive project '{project.name}'? This will archive it and close its iTerm2 tab.",
        hint="Enter to archive, Escape to cancel",
    ),
    on_archive,
)
```

**`ConfirmationModal` signature** (from `src/joy/screens/confirmation.py` line 41):
```python
def __init__(self, title: str, prompt: str, *, hint: str = "Enter to delete, Escape to cancel") -> None:
```
The `hint` kwarg is optional but should be overridden to say "archive" not "delete".

---

### `src/joy/screens/archive_modal.py` — DELETE

**No pattern needed.** File is removed entirely.
`ArchiveModal` and `ArchiveChoice` are replaced by the existing `ConfirmationModal`.

---

### `src/joy/screens/__init__.py` — remove `ArchiveModal`/`ArchiveChoice` exports

**Analog:** `src/joy/screens/__init__.py` (lines 1–22, the full file)

**Current exports to REMOVE** (lines 2, 6, 12–13):
```python
# Lines to delete:
from joy.screens.archive_modal import ArchiveChoice, ArchiveModal
# ...
"ArchiveChoice",
"ArchiveModal",
```
All other imports and `__all__` entries stay unchanged.

---

### `tests/conftest.py` — add autouse store-path fixture

**Analog:** `tests/test_store.py` (monkeypatch pattern, line 147) + `tests/conftest.py` existing fixtures (lines 1–43)

**Existing conftest fixture structure** (lines 1–43 — follow same style: no classes, plain functions):
```python
"""Shared test fixtures for joy tests."""
from datetime import date

import pytest

from joy.models import Config, ObjectItem, PresetKind, Project


@pytest.fixture
def sample_config() -> Config:
    ...
```

**`monkeypatch` session-scope pattern** — pytest `MonkeyPatch` can be used at session scope by instantiating it manually:
```python
import pytest
from unittest.mock import patch  # alternative: use pytest.MonkeyPatch() directly

@pytest.fixture(autouse=True, scope="session")
def _isolated_store_paths(tmp_path_factory):
    """Patch all joy.store path constants to a session-scoped tmp directory.

    Prevents any test from accidentally reading/writing ~/.joy/.
    """
    tmp = tmp_path_factory.mktemp("joy_store")
    mp = pytest.MonkeyPatch()
    mp.setattr("joy.store.JOY_DIR", tmp)
    mp.setattr("joy.store.PROJECTS_PATH", tmp / "projects.toml")
    mp.setattr("joy.store.CONFIG_PATH", tmp / "config.toml")
    mp.setattr("joy.store.REPOS_PATH", tmp / "repos.toml")
    mp.setattr("joy.store.ARCHIVE_PATH", tmp / "archive.toml")
    yield
    mp.undo()
```

**Constants to patch** (from `src/joy/store.py` lines 16–20):
```python
JOY_DIR = Path.home() / ".joy"
PROJECTS_PATH = JOY_DIR / "projects.toml"
CONFIG_PATH = JOY_DIR / "config.toml"
REPOS_PATH = JOY_DIR / "repos.toml"
ARCHIVE_PATH = JOY_DIR / "archive.toml"
```
All five must be patched because module-level code (`_atomic_write`) calls `path.parent.mkdir(parents=True, ...)` on any write, and the store functions reference the constants at call-time (not import-time), so `setattr` on the module-level names is sufficient.

**test_store.py individual test paths stay unchanged** — those tests pass `path=tmp_path / "projects.toml"` explicitly; the autouse fixture is additive and does not conflict.

---

## Shared Patterns

### Background worker (all `@work` functions in `app.py`)
**Source:** `src/joy/app.py` lines 664–684, 686–696, 889–899
**Apply to:** new `_close_tab_bg` worker
```python
@work(thread=True, exit_on_error=False)
def _close_tab_bg(self, tab_id: str) -> None:
    from joy.terminal_sessions import close_tab  # noqa: PLC0415
    close_tab(tab_id, force=False)
```
- Always `@work(thread=True, exit_on_error=False)` — no variation
- Always lazy-import inside the function body (`# noqa: PLC0415`)
- No try/except needed in the worker itself — the iTerm2 function handles exceptions internally and returns bool

### Notification
**Source:** `src/joy/app.py` lines 626, 640, 696, 350
**Apply to:** stale-heal notification in `_set_terminal_sessions`
```python
self.notify(message, markup=False)                            # info (no severity)
self.notify(message, severity="warning", markup=False)        # warning
self.notify(message, severity="error", markup=False)          # error
# From a background thread:
self.app.call_from_thread(self.notify, message, severity="warning", markup=False)
```

### Lazy iTerm2 import
**Source:** `src/joy/terminal_sessions.py` lines 70–71, 116–117, 146–147, etc.
**Apply to:** new `close_tab` function
```python
import iterm2
from iterm2.connection import Connection
```
Both imports must appear inside the function body, not at module level.

### ConfirmationModal usage
**Source:** `src/joy/widgets/project_list.py` lines 473–517 (`action_delete_project`)
**Apply to:** `action_archive_project` replacement
```python
from joy.screens import ConfirmationModal  # noqa: PLC0415
self.app.push_screen(
    ConfirmationModal(title=..., prompt=..., hint=...),
    on_confirm,
)
```
Callback receives `bool` — `True` = confirmed, `False` = cancelled.

## No Analog Found

None — all files have close analogs in the codebase.

## Metadata

**Analog search scope:** `src/joy/`, `tests/`
**Files read:** `app.py`, `terminal_sessions.py`, `widgets/project_list.py`, `screens/__init__.py`, `screens/archive_modal.py`, `screens/confirmation.py`, `store.py`, `tests/conftest.py`, `tests/test_store.py`
**Pattern extraction date:** 2026-04-16
