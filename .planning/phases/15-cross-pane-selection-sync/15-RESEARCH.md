# Phase 15: Cross-Pane Selection Sync - Research

**Researched:** 2026-04-14
**Domain:** Textual TUI event messaging, reactive bindings, cursor mutation patterns
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Sync fires on every cursor movement (j/k, arrow keys) — same trigger as `ProjectList.ProjectHighlighted`. WorktreePane and TerminalPane need new cursor message classes (`WorktreePane.WorktreeHighlighted`, `TerminalPane.SessionHighlighted`).
- **D-02:** Each message carries enough identity for the app to call `RelationshipIndex` query methods.
- **D-03:** App-level boolean guard `_is_syncing: bool = False` — must be first implementation step. Handlers check flag at top and return immediately if True.
- **D-04:** Project highlighted → WorktreePane cursor to first related worktree; TerminalPane cursor to first related agent session. (SYNC-01, SYNC-02)
- **D-05:** Worktree highlighted → ProjectList cursor to owning project; TerminalPane cursor to first related agent session. (SYNC-03, SYNC-04)
- **D-06:** Agent session highlighted → ProjectList cursor to owning project; WorktreePane cursor to first related worktree. (SYNC-05, SYNC-06)
- **D-07:** "First related" = first item in pane's current `_rows` display order. No tie-breaking.
- **D-08:** When no related item exists, target pane cursor is left unchanged ("keeps current"). Not reset to 0.
- **D-09:** Sync operations update `_cursor` directly and call `_update_highlight()` — they do NOT call `.focus()`. (SYNC-07)
- **D-10:** Each pane exposes a `sync_to(identity)` method that moves cursor without posting a new message.
- **D-11:** Toggle key: `x` (unused in current BINDINGS).
- **D-12:** Default state: sync ON from first launch.
- **D-13:** Footer toggle label via BINDINGS. Binding description updates to reflect state (e.g., `x Sync: on` / `x Sync: off`). Use reactive `_sync_enabled` with `watch__sync_enabled` or `check_action` + `refresh_bindings()` to update footer dynamically.
- **D-14:** Toggle state is ephemeral — not persisted to disk.

### Claude's Discretion

- Exact method names for pane cursor mutations (`sync_to`, `set_cursor_by_identity`, etc.)
- Whether footer toggle label uses reactive binding description or CSS visibility trick
- Internal structure of new message classes
- Whether `_is_syncing` guard and `sync_to()` no-message-method are both used, or just one

### Deferred Ideas (OUT OF SCOPE)

- **SYNC-10:** Toggle state persists across restarts — deferred to v1.3+
- **PERF-01:** Real-time file watching — 30s refresh sufficient for v1.2
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SYNC-01 | Selecting a project updates WorktreePane cursor to first related worktree (keeps current if no match) | `RelationshipIndex.worktrees_for(project)` returns list; first element drives `WorktreePane.sync_to(wt)` |
| SYNC-02 | Selecting a project updates TerminalPane cursor to first related agent session (keeps current if no match) | `RelationshipIndex.agents_for(project)` returns list; first element drives `TerminalPane.sync_to(session_name)` |
| SYNC-03 | Selecting a worktree updates ProjectList cursor to its related project (keeps current if no match) | `RelationshipIndex.project_for_worktree(wt)` returns Project or None; drives `ProjectList.sync_to(project_name)` |
| SYNC-04 | Selecting a worktree updates TerminalPane cursor to first related agent session (keeps current if no match) | After resolving project via SYNC-03, call `agents_for(project)` and drive TerminalPane |
| SYNC-05 | Selecting an agent session updates ProjectList cursor to its related project (keeps current if no match) | `RelationshipIndex.project_for_agent(session_name)` returns Project or None |
| SYNC-06 | Selecting an agent session updates WorktreePane cursor to first related worktree (keeps current if no match) | After resolving project, call `worktrees_for(project)` and drive WorktreePane |
| SYNC-07 | Focus remains on the active pane during all sync operations | `sync_to()` method must not call `.focus()` — mutates `_cursor` and calls `_update_highlight()` only |
| SYNC-08 | User can toggle cross-pane sync on/off via keyboard shortcut | Binding `("x", "action_toggle_sync", ...)` in `JoyApp.BINDINGS` |
| SYNC-09 | Sync toggle state visible in footer key hints | `check_action` + `refresh_bindings()` pattern from Textual DOM; see Architecture Patterns |
</phase_requirements>

