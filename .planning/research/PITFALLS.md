# Domain Pitfalls: v1.2 Cross-Pane Intelligence

**Domain:** Cross-pane selection sync and live data propagation in an existing Textual 8.x TUI
**Researched:** 2026-04-14
**Confidence:** HIGH (pitfalls derived from actual codebase analysis + Textual docs + thread-safety fundamentals)

---

## Critical Pitfalls

Mistakes that cause infinite loops, data corruption, or require significant rework.

### CP-1: Sync Loop — Pane A Syncs Pane B, Pane B Triggers Sync Back to A

**What goes wrong:** Selecting a project in ProjectList fires a sync message to WorktreePane and TerminalPane. WorktreePane receives the message, moves its cursor to the matching worktree, and posts its own "cursor moved" message. That message arrives back at the sync coordinator, which interprets it as a user-initiated cursor move in WorktreePane and tries to sync ProjectList back to a matching project. Infinite loop.

**Why it happens:** Joy's four panes all use the same `_update_highlight()` pattern that could trigger messages. The existing `ProjectList.ProjectHighlighted` message is already used to update ProjectDetail. Adding cross-pane sync means every pane becomes both a sync source and a sync target. Without distinguishing user-initiated cursor moves from programmatic cursor moves, every sync action triggers another sync action.

**Consequences:** The app freezes in a tight message loop. CPU spins at 100%. The only escape is Ctrl+C. Even if the loop terminates (e.g., because the cursor is already at the target), it still causes unnecessary work on every cursor move.

**Prevention:**
- **Use a guard flag.** Set `self._syncing = True` before programmatic cursor moves, check it before emitting sync messages: `if self._syncing: return`. Clear after the operation. This is the simplest approach and matches how joy already uses generation counters for render deduplication.
- **Distinguish message sources.** Add an `is_user_initiated: bool` field to cursor-move messages. Only user-initiated moves trigger sync. Programmatic moves (from sync) carry `is_user_initiated=False` and are ignored by the sync coordinator.
- **Use Textual's `prevent()` context manager.** Wrap programmatic cursor updates in `with self.prevent(CursorMoved):` to suppress the message entirely during sync operations. This is the most idiomatic Textual approach.
- **Do NOT use reactive attributes for cursor position.** Reactives trigger watchers automatically, making loop prevention harder. The existing `_cursor: int` plain attribute pattern in all four panes is correct. Keep it.

**Detection:** Test: select project, observe that worktree pane cursor moves to matching worktree, and the project pane cursor does NOT move again. If the cursor "bounces" or the app freezes, the loop exists.

**Phase:** Must be solved in the first phase of v1.2, before any sync logic ships. The guard flag or prevent() pattern must be the first thing implemented.

**Confidence:** HIGH -- this is a well-known pattern in reactive UI systems. Textual's `prevent()` context manager exists specifically for this. The existing codebase already has the `ProjectHighlighted` message flowing from ProjectList to JoyApp; adding bidirectional flow without guards will immediately loop.

---

### CP-2: Concurrent TOML Mutations from Overlapping Workers

**What goes wrong:** Two `@work(thread=True)` workers run simultaneously -- one from a user action (e.g., `_save_projects_bg` after adding an object) and one from live data propagation (e.g., auto-adding a detected MR). Both read `self.app._projects`, mutate it, and call `save_projects()`. The second writer overwrites the first writer's changes because both started from the same snapshot.

**Why it happens:** Joy's current architecture has a single shared `self._projects: list[Project]` on JoyApp. Multiple `@work(thread=True)` methods can access this list concurrently. The existing code already has this potential issue with `_save_projects_bg` and `_save_toggle` both writing projects, but in practice users don't trigger both simultaneously. v1.2's live data propagation adds automatic mutations that WILL overlap with user actions.

**Current risk surface in the codebase:**
- `_save_projects_bg()` -- called after new project, add object, rename, delete, assign repo
- `_save_toggle()` -- called from ProjectDetail after toggle/edit/delete object
- NEW in v1.2: auto-add MR, auto-remove worktree, auto-mark agent stale -- all background mutations

