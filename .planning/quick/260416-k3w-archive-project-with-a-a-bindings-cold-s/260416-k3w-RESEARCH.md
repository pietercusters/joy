# Quick Task 260416-k3w: Project Archive — Research

**Researched:** 2026-04-16
**Domain:** Textual modal patterns, TOML persistence, iTerm2 session management
**Confidence:** HIGH — all findings verified directly from codebase source files

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- `a` in ProjectList → new dedicated `ArchiveModal` screen (not extending ConfirmationModal). Three bindings: `Enter` = archive + close terminals, `a` = archive only, `Esc` = cancel.
- `A` in ProjectList → archive browser popup listing archived projects. Two sections: top = projects whose BRANCH value matches a currently checked-out worktree branch; bottom = remaining. Both sorted by `archived_at` descending. `u` unarchives highlighted project and closes popup.
- `ArchivedProject` wrapper dataclass: `project: Project`, `archived_at: datetime`. Keeps Project model clean.
- Storage: `~/.joy/archive.toml` with keyed schema following the `projects.toml` pattern.
- Strip `PresetKind.WORKTREE` and `PresetKind.TERMINALS` objects on archive; preserve all others (MR, BRANCH, TICKET, etc.).
- Unarchive: append restored project to `projects.toml`, remove from `archive.toml`, no WORKTREE/TERMINAL objects.
- Worktree/terminal pane code requires zero changes — `_rel_index` rebuild drops the archived project automatically on next refresh cycle.

### Claude's Discretion
- TOML storage schema for `archive.toml` (follow keyed schema pattern, add `archived_at` per entry)
- Archive popup widget structure (new Screen subclass with scrollable list)
- Whether to show section headers in the popup

### Deferred Ideas (OUT OF SCOPE)
- None specified
</user_constraints>

---

## 1. Modal Result Handling

**How `push_screen` + callback works** [VERIFIED: src/joy/widgets/project_list.py, src/joy/screens/confirmation.py]

The entire codebase uses one pattern exclusively — `push_screen(modal, callback)`:

```python
# From project_list.py action_delete_project()
def on_confirm(confirmed: bool) -> None:
    if not confirmed:
        return
    # ... do the work

self.app.push_screen(
    ConfirmationModal(title="Delete Project", prompt="..."),
    on_confirm,
)
```

The modal calls `self.dismiss(value)` and Textual delivers the value to the callback. `ModalScreen[T]` is generic — the type parameter `T` declares what `dismiss()` accepts and what the callback receives.

**For ArchiveModal**, the dismiss type should be an enum or string literal to distinguish the three outcomes:

```python
from enum import Enum

class ArchiveChoice(str, Enum):
    ARCHIVE_WITH_CLOSE = "archive_with_close"   # Enter
    ARCHIVE_ONLY = "archive_only"               # a
    CANCEL = "cancel"                           # Esc

class ArchiveModal(ModalScreen["ArchiveChoice"]):
    ...
    def action_confirm_with_close(self) -> None:
        self.dismiss(ArchiveChoice.ARCHIVE_WITH_CLOSE)
    def action_confirm_only(self) -> None:
        self.dismiss(ArchiveChoice.ARCHIVE_ONLY)
    def action_cancel(self) -> None:
        self.dismiss(ArchiveChoice.CANCEL)
```

Caller pattern in `action_archive_project()`:

```python
def on_archive(choice: ArchiveChoice) -> None:
    if choice is ArchiveChoice.CANCEL:
        return
    close_terminals = (choice is ArchiveChoice.ARCHIVE_WITH_CLOSE)
    # ... perform archive

self.app.push_screen(ArchiveModal(project=project), on_archive)
```

**Key detail:** `RepoPickerModal` uses a sentinel object (`CANCELLED = object()`) to distinguish cancel from "chose None". For ArchiveModal the three outcomes are all distinct so an enum is cleaner.

**For ArchiveBrowserModal** (`A`), it dismisses with `None` (no data needed — the unarchive operation happens inside the modal or via a callback that receives the selected `ArchivedProject`). Pattern options:

- Option A: `ModalScreen[None]` — modal performs unarchive internally and notifies via `self.app.notify(...)`, then `self.dismiss(None)`. Simplest.
- Option B: `ModalScreen[ArchivedProject | None]` — modal returns selected project, caller does the unarchive. More testable.

Option B is preferred (consistent with how `action_delete_project` works — the action handler owns the persistence logic, not the modal).

---

## 2. TOML Schema Design for archive.toml

**Existing `projects.toml` keyed schema** [VERIFIED: src/joy/store.py `_projects_to_toml`]

```toml
[projects.my-project]
name = "my-project"
created = 2025-01-15

[[projects.my-project.objects]]
kind = "branch"
value = "feature/foo"
label = ""
open_by_default = false
```

The key insight from `_repos_to_toml`: for repos, `name` is the TOML key and is NOT duplicated as a field inside the table. For projects, `name` IS stored inside the table (redundantly with the key). Follow the project pattern for archive.toml for consistency.

**Proposed archive.toml schema:**

```toml
[archive.my-project]
name = "my-project"
created = 2025-01-15
archived_at = 2026-04-16T14:30:00+00:00

[[archive.my-project.objects]]
kind = "branch"
value = "feature/foo"
label = ""
open_by_default = false
```

Top-level key is `archive` (not `projects`) to make it self-describing. `archived_at` is an ISO 8601 datetime with timezone offset — TOML natively supports offset datetime (`datetime` type), and Python's `tomllib` returns it as `datetime` with `tzinfo`. Use `datetime.now(timezone.utc)` when writing.

**Serialization for `ArchivedProject.to_dict()`:**

```python
def to_dict(self) -> dict:
    d = self.project.to_dict()   # includes name, created, objects (stripped of WORKTREE/TERMINALS)
    d["archived_at"] = self.archived_at  # datetime object — tomli_w handles offset-aware datetime natively
    return d
```

`tomli_w` serializes `datetime` objects with timezone to TOML offset datetime. `tomllib` parses them back as `datetime` with `tzinfo`. No manual formatting needed.

**Store functions needed:**

```python
ARCHIVE_PATH = JOY_DIR / "archive.toml"

def load_archived_projects(*, path: Path = ARCHIVE_PATH) -> list[ArchivedProject]: ...
def save_archived_projects(projects: list[ArchivedProject], *, path: Path = ARCHIVE_PATH) -> None: ...
```

Follow the exact `_atomic_write` + `tomli_w.dumps` pattern from `save_projects`.

---

## 3. Action Handler Pattern for `action_archive_project`

**Direct pattern from `action_delete_project`** [VERIFIED: src/joy/widgets/project_list.py lines 282-328]

```python
def action_archive_project(self) -> None:
    from joy.screens.archive_modal import ArchiveModal  # lazy import
    from joy.screens.archive_modal import ArchiveChoice

    if self._cursor < 0 or self._cursor >= len(self._rows):
        return
    project = self._rows[self._cursor].project
    cursor_at = self._cursor

    def on_archive(choice: ArchiveChoice) -> None:
        if choice is ArchiveChoice.CANCEL:
            return

        close_terminals = (choice is ArchiveChoice.ARCHIVE_WITH_CLOSE)

        # 1. Strip WORKTREE + TERMINALS objects
        stripped_objects = [
            obj for obj in project.objects
            if obj.kind not in (PresetKind.WORKTREE, PresetKind.TERMINALS)
        ]
        archived_project_data = Project(
            name=project.name,
            objects=stripped_objects,
            created=project.created,
            repo=project.repo,
        )

        # 2. Optionally close terminal sessions
        if close_terminals and self.app._rel_index is not None:
            sessions = self.app._rel_index.terminals_for(project)
            if sessions:
                self.app._close_sessions_bg(sessions)  # new @work(thread=True) method

        # 3. Remove from projects list
        projects = self.app._projects
        try:
            projects.remove(project)
        except ValueError:
            return
        self.app._save_projects_bg()

        # 4. Add to archive
        from joy.models import ArchivedProject
        from datetime import datetime, timezone
        archived = ArchivedProject(project=archived_project_data, archived_at=datetime.now(timezone.utc))
        self.app._append_to_archive_bg(archived)  # new @work(thread=True) method

        # 5. Update list, restore cursor (same as action_delete_project)
        self.set_projects(projects, self._repos)
        if projects:
            new_index = min(cursor_at, len(projects) - 1)
            def _restore():
                self.focus()
                self.select_index(new_index)
            self.call_after_refresh(_restore)
        self.app.notify(f"Archived: '{project.name}'", markup=False)

    self.app.push_screen(ArchiveModal(project=project), on_archive)
```