## Summary

Phase 15 wires cursor navigation across all three scrollable panes (ProjectList, WorktreePane, TerminalPane) using Textual's message-passing system. The existing `ProjectList.ProjectHighlighted` message/handler pattern serves as the template — WorktreePane and TerminalPane each need an equivalent message class and the app gains handlers for all three directions.

The core challenge is preventing sync loops: when pane A fires a message that causes pane B to move, pane B must not fire a new message that causes pane A to move again. Two complementary mechanisms address this: (1) an app-level `_is_syncing` boolean guard checked at the top of all cursor-message handlers, and (2) a `sync_to()` method on each pane that mutates cursor state directly without posting a new message.

The sync toggle (SYNC-08, SYNC-09) uses Textual 8.2.3's `check_action` + `refresh_bindings()` mechanism. The Footer widget subscribes to `screen.bindings_updated_signal`; calling `self.refresh_bindings()` causes the Footer to recompose and re-read the current BINDINGS. Two Binding objects with the same key `x` (one showing "Sync: on", one "Sync: off") are defined in BINDINGS, and `check_action` returns `False` for whichever is not current, hiding it from the footer.

**Primary recommendation:** Implement in order: (1) `_is_syncing` guard, (2) new message classes + `sync_to()` methods on all three panes, (3) all six cross-pane handlers in `app.py`, (4) toggle binding with `check_action` + `refresh_bindings()`.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| textual | 8.2.3 (installed) | TUI framework | Project requirement; all widgets already use it |
| textual.message.Message | built-in | Inner message classes | Pattern already established by ProjectList.ProjectHighlighted |
| textual.reactive.reactive | built-in | `_sync_enabled` reactive | Enables `watch_` callbacks for clean state management |

No new dependencies. This phase is pure logic wiring within the existing codebase.

**Installation:** none required — all dependencies already in place.

## Architecture Patterns

### Established Cursor Pattern (verified in codebase)

All three scrollable panes share an identical cursor implementation:

```python
# [VERIFIED: src/joy/widgets/project_list.py, worktree_pane.py, terminal_pane.py]
self._cursor: int = -1          # current row index, -1 = none
self._rows: list[RowType] = []  # ordered display rows

def _update_highlight(self) -> None:
    for row in self._rows:
        row.remove_class("--highlight")
    if 0 <= self._cursor < len(self._rows):
        self._rows[self._cursor].add_class("--highlight")
        self._rows[self._cursor].scroll_visible()
        # ProjectList also calls self.post_message(self.ProjectHighlighted(...)) here
```

### Pattern 1: New Cursor Message Classes

Add inner Message classes to WorktreePane and TerminalPane, matching the ProjectList pattern:

```python
# [VERIFIED: pattern from src/joy/widgets/project_list.py lines 127-139]
# WorktreePane (src/joy/widgets/worktree_pane.py):
class WorktreeHighlighted(Message):
    """Fired when highlight moves to a different worktree row."""
    def __init__(self, worktree: WorktreeInfo) -> None:
        self.worktree = worktree
        super().__init__()

# TerminalPane (src/joy/widgets/terminal_pane.py):
class SessionHighlighted(Message):
    """Fired when highlight moves to a different session row."""
    def __init__(self, session_name: str) -> None:
        self.session_name = session_name
        super().__init__()
```

