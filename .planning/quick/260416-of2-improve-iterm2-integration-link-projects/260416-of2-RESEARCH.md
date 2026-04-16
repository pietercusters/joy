# Quick Task 260416-of2: Improve iTerm2 Integration — Research

**Researched:** 2026-04-16
**Domain:** iTerm2 Python API, Textual TUI refactor, TOML schema design
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Auto-recreate tab when stored tab ID is no longer valid: silently create a new tab, update stored ID. No user-visible errors.
- Tab creation on project creation: best-effort, silent. If iTerm2 is not running or the call fails, skip and continue. No blocking error.
- "Other" group: all sessions whose tab is not linked to any joy project, regardless of window/tab.

### Claude's Discretion
- Whether to use window IDs or tab IDs as the link (investigate stability)
- How to detect a "stale" tab ID
- Exact layout changes in the Terminals pane
- Whether to store the tab ID in project config (TOML) or separate state file
- Refactoring scope: keep clean, remove obsolete link-icon code paths

### Deferred Ideas (OUT OF SCOPE)
- None specified
</user_constraints>

---

## Summary

The iTerm2 Python API (used exclusively in joy today) exposes a `tab_id` property on `Tab` objects and `session_id` on `Session` objects — both are described as "globally unique identifiers" (`unique_identifier` in the underlying protobuf). Neither persists across iTerm2 restarts: they are runtime-assigned UUIDs generated when iTerm2 creates the session/tab, and iTerm2 does not save/restore them between restarts.

**Consequence for design:** Because no stable cross-restart ID exists, the stored ID becomes stale after every iTerm2 restart. The user has already decided this is acceptable (auto-recreate silently). The implementation must detect "stale" gracefully — the API provides a direct path: `app.get_tab_by_id(tab_id)` returns `None` for unknown IDs.

**Primary recommendation:** Store `tab_id` (not `session_id`) per project in `Project.iterm_tab_id: str | None`. Use the Python API exclusively (already the pattern). On fetch, enumerate all tabs and build a `tab_id -> [TerminalSession]` map for the pane grouping. Stale detection is `app.get_tab_by_id(stored_id) is None`.

---

## Focus Area 1: iTerm2 Unique IDs — Stability Analysis

### What exists in the API

[VERIFIED: uv run iterm2 source inspection]

| Object | Property | Type | Globally unique? | Persists across restart? |
|--------|----------|------|------------------|--------------------------|
| `Tab` | `tab_id` | `str` | Yes — described as "globally unique identifier" | **No** — runtime-assigned |
| `Session` | `session_id` | `str` | Yes — from `unique_identifier` protobuf field | **No** — runtime-assigned |
| `Window` | `window_id` | `str` | Yes | **No** — runtime-assigned |

**Key finding:** The iterm2 Python library uses `unique_identifier` from iTerm2's protobuf API (`api.proto`). These are UUIDs assigned when the tab/session is created in the current iTerm2 process. They reset on restart. iTerm2 does not persist these UUIDs to disk. [VERIFIED: source inspection of `iterm2.Session.__init__` — sets `self.__session_id = summary.unique_identifier`]

### Why tab_id is better than session_id for this use case

- A tab has one `tab_id`. A tab can have multiple sessions (split panes). Storing `tab_id` as the project link means the whole tab (including any splits) belongs to the project.
- `session_id` is what joy currently stores (via `create_session` returning `session.session_id`). This is a session-level granularity, which is smaller than a tab.
- The user wants "group by tab" in the pane — so tab_id is the natural key.
- `app.get_tab_by_id(tab_id)` is a direct O(1) lookup available on App. [VERIFIED: iterm2 App source]

### Stale detection

```python
# Inside an async context with `app = await iterm2.async_get_app(connection)`
tab = app.get_tab_by_id(stored_tab_id)
if tab is None:
    # Tab is stale — create new tab, store new tab_id
```

`get_tab_by_id` returns `None` for unknown IDs without raising. [VERIFIED: iterm2 App source]

---

## Focus Area 2: Current joy iTerm2 Integration — Critical Audit

### What exists today

**`terminal_sessions.py`** — All iTerm2 interaction via Python API (lazy import pattern):

| Function | What it does | What it returns |
|----------|-------------|-----------------|
| `fetch_sessions()` | Enumerates all windows/tabs/sessions | `list[TerminalSession] | None` |
| `create_session(name)` | Creates new tab in front window, sets session name | `session_id: str | None` |
| `rename_session(session_id, new_name)` | Renames session by session_id | `bool` |
| `close_session(session_id, force)` | Closes session by session_id | `bool` |
| `activate_session(session_id)` | Focuses session by session_id | `bool` |

