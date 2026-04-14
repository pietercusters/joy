# Technology Stack: Cross-Pane Sync & Live Data Propagation

**Project:** joy v1.2 -- Cross-Pane Intelligence
**Researched:** 2026-04-14
**Overall confidence:** HIGH

---

## No New Dependencies Required

The entire v1.2 feature set (cross-pane selection sync + live data propagation) is achievable using Textual 8.2.x APIs already installed. **Zero new packages.**

| What's Needed | Provided By | Already in joy? |
|---------------|-------------|-----------------|
| Cross-widget message routing | `textual.message.Message` + bubbling | YES (ProjectHighlighted/ProjectSelected) |
| App-level message handlers | `on_<widget>_<message>()` naming convention | YES (on_project_list_project_highlighted) |
| Background thread -> UI updates | `call_from_thread()` + `@work(thread=True)` | YES (_load_worktrees, _load_terminal) |
| State coordination across panes | Custom Messages bubbling to App | Extend existing pattern |
| Keyboard toggle for sync | `BINDINGS` + action methods | Extend existing pattern |

---

## Recommended Stack for v1.2 Features

### Pattern 1: Custom Messages Bubbling to App (PRIMARY)

**Use for:** Cross-pane selection sync (cursor move in one pane triggers cursor moves in others).

**How it works:** Each pane already posts `Message` subclasses that bubble up through the DOM. The `App` class catches them via `on_<widget>_<message>()` handlers. The App then queries other panes and calls methods on them directly.

**This is the established joy pattern.** ProjectList already does this:

```python
# In ProjectList (child widget):
class ProjectHighlighted(Message):
    def __init__(self, project: Project) -> None:
        self.project = project
        super().__init__()

def _update_highlight(self):
    self.post_message(self.ProjectHighlighted(self._rows[self._cursor].project))

# In JoyApp (parent):
def on_project_list_project_highlighted(self, message):
    self.query_one(ProjectDetail).set_project(message.project)
```

**Extend for v1.2:** Add similar messages to WorktreePane and TerminalPane:

```python
# WorktreePane:
class WorktreeHighlighted(Message):
    def __init__(self, repo_name: str, branch: str) -> None: ...

# TerminalPane:
class SessionHighlighted(Message):
    def __init__(self, session_name: str, cwd: str) -> None: ...
```

App handles these and dispatches to other panes via `query_one()`.

**Why this pattern over alternatives:**

| Pattern | Verdict | Reason |
|---------|---------|--------|
| Messages bubble to App | **USE THIS** | Already established in joy. App is the natural coordinator. Minimal new code. |
| Signal (pub/sub) | Do NOT use | Textual's `Signal` class is designed for App-level system events (theme changes, suspend/resume). Using it for widget-to-widget coordination is fighting the framework. Signals also require widgets to be mounted before subscribing, which complicates the lifecycle. |
| data_bind | Do NOT use | One-directional parent-to-child only. Cannot bind between siblings. Would require restructuring all panes as children of a coordinator widget, which is over-engineering. |
| Reactive attributes on App | Do NOT use | Tempting, but reactive watchers on App would trigger before panes are mounted during startup. Also mixes state management (what's selected) with UI state (what's highlighted) in a way that's hard to test. |
| Direct sibling.post_message() | Do NOT use | Textual's official guidance (Will McGugan, discussion #186) explicitly recommends against this. Breaks encapsulation. Hard to add/remove panes later. |

**Confidence:** HIGH -- This is the textbook Textual pattern and is already proven in joy's codebase.

### Pattern 2: Relationship Resolver (Pure Python, No Framework)

**Use for:** Computing Project <-> Worktree <-> Agent matches at runtime.

**No Textual API needed.** This is a pure data function:

```python
def resolve_relationships(
    project: Project,
    worktrees: list[WorktreeInfo],
    sessions: list[TerminalSession],
) -> RelationshipMap:
    """Match project to its worktrees and agent sessions."""
```

The resolver is called by the App when:
1. A cursor highlight message arrives (sync: find related items across panes)
2. A refresh completes (propagation: compute what changed)

**Why pure function, not framework feature:**
- Testable without TUI
- No dependency on widget lifecycle
- Can run in background thread if needed
- Joy's data model is small (dozens of projects, <100 worktrees, <20 sessions); computation is O(n) and sub-millisecond

**Confidence:** HIGH -- Standard application architecture.