The `WorktreeHighlighted` message carries a `WorktreeInfo` object — enough for `RelationshipIndex.project_for_worktree(wt)`. The `SessionHighlighted` message carries `session_name` (string) — enough for `RelationshipIndex.project_for_agent(session_name)`.

### Pattern 2: `_update_highlight()` Now Posts Messages

WorktreePane and TerminalPane's `_update_highlight()` currently only apply CSS and scroll. Phase 15 adds `post_message()` calls, matching ProjectList:

```python
# [VERIFIED: pattern from project_list.py line 220]
def _update_highlight(self) -> None:
    for row in self._rows:
        row.remove_class("--highlight")
    if 0 <= self._cursor < len(self._rows):
        self._rows[self._cursor].add_class("--highlight")
        self._rows[self._cursor].scroll_visible()
        self.post_message(self.WorktreeHighlighted(self._rows[self._cursor].worktree_info))
        # ^ WorktreeRow needs to store the WorktreeInfo (it already stores repo_name, branch, path)
```

Note: `WorktreeRow` stores `repo_name`, `branch`, and `path` as separate attributes but not the full `WorktreeInfo` object. The `sync_to` lookup uses `(repo_name, branch)` identity, so the message can be constructed from those fields. Alternatively, store the full `WorktreeInfo` on the row.

### Pattern 3: `sync_to()` — No-Message Cursor Mutation

Each pane gets a `sync_to()` method that moves the cursor without triggering a new message:

```python
# WorktreePane.sync_to(repo_name, branch) — moves cursor to matching row, no message posted
def sync_to(self, repo_name: str, branch: str) -> None:
    """Move cursor to matching row. Silent — does NOT post WorktreeHighlighted. (D-10)"""
    for i, row in enumerate(self._rows):
        if row.repo_name == repo_name and row.branch == branch:
            self._cursor = i
            self._update_highlight_silent()  # highlight only, no post_message
            return
    # No match — leave cursor unchanged (D-08)

# TerminalPane.sync_to(session_name)
def sync_to(self, session_name: str) -> None:
    for i, row in enumerate(self._rows):
        if row.session_name == session_name:
            self._cursor = i
            self._update_highlight_silent()
            return

# ProjectList.sync_to(project_name)
def sync_to(self, project_name: str) -> None:
    for i, row in enumerate(self._rows):
        if row.project.name == project_name:
            self._cursor = i
            self._update_highlight_silent()
            return
```

**Implementation choice:** Either add a separate `_update_highlight_silent()` that omits `post_message`, or pass a `post_message=True/False` flag. A separate method is cleaner. Alternatively, the guard in `_update_highlight()` can skip posting when `self.app._is_syncing` is True — this is simpler and requires no structural change.

### Pattern 4: `_is_syncing` Guard in app.py

```python
# [VERIFIED: D-03 in CONTEXT.md, confirmed as first implementation step in STATE.md]
class JoyApp(App):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # ... existing fields ...
        self._is_syncing: bool = False
        self._sync_enabled: bool = True  # or reactive[bool]

    def on_project_list_project_highlighted(
        self, message: ProjectList.ProjectHighlighted
    ) -> None:
        """Existing handler — extend to drive WorktreePane and TerminalPane. (SYNC-01, SYNC-02)"""
        if self._is_syncing:
            return
        # existing: update detail pane
        self.query_one(ProjectDetail).set_project(message.project)
        # new: drive cross-pane sync
        if self._sync_enabled and self._rel_index is not None:
            self._sync_from_project(message.project)

    def _sync_from_project(self, project: Project) -> None:
        self._is_syncing = True
        try:
            worktrees = self._rel_index.worktrees_for(project)
            if worktrees:
                wt = worktrees[0]
                self.query_one(WorktreePane).sync_to(wt.repo_name, wt.branch)
            agents = self._rel_index.agents_for(project)
            if agents:
                self.query_one(TerminalPane).sync_to(agents[0].session_name)
        finally:
            self._is_syncing = False

    def on_worktree_pane_worktree_highlighted(
        self, message: WorktreePane.WorktreeHighlighted
    ) -> None:
        if self._is_syncing:
            return
        if self._sync_enabled and self._rel_index is not None:
            self._sync_from_worktree(message.worktree)

    def on_terminal_pane_session_highlighted(
        self, message: TerminalPane.SessionHighlighted
    ) -> None:
        if self._is_syncing:
            return
        if self._sync_enabled and self._rel_index is not None:
            self._sync_from_session(message.session_name)
```