**Consequences:** Data loss. A user adds an object, then a background refresh auto-adds an MR. The MR write uses the pre-add snapshot and overwrites the user's new object. The user's object silently disappears.

**Prevention:**
- **Serialize all TOML mutations through the main thread.** Never mutate `_projects` from a worker thread. Workers discover data (e.g., "MR #42 found for project X"), then `call_from_thread` a main-thread method that performs the actual mutation and save. Since Textual's main thread is single-threaded (asyncio event loop), mutations are serialized.
- **Add a `threading.Lock` to `save_projects()`.** This prevents two concurrent writes from interleaving, but does NOT prevent the read-snapshot problem. The lock must guard both the mutation and the write, not just the write.
- **Preferred pattern:** Worker discovers data -> `call_from_thread(self._apply_discovered_mr, project_name, mr_data)` -> main thread method mutates `_projects` and calls `_save_projects_bg()`. This matches the existing `_set_worktrees` pattern where workers push data to the main thread.

**Detection:** Add an MR object to a project while a background refresh is running. If the MR appears but the user's recent addition disappears, the race exists.

**Phase:** Must be the foundational pattern for all live data propagation. Establish the "workers discover, main thread mutates" rule before implementing any auto-add/remove feature.

**Confidence:** HIGH -- the existing `_save_projects_bg` is already a `@work(thread=True)` that accesses shared state. The pattern is safe today only because user actions don't overlap with background writes. v1.2 breaks that assumption.

---

### CP-3: "Branch is King" Invariant Accidentally Mutates Branch Objects

**What goes wrong:** The live data propagation system detects that a worktree's branch matches a different project and tries to "move" the worktree object. The move logic incorrectly also moves or modifies the branch object, or creates a new branch object on the target project, violating the rule that branch objects are user-managed and never auto-touched.

