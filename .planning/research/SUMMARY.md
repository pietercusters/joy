# Project Research Summary

**Project:** joy v1.2 — Cross-Pane Intelligence
**Domain:** Cross-pane selection sync and live data propagation in a 4-pane Textual TUI
**Researched:** 2026-04-14
**Confidence:** HIGH

## Executive Summary

joy v1.2 extends an existing keyboard-driven Python TUI by adding cross-pane intelligence: selecting an item in any pane highlights related items in the other three panes, and background refresh cycles automatically propagate live data (worktrees, MRs, agent sessions) into project TOML files. The feature set is well-scoped. All required capabilities are available in Textual 8.2.x — no new dependencies are needed. The existing codebase already implements the foundational patterns (message bubbling to App, background workers, call_from_thread) that v1.2 extends.

The recommended architecture introduces three standalone pure-Python modules (resolver.py, sync.py, propagator.py) that sit alongside the existing widget layer. The App acts as mediator: panes post CursorMoved messages upward, the App delegates to SyncController which calls sync_to() downward on target panes. This is the textbook Textual "messages up, data down" pattern and is already proven in the codebase via ProjectHighlighted. Live data propagation follows the same established worker pattern: workers discover data on background threads, main-thread callbacks apply mutations.

The two highest risks are sync loops (pane A syncs pane B syncs pane A infinitely) and concurrent TOML mutations from overlapping automatic writes. Both have clear preventions: a boolean guard flag on SyncController eliminates loops in Textual's single-threaded event loop; the "workers discover, main thread mutates" rule prevents data-loss races. A third prerequisite before sync goes live is cursor preservation across DOM rebuilds — the current codebase resets cursors to row 0 on every refresh, which would trigger a sync cascade every 30 seconds.

## Key Findings

### Recommended Stack

No new packages required. Textual 8.2.x (already installed) provides everything: custom Message subclasses for cross-widget event routing, `@work(thread=True)` + `call_from_thread()` for background refresh, `Binding` for the sync toggle, and `call_after_refresh()` for deferred DOM operations. The full v1.2 dependency footprint remains two packages (textual, tomli_w).

**Core technologies:**
- `textual.message.Message` + bubbling: cross-pane event routing — already proven in joy via ProjectHighlighted
- `@work(thread=True)` + `call_from_thread()`: background data loading and propagation — already established in joy
- `tomli_w`: TOML writes for auto-mutations — already in use
- Pure Python dataclasses: RelationshipIndex, PropagationResult — no framework dependency