**Textual message handler naming convention:** `on_{widget_class_lower}_{message_class_lower}`. For `WorktreePane.WorktreeHighlighted`, the handler name is `on_worktree_pane_worktree_highlighted`. [VERIFIED: pattern confirmed from existing `on_project_list_project_highlighted` in app.py line 318]

### Pattern 5: Footer Toggle via `check_action` + `refresh_bindings()`

This is the recommended approach (Claude's discretion per D-13).

**How it works** [VERIFIED: textual/screen.py lines 459-496, textual/dom.py lines 1880-1904, textual/widgets/_footer.py lines 351-354]:

1. `Footer.on_mount()` subscribes to `screen.bindings_updated_signal`
2. `self.refresh_bindings()` publishes that signal, causing Footer to `recompose`
3. During recompose, Footer calls `screen.active_bindings` which calls `app.check_action()` for each binding
4. `check_action()` returning `False` removes a binding from the footer entirely (not just greyed out)

```python
# In JoyApp.BINDINGS — two entries for key 'x':
BINDINGS = [
    # ... existing bindings ...
    Binding("x", "toggle_sync", "Sync: on", id="sync-on"),
    Binding("x", "toggle_sync_off", "Sync: off", id="sync-off"),
]

def check_action(self, action: str, parameters: tuple) -> bool | None:
    if action == "toggle_sync":
        return self._sync_enabled     # show "Sync: on" when enabled
    if action == "toggle_sync_off":
        return not self._sync_enabled  # show "Sync: off" when disabled
    return super().check_action(action, parameters)

def action_toggle_sync(self) -> None:
    self._sync_enabled = not self._sync_enabled
    self.refresh_bindings()  # triggers footer recompose

def action_toggle_sync_off(self) -> None:
    self._sync_enabled = not self._sync_enabled
    self.refresh_bindings()
```

**Alternative:** Single binding with `reactive[bool]` and `watch__sync_enabled` calling `refresh_bindings()`. The two-binding approach is slightly cleaner as the footer label text changes without the reactive overhead, but either works. [ASSUMED: watch_ watcher pattern is compatible with `refresh_bindings` in Textual 8.x — needs verification against BINDINGS being a class-level list].

**Simpler alternative** (lowest risk): A single binding entry whose description string is updated by mutating the Binding object in BINDINGS and calling `refresh_bindings()`. However, BINDINGS is a class variable — mutating it changes it for all instances and is not idiomatic. The `check_action` approach is the correct Textual-native pattern.

### Pattern 6: WorktreeRow Identity for `sync_to`

`WorktreeRow` currently stores `repo_name`, `branch`, and `path` as separate attributes (verified: lines 133-137 of worktree_pane.py). The `sync_to(repo_name, branch)` signature matches the existing identity tuple `(row.repo_name, row.branch)` used by FOUND-03 cursor preservation. No changes needed to `WorktreeRow`.

### Recommended Project Structure (new files: none, modified files: 4)

```
src/joy/
├── app.py                  # add: _is_syncing, _sync_enabled, 2 new handlers,
│                           #      _sync_from_project/worktree/session helpers,
│                           #      toggle binding + check_action + action_toggle_sync
├── widgets/
│   ├── project_list.py     # add: sync_to(project_name) method
│   ├── worktree_pane.py    # add: WorktreeHighlighted message, post in _update_highlight,
│   │                       #      sync_to(repo_name, branch) method
│   └── terminal_pane.py    # add: SessionHighlighted message, post in _update_highlight,
│                           #      sync_to(session_name) method
```

### Anti-Patterns to Avoid

- **Calling `.focus()` in sync_to():** Focus must remain on the pane the user is actively navigating (SYNC-07, D-09). `sync_to()` only mutates `_cursor` and calls the highlight method.
- **Using `select_index()` in sync_to():** `ProjectList.select_index()` calls `_update_highlight()` which posts a `ProjectHighlighted` message — this would create a sync loop even with the guard. Use a separate path that does not post a message.
- **Checking `_is_syncing` only in the handler:** The guard must be checked before the `_sync_enabled` check to prevent infinite re-entry even when sync is toggled off during an in-flight sync operation.
- **Mutating BINDINGS class variable:** BINDINGS is shared across all instances. Use `check_action` instead.
- **Skipping `finally:` around `_is_syncing = False`:** Any exception during sync would leave `_is_syncing` permanently True, disabling all sync. Use try/finally.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Footer toggle label updates | Custom CSS/visibility toggling of footer elements | `check_action` + `refresh_bindings()` | Textual's official mechanism; Footer auto-subscribes to signal |
| Message handler loop prevention | Complex state machine or event queue | Simple `_is_syncing: bool` guard | Textual message handlers run sequentially on the main thread — no concurrency race |
| Pane cursor lookup | Linear scan with custom caching | Direct `_rows` list iteration with early return | `_rows` is already the display-order list; O(n) is fine for <100 rows |

**Key insight:** The sync loop problem is simpler than it appears because Textual processes messages synchronously on the main thread. There is no concurrency; the guard is just preventing re-entrant calls in the same call chain.

## Common Pitfalls

### Pitfall 1: `_update_highlight()` Posts Message from `sync_to()` Path
**What goes wrong:** If `sync_to()` sets `_cursor` and calls `_update_highlight()`, and `_update_highlight()` always posts a message, then calling `sync_to()` from an app handler fires a new highlighted message — exactly the loop we want to prevent. The `_is_syncing` guard stops the *app handler* from re-entering, but the message still gets posted and sits in the queue.
**Why it happens:** `_update_highlight()` is the single method for both user-driven cursor moves and sync-driven moves.
**How to avoid:** Either (a) add a `_silent_highlight()` variant that skips `post_message`, or (b) check `self.app._is_syncing` inside `_update_highlight()` before posting. Option (b) is simpler — one guard location covers both.
**Warning signs:** In manual testing, moving the cursor in any pane causes rapid flickering or cursor bouncing.

### Pitfall 2: `sync_to()` Called When `_rel_index` is None
**What goes wrong:** On first launch, `_rel_index` is None until both `_load_worktrees` and `_load_terminal` complete. If a cursor move fires before that, the handler checks `self._rel_index is not None` and skips sync — correct. But if a developer removes that guard, a `None.worktrees_for()` call raises `AttributeError`.
**How to avoid:** Always guard with `if self._sync_enabled and self._rel_index is not None:` before calling any RelationshipIndex method.

### Pitfall 3: WorktreeRow Stores `WorktreeInfo` Fields, Not the Object
**What goes wrong:** `WorktreeHighlighted` needs to carry enough identity for `RelationshipIndex.project_for_worktree(wt)`. That method takes a `WorktreeInfo` object and looks up `wt.path` and `(wt.repo_name, wt.branch)`. `WorktreeRow` stores these three fields separately — a `WorktreeInfo` can be reconstructed, or the message can carry `(repo_name, branch, path)` directly.
**How to avoid:** Either store the full `WorktreeInfo` on `WorktreeRow` (requires small change to `WorktreeRow.__init__`) OR reconstruct it in `_update_highlight()` using `WorktreeInfo(repo_name=row.repo_name, branch=row.branch, path=row.path)`. The reconstruction approach avoids changing `WorktreeRow`.
**Warning signs:** `AttributeError: 'WorktreeRow' object has no attribute 'worktree'` at runtime.

### Pitfall 4: `check_action` Not Called for App-Level Bindings When a Widget Has Focus
**What goes wrong:** Textual's `active_bindings` walks the modal binding chain (focused widget → parent → ... → screen → app). `check_action` is called on the namespace that owns the binding. App-level bindings call `app.check_action()` — this works regardless of which widget has focus.
**How to avoid:** Keep the toggle binding in `JoyApp.BINDINGS` (not on a widget). Override `check_action` on `JoyApp`. [VERIFIED: textual/screen.py line 474-475]

### Pitfall 5: Cursor "Keeps Current" Means Literally Unchanged
**What goes wrong:** Misreading "keeps current if no match" as "reset to 0" or "move to nearest". D-08 is explicit: no match → target pane cursor does not move at all.
**How to avoid:** In `sync_to()`, the early return with no cursor mutation is the correct no-match path. Do not set `_cursor = 0` as a fallback.

## Code Examples

### Minimal `sync_to()` + silent highlight pattern

```python
# [VERIFIED: structure from src/joy/widgets/worktree_pane.py — cursor/rows pattern]
# WorktreePane addition:
def sync_to(self, repo_name: str, branch: str) -> None:
    """Move cursor to (repo_name, branch) row. Silent — no WorktreeHighlighted posted. (D-10)"""
    for i, row in enumerate(self._rows):
        if row.repo_name == repo_name and row.branch == branch:
            self._cursor = i
            # Highlight-only path: CSS + scroll, no post_message
            for r in self._rows:
                r.remove_class("--highlight")
            row.add_class("--highlight")
            row.scroll_visible()
            return
    # No match: leave _cursor unchanged (D-08)
```

### `_is_syncing` guard in `_update_highlight()` (avoids separate method)

```python
# [VERIFIED: extension of pattern in src/joy/widgets/worktree_pane.py lines 402-407]
def _update_highlight(self) -> None:
    for row in self._rows:
        row.remove_class("--highlight")
    if 0 <= self._cursor < len(self._rows):
        self._rows[self._cursor].add_class("--highlight")
        self._rows[self._cursor].scroll_visible()
        # Only post message when not in a sync operation
        if not getattr(self.app, "_is_syncing", False):
            self.post_message(self.WorktreeHighlighted(
                self._rows[self._cursor].worktree_info  # or reconstructed WorktreeInfo
            ))
```

### Textual message handler naming

```python
# [VERIFIED: existing pattern in src/joy/app.py line 318]
# Class: WorktreePane, Message: WorktreeHighlighted
# Handler name: on_worktree_pane_worktree_highlighted

def on_worktree_pane_worktree_highlighted(
    self, message: WorktreePane.WorktreeHighlighted
) -> None:
    if self._is_syncing:
        return
    if self._sync_enabled and self._rel_index is not None:
        self._sync_from_worktree(message.worktree)
```

### check_action pattern for footer toggle

```python
# [VERIFIED: textual/dom.py lines 1880-1903 — check_action returns bool | None]
# [VERIFIED: textual/screen.py lines 474-482 — False hides binding from footer]

BINDINGS = [
    ("q", "quit", "Quit"),
    # ... existing bindings ...
    Binding("x", "toggle_sync", "Sync: on"),   # shown when sync is ON
    Binding("x", "disable_sync", "Sync: off"),  # shown when sync is OFF
]

def check_action(self, action: str, parameters: tuple) -> bool | None:
    if action == "toggle_sync":
        return self._sync_enabled        # True = show; False = hide
    if action == "disable_sync":
        return not self._sync_enabled    # True = show; False = hide
    return super().check_action(action, parameters)

def action_toggle_sync(self) -> None:
    """Disable sync (called when sync is currently ON)."""
    self._sync_enabled = False
    self.refresh_bindings()

def action_disable_sync(self) -> None:
    """Enable sync (called when sync is currently OFF)."""
    self._sync_enabled = True
    self.refresh_bindings()
```

Note: Both action names map to key `x`. Textual's binding lookup finds the first active binding for a key — with `check_action` hiding one at a time, exactly one will be active and shown in the footer.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Textual `watch_` reactive for footer label updates | `check_action` + `refresh_bindings()` for conditional binding visibility | Textual ~0.50+ | `check_action` is the idiomatic way to show/hide/disable bindings dynamically |
| Textual `ListView` built-in | Custom cursor/_rows pattern (already used in codebase) | Phase 9 (joy-specific) | All panes share identical cursor pattern; Phase 15 extends it uniformly |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Two Binding entries for the same key `x` with `check_action` controlling visibility is the correct Textual-native pattern for dynamic footer labels | Architecture Patterns §5 | If wrong: footer may show both entries simultaneously or neither — verify with a small prototype before committing to this approach |
| A2 | `getattr(self.app, "_is_syncing", False)` in `_update_highlight()` is safe when called before `JoyApp.__init__` sets the attribute | Architecture Patterns §2, Code Examples | If wrong: AttributeError at startup — use `getattr` with default `False` as shown, or initialize `_is_syncing = False` in widget `__init__` (app always has `_is_syncing` after init) |

## Open Questions

1. **WorktreeRow: store full WorktreeInfo or reconstruct?**
   - What we know: `WorktreeRow` stores `repo_name`, `branch`, `path` individually. `WorktreeInfo` has these plus `is_dirty`, `has_upstream`, `is_default_branch`.
   - What's unclear: Whether the planner should store the full `WorktreeInfo` on the row (requires `WorktreeRow.__init__` change) or reconstruct a minimal `WorktreeInfo(repo_name, branch, path)` at message creation time.
   - Recommendation: Reconstruct — `WorktreeInfo` is a dataclass, reconstruction is trivial, and it avoids adding state to `WorktreeRow`. `project_for_worktree()` only needs path and (repo_name, branch).

2. **`check_action` with two bindings for same key: is only one shown at a time?**
   - What we know: `check_action` returning `False` removes binding from `active_bindings` dict. `active_bindings` is key-keyed, so later entries overwrite earlier ones for the same key.
   - What's unclear: If both bindings are evaluated and the second (with `False`) overwrites the first (with `True`), the footer would show nothing.
   - Recommendation: Use `id` parameter on Binding objects and verify in implementation that only one shows. If this has issues, fallback: single binding with description text managed differently (e.g., `Footer` subclass or subtitle area).

## Environment Availability

Step 2.6: SKIPPED — Phase 15 is purely code/logic changes within the existing Textual app. No new external tools, services, CLIs, databases, or package managers are required. All dependencies (textual 8.2.3, uv, pytest) are already installed and verified.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_sync.py -x -q` |
| Full suite command | `uv run pytest -m "not slow and not macos_integration" -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SYNC-01 | Project highlighted → WorktreePane cursor moves to first related worktree | unit (pure) | `uv run pytest tests/test_sync.py::test_sync_project_to_worktree -x` | ❌ Wave 0 |
| SYNC-02 | Project highlighted → TerminalPane cursor moves to first related agent | unit (pure) | `uv run pytest tests/test_sync.py::test_sync_project_to_terminal -x` | ❌ Wave 0 |
| SYNC-03 | Worktree highlighted → ProjectList cursor moves to owning project | unit (pure) | `uv run pytest tests/test_sync.py::test_sync_worktree_to_project -x` | ❌ Wave 0 |
| SYNC-04 | Worktree highlighted → TerminalPane cursor moves to first related agent | unit (pure) | `uv run pytest tests/test_sync.py::test_sync_worktree_to_terminal -x` | ❌ Wave 0 |
| SYNC-05 | Agent highlighted → ProjectList cursor moves to owning project | unit (pure) | `uv run pytest tests/test_sync.py::test_sync_agent_to_project -x` | ❌ Wave 0 |
| SYNC-06 | Agent highlighted → WorktreePane cursor moves to first related worktree | unit (pure) | `uv run pytest tests/test_sync.py::test_sync_agent_to_worktree -x` | ❌ Wave 0 |
| SYNC-07 | Focus stays on active pane during sync | unit (pure state check) | `uv run pytest tests/test_sync.py::test_sync_does_not_steal_focus -x` | ❌ Wave 0 |
| SYNC-08 | Toggle sync on/off via `x` | TUI pilot | `uv run pytest tests/test_sync.py::test_toggle_sync_key -x -m slow` | ❌ Wave 0 |
| SYNC-09 | Toggle state visible in footer | unit (check_action) | `uv run pytest tests/test_sync.py::test_toggle_sync_footer_visibility -x` | ❌ Wave 0 |

**Test strategy:** SYNC-01 through SYNC-07 are pure Python unit tests — they construct `RelationshipIndex`, call `sync_to()` directly, and assert `_cursor` values. No TUI pilot needed. SYNC-08 is a `@pytest.mark.slow` TUI pilot test. SYNC-09 can be tested by verifying `check_action` return values directly — no pilot needed.

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_sync.py -x -q`
- **Per wave merge:** `uv run pytest -m "not slow and not macos_integration" -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_sync.py` — covers SYNC-01 through SYNC-09 (all new)

*(No existing test files cover Phase 15 requirements — single new test file needed)*

## Sources

### Primary (HIGH confidence)
- `src/joy/widgets/project_list.py` lines 127-139, 213-220 — ProjectHighlighted message class and _update_highlight() posting pattern [VERIFIED: read in this session]
- `src/joy/widgets/worktree_pane.py` lines 276-283, 402-407 — cursor pattern and _update_highlight() [VERIFIED: read in this session]
- `src/joy/widgets/terminal_pane.py` lines 197-204, 300-307 — SessionRow with session_name identity field [VERIFIED: read in this session]
- `src/joy/app.py` lines 318-322 — on_project_list_project_highlighted handler, message naming convention [VERIFIED: read in this session]
- `src/joy/resolver.py` lines 31-49 — RelationshipIndex query methods [VERIFIED: read in this session]
- `.venv/lib/python3.14/site-packages/textual/dom.py` lines 1880-1903 — `check_action` and `refresh_bindings()` API [VERIFIED: read in this session]
- `.venv/lib/python3.14/site-packages/textual/screen.py` lines 459-496, 393-395 — `active_bindings` calls `check_action`; `refresh_bindings()` publishes signal [VERIFIED: read in this session]
- `.venv/lib/python3.14/site-packages/textual/widgets/_footer.py` lines 351-354 — Footer subscribes to `bindings_updated_signal` via `on_mount` [VERIFIED: read in this session]
- `.venv/lib/python3.14/site-packages/textual/binding.py` lines 55-90 — `Binding` dataclass fields [VERIFIED: read in this session]

### Secondary (MEDIUM confidence)
- Textual 8.2.3 installed version confirmed via `.venv/lib/python3.14/site-packages/textual-8.2.3.dist-info/METADATA`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all patterns verified in installed codebase
- Architecture: HIGH — all patterns verified in existing source files and Textual internals
- Pitfalls: HIGH — derived from direct code inspection of cursor pattern and Textual binding machinery
- Toggle/check_action pattern: MEDIUM — mechanism verified in Textual source, but two-binding-same-key behavior is ASSUMED to work as described (Open Question 2)

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (textual 8.x is stable; internal APIs unlikely to change in 30 days)