**Why it happens:** Projects have both `branch` objects (user-created, storing the branch name as a string) and `worktree` objects (storing the filesystem path). The branch name is the matching key. When "branch is king" triggers a worktree ownership transfer, the naive implementation might:
1. Move all objects matching the branch name, not just the worktree object
2. Create a new branch object on the target project (the user didn't ask for this)
3. Delete the branch object from the source project (destroying user data)

**Consequences:** User-curated branch objects (which may have labels, open_by_default settings) are silently moved, duplicated, or deleted. The user loses their careful configuration.

**Prevention:**
- **Filter by `PresetKind` explicitly.** Auto-propagation code must ONLY touch objects where `item.kind == PresetKind.WORKTREE` (for worktree moves) or `item.kind == PresetKind.MR` (for MR auto-add). Never touch `PresetKind.BRANCH`, `PresetKind.AGENTS`, or any other kind.
- **Whitelist, not blacklist.** The propagation system should have an explicit set of kinds it is allowed to create/modify/delete: `ALLOWED_AUTO_KINDS = {PresetKind.WORKTREE, PresetKind.MR}`. Anything not in this set is never touched.
- **Unit test the invariant.** Create a test that sets up a project with branch + worktree objects, triggers a branch-ownership change, and asserts that the branch object is untouched on both source and target projects.

**Detection:** After a worktree ownership transfer, check that branch objects on both source and target projects are identical to their pre-transfer state.

**Phase:** Must be codified as a design constraint before implementing worktree ownership transfer. The `ALLOWED_AUTO_KINDS` constant should be defined in the first v1.2 phase.

**Confidence:** HIGH -- derived directly from the codebase. `PresetKind.BRANCH` (value: "branch", type: STRING) and `PresetKind.WORKTREE` (value: "worktree", type: WORKTREE) are distinct kinds. The risk is in matching logic that uses branch name strings rather than object kind.

---

### CP-4: Cursor Position Lost During Background Refresh DOM Rebuilds

**What goes wrong:** A background refresh completes and calls `set_worktrees()` or `set_sessions()`, which does `await scroll.remove_children()` followed by mounting new rows. The cursor resets to 0 (first row). If the user was looking at row 15 in the worktree pane, they are suddenly snapped back to row 0.

**Why it happens:** This is ALREADY happening in the current codebase, but it is partially mitigated. The WorktreePane and TerminalPane save and restore `scroll_y` position, but they reset `self._cursor = 0` on every rebuild. The existing code in `set_worktrees()`:
```python
self._cursor = 0 if new_rows else -1
```
This means every 30-second refresh resets the cursor to the first row. Scroll position is preserved (via `saved_scroll_y`), but the highlight jumps to row 0.

**Consequences:** User is browsing worktrees, every 30 seconds the highlight jumps to the top. Mildly annoying in v1.1. In v1.2 with cross-pane sync, this cursor reset would trigger a sync cascade: cursor resets to row 0 -> sync fires -> project pane jumps to the project matching row 0's branch. Catastrophic UX.

**Prevention:**
- **Match cursor by identity, not index.** Before rebuild, save the current row's identity (e.g., `(repo_name, branch)` for worktrees, `session_id` for terminals). After rebuild, find the row with the same identity and set cursor there. Fall back to 0 if the item no longer exists.
- **The pattern already exists in ProjectList.** The `action_rename_project` method does exactly this: saves `project`, rebuilds, then iterates `_rows` to find the same project object. Replicate this pattern in WorktreePane and TerminalPane.
- **Suppress sync messages during refresh-triggered cursor updates.** Even with identity matching, the cursor technically "moves" (from -1 during rebuild back to the matched index). Use the sync guard flag from CP-1 to prevent this from triggering cross-pane sync.

**Detection:** Focus the worktree pane, move cursor to a non-first row, wait for auto-refresh (30s). If the highlight jumps to row 0, the bug exists.

**Phase:** Must be fixed BEFORE cross-pane sync is enabled. Otherwise every background refresh triggers a sync cascade. This is a prerequisite for v1.2, not a v1.2 feature itself.

**Confidence:** HIGH -- directly observed in the codebase. `set_worktrees()` line 361: `self._cursor = 0 if new_rows else -1`. The scroll position IS preserved (line 364: `scroll_to(y=saved_scroll_y)`), but the cursor is not.

---

## Moderate Pitfalls

### MP-1: Matching Ambiguity -- Multiple Projects Share the Same Branch Name

**What goes wrong:** The cross-pane sync resolver finds a worktree with branch `feature-auth`. Two projects both have a branch object with value `feature-auth`. The resolver picks one arbitrarily, and the sync highlights the wrong project.

**Why it happens:** Branch names are not globally unique. Two repos can both have a `feature-auth` branch. Projects are grouped by repo, so the repo context should disambiguate. But the resolver might match on branch name alone.

**Consequences:** Selecting a worktree syncs to the wrong project. User is confused about which project is actually associated with the worktree.

**Prevention:**
- **Always match on (repo_name, branch) pair, never branch alone.** A worktree knows its `repo_name`. A project knows its `repo` field. The resolver must require both to match.
- **Projects without a `repo` field are excluded from sync.** This is already in the v1.2 requirements: "Projects without repo field excluded from live sync." Enforce this strictly.
- **If multiple projects share the same repo AND the same branch name, prefer the one with a worktree object for that branch.** If still ambiguous, prefer the first match and log a warning (visible in debug mode, not a toast).

**Detection:** Create two projects with different repos, both having a branch named `main`. Select the `main` worktree for repo A. Verify the sync highlights the correct project (the one assigned to repo A, not repo B).

**Phase:** Part of the relationship resolver implementation. Must be designed before the resolver is coded.

**Confidence:** HIGH -- the data model supports this. `Project.repo` exists (added in v1.1). `WorktreeInfo.repo_name` exists. The matching key is `(project.repo, object.value)` == `(worktree.repo_name, worktree.branch)`.

---

### MP-2: Agent Stale Marking Overwrites Other Object Data

**What goes wrong:** The stale-marking system adds or modifies a field on agent objects in TOML. A naive implementation adds a `stale: true` field to the ObjectItem. But ObjectItem's `to_dict()` doesn't include `stale`, so the next save drops it. Or worse, the stale flag is stored as a parallel data structure that gets out of sync with the main objects list.

**Why it happens:** The current `ObjectItem` dataclass has exactly four fields: `kind`, `value`, `label`, `open_by_default`. Adding `stale` requires changing the data model, which affects TOML serialization, deserialization, and all existing code that creates ObjectItems.

**Consequences:** Stale flags don't persist across restarts. Or stale flags corrupt existing object data. Or a parallel stale tracking dict diverges from the objects list after adds/deletes.

**Prevention:**
- **Add `stale: bool = False` to the ObjectItem dataclass.** Update `to_dict()` to include it only when True (to avoid polluting existing TOML). Update `_toml_to_projects()` to read it with `obj.get("stale", False)`. This is the cleanest approach -- the flag travels with the object through all code paths.
- **Do NOT use a separate tracking dict.** A `stale_agents: dict[str, bool]` would need to be kept in sync with adds, deletes, renames, and project transfers. It will inevitably diverge.
- **Only write `stale` to TOML when True.** This keeps the TOML clean for non-stale objects and is backward-compatible (old code that doesn't know about `stale` will just ignore it, and `to_dict()` for non-stale objects produces identical output).

**Detection:** Mark an agent stale, restart joy, verify it's still marked stale. Delete the agent, add a new one with the same name, verify it's not stale.

**Phase:** Part of agent stale detection. Should be implemented as a model change before the detection logic.

**Confidence:** HIGH -- derived from the actual ObjectItem dataclass in `models.py`. The current four-field structure requires extension.

---

### MP-3: Worktree Ownership Transfer is Not Atomic

**What goes wrong:** Moving a worktree object from project A to project B involves: (1) find the object in A, (2) remove it from A, (3) add it to B, (4) save. If the save fails between step 2 and step 3 (or if there's a crash), the object is lost from A but never added to B.

**Why it happens:** The current `save_projects()` writes all projects atomically (temp file + `os.replace`). So as long as steps 2 and 3 both happen before the save, the save itself is atomic. The real risk is: what if step 2 succeeds but step 3 raises an exception (e.g., project B was deleted between discovery and application)?

**Consequences:** A worktree object disappears from both projects. The user has to manually re-add it.

**Prevention:**
- **Perform both mutation steps in a single method, then save once.** The mutation is: `a.objects.remove(obj)` + `b.objects.append(obj)`. Both operations are in-memory list operations that won't raise unless the object/project doesn't exist. Wrap in try/except and only save if both succeeded.
- **Check that both source and target projects still exist before mutating.** Between discovery (worker thread) and application (main thread via `call_from_thread`), a project might have been deleted. The apply method must verify both projects are still in `_projects`.
- **If target project doesn't exist, leave the object where it is.** A worktree in the "wrong" project is better than a lost worktree. Log a warning.
- **The existing `_atomic_write` in store.py handles the filesystem atomicity.** The risk is purely in the in-memory mutation logic.

**Detection:** Trigger a worktree ownership transfer while simultaneously deleting the target project. The worktree object should remain in the source project, not vanish.

**Phase:** Part of worktree ownership transfer implementation.

**Confidence:** HIGH -- the `_atomic_write` pattern already handles filesystem atomicity. This pitfall is about in-memory mutation ordering, which is straightforward to get right if you're aware of it.

---

### MP-4: @work(thread=True) Worker Overlap During Rapid Refresh

**What goes wrong:** User presses `r` (manual refresh) while an auto-refresh is already in progress. Two `_load_worktrees()` workers run simultaneously. Both call `discover_worktrees()` and `fetch_mr_data()` (expensive subprocess calls). Both call `call_from_thread(self._set_worktrees, ...)`. The first to arrive renders correctly, but the second arrives moments later and overwrites it -- possibly with stale data if the git state changed between the two reads.

**Why it happens:** The current `_load_worktrees` uses `@work(thread=True)` but does NOT use `exclusive=True`. Looking at the code: `_load_worktrees`, `_load_terminal`, `_save_projects_bg`, `_save_config_bg`, `_reload_repos` -- none use `exclusive=True` or worker groups.

**Consequences:** Wasted work (two full git scans + MR fetches). Possible flickering as the pane renders twice. Possible out-of-order updates if the first worker's subprocess calls take longer than the second's (second arrives first, then first overwrites with older data).

**Prevention:**
- **Add `exclusive=True` to `_load_worktrees` and `_load_terminal`.** This tells Textual to cancel the previous worker before starting a new one. The cancelled worker's `call_from_thread` calls are never executed (Textual checks `worker.is_cancelled`).
- **Use worker groups for fine-grained control:** `@work(thread=True, exclusive=True, group="worktree-refresh")`. This ensures only one worktree refresh runs at a time, without affecting terminal refresh workers.
- **For save workers, `exclusive=True` is risky.** If a save is cancelled, data is lost. Save workers should use a lock instead, or queue saves (debounce: only save once after all mutations in a batch complete).

**Detection:** Rapidly press `r` multiple times. Check that only one refresh completes (not multiple sequential renders). Add logging to `_set_worktrees` to count invocations.

**Phase:** Should be applied to existing refresh workers as a prerequisite for v1.2. With sync enabled, out-of-order updates would trigger incorrect sync cascades.

**Confidence:** HIGH -- directly observed: `_load_worktrees` at line 119 of app.py uses `@work(thread=True)` without `exclusive=True`. Textual's `exclusive` parameter is documented specifically for this use case.

---

### MP-5: Cross-Pane Sync Toggle State Persists Across Context Changes

**What goes wrong:** User turns sync off (because they want to browse worktrees independently), then forgets sync is off. Later, they expect selecting a project to sync worktrees, but it doesn't. Or conversely: user turns sync on, expects it to stay on across app restarts, but the toggle resets.

**Why it happens:** The sync toggle needs a clear UX contract: is it persistent (saved to config) or ephemeral (reset on restart)? Is it a global toggle or per-pane? The v1.2 requirements just say "sync on/off toggle via keyboard shortcut" without specifying persistence.

**Consequences:** User confusion about why sync "stopped working" or "won't turn off."

**Prevention:**
- **Make sync ON by default, ephemeral (not persisted).** This matches the expected workflow: sync is the normal mode, turning it off is a temporary override for independent browsing.
- **Show sync state in the UI.** Add a visible indicator -- a character in the header, border, or footer that shows whether sync is active. The existing border_title pattern (used for refresh timestamps) is a natural home.
- **If persisted, add to Config.** Add `sync_enabled: bool = True` to Config and save/load it. But this adds complexity for minimal value in a personal tool.

**Detection:** Turn sync off, restart app, verify sync is back on (if ephemeral) or still off (if persistent). Either is fine as long as it's intentional and visible.

**Phase:** Design decision for the sync toggle implementation.

**Confidence:** MEDIUM -- this is a UX design question, not a technical pitfall. But getting it wrong causes ongoing user confusion.

---

## Minor Pitfalls

### MN-1: Badge Count Flicker During Refresh

**What goes wrong:** Badge counts on project rows (e.g., "2 worktrees, 1 agent") show stale counts during a refresh cycle. The worktree data arrives first, badges update to show worktree counts, then terminal data arrives and badges update again. Users see numbers changing rapidly.

**Why it happens:** `_load_worktrees()` and `_load_terminal()` are independent workers that complete at different times. Each triggers a badge recalculation. The badges flicker as each data source arrives.

**Prevention:**
- **Debounce badge updates.** After receiving new data from either source, wait a short period (100-200ms) before recalculating badges. If the other source arrives within that window, calculate once.
- **Or accept the flicker.** For a 30-second refresh cycle, a brief flicker is acceptable. The "final" state is correct within a few hundred milliseconds.
- **Do NOT block one worker waiting for the other.** That defeats the purpose of parallel loading.

**Phase:** Badge count implementation.

**Confidence:** MEDIUM -- depends on how fast the two workers complete. If terminal fetching is slow (iTerm2 Python API), the gap may be noticeable.

---

### MN-2: Stale MR Objects After Branch Force-Push or Rename

**What goes wrong:** Live propagation auto-added an MR object for branch `feature-x`. The user force-pushes to a new branch name or the MR is closed. The auto-added MR object lingers in the project with a stale URL.

**Why it happens:** Auto-add is easy. Auto-remove is harder. How do you know an MR object should be removed? The MR might be closed but the user wants to keep the link for reference. Or the user might have manually added the MR object (not auto-added), and auto-remove would delete their intentional data.

**Prevention:**
- **Tag auto-added objects.** Add a flag (e.g., `auto_managed: bool = False`) to ObjectItem. Auto-added MRs have `auto_managed=True`. Only auto-managed objects are candidates for auto-removal.
- **Alternatively, use a naming convention.** Auto-added MR labels start with a prefix like `[auto]`. But this is fragile -- users might remove the prefix.
- **Safest approach: auto-add, never auto-remove MRs.** Let users manually delete stale MRs. This is simpler and avoids the "who owns this object" ambiguity. Auto-removal should only apply to worktree objects (which are tied to filesystem state that's definitively observable).

**Phase:** MR auto-add implementation.

**Confidence:** MEDIUM -- design trade-off. The safest default is to auto-add but not auto-remove MR objects.

---

### MN-3: Sync Flicker When Multiple Panes Match the Same Entity

**What goes wrong:** User selects a project. Sync resolver finds matching worktree and matching agent. Both panes update their cursors simultaneously. The sync events arrive in unpredictable order, causing brief visual inconsistency.

**Prevention:**
- **Batch sync updates.** When a source pane triggers sync, compute ALL target cursor positions first, then apply them in a single `call_after_refresh` batch. This ensures all panes update in the same render frame.
- **Use `self.app.batch_update()` context manager** (if available in Textual 8.x) or schedule all updates via `call_after_refresh` with a single callback that updates all panes.

**Phase:** Cross-pane sync implementation.

**Confidence:** MEDIUM -- visual flicker depends on render timing. May not be noticeable in practice.

---

## Integration Pitfalls Specific to This System

### IP-1: ProjectDetail's Synthetic Repo Object Confuses the Sync Resolver

**What goes wrong:** ProjectDetail's `_render_project` method (line 137-139 of project_detail.py) synthesizes a repo ObjectItem if `project.repo` is set:
```python
if self._project.repo:
    repo_item = ObjectItem(kind=PresetKind.REPO, value=self._project.repo, label="")
    grouped.setdefault(PresetKind.REPO, []).append(repo_item)
```
This synthetic object exists in the UI but NOT in `project.objects`. If the sync resolver iterates `project.objects` to find matches, it won't find the repo object. If it iterates the rendered rows, it will find a "phantom" object that doesn't exist in the data model.

**Prevention:**
- **The sync resolver must use `project.objects` (the data model), not rendered rows.** The renderer adds display-only elements (group headers, spacers, the synthetic repo item). The resolver must ignore these.
- **Alternatively, if the resolver needs to match by branch, it should look at `project.repo` directly,** not at the objects list. The repo field is the canonical source for which repo a project belongs to.

**Phase:** Relationship resolver design.

**Confidence:** HIGH -- directly observed in the codebase. The synthetic repo object is a display concern that must not leak into the data-matching layer.

---

### IP-2: _render_generation Counter Race with Sync-Triggered Re-renders

**What goes wrong:** ProjectDetail uses `_render_generation` to deduplicate rapid re-renders. A sync-triggered `set_project()` increments the generation. If a user-triggered `set_project()` fires in the same tick (e.g., user moves cursor while sync is updating), the generation increments again, and the sync render is correctly discarded. But now the user's render also increments the generation, and if sync fires AGAIN (because the user's cursor move triggered a new sync), we get a cascade of incrementing generations where some renders are discarded and the cursor ends up in an unexpected position.

**Prevention:**
- **Sync should NOT call `set_project()` on ProjectDetail.** Sync should only move the cursor, not re-render the entire detail pane. If the sync resolver determines "project X matches," and project X is already displayed in ProjectDetail, just leave it alone. Only call `set_project()` if the project actually changes.
- **Guard: `if detail._project is project: return`** (identity check, not equality). Since `_projects` is a stable list of the same Project objects, identity comparison works.

**Phase:** Cross-pane sync to ProjectDetail connection.

**Confidence:** HIGH -- the `_render_generation` pattern exists at line 108-109 of project_detail.py. It works well for rapid user navigation but could interact badly with sync-triggered updates.

---

### IP-3: WorktreePane.set_worktrees() is async, But call_from_thread Expects Sync

**What goes wrong:** `_set_worktrees` in app.py is defined as `async def _set_worktrees(...)` and calls `await self.query_one(WorktreePane).set_worktrees(...)`. But `_load_worktrees()` calls it via `self.app.call_from_thread(self._set_worktrees, worktrees, ...)`. The `call_from_thread` function can handle both sync and async callables -- Textual schedules async ones on the event loop. However, if the sync coordinator also calls `set_worktrees()` (to update cursor position after sync), there's now two paths to the same async method, and they can overlap.

**Prevention:**
- **Separate data-push from cursor-update.** `set_worktrees()` should remain the data-push path (called from refresh workers). Sync should call a separate, lighter method like `sync_cursor_to_branch(repo_name, branch)` that only moves the cursor without rebuilding the DOM.
- **This avoids the heavyweight remove_children + mount cycle during sync.** Sync should be a cursor move, not a full re-render.

**Phase:** Cross-pane sync to WorktreePane connection.

**Confidence:** HIGH -- derived from the code. `set_worktrees()` is a full DOM rebuild. Using it for cursor sync would be absurdly wasteful and could interact with concurrent refresh rebuilds.

---

### IP-4: Existing call_after_refresh Chains Interact Poorly with Sync

**What goes wrong:** The codebase uses `call_after_refresh` extensively for deferred operations:
- `ProjectList.set_projects()` -> `call_after_refresh(self._rebuild)` 
- `ProjectDetail.set_project()` -> `call_after_refresh(self._render_project)`
- `ProjectList.action_rename_project()` -> `call_after_refresh(_restore_cursor)`
- Scroll position restoration -> `call_after_refresh(scroll_to)`

If sync also uses `call_after_refresh`, the ordering of deferred callbacks becomes unpredictable. A sync callback might execute before a rebuild callback, operating on stale DOM state.

**Prevention:**
- **Sync cursor updates should be immediate, not deferred.** Since sync only moves the cursor (MP-4 prevention: don't re-render), it operates on existing `_rows` which are already in the DOM. No `call_after_refresh` needed.
- **If sync must be deferred (because it depends on a rebuild completing), chain it explicitly.** The rebuild method should call the sync update at the end, not schedule a separate deferred callback.

**Phase:** Integration of sync with the existing refresh pipeline.

**Confidence:** HIGH -- the six `call_after_refresh` usages in the codebase create a deferred callback queue. Adding more without understanding the order is a recipe for flaky behavior.

---

### IP-5: _rows List References Become Stale After DOM Rebuild

**What goes wrong:** The sync resolver grabs a reference to `worktree_pane._rows[i]` to extract the branch name for matching. A background refresh runs, `set_worktrees()` rebuilds the DOM, and `_rows` is replaced with a new list. The resolver's reference now points to a detached `WorktreeRow` that's no longer in the DOM. Calling `add_class("--highlight")` on it does nothing visible.

**Why it happens:** `_rows` is reassigned on every rebuild: `self._rows = new_rows`. Old references are invalidated.

**Prevention:**
- **Never cache `_rows` references across async boundaries.** Any code that reads `_rows` must re-read it at the point of use, not cache it from an earlier tick.
- **The sync resolver should operate on identity data (branch name, repo name), not on row widget references.** Resolve "which row index matches this branch?" by iterating `_rows` at the moment of cursor movement, not from a pre-computed mapping.

**Phase:** Sync cursor positioning implementation.

**Confidence:** HIGH -- all four panes use `self._rows = new_rows` pattern that replaces the list on rebuild.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Severity | Mitigation |
|-------------|---------------|----------|------------|
| Relationship resolver | CP-1: Sync loop | CRITICAL | Guard flag or prevent() on programmatic cursor moves |
| Relationship resolver | MP-1: Branch ambiguity | MODERATE | Match on (repo_name, branch) pair, never branch alone |
| Relationship resolver | IP-1: Synthetic repo object | MODERATE | Use data model, not rendered rows |
| Live data propagation | CP-2: Concurrent TOML mutation | CRITICAL | Workers discover, main thread mutates, then saves |
| Live data propagation | CP-3: Branch objects mutated | CRITICAL | ALLOWED_AUTO_KINDS whitelist |
| Live data propagation | MP-2: Stale marking model | MODERATE | Add stale field to ObjectItem dataclass |
| Live data propagation | MP-3: Non-atomic ownership transfer | MODERATE | Both mutations in one method, verify both projects exist |
| Worktree ownership transfer | MP-3: Transfer not atomic | MODERATE | Single-method mutation, fallback to keeping object in source |
| Cursor sync | CP-4: Cursor reset on refresh | CRITICAL | Match by identity before/after rebuild |
| Cursor sync | IP-3: set_worktrees for sync | MODERATE | Separate sync_cursor method, don't rebuild DOM |
| Cursor sync | IP-5: Stale _rows references | MODERATE | Resolve at point-of-use, not cached |
| Badge counts | MN-1: Badge flicker | MINOR | Debounce or accept brief inconsistency |
| Worker management | MP-4: Overlapping refresh workers | MODERATE | Add exclusive=True to refresh workers |
| Sync toggle UX | MP-5: Toggle persistence | MODERATE | Ephemeral + visible indicator |
| Deferred callbacks | IP-4: call_after_refresh ordering | MODERATE | Sync cursors immediately, don't defer |
| Auto MR management | MN-2: Stale MR objects | MINOR | Auto-add only, never auto-remove MRs |

---

## Key Findings

1. **The sync loop (CP-1) is the highest-risk pitfall.** Every cross-pane sync system must solve the "A syncs B syncs A" problem. Textual's `prevent()` context manager is purpose-built for this. The existing codebase already has unidirectional message flow (ProjectList -> ProjectDetail); making it bidirectional requires explicit loop prevention.

2. **Concurrent TOML mutation (CP-2) is currently safe by accident.** The single-user, low-frequency mutation pattern in v1.1 means workers rarely overlap. v1.2's automatic mutations (MR auto-add, worktree auto-remove, stale marking) will run concurrently with user actions. The "workers discover, main thread mutates" pattern must be enforced from the first v1.2 phase.

3. **Cursor preservation during DOM rebuilds (CP-4) is a prerequisite for sync.** The current `_cursor = 0` reset on every refresh would trigger sync cascades every 30 seconds. This must be fixed before sync is enabled. The identity-matching pattern already exists in `action_rename_project` and should be generalized.

4. **Sync should move cursors, not rebuild panes.** The biggest integration risk is using the existing `set_worktrees()`/`set_sessions()`/`set_project()` methods for sync updates. These are heavyweight DOM rebuilds. Sync should be a lightweight cursor move on existing rows.

5. **The "branch is king" invariant needs a code-level enforcement mechanism.** A whitelist of auto-manageable PresetKinds (`ALLOWED_AUTO_KINDS`) prevents accidental mutation of user-curated objects.

---

## Sources

- Textual Events and Messages (prevent() context manager): https://textual.textualize.io/guide/events/
- Textual Reactivity (watch methods, prevent): https://textual.textualize.io/guide/reactivity/
- Textual Workers (call_from_thread, exclusive, thread safety): https://textual.textualize.io/guide/workers/
- Textual Worker API (cancel_group, exclusive): https://textual.textualize.io/api/work/
- Textual GitHub Issue #5269 (focus lost with recompose): https://github.com/Textualize/textual/issues/5269
- Textual GitHub Issue #4691 (mount before widget mounted): https://github.com/Textualize/textual/issues/4691
- Textual GitHub PR #954 (focus handling after widget removal): https://github.com/Textualize/textual/pull/954
- Python tomllib docs: https://docs.python.org/3/library/tomllib.html
- Thread-safe file writes in Python: https://superfastpython.com/thread-safe-write-to-file-in-python/
- Atomic file operations (os.replace): https://zetcode.com/python/os-replace/
