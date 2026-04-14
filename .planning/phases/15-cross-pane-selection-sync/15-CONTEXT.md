# Phase 15: Cross-Pane Selection Sync - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire cursor navigation across all four panes so that moving the cursor in any pane silently updates the cursor in the other panes to the related item. Add a keyboard toggle (`x`) to enable/disable sync. Focus always stays on the pane the user is actively navigating.

Out of scope: data propagation (Phase 16), persistence of toggle state across restarts (SYNC-10, deferred).

</domain>

<decisions>
## Implementation Decisions

### Sync trigger

- **D-01:** Sync fires on every cursor movement (j/k, arrow keys) in all three scrollable panes — the same trigger point that `ProjectList.ProjectHighlighted` already uses. WorktreePane and TerminalPane need new cursor message classes to match this pattern (e.g., `WorktreePane.WorktreeHighlighted`, `TerminalPane.SessionHighlighted`).
- **D-02:** Each new message carries enough identity for the app to call `RelationshipIndex.project_for_worktree()` / `RelationshipIndex.project_for_agent()` and drive the cross-pane updates.

### Sync loop prevention (CP-1)

- **D-03:** App-level boolean guard `_is_syncing: bool = False` must be the first thing implemented. Before any sync handler mutates a pane cursor, it sets `_is_syncing = True`; clears it when done. All cursor-message handlers check this flag at the top and return immediately if it is True. This is the mandatory first implementation step flagged in STATE.md (Research CP-1).

### Sync direction — all 6 pairs

- **D-04:** Project highlighted → WorktreePane cursor moves to first related worktree; TerminalPane cursor moves to first related agent session. (SYNC-01, SYNC-02)
- **D-05:** Worktree highlighted → ProjectList cursor moves to owning project; TerminalPane cursor moves to first related agent session. (SYNC-03, SYNC-04)
- **D-06:** Agent session highlighted → ProjectList cursor moves to owning project; WorktreePane cursor moves to first related worktree. (SYNC-05, SYNC-06)
- **D-07:** "First related" = first item in the pane's current `_rows` display order. No special tie-breaking — display order is already deterministic.
- **D-08:** When no related item exists, the target pane cursor is left unchanged ("keeps current"). Not reset to 0, not moved. (All SYNC-0x "keeps current if no match" clause)

### Focus (SYNC-07)

- **D-09:** Sync operations update `_cursor` directly on the target pane and call `_update_highlight()` — they do NOT call `.focus()`. Focus remains on the pane the user is navigating. (SYNC-07)

### Pane cursor mutation API

- **D-10:** Each pane exposes a `sync_to(identity)` method (or equivalent name) that the app calls to move that pane's cursor without triggering a new cursor message. This avoids the sync loop without relying solely on the guard flag — the method simply does not post a message. Complements D-03.

### Toggle (SYNC-08, SYNC-09)

- **D-11:** Key binding: `x` — unused in current BINDINGS (`q/O/n/s/r/l`). Mnemonic: "x = cross-pane".
- **D-12:** Default state: **ON**. Sync is active from first launch. Footer shows the toggle state so users can see it immediately and disable with `x` if distracting.
- **D-13:** Footer display: Textual's `BINDINGS` auto-renders in the Footer widget. The binding label updates to reflect state, e.g. `x Sync: on` / `x Sync: off`. Use a reactive `_sync_enabled: reactive[bool] = reactive(True)` with a `watch__sync_enabled` to update the binding description dynamically, or toggle two binding entries.
- **D-14:** Toggle state is ephemeral — not persisted to disk. SYNC-10 (persistence) is deferred to v1.3+.

### Claude's Discretion

- Exact method names for pane cursor mutations (`sync_to`, `set_cursor_by_identity`, etc.)
- Whether footer toggle label uses reactive binding description or CSS visibility trick
- Internal structure of new message classes
- Whether `_is_syncing` guard and `sync_to()` no-message-method are both used, or just one

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Sync — SYNC-01 through SYNC-09: full sync direction matrix and toggle spec

### Roadmap
- `.planning/ROADMAP.md` §Phase 15 — Phase goal, success criteria

### Prior phase context
- `.planning/phases/14-relationship-foundation-badges/14-CONTEXT.md` — RelationshipIndex API, cursor pattern decisions (D-12 through D-14), integration points

### No external specs
No external ADRs or design docs — requirements fully captured in decisions above and REQUIREMENTS.md.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/joy/resolver.py` `RelationshipIndex` — the 4 query methods Phase 15 calls:
  - `.worktrees_for(project)` → list of WorktreeInfo (for project → worktree sync)
  - `.agents_for(project)` → list of TerminalSession (for project → terminal sync)
  - `.project_for_worktree(wt)` → Project | None (for worktree → project sync)
  - `.project_for_agent(session_name)` → Project | None (for terminal → project sync)
- `src/joy/app.py` `self._rel_index` — already stored, updated after each refresh cycle via `_maybe_compute_relationships()`
- `src/joy/widgets/project_list.py` `ProjectList.ProjectHighlighted` — the existing message pattern to replicate in WorktreePane and TerminalPane
- `src/joy/widgets/project_list.py` `_update_highlight()` — the cursor paint method; call this after mutating `_cursor` in any sync operation

### Established Patterns
- Cursor pattern: `_cursor: int` + `_rows: list[...]` + `_update_highlight()` — identical in all 4 panes; Phase 15 extends it with a `sync_to()` no-message variant
- Message classes: inner classes on their widget (e.g., `ProjectList.ProjectHighlighted`); carry the relevant data object
- `on_project_list_project_highlighted` in `app.py` — existing handler that fires on every ProjectList cursor move; Phase 15 adds analogous handlers for WorktreePane and TerminalPane messages

### Integration Points
- `src/joy/app.py` — add `_is_syncing` guard, `_sync_enabled` reactive, new `on_*_highlighted` handlers for WorktreePane and TerminalPane, extend `on_project_list_project_highlighted` to drive worktree/terminal sync
- `src/joy/widgets/worktree_pane.py` — add `WorktreePane.WorktreeHighlighted` message class, post it from `action_cursor_up/down`, add `sync_to(identity)` method
- `src/joy/widgets/terminal_pane.py` — add `TerminalPane.SessionHighlighted` message class, post it from `action_cursor_up/down`, add `sync_to(identity)` method
- `src/joy/widgets/project_list.py` — add `sync_to(project_name)` method that moves `_cursor` to the matching project row without posting a message
- `src/joy/app.py` BINDINGS — add `("x", "toggle_sync", "Sync: on")` with dynamic label update on toggle

</code_context>

<specifics>
## Specific Ideas

- "Every cursor move (j/k fires sync immediately)" — same trigger pattern as the existing ProjectList→Detail sync, confirmed by user
- Default sync ON — feature is visible from first launch; user presses `x` to disable if distracting
- `x` key for toggle — cross-pane mnemonic, unused in current bindings

</specifics>

<deferred>
## Deferred Ideas

- **SYNC-10**: Toggle state persists across restarts — explicitly deferred to v1.3+ (already in REQUIREMENTS.md Future section)
- **PERF-01**: Real-time file watching — 30s refresh sufficient for v1.2

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 15-cross-pane-selection-sync*
*Context gathered: 2026-04-14*