**Two new `@work(thread=True)` helpers needed on `JoyApp`:**

1. `_close_sessions_bg(sessions: list[TerminalSession])` — calls `close_session(s.session_id, force=False)` for each session in a background thread. Matches the pattern used in TerminalPane's close actions.

2. `_append_to_archive_bg(archived: ArchivedProject)` — loads existing `archive.toml`, appends the new entry, saves atomically. Background thread safe because it's the only writer (no concurrent writes to archive.toml at this stage).

**BINDINGS addition to ProjectList:**

```python
Binding("a", "archive_project", "Archive", show=True),
Binding("A", "open_archive_browser", "Archives", show=True),
```

---

## 4. Archive Browser Popup Approach (`A` key)

**Best structural reference: `LegendModal`** [VERIFIED: src/joy/screens/legend.py]

LegendModal is the closest match — it uses `VerticalScroll` inside a `Vertical` container inside a `ModalScreen`. For the archive browser, replace the static content with interactive rows using the ProjectList cursor pattern.

**Alternative reference: `RepoPickerModal`** — uses `ListView` + `ListItem`. Simpler for a flat list. The archive browser needs two sections (headers + rows) so the custom cursor pattern from `ProjectList`/`WorktreePane`/`TerminalPane` is a better fit.

**Recommended structure:**

```python
class ArchiveBrowserModal(ModalScreen["ArchivedProject | None"]):
    BINDINGS = [
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("u", "unarchive", "Unarchive"),
        Binding("escape", "cancel", "Close"),
    ]
    DEFAULT_CSS = """
    ArchiveBrowserModal {
        align: center middle;
    }
    ArchiveBrowserModal > Vertical {
        width: 70;
        max-height: 80%;
        background: $surface;
        border: solid $accent;
        padding: 1 2;
    }
    ArchiveBrowserModal ._archive-row.--highlight {
        background: $accent;
    }
    """

    def __init__(self, archived: list[ArchivedProject], active_branches: set[str]) -> None:
        super().__init__()
        self._archived = archived
        self._active_branches = active_branches
        self._rows: list[_ArchiveRow] = []   # flat list, excludes headers
        self._cursor: int = -1

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Archived Projects", classes="modal-title")
            with VerticalScroll():
                # Two sections built in on_mount / _rebuild()
                pass
            yield Static("↑/↓ to navigate • u: unarchive • Esc: close", classes="modal-hint")
```

**Section rendering:** In `on_mount`, split `self._archived` into `matched` (BRANCH value in `active_branches`) and `rest`. Render `SectionHeader("Active Branch")` + rows, then `SectionHeader("Other")` + rows. Populate `self._rows` with only the data rows (not headers), so cursor arithmetic works identically to `ProjectList`.