### Pattern 3: App-Level State + Method Dispatch (For Sync Toggle)

**Use for:** The sync on/off toggle (`Ctrl+S` or similar keybinding).

```python
class JoyApp(App):
    _sync_enabled: bool = True  # Plain attribute, not reactive

    def action_toggle_sync(self) -> None:
        self._sync_enabled = not self._sync_enabled
        self.notify(f"Sync {'on' if self._sync_enabled else 'off'}")
```

**Why plain attribute, not reactive:**
- Reactive would trigger a refresh of the App itself (unnecessary -- App has no render)
- The toggle only affects behavior of message handlers, not display
- `var()` (non-refreshing reactive) would also work, but a plain bool is simpler and more explicit

**Confidence:** HIGH

### Pattern 4: Worker Thread -> call_from_thread (For Live Data Propagation)

**Use for:** After background refresh completes, automatically updating TOML data (add/remove worktree objects, mark agents stale).

**Already established in joy.** The `_load_worktrees` worker uses `call_from_thread` to push results to the UI. v1.2 extends this by adding a propagation step between data arrival and UI update:

```python
@work(thread=True)
def _load_worktrees(self) -> None:
    worktrees = discover_worktrees(repos, branch_filter)
    # NEW: compute changes and propagate to TOML
    changes = compute_data_changes(self._projects, worktrees, ...)
    self.app.call_from_thread(self._apply_propagation, changes)
    self.app.call_from_thread(self._set_worktrees, worktrees, ...)
```

**Key constraint:** TOML writing (`save_projects`) must happen in the background thread (already does via `_save_projects_bg`). The propagation logic should compute changes in the worker, then apply UI updates + trigger save on the main thread.

**Confidence:** HIGH -- Direct extension of existing pattern.

---

## Textual API Reference for v1.2

### APIs to USE

| API | Import | Purpose in v1.2 |
|-----|--------|-----------------|
| `Message` | `textual.message.Message` | Custom highlight/selection messages for each pane |
| `post_message()` | method on Widget | Emit highlight events from panes |
| `query_one()` | method on App/Widget | App locates panes to dispatch sync updates |
| `@work(thread=True)` | `textual.work` | Background data propagation computation |
| `call_from_thread()` | method on App | Push propagation results to main thread |
| `call_after_refresh()` | method on Widget | Ensure DOM is stable before cursor manipulation |
| `Binding` | `textual.binding.Binding` | Sync toggle keybinding |
| `@on()` decorator | `textual.on` | Optional: route messages from specific widget IDs |

### APIs to AVOID

| API | Why Not |
|-----|---------|
| `Signal` | For system-level pub/sub (theme, suspend). Not designed for widget coordination. Subscription requires mounted widgets, complicating startup order. |
| `data_bind()` | Parent-to-child only. Cannot bind between sibling panes. |
| `reactive()` on App | Triggers refresh on App (pointless). Use plain attributes for App-level state like sync toggle. |
| `mutate_reactive()` | Only needed if storing mutable collections in reactive attributes. Joy doesn't use reactive for its data model. |
| `recompose=True` | Destroys and rebuilds child widgets on every change. Expensive and unnecessary -- joy already uses the efficient `remove_children() + mount()` pattern. |

---

## Integration Points with Existing Code

### Current Message Flow (v1.1)

```
ProjectList.cursor_move
  -> post_message(ProjectHighlighted)
    -> bubbles to JoyApp
      -> on_project_list_project_highlighted()
        -> query_one(ProjectDetail).set_project()
```

### Extended Message Flow (v1.2)

```
ProjectList.cursor_move
  -> post_message(ProjectHighlighted)
    -> bubbles to JoyApp
      -> on_project_list_project_highlighted()
        -> IF sync_enabled:
             resolve_relationships(project, worktrees, sessions)
             query_one(WorktreePane).highlight_by_match(repo, branch)
             query_one(TerminalPane).highlight_by_match(cwd, session_name)
        -> query_one(ProjectDetail).set_project()

WorktreePane.cursor_move
  -> post_message(WorktreeHighlighted)
    -> bubbles to JoyApp
      -> on_worktree_pane_worktree_highlighted()
        -> IF sync_enabled:
             resolve_relationships(worktree, projects, sessions)
             query_one(ProjectList).highlight_by_match(project_name)
             query_one(TerminalPane).highlight_by_match(cwd)

TerminalPane.cursor_move
  -> post_message(SessionHighlighted)
    -> bubbles to JoyApp
      -> on_terminal_pane_session_highlighted()
        -> IF sync_enabled:
             resolve_relationships(session, projects, worktrees)
             query_one(ProjectList).highlight_by_match(project_name)
             query_one(WorktreePane).highlight_by_match(repo, branch)
```

