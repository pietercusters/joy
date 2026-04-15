# Quick Task 260415-mh6: Refactor Worktree Logic — Research

**Researched:** 2026-04-15
**Domain:** Python TUI (Textual) — worktree discovery, key bindings, IDE open
**Confidence:** HIGH (codebase read directly)

---

## Summary

The worktree logic has two conceptually different IDE-open paths that are both wrong for the new requirement. The global `action_open_ide` ('i' in JoyApp) routes through `_open_first_of_kind(PresetKind.WORKTREE)`, which searches project *objects* for a `WORKTREE`-kind entry — a manually-added path that may or may not exist. This is the "IDE path configured on linked project" concept the user wants removed. The Worktrees pane `action_activate_row` (Enter/'o') correctly opens the highlighted worktree's *auto-detected* path, but conditionally: if an MR is present it opens the MR URL instead of the IDE, which is the exact bug.

The new requirement collapses both paths into one: **'i' and Enter always do `ide <worktree_path>` using the auto-detected path of the highlighted worktree row** — no project-object lookup, no MR URL detour.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Always open the specific worktree path in the IDE: `ide <worktree_path>`
- Do NOT use any "IDE path configured on linked project" concept — remove that if it exists
- Both 'i' and Enter trigger the same action: open the worktree directory in the IDE
- Show all auto-detected worktrees including those with no matching project branch (unlinked)
- Unlinked worktrees get a visual indicator (e.g. "unlinked" label or dim styling)
- IDE open action still works on unlinked worktrees (just opens their path)
- Enter replaces the current action — it now opens the IDE on the highlighted worktree

### Claude's Discretion
- Exact visual indicator for unlinked worktrees (label text, color, etc.)
- Whether to keep 'i' as a parallel binding alongside Enter, or just use Enter
- How to handle stale/missing worktree paths
- Any other bugs found during investigation

### Deferred Ideas (OUT OF SCOPE)
- Nothing explicitly deferred
</user_constraints>

---

## Bug Inventory

### Bug 1: Global 'i' binding opens wrong path (CRITICAL)

**File:** `src/joy/app.py:700-701`

```python
def action_open_ide(self) -> None:
    self._open_first_of_kind(PresetKind.WORKTREE)
```

**Code path:**
1. `_open_first_of_kind(PresetKind.WORKTREE)` — line 657
2. Searches `project.objects` for an item with `kind == PresetKind.WORKTREE`
3. Found item's `.value` is the path stored when user manually added a WORKTREE object
4. Calls `_do_open_global(item)` → `open_object()` → `subprocess.run(["open", "-a", config.ide, item.value])`

**Why it's wrong:** This uses a *manually added* worktree path stored in the project's object list. It does not look at the highlighted row in the Worktrees pane. If the user has no WORKTREE object on the project (very likely in the new auto-detect world), the command notifies "No worktree found for this project" and does nothing.

**What it should do:** Open the path from `WorktreePane._rows[WorktreePane._cursor].path`.

---

### Bug 2: Enter in Worktrees pane opens MR URL instead of IDE (CRITICAL)

**File:** `src/joy/widgets/worktree_pane.py:452-468`

```python
def action_activate_row(self) -> None:
    if self._cursor < 0 or self._cursor >= len(self._rows):
        return
    row = self._rows[self._cursor]
    mr_info = row.mr_info
    if mr_info is not None and mr_info.url:       # <-- problem: MR takes priority
        from urllib.parse import urlparse
        parsed = urlparse(mr_info.url)
        if parsed.scheme in ("https", "http"):
            webbrowser.open(mr_info.url)
    else:                                          # IDE open only when no MR
        config = getattr(self.app, "_config", None)
        ide = config.ide if config else "Cursor"
        subprocess.run(
            ["open", "-a", ide, row.path],
            check=False,
        )
```

**Why it's wrong:** When a worktree has an MR, Enter opens the MR in the browser. The user wants Enter to always open the IDE. The MR-open-on-Enter was added in quick task 260414-qk4 but is now superseded.

**Fix:** Remove the `if mr_info` branch entirely. Always `open -a <ide> <row.path>`. The MR URL can be opened via the 'm' global binding.

---

### Bug 3: `action_activate_row` runs subprocess on main thread (SMELL)

**File:** `src/joy/widgets/worktree_pane.py:465-468`