**Two-section display (Claude's discretion — recommend showing headers):** Section headers make the branch-match signal obvious. Without them users won't know why some projects appear at the top.

---

## 5. Terminal Close Approach

**`close_session()` signature** [VERIFIED: src/joy/terminal_sessions.py lines 159-185]

```python
def close_session(session_id: str, force: bool = False) -> bool:
    """Close an iTerm2 session. Returns True on success, False on failure.
    force=False for graceful close, force=True to skip iTerm2's confirmation.
    If session is already gone (None), returns True.
    """
```

Accepts `session_id: str`, optional `force: bool`. Returns `bool`.

**Thread safety:** Every function in `terminal_sessions.py` uses `Connection().run_until_complete(...)` with its own synchronous call. The pattern comment in `fetch_sessions` states "runs in @work(thread=True) worker with its own event loop." All terminal functions are designed to be called from background threads. [VERIFIED: terminal_sessions.py lines 55-100, comments]

**How TerminalPane closes sessions** — look at `app._rel_index.terminals_for(project)` to get `TerminalSession` objects, then iterate calling `close_session(s.session_id, force=False)`.

**`_close_sessions_bg` implementation:**

```python
@work(thread=True, exit_on_error=False)
def _close_sessions_bg(self, sessions: list[TerminalSession]) -> None:
    from joy.terminal_sessions import close_session  # noqa: PLC0415
    for session in sessions:
        close_session(session.session_id, force=False)
    # No UI feedback needed — sessions disappear on next refresh cycle
```

The sessions available for close come from `self.app._rel_index.terminals_for(project)` — this is the same index used by `TerminalPane`. The project may have no matched sessions (common if project was never linked to a terminal), so the session list may be empty.

**Important:** Session IDs in `_rel_index` are from the last refresh cycle. If iTerm2 sessions changed since the last refresh, IDs may be stale. `close_session` handles this gracefully — it returns `True` if session is already gone.

---

## 6. Worktree Branch Matching

**Getting active branch names** [VERIFIED: src/joy/app.py, src/joy/resolver.py]

`JoyApp` stores `self._current_worktrees: list[WorktreeInfo]` updated on every refresh cycle (line 95, set in `_set_worktrees` line 214). `WorktreeInfo.branch` is the branch name string (or `"HEAD"` for detached HEAD).

The `RelationshipIndex` has `_project_for_wt_branch` but that's keyed by `(repo_name, branch)` pairs, not raw branch strings. For archive browser branch-matching, we need raw branch names only.

**Cleanest approach — pass active branch set to the modal:**

```python
def action_open_archive_browser(self) -> None:
    from joy.screens.archive_browser import ArchiveBrowserModal  # lazy import
    from joy.store import load_archived_projects               # lazy import

    archived = load_archived_projects()
    if not archived:
        self.app.notify("No archived projects.", markup=False)
        return

    # Build active branch set from most recent worktree data
    active_branches: set[str] = {
        wt.branch for wt in self.app._current_worktrees
        if wt.branch != "HEAD"  # exclude detached HEAD
    }

    def on_unarchive(result: ArchivedProject | None) -> None:
        if result is None:
            return
        # Restore project (stripped — already has no WORKTREE/TERMINALS)
        self.app._projects.append(result.project)
        self.app._save_projects_bg()
        self.app._remove_from_archive_bg(result)
        self.set_projects(list(self.app._projects), self._repos)
        self.app.notify(f"Unarchived: '{result.project.name}'", markup=False)

    self.app.push_screen(
        ArchiveBrowserModal(archived=archived, active_branches=active_branches),
        on_unarchive,
    )
```

**Branch-match logic inside ArchiveBrowserModal:**

```python
def _partition_by_branch(self) -> tuple[list[ArchivedProject], list[ArchivedProject]]:
    matched, rest = [], []
    for ap in self._archived:
        branch_objs = [o for o in ap.project.objects if o.kind == PresetKind.BRANCH]
        if any(o.value in self._active_branches for o in branch_objs):
            matched.append(ap)
        else:
            rest.append(ap)
    # Both sorted by archived_at descending
    matched.sort(key=lambda ap: ap.archived_at, reverse=True)
    rest.sort(key=lambda ap: ap.archived_at, reverse=True)
    return matched, rest
```

**Important:** `_current_worktrees` is the last-refreshed snapshot. If the user opens the archive browser before the first worktree refresh completes, the list is empty (initialized to `[]` in `__init__`). The branch-matching section will simply be empty — all projects land in "Other". This is acceptable behavior (not a bug, graceful degradation).

**Alternative using `_rel_index`:** `_rel_index._project_for_wt_branch` keys are `(repo_name, branch)` tuples, so extracting just branch names would require iterating all keys. Less clean than using `_current_worktrees` directly.

---

## 7. Risks and Smell Flags

### Risk 1: `action_open_archive_browser` lives in ProjectList but needs app-level data
`_current_worktrees` and `load_archived_projects()` are app-level concerns. The pattern in this codebase is that `action_*` in `ProjectList` accesses `self.app.*` freely (see `action_rename_project` line 255, `action_delete_project` line 295). This is an established pattern, not a smell. Still, the action could live in `JoyApp` with a delegation call from `ProjectList` — but the existing `action_new_project` shows `self.app.action_new_project()` delegation is also used. Both approaches are valid; delegation keeps ProjectList thinner.

### Risk 2: `_append_to_archive_bg` and `_remove_from_archive_bg` are NOT safe for concurrent calls
Both functions read-then-write `archive.toml`. If archive + unarchive operations somehow overlap (unlikely in practice — one user, one action at a time), the second write could overwrite the first. Given this is a single-user TUI, this is acceptable. A docstring note is sufficient.

### Risk 3: `archived_at` timezone handling
`datetime.now(timezone.utc)` produces an offset-aware datetime. `tomllib` parses TOML offset datetimes as offset-aware `datetime`. The round-trip is clean. If the code ever uses `datetime.now()` (naive), the sort in the archive browser will fail when mixing naive and aware datetimes. Enforce `datetime.now(timezone.utc)` at write time (easy — single call site).

### Risk 4: `archive.toml` does not exist on first archive operation
`_append_to_archive_bg` needs to handle the "file doesn't exist yet" case in `load_archived_projects`. The existing `load_projects` pattern returns `[]` when the file is missing — follow exactly. `_atomic_write` already handles creating parent dirs (`path.parent.mkdir(parents=True, exist_ok=True)`).

### Risk 5: ArchiveBrowserModal loads `archive.toml` synchronously on the main thread
`load_archived_projects()` is a file read. For small files (which archive.toml will always be — it's a developer's project list), a synchronous read in an action handler is fine. This matches how the settings modal works. No background worker needed here.

### Risk 6: Key binding conflicts
`a` in ProjectList currently has no binding. `A` (shift+a) has no binding. Safe to add both. [VERIFIED: project_list.py BINDINGS lines 102-114]

`u` in `JoyApp.BINDINGS` is bound to `open_note` (show=False, line 73). This is a global binding. Inside `ArchiveBrowserModal`, the modal's own `u` binding on the screen will take priority over the app-level binding — `ModalScreen` pushes a new screen on the stack, so app-level bindings are not active while a modal is displayed. Safe. [ASSUMED: Textual modal screen focus behavior — consistent with all existing modal patterns in this codebase]

### Smell: archive.toml written as a full reload+rewrite on every archive operation
`_append_to_archive_bg` will: `load_archived_projects()` → `append(new_entry)` → `save_archived_projects(all_entries)`. For a small file this is fine. The same pattern is used for `save_projects`. Not a smell given the data scale.

---

## Implementation File Map

| New File | Purpose |
|----------|---------|
| `src/joy/screens/archive_modal.py` | `ArchiveModal` (3-option confirmation) + `ArchiveChoice` enum |
| `src/joy/screens/archive_browser.py` | `ArchiveBrowserModal` (A popup) |

| Modified File | Changes |
|---------------|---------|
| `src/joy/models.py` | Add `ArchivedProject` dataclass, add `datetime` import |
| `src/joy/store.py` | Add `ARCHIVE_PATH`, `load_archived_projects`, `save_archived_projects`, `_archived_to_toml`, `_toml_to_archived` |
| `src/joy/widgets/project_list.py` | Add `Binding("a", ...)`, `Binding("A", ...)`, `action_archive_project()`, `action_open_archive_browser()` |
| `src/joy/app.py` | Add `_close_sessions_bg()`, `_append_to_archive_bg()`, `_remove_from_archive_bg()` |
| `src/joy/screens/__init__.py` | Export new modals if needed |

---

## Confidence Summary

| Area | Level | Reason |
|------|-------|--------|
| Modal result handling | HIGH | Pattern verified directly in project_list.py and confirmation.py |
| TOML schema design | HIGH | Verified _projects_to_toml and tomli_w datetime handling from store.py and models.py |
| Action handler pattern | HIGH | Direct copy of action_delete_project structure |
| Archive browser popup | HIGH | LegendModal + VerticalScroll pattern verified, cursor pattern from ProjectList verified |
| Terminal close | HIGH | close_session() signature verified, thread pattern verified |
| Branch matching | HIGH | _current_worktrees field verified in app.py, WorktreeInfo.branch verified in models.py |
| `u` key modal binding precedence | ASSUMED | Consistent with all modal patterns but not explicitly verified in Textual docs this session |