**APIs to avoid:** `Signal` (system-level pub/sub, wrong tool for widget coordination), `data_bind` (parent-to-child only), `reactive` on App (triggers unnecessary refresh), `recompose=True` (destroys/rebuilds all children — joy's remove_children + mount pattern is already correct).

### Expected Features

**Must have (table stakes):**
- Selection in one pane highlights related items in the other panes — users of lazygit/k9s/ranger will expect this immediately
- Sync is instant and non-blocking — data is already in memory; no I/O required during cursor movement
- Graceful empty state when no match found — show "no matching worktrees" rather than blank or stale content
- Badge counts on project rows (worktree count, agent count) — prevents needing to look at other panes to assess project state
- Sync toggle must appear in the footer — undiscoverable features are invisible features
- Stale items dimmed, not hidden — sudden disappearance is disorienting; show the transition state

**Should have (differentiators):**
- Bidirectional sync: any pane can drive — lazygit and k9s are unidirectional; this is a genuine differentiator
- "Branch is king" ownership model: worktrees auto-migrate between projects when branches move
- Auto-add MR objects when detected for a project's active branch
- Auto-remove stale worktree objects after they disappear from git worktree list
- Agent stale detection with visual dimming + ghost icon

**Defer to v2+:**
- Persistent sync state across sessions (ephemeral is correct for v1.2)
- Complex relationship graph visualization (the 4-pane grid IS the visualization)
- Real-time file watching on ~/.joy/ TOML files (periodic refresh is sufficient)
- Undo for auto-mutations
- Automatic project creation from discovered worktrees (explicitly dropped, still a bad idea)

**Explicit anti-features for v1.2:**
- Do NOT auto-move cursor in synced panes — highlight/dim related items, leave cursor position to the user
- Do NOT hide non-matching rows — dim to 30% opacity; spatial memory depends on row stability
- Do NOT auto-remove MR objects — auto-add only; MR removal is ambiguous

### Architecture Approach

Three new standalone modules wrap around the existing App/widget layer. The App gains a SyncController instance and orchestration methods; each pane gains a `sync_to(key)` method and posts `CursorMoved` on user cursor moves. All relationship logic and propagation logic lives outside the widget layer and is independently testable without a running TUI.

**Major components:**
1. **resolver.py** — Pure function `build_index()` produces a `RelationshipIndex` (bidirectional dict of ItemKey sets) from current projects + live worktrees + live sessions. Rebuilt on every refresh cycle.
2. **sync.py** — `SyncController` holds sync-enabled flag, current RelationshipIndex, and loop guard (`_syncing` boolean). Handles `CursorMoved` messages from the App and calls `pane.sync_to(target_key)`.
3. **propagator.py** — Pure function `propagate()` diffs live data against project objects and returns a `PropagationResult` (adds, removes, moves, stale marks). App applies mutations on main thread, then saves.
4. **Modified panes** — ProjectList, WorktreePane, TerminalPane each gain `sync_to(key)` (silent cursor move) and post `CursorMoved` from `_update_highlight()`.
5. **`_maybe_run_propagation()` in JoyApp** — Fires only when both `_worktrees_ready` and `_terminals_ready` flags are set, ensuring propagation has complete data before running.

**Key patterns:**
- Data down, messages up (Textual idiom) — enforced throughout
- Rebuild-not-mutate for derived state (RelationshipIndex rebuilt per refresh)
- Ready-flags for multi-source coordination (worktrees + terminals must both arrive before propagation runs)
- Workers discover, main thread mutates (prevents concurrent TOML corruption)

### Critical Pitfalls

1. **Sync loop (CP-1)** — Pane A syncs pane B which triggers sync back to A, CPU spins at 100%. Prevention: boolean `_syncing` guard on SyncController — works because Textual's event loop is single-threaded. Must be solved before any sync code ships.

2. **Concurrent TOML mutation (CP-2)** — Auto-propagation workers overlap with user-action save workers, one overwrites the other's changes with a stale snapshot. Prevention: "workers discover, main thread mutates" rule — workers call `call_from_thread(self._apply_discovered_X)` rather than mutating `_projects` directly. Currently safe by accident in v1.1; v1.2's automatic mutations expose this race.

3. **Cursor reset on refresh (CP-4)** — All panes reset `_cursor = 0` on every DOM rebuild. With sync enabled, every 30-second refresh triggers a sync cascade from row 0. Prevention: match cursor by identity (repo_name + branch for worktrees, session_id for terminals) before and after rebuild. The pattern already exists in `action_rename_project`. This is a prerequisite for sync, not a sync feature.

4. **Branch object mutation during propagation (CP-3)** — Auto-propagation "branch is king" logic might accidentally move or duplicate user-curated branch objects. Prevention: `ALLOWED_AUTO_KINDS = {PresetKind.WORKTREE, PresetKind.MR}` whitelist — the propagator never touches any other kind.

5. **Synthetic repo object in ProjectDetail confuses resolver (IP-1)** — ProjectDetail synthesizes a repo ObjectItem for display that does not exist in `project.objects`. The sync resolver must use the data model, never rendered rows.

## Implications for Roadmap

Based on dependency analysis across all four research files, four phases in strict order:

### Phase 1: Resolver + Cursor Preservation Prerequisites
**Rationale:** Everything else depends on RelationshipIndex. Cursor identity-matching must be fixed before sync is enabled or every auto-refresh triggers cascades. Both are pure-logic changes with no visible UX impact — safe to ship and validate independently.
**Delivers:** `resolver.py` with ItemKey, RelationshipIndex, `build_index()`; cursor identity preservation in WorktreePane and TerminalPane; unit tests for resolver.
**Addresses:** Relationship foundation for all subsequent phases; CP-4 fixed as prerequisite.
**Avoids:** CP-1, CP-4, IP-1.

### Phase 2: Badge Counts
**Rationale:** Badge counts are the first visible proof the RelationshipIndex works correctly — worktree and agent counts on project rows, without requiring any sync logic. Validates the index in production. No data mutations, no risk.
**Delivers:** ProjectRow accepts badge data; `ProjectList.set_badges()`; `_push_badge_counts()` in JoyApp wired after index rebuild.
**Uses:** RelationshipIndex output from Phase 1; existing ProjectRow label rendering.
**Implements:** Badge count display from architecture.
**Avoids:** MN-1 (badge flicker — acceptable for initial ship; debounce can be added later).

### Phase 3: Cross-Pane Cursor Sync + Toggle
**Rationale:** The headline v1.2 feature. Visual-only — no data mutations. Safe to iterate on UX before adding propagation complexity. The sync loop guard (CP-1) must be the first implementation step in this phase.
**Delivers:** `sync.py` with SyncController and CursorMoved message; `sync_to()` on all three panes; `_update_highlight()` modifications; sync toggle (S key) with footer display; visual dimming of non-matching rows.
**Implements:** SyncController, CursorMoved message flow, bidirectional sync.
**Avoids:** CP-1 (guard flag is phase prerequisite), IP-3 (sync calls `sync_to` not `set_worktrees`), IP-4 (sync cursors immediately, not deferred), IP-5 (resolve rows at point-of-use, not cached).

### Phase 4: Live Data Propagation
**Rationale:** Highest complexity, highest risk — mutates user data. Ships last, after the refresh/sync pipeline is proven stable. "Workers discover, main thread mutates" rule (CP-2 prevention) must be the first implementation step.
**Delivers:** `propagator.py` with PropagationResult and `propagate()`; `_maybe_run_propagation()` with ready-flag coordination; auto-add MR objects; auto-remove stale worktree objects; agent stale detection with visual dimming; worktree ownership transfer.
**Implements:** Propagator module, ready-flag coordination, ObjectItem.stale field extension.
**Avoids:** CP-2, CP-3 (ALLOWED_AUTO_KINDS whitelist), MP-2 (stale field on ObjectItem), MP-3 (atomic ownership transfer), MP-4 (exclusive=True on refresh workers), MN-2 (auto-add MR only, never auto-remove).

### Phase Ordering Rationale

- RelationshipIndex is a pure dependency — nothing in v1.2 works without it, so it goes first.
- Cursor preservation is a prerequisite for sync (not a sync feature), so it belongs in Phase 1 even though it modifies existing pane behavior.
- Badge counts come before sync because they validate the index in production without risk, providing early payoff for Phase 1 work.
- Sync ships before propagation because sync is non-destructive. Isolating it lets the team validate the CursorMoved message flow and guard logic before adding propagation complexity.
- Propagation ships last because it mutates user TOML. All prerequisite patterns must be in place before it lands.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (Propagation):** Worktree ownership transfer edge cases; debounce logic for temporarily-unavailable worktrees (2 consecutive missing refreshes before removal); auto-add MR deduplication against manually-added MR objects.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Resolver + Prerequisites):** Pure Python dataclass logic; identity matching pattern already exists in codebase in `action_rename_project`.
- **Phase 2 (Badge Counts):** Straightforward data derivation from RelationshipIndex; no new patterns.
- **Phase 3 (Sync):** Well-documented Textual pattern; lightweight research on `prevent()` vs. boolean guard only if needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new dependencies. All APIs verified against Textual 8.2.x docs and maintainer guidance. Existing codebase already uses all required patterns. |
| Features | MEDIUM | Cross-pane sync patterns synthesized from lazygit/k9s/ranger analysis; no single authoritative TUI spec. Feature list is well-reasoned but not benchmarked against real user workflows. |
| Architecture | HIGH | Three new modules follow existing joy conventions (standalone pure-logic modules). All Textual API interactions verified. Component boundaries are clear and testable. |
| Pitfalls | HIGH | All critical pitfalls derived from actual codebase analysis (direct line citations) plus Textual documentation. Not speculative. |