```python
subprocess.run(["open", "-a", ide, row.path], check=False)
```

This runs `subprocess.run` directly on the main Textual event loop thread. This is inconsistent with the app pattern (`_do_open_global` uses `@work(thread=True)`). For `open -a`, the subprocess typically returns instantly on macOS (the OS launches asynchronously), so this is unlikely to block in practice, but it's still a smell. The fix should use `@work(thread=True)` or post a message to the app to do the open.

---

### Bug 4: `action_open_ide` fallback to WORKTREE object is now conceptually wrong

**File:** `src/joy/app.py:700-701` (same as Bug 1)

The `PresetKind.WORKTREE` object type exists as a *manually-added* object a user can attach to a project (appears in "Code" section of project detail, icon = folder). This is the "IDE path configured on linked project" concept the user wants removed from the 'i' key. The object type itself can remain (it's still useful in the detail pane for opening with Enter/o), but 'i' should stop routing through it.

---

### Bug 5: 'i' binding has `show=False` — not visible in hints bar

**File:** `src/joy/app.py:71` and `src/joy/app.py:29`

```python
Binding("i", "open_ide", "IDE", show=False),
```

```python
"worktrees-pane": "",   # empty — no pane-specific hints
```

The worktrees pane hint bar is empty. If 'i' is kept as a binding, it should appear in the hints. This is a discoverability smell, not a functional bug.

---

## Architecture: How Worktrees Reach the Pane

The current auto-detect flow is correct and should be kept:

```
JoyApp._load_worktrees() [thread]
  └─> discover_worktrees(repos, branch_filter)   [worktrees.py]
        └─> _list_worktrees(repo.local_path)      [git worktree list --porcelain]
        └─> WorktreeInfo(repo_name, branch, path, is_dirty, has_upstream, is_default_branch)
  └─> fetch_mr_data(repos, worktrees)             [mr_status.py]
  └─> _set_worktrees(worktrees, repo_count, branch_filter, mr_data)  [main thread]
        └─> WorktreePane.set_worktrees(...)
```

**Key point:** `WorktreeInfo` already has `.path` (the absolute fs path). The pane's `WorktreeRow` already stores `self.path = worktree.path`. The data needed for `ide <path>` is already right there in the row object.

---

## How Project-Worktree Linking Works (Resolver)

**File:** `src/joy/resolver.py:52-109`

Two matching strategies:
1. **Path match:** Project has a `WORKTREE` object whose `.value` equals `wt.path`
2. **Branch match:** Project has a `BRANCH` object whose `.value` equals `wt.branch` AND `project.repo == wt.repo_name`

Worktrees that match neither strategy are present in `_current_worktrees` but absent from `_rel_index`. The `project_for_worktree()` returns `None` for them.

**For unlinked worktrees:** `RelationshipIndex.project_for_worktree(wt)` returns `None`. The pane shows them normally (they are not filtered out by `discover_worktrees` or `set_worktrees`). The pane doesn't currently mark them as unlinked — this is the new visual indicator to add.

---

## What Changes Are Needed

### Change 1: Fix `action_open_ide` in `app.py`

**Remove:** `_open_first_of_kind(PresetKind.WORKTREE)` path.

**Replace with:** Get the highlighted row from `WorktreePane` and open its `.path`.

```python
def action_open_ide(self) -> None:
    """Open the highlighted worktree in the IDE."""
    pane = self.query_one(WorktreePane)
    if pane._cursor < 0 or not pane._rows:
        self.notify("No worktree selected", markup=False)
        return
    path = pane._rows[pane._cursor].path
    self._open_worktree_path(path)

@work(thread=True, exit_on_error=False)
def _open_worktree_path(self, path: str) -> None:
    ide = self._config.ide or "Cursor"
    try:
        subprocess.run(["open", "-a", ide, path], check=False)
    except Exception as exc:
        self.app.notify(f"Failed to open IDE: {exc}", severity="error", markup=False)
```

### Change 2: Fix `action_activate_row` in `worktree_pane.py`

**Remove:** The `if mr_info` branch (MR URL open).

**Replace with:** Always open IDE. The `subprocess.run` call should either stay (it returns instantly on macOS) or be moved to a `@work(thread=True)` method/message to the app. Cleanest approach: post a message to the app to call `action_open_ide`, or directly call `self.app.action_open_ide()` — this reuses Change 1 and avoids duplicating subprocess logic.

```python
def action_activate_row(self) -> None:
    if self._cursor < 0 or self._cursor >= len(self._rows):
        return
    self.app.action_open_ide()  # delegate to app — single open path
```

This means Enter and 'i' both hit the same code path.

### Change 3: Add unlinked visual indicator

In `WorktreePane.set_worktrees()`, after the resolver runs — but the resolver runs in `app._maybe_compute_relationships()`, which is after `set_worktrees` completes. So the pane doesn't have access to the rel_index during row construction.

**Options:**
1. Pass linked status as a parameter to `set_worktrees` (add `linked_paths: set[str]` arg computed from rel_index)
2. Add a `mark_unlinked(paths: set[str])` method called after rel_index is computed
3. Store a `is_linked: bool` on `WorktreeRow` and update it via a second pass

The cleanest approach given the current architecture: add a `set_linked_paths(linked_paths: set[str])` method that iterates `_rows` and adds/removes a CSS class or updates the rendered text. This is called from `app._update_badges()` or a new `_update_worktree_link_status()` method called after `_maybe_compute_relationships`.

**Visual indicator:** Dim styling with "(unlinked)" suffix label is appropriate. Use existing `--highlight` pattern.

### Change 4: Update hint bar

Update `_PANE_HINTS["worktrees-pane"]` in `app.py` to show `"i/Enter: Open IDE"`.

---

## Textual Key Dispatch — Relevant Pitfalls

**Pitfall: `action_open_ide` at app level vs pane level**

The 'i' binding is on `JoyApp.BINDINGS` (not `WorktreePane.BINDINGS`). Textual dispatches keys up the focus chain from the focused widget to the app. Since `WorktreePane` does not have 'i' in its own `BINDINGS`, pressing 'i' always bubbles up to `JoyApp`. This is correct behavior and should be kept.

**Pitfall: Calling `self.app.action_open_ide()` from a widget**

Calling app actions from widget action methods is valid in Textual. The call is synchronous on the event loop thread and will immediately execute the method. Since `action_open_ide` itself delegates to `@work(thread=True)`, this is safe.

**Pitfall: `subprocess.run` on event loop thread**

`open -a AppName /path` returns in ~5ms on macOS (the OS queues the launch). This is unlikely to block. But for consistency with the rest of the codebase, it should be in a `@work(thread=True)` method.

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/joy/app.py` | Rewrite `action_open_ide`, add `_open_worktree_path`, update `_PANE_HINTS` |
| `src/joy/widgets/worktree_pane.py` | Rewrite `action_activate_row`, add unlinked indicator logic |

No model changes needed. `WorktreeInfo` already has all needed fields. No changes to `worktrees.py` or `resolver.py`.

---

## Open Questions

1. **How to trigger `set_linked_paths` after rel_index is computed**
   - `_maybe_compute_relationships` calls `_update_badges()` and `_propagate_changes()`
   - A new `_update_worktree_link_status()` call can be added there
   - It needs `rel_index._wt_for_project` or a set of linked `wt.path` values

2. **Whether to keep 'i' as a parallel binding or only Enter**
   - CONTEXT.md says this is Claude's discretion
   - Recommendation: keep both — 'i' stays as global quick-open (works from any pane), Enter is pane-local
   - This matches the pattern used by 'm', 'b', etc. (global shortcuts)

3. **Missing worktree path handling**
   - If `row.path` doesn't exist on disk, `open -a IDE /nonexistent/path` will fail silently (macOS returns an error code)
   - The `check=False` in the current code swallows this
   - Recommendation: add a `Path(path).exists()` check, notify if missing

---

## Sources

- `src/joy/widgets/worktree_pane.py` — read directly (lines 452-468: action_activate_row bug; lines 241-248: BINDINGS)
- `src/joy/app.py` — read directly (lines 700-701: action_open_ide; lines 657-672: _open_first_of_kind)
- `src/joy/resolver.py` — read directly (compute_relationships, path/branch match logic)
- `src/joy/operations.py` — read directly (_open_worktree implementation)
- `src/joy/worktrees.py` — read directly (discover_worktrees, _list_worktrees)
- `src/joy/models.py` — read directly (WorktreeInfo dataclass)
- `.planning/quick/260415-jab-*/260415-jab-SUMMARY.md` — read directly (prior 'i' fix context)