**Critical gaps in `fetch_sessions()`:**

```python
# Current: only stores session-level data, NO tab_id
raw.append((session.session_id, session.name or "", job, cwd, tty))
```

Tab membership is currently lost at fetch time. To implement tab-level grouping, `fetch_sessions` must also capture `tab.tab_id` per session.

**`create_session(name)`:**

```python
# Current: returns session_id
result = session.session_id
```

Must be changed to return `tab_id` (from `tab = await window.async_create_tab(); tab.tab_id`). [VERIFIED: terminal_sessions.py]

### What's stored in project TOML

**`PresetKind.TERMINALS` object:** `obj.value` = session name string (e.g., `"dexter-power claude (node)"`).

The relationship resolver matches by `session.session_name == obj.value`. [VERIFIED: resolver.py, projects.toml sample]

**No tab ID is stored anywhere today.** The existing design is purely name-based matching.

### What the link-icon mechanism does today

`app.py` calls `_update_terminal_link_status()` which pushes `linked_names: set[str]` (session names) to `TerminalPane.set_linked_names()`. Each `SessionRow` receives `is_linked=True/False` and renders `ICON_LINK` (`\uf0c1`) if linked. [VERIFIED: terminal_pane.py lines 29, 158-159, 335-346]

This entire mechanism becomes obsolete after this task: grouping by tab replaces the link icon as the visual indicator of project ownership.

---

## Focus Area 3: Current Sessions Pane Structure

### Current grouping logic (terminal_pane.py `set_sessions`)

1. Split all sessions into `claude_sessions` (is_claude=True) and `other_sessions`
2. Claude group: sorted busy-first then alpha, rendered under `GroupHeader("Claude")`
3. Other group: sorted alpha, rendered under `GroupHeader("Other")`
4. Each row: `SessionRow(session, is_linked=...)` — is_linked drives the link icon

### New grouping logic (target)

1. Each project with a linked tab gets a group header (project name)
2. Sessions whose tab_id matches the project's stored tab_id appear under that header
3. Dot marker (existing INDICATOR_BUSY/INDICATOR_WAITING) kept for Claude detection
4. All sessions in tabs not linked to any project fall under `GroupHeader("Other")`

### Key data structure change needed

`TerminalSession` must carry `tab_id: str` so the pane can group by it:

```python
@dataclass
class TerminalSession:
    session_id: str
    session_name: str
    foreground_process: str
    cwd: str
    tab_id: str = ""          # NEW: tab this session belongs to
    is_claude: bool = False
```

[VERIFIED: models.py — current dataclass has no tab_id field]

### Data flow for new grouping

`set_sessions` in `TerminalPane` needs to receive the project->tab_id mapping alongside sessions. Two options:

**Option A (recommended):** Pass `tab_groups: list[tuple[str, str]]` to `TerminalPane` — list of `(project_name, tab_id)` pairs in display order. Pane builds the groups from this + `session.tab_id`.

**Option B:** Build a `tab_id -> project_name` dict in `app.py` and push it to `TerminalPane` via a new method (analogous to `set_linked_names`).

Option A is cleaner — one call conveys all grouping data.

---

## Focus Area 4: Tab ID Persistence — Conclusion

**Conclusion:** `tab_id` does NOT survive iTerm2 restarts. It is a runtime UUID. [VERIFIED: source inspection]

**Implication for storage design:** Storing `tab_id` in `Project` is still correct — it just becomes stale after each restart and must be auto-healed per the user's locked decision. The stored value is "the tab ID that was valid last time joy created or found a tab for this project."

**Where to store:** Project TOML (`projects.toml`) in the `Project` model as a new optional field `iterm_tab_id: str | None = None`. Rationale:
- It is per-project state, not global state
- TOML already handles optional fields cleanly (field absent = None)
- Putting it in a separate state file adds complexity for no benefit [ASSUMED: no architectural reason discovered to separate it]
- The `Project.to_dict()` / `_toml_to_projects()` pair already handles optional fields (see `repo` field pattern)

**TOML schema change (additive, backward-compatible):**

```toml
[projects."My Project"]
name = "My Project"
created = 2026-04-16
iterm_tab_id = "ABCDEF12-3456-7890-ABCD-EF1234567890"   # NEW optional field
```

