# Phase 14: Relationship Foundation & Badges - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the cross-pane relationship resolver, add badge counts (active worktrees + agent sessions) to project rows, and fix cursor preservation in WorktreePane and TerminalPane so DOM rebuilds triggered by background refresh no longer jump the cursor to row 0.

New capabilities (sync, propagation) are out of scope — those belong in Phases 15 and 16.

</domain>

<decisions>
## Implementation Decisions

### Resolver module

- **D-01:** New standalone module `src/joy/resolver.py` — pure functions only (no I/O, no side effects). Easily testable and importable by Phases 15/16 without coupling to app.py internals.
- **D-02:** Entry point: `compute_relationships(projects, worktrees, sessions, repos) -> RelationshipIndex`
- **D-03:** `RelationshipIndex` is a dataclass with four query methods:
  - `.worktrees_for(project: Project) -> list[WorktreeInfo]`
  - `.agents_for(project: Project) -> list[TerminalSession]`
  - `.project_for_worktree(wt: WorktreeInfo) -> Project | None`
  - `.project_for_agent(session_name: str) -> Project | None`
- **D-04:** Matching logic (from REQUIREMENTS.md FOUND-01/02 and prior milestone decisions):
  - Project ↔ Worktree: project has a WORKTREE object whose value matches `wt.path` (path match), OR project has a BRANCH object whose value matches `wt.branch` AND `project.repo == wt.repo_name` (branch match). Path-based match takes precedence when both apply.
  - Project ↔ Agent: project has an AGENTS object whose value matches `session.session_name` (exact string match).
- **D-05:** Projects with no `repo` field are excluded from worktree matching (branch-based path excluded; path-based match still applies if worktree path appears as an object value).
- **D-06:** `RelationshipIndex` is stored on `JoyApp` as `self._rel_index: RelationshipIndex | None = None`.

### Refresh coordination

- **D-07:** The resolver is computed after **both** worktrees and sessions have loaded for the current refresh cycle. App tracks two flags: `_worktrees_ready: bool` and `_sessions_ready: bool`. `_maybe_compute_relationships()` runs only when both are True, then resets both flags.
- **D-08:** `_maybe_compute_relationships()` calls `compute_relationships(...)`, stores the result on `self._rel_index`, and then calls `_update_badges()` to push counts to ProjectList.

### Badge appearance

- **D-09:** Badge counts are displayed on each `ProjectRow` using Nerd Font icons + numbers, appended after the project name. Reuse existing icon constants: `ICON_BRANCH` (`\ue0a0`) for worktree count, `ICON_CLAUDE` (`\U000f1325`) for agent count.
- **D-10:** Both counts are always shown, even when zero. Consistent row width — no layout shifting as items appear/disappear.
- **D-11:** `ProjectRow` receives counts via a `set_counts(wt_count: int, agent_count: int)` method (or counts passed at construction). `_update_badges()` in app iterates all rows and calls this after the RelationshipIndex is computed.

### Cursor preservation

- **D-12:** Both `WorktreePane` and `TerminalPane` must preserve the cursor across DOM rebuilds triggered by refresh.
  - `WorktreePane`: cursor identity = `(repo_name, branch)` tuple (both stored on `WorktreeRow`).
  - `TerminalPane`: cursor identity = `session_name` (currently `SessionRow` stores `session_id` only — add `session_name` field to `SessionRow`).
- **D-13:** Before calling `remove_children()`, each pane saves the current identity. After rebuilding `new_rows`, it searches for the identity and sets `self._cursor` to that index.
- **D-14:** Fallback when the item is gone: clamp cursor to `min(saved_index, len(new_rows) - 1)`. Same pattern as ProjectList project deletion (D-13 in Phase 5 context). Never reset to 0 unless the list was previously empty.

### Claude's Discretion
- Internal data structure of `RelationshipIndex` (dicts, sets, etc.) — implementation detail
- Whether `_maybe_compute_relationships` uses flags, counters, or asyncio.gather — implementation detail
- Exact spacing/padding of badge counts in ProjectRow content string

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Foundation — FOUND-01 through FOUND-04: relationship resolver spec, cursor preservation spec
- `.planning/REQUIREMENTS.md` §Badge — BADGE-01 through BADGE-03: badge count requirements

### Roadmap
- `.planning/ROADMAP.md` §Phase 14 — Phase goal, success criteria, plan structure

### No external specs
No external ADRs or design docs — requirements are fully captured in decisions above and REQUIREMENTS.md.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/joy/widgets/worktree_pane.py` `ICON_BRANCH` (`\ue0a0`) — reuse as worktree badge icon
- `src/joy/widgets/terminal_pane.py` `ICON_CLAUDE` (`\U000f1325`) — reuse as agent badge icon
- `src/joy/models.py` `PresetKind` enum — `WORKTREE`, `ITERM`, `BRANCH` values used in resolver matching logic
- `src/joy/models.py` `WorktreeInfo` — has `repo_name`, `branch`, `path` (all three fields needed for matching)
- `src/joy/models.py` `TerminalSession` — has `session_name` (matching key for agent resolver)
- `src/joy/models.py` `Project` — has `repo: str | None` and `objects: list[ObjectItem]`
- `src/joy/models.py` `ObjectItem` — has `kind: PresetKind` and `value: str`

### Established Patterns
- Cursor management: all four panes use `_cursor: int` + `_rows: list[...]` + `_update_highlight()` pattern
- DOM rebuild: panes call `scroll.remove_children()`, mount new rows, then restore scroll position via `saved_scroll_y`
- Background loading: `@work(thread=True)` workers call `self.app.call_from_thread(callback)` to push data to the UI thread
- Pure data modules: `worktrees.py`, `terminal_sessions.py`, `mr_status.py` all follow the pure-function-module pattern that `resolver.py` should follow

### Integration Points
- `src/joy/app.py` `_set_worktrees` and `_set_terminal_sessions` — both need to set ready flags and call `_maybe_compute_relationships()`
- `src/joy/widgets/project_list.py` `ProjectRow` — needs `set_counts()` method or counts at construction
- `src/joy/widgets/project_list.py` `ProjectList` — needs `update_badges(index: RelationshipIndex)` method that iterates rows
- `src/joy/widgets/worktree_pane.py` `WorktreePane.set_worktrees()` — save/restore cursor identity by `(repo_name, branch)`
- `src/joy/widgets/terminal_pane.py` `TerminalPane.set_sessions()` — save/restore cursor identity by `session_name`; add `session_name` field to `SessionRow`

</code_context>

<specifics>
## Specific Ideas

No specific references — open to standard approaches within the decisions above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 14-relationship-foundation-badges*
*Context gathered: 2026-04-14*