### New Methods Needed on Each Pane

Each pane needs a `highlight_by_match()` or `select_by_*()` method that:
1. Searches `_rows` for a matching item
2. Updates `_cursor` to that index
3. Calls `_update_highlight()` **without** re-posting a highlight message (to prevent infinite loops)

**Infinite loop prevention:** The `highlight_by_match()` method must NOT call `post_message()`. Only user-initiated cursor movements (j/k/up/down) post highlight messages. Programmatic cursor moves during sync are silent.

This is the critical design decision for v1.2 sync. Two approaches:

| Approach | How | Tradeoff |
|----------|-----|----------|
| Separate method (recommended) | `highlight_by_match()` updates cursor + highlight CSS but skips `post_message` | Clean, explicit, no risk of loops |
| Guard flag | Set `self._syncing = True` before updating, check in `_update_highlight()` | Fragile, easy to forget, stateful |

**Use the separate method approach.**

---

## Live Data Propagation: No New Stack

The propagation logic (auto-add/remove worktree objects, mark agents stale) is pure Python:

1. **Input:** Current `_projects` list + fresh `worktrees` list + fresh `sessions` list
2. **Compute:** Diff what exists in project objects vs. what was discovered
3. **Output:** List of mutations (add object, remove object, mark stale)
4. **Apply:** Mutate `_projects` in place, trigger `_save_projects_bg()`, refresh affected panes

No Textual API is needed for the computation. The only framework touch point is calling `_save_projects_bg()` (already exists) and refreshing panes (already exists via `set_project()` / `set_worktrees()`).

---

## Alternatives Considered

| Approach | Recommended? | Why / Why Not |
|----------|-------------|---------------|
| Messages bubble to App, App dispatches | YES | Proven pattern in joy. App is natural coordinator. Testable. |
| Centralized state store (Redux-like) | NO | Massive over-engineering for 4 panes with simple relationships. Would require inventing a state management layer that Textual doesn't provide. |
| Reactive attributes for sync state | NO | `reactive` triggers widget refresh, which is not what sync needs (sync needs cursor manipulation, not re-render). |
| Signal pub/sub between panes | NO | Textual Signals are for system events. Subscription requires mounted widgets. More ceremony than message bubbling for the same result. |
| EventEmitter / observer pattern (custom) | NO | Reinventing what Textual's message system already provides. |
| Direct pane-to-pane method calls | NO | Tight coupling. Textual's Will McGugan explicitly recommends against this. |

---

## Confidence Assessment

| Decision | Confidence | Reasoning |
|----------|------------|-----------|
| Messages bubble to App for sync | HIGH | Official Textual pattern. Already used in joy for ProjectHighlighted. Verified via Textual docs and maintainer guidance (Discussion #186). |
| Pure function relationship resolver | HIGH | Standard architecture. No framework dependency. Trivially testable. |
| No new dependencies | HIGH | Textual 8.2.3 provides everything needed. Verified against API docs for Message, Signal, reactive, data_bind, @work, call_from_thread. |
| Silent highlight_by_match (no post_message) | HIGH | Only sound approach to prevent infinite message loops during sync. Common pattern in coordinated UI systems. |
| Plain bool for sync toggle (not reactive) | HIGH | App has no render method. Reactive would be pointless overhead. |
| Worker thread for propagation computation | HIGH | Already established pattern. Keeps UI responsive during diff computation. |

---

## Sources

- Textual Reactivity Guide: https://textual.textualize.io/guide/reactivity/
- Textual Events and Messages Guide: https://textual.textualize.io/guide/events/
- Textual Signal API: https://textual.textualize.io/api/signal/
- Textual Message API: https://textual.textualize.io/api/message/
- Textual Workers Guide: https://textual.textualize.io/guide/workers/
- Textual Widget API: https://textual.textualize.io/api/widget/
- Textual Data Binding: https://textual.textualize.io/guide/reactivity/#data-binding
- Will McGugan on sibling messaging (Discussion #186): https://github.com/Textualize/textual/discussions/186
- Textual 8.2.3 (installed): verified via `uv pip show textual`