If field is absent → `iterm_tab_id = None` → treat as stale, create new tab on next access.

---

## Focus Area 5: Stale Tab Detection and Auto-Heal

### Detection strategy

At fetch time (inside `fetch_sessions`), collect all live `tab_id` values from iTerm2. The pane receives both sessions and the live tab_id set. In `app.py`, when building the project->tab mapping, check if the stored `project.iterm_tab_id` is in the live set.

**Pattern:**

```python
# In fetch_sessions, collect live tab IDs
live_tab_ids: set[str] = set()
for window in app.terminal_windows:
    for tab in window.tabs:
        live_tab_ids.add(tab.tab_id)
        for session in tab.sessions:
            raw.append((session.session_id, tab.tab_id, session.name or "", job, cwd, tty))
```

In `app.py` `_set_terminal_sessions`:

```python
for project in self._projects:
    if project.iterm_tab_id and project.iterm_tab_id not in live_tab_ids:
        # Stale: clear stored ID (no auto-create at refresh time — only on explicit open)
        # OR: trigger auto-create silently
        self._heal_stale_tab(project)
```

### Auto-heal strategy

**Trigger:** On `_set_terminal_sessions` when stored tab_id is not in live_tab_ids AND iTerm2 is available (sessions list is not None).

**Action:** `_do_create_tab_for_project(project)` — background worker that calls a new `create_tab(name) -> str | None` (returns `tab_id`, not `session_id`), updates `project.iterm_tab_id`, saves projects.

**When to NOT auto-heal:** When `sessions is None` (iTerm2 unavailable) — stale check requires live data.

### New function needed: `create_tab(name) -> str | None`

Replaces current `create_session(name) -> session_id`. Returns `tab.tab_id`:

```python
def create_tab(name: str) -> str | None:
    """Create new iTerm2 tab, set session name, return tab_id."""
    ...
    async def _create(connection):
        nonlocal result
        app = await iterm2.async_get_app(connection)
        window = app.current_window
        if window is None:
            return
        tab = await window.async_create_tab()
        if tab is None or not tab.sessions:
            return
        session = tab.sessions[0]
        await session.async_set_name(name)
        result = tab.tab_id   # KEY CHANGE: tab_id not session_id
    ...
```

---

## Architecture Patterns

### Resolver changes

`compute_relationships` currently matches `session.session_name == obj.value`. After this task, terminal matching via `PresetKind.TERMINALS` objects may be retained as a fallback OR removed entirely in favor of tab_id matching.

**Recommended:** Remove `TERMINALS` object-based matching from the resolver. Tab ID stored on `Project` is the authoritative link. The resolver's `terminals_for(project)` method returns sessions whose `tab_id == project.iterm_tab_id`.

This is simpler and more robust than the current name-based string matching.

**Resolver signature change:**

```python
def compute_relationships(
    projects: list[Project],
    worktrees: list[WorktreeInfo],
    sessions: list[TerminalSession],   # now carries tab_id
    repos: list[Repo],
) -> RelationshipIndex:
    # Tab-ID based matching:
    for project in projects:
        if project.iterm_tab_id:
            matched = [s for s in sessions if s.tab_id == project.iterm_tab_id]
            if matched:
                index._term_for_project[project.name] = matched
                for s in matched:
                    index._project_for_terminal[s.session_name] = project
```

### Project creation flow changes

In `app.py` `action_new_project` → after project is created, call `_do_create_tab_for_project(project)` (best-effort background). If successful, update `project.iterm_tab_id` and persist.

The current `_auto_create_terminal_session(name)` in the add-object loop becomes obsolete and should be removed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Tab ID lookup | Custom tab enumeration | `app.get_tab_by_id(tab_id)` returns None for stale IDs |
| UUID format | Parsing/validating tab IDs | Treat as opaque strings — the API handles format |
| Tab activation | Custom AppleScript | `session.async_activate(select_tab=True)` already in `activate_session()` |

---

## Common Pitfalls

### Pitfall 1: Storing session_id instead of tab_id
**What goes wrong:** `create_session` currently returns `session.session_id`. If this is stored as `iterm_tab_id`, `app.get_tab_by_id()` will never find it (different type).
**How to avoid:** The new `create_tab()` function must explicitly use `tab.tab_id`, not `session.session_id`.

### Pitfall 2: Tab with splits — which session to name?
**What goes wrong:** A tab created via `async_create_tab()` has `tab.sessions[0]` — naming this session sets the tab's visible name. If the user splits the pane, the tab now has multiple sessions. The grouping logic must put ALL sessions in a tab under the same project header.
**How to avoid:** Group by `session.tab_id`, not by session name. All sessions with the same `tab_id` belong to the same group.