**Overall confidence:** HIGH

### Gaps to Address

- **MR auto-add deduplication:** How to distinguish auto-added MR objects from user-added ones with the same URL. `auto_managed: bool = False` field on ObjectItem is the likely solution — validate during Phase 4 planning.
- **Worktree temporarily unavailable vs. permanently deleted:** Propagator needs a debounce (2 consecutive missing refreshes before auto-removing). Exact debounce window needs a decision.
- **Sync visual design:** CSS opacity value and color treatment for dimmed non-matching rows — design decision for Phase 3 implementation, not a blocker.
- **iTerm2 session identity stability:** Research assumes `session_name` is stable across refresh cycles. Validate during Phase 3 implementation.

## Sources

### Primary (HIGH confidence)
- Textual Events/Messages guide — message bubbling, `prevent()` context manager, `post_message()`
- Textual Workers guide — `@work(thread=True)`, `call_from_thread()`, `exclusive=True`
- Textual Reactivity guide — `reactive`, `data_bind`, watch methods (consulted to confirm what NOT to use)
- Textual Widget API — `query_one()`, `call_after_refresh()`
- Will McGugan on sibling messaging (Discussion #186) — explicit guidance against direct pane-to-pane calls
- Existing joy codebase — app.py, project_list.py, worktree_pane.py, terminal_pane.py, project_detail.py, models.py, store.py

### Secondary (MEDIUM confidence)
- lazygit panel architecture (freeCodeCamp guide, oliverguenther.de) — unidirectional master-detail pattern
- k9s navigation (k9scli.io, DeepWiki) — drill-down stack, badge count patterns
- ranger Miller columns (ArchWiki) — preview column update on cursor move
- Carbon Design System — badge and disabled/stale state patterns
- VS Code issue #134116 — strikethrough for deleted files pattern

### Tertiary (LOW confidence)
- gitui architecture (DEV community) — multi-panel layout (less documented than lazygit/k9s)
- General TUI dim/opacity patterns (synthesized from multiple sources; no single standard)

---
*Research completed: 2026-04-14*
*Ready for roadmap: yes*