### Pitfall 3: Race — project creation + iTerm2 unavailable
**What goes wrong:** On project creation, auto-create tab call fails silently. `project.iterm_tab_id` remains None. First fetch of sessions won't auto-create (stale detection requires live data).
**How to avoid:** Auto-create on fetch: when `project.iterm_tab_id is None` AND sessions list is not None (iTerm2 IS available), trigger `_do_create_tab_for_project()`. This repairs the None case at next refresh.

### Pitfall 4: TerminalPane `set_sessions` still uses `_linked_names`
**What goes wrong:** If `set_linked_names` / `_linked_names` code paths are not removed, the link icon renders on top of the new tab-grouped display.
**How to avoid:** Remove `_linked_names`, `set_linked_names`, `is_linked` parameters, and `ICON_LINK` usage from `terminal_pane.py` as part of this task.

### Pitfall 5: Cursor restoration after pane rebuild
**What goes wrong:** Current cursor restoration uses `session_name` as identity key (FOUND-04). After grouping by tab, the cursor position logic must still work. Group headers are not in `_rows`.
**How to avoid:** Keep `_rows` as flat list of `SessionRow` (no headers). Cursor identity stays `session_name`. Group headers are non-row widgets (same pattern as today).

---

## TOML Schema Impact

### `models.py` — `Project` dataclass

Add one field:

```python
@dataclass
class Project:
    name: str
    objects: list[ObjectItem] = field(default_factory=list)
    created: date = field(default_factory=date.today)
    repo: str | None = None
    status: str = "idle"
    iterm_tab_id: str | None = None    # NEW: persisted tab ID for linked iTerm2 tab
```

### `Project.to_dict()`

```python
if self.iterm_tab_id is not None:
    d["iterm_tab_id"] = self.iterm_tab_id
```

### `_toml_to_projects()` in `store.py`

```python
iterm_tab_id = proj_data.get("iterm_tab_id")  # None if absent
projects.append(Project(..., iterm_tab_id=iterm_tab_id))
```

Backward-compatible: existing projects.toml files without this field will have `iterm_tab_id=None`, which triggers auto-create on first fetch when iTerm2 is available.

### `PresetKind.TERMINALS` objects — keep or remove?

**Decision for planner:** The `terminals` objects in the project's object list currently drive two things:
1. The "open terminal" action (`action_open_terminal` → `_open_first_of_kind(PresetKind.TERMINALS)`)
2. The relationship matching in the resolver

After this task, relationship matching moves to tab_id. But `PresetKind.TERMINALS` objects may still be useful for the open action (to activate the linked tab). However, if we store `iterm_tab_id` on `Project`, the open action can use that directly — making `TERMINALS` objects redundant.

**Recommendation:** Keep `TERMINALS` objects for backward compat but make the resolver ignore them (use tab_id exclusively). Planner should decide whether to remove the open-by-object path or migrate it to use `project.iterm_tab_id`. [ASSUMED: keeping TERMINALS objects during transition is safest]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | tab_id and session_id do not survive iTerm2 restart | Focus Area 4 | Low — behavior would be better (IDs persist), not worse |
| A2 | Storing iterm_tab_id in project TOML is better than separate state file | Focus Area 4 | Low — separate file would work too, just more complex |
| A3 | Keeping TERMINALS objects during transition is safest | TOML Schema Impact | Low — could remove them cleanly; keeping is just more conservative |

---

## Sources

### Primary (HIGH confidence)
- `src/joy/terminal_sessions.py` — complete source of all iTerm2 operations
- `src/joy/widgets/terminal_pane.py` — complete pane implementation
- `src/joy/models.py` — current TerminalSession and Project dataclasses
- `src/joy/resolver.py` — relationship computation
- `src/joy/app.py` — app-level iTerm2 integration points
- `src/joy/store.py` — TOML persistence layer
- `iterm2` Python package source (via `uv run python -c "import inspect; inspect.getsource(...)"`) — Tab.tab_id, Session.session_id, App.get_tab_by_id

### Secondary (MEDIUM confidence)
- `~/.joy/projects.toml` sample — confirmed TERMINALS object stores session name string

**Research date:** 2026-04-16
**Valid until:** 2026-05-16 (stable Python API, monthly iTerm2 releases unlikely to break these)
