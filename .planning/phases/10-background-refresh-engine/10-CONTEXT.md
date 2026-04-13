# Phase 10: Background Refresh Engine - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a polling timer to `JoyApp` that periodically re-runs `_load_worktrees()` in a background thread at the configured interval (`Config.refresh_interval`, default 30s). Wire up `r` as an app-level force-refresh keybinding that works from any pane. Display a last-refresh timestamp in the `WorktreePane` border_title at all times. Signal stale data visually when the last refresh is older than expected (refresh failed or timer drifted). Preserve the `_WorktreeScroll` vertical position across every rebuild.

Out of scope: MR/CI status on rows (Phase 11), terminal pane content (Phase 12), repo registry UI (Phase 13). The worktree list content itself is unchanged — this phase is infrastructure around how and when it refreshes.

</domain>

<decisions>
## Implementation Decisions

### Timestamp Display
- **D-01:** Last-refresh time shown as a suffix in `WorktreePane.border_title` — e.g., `"Worktrees  2m ago"`. Always visible regardless of which pane has focus. Zero extra DOM nodes. Fits the minimalist aesthetic.
- **D-02:** Timestamp format is Claude's discretion — either absolute time (`"14:32"`) or relative (`"2m ago"`). Relative is more glanceable; absolute is more precise. Prefer relative with a 1-second heartbeat timer to keep it live; fall back to absolute if a heartbeat timer creates visible jitter.

### Stale Data Signaling
- **D-03:** When data is stale (age > 2× `Config.refresh_interval`, OR the refresh worker raised an exception), the border_title timestamp gains a warning icon and turns yellow/orange — e.g., `"Worktrees  ⚠ 2m ago"`. Color rendered via a Rich `Text` or Textual markup string on `border_title`.
- **D-04:** Stale threshold: `age > 2 × refresh_interval`. At the default 30s interval this trips after 60s of failed/missed refreshes. Implementation: track `_last_refresh_at: datetime | None` and `_refresh_failed: bool` on `JoyApp`; pane reads neither — the app pushes the formatted title string to the pane.

### Manual Refresh
- **D-05:** `r` is an app-level binding with `priority=True` so it fires from any focused pane (projects, detail, terminal, worktrees). It calls the same `_load_worktrees()` worker that the timer uses.
- **D-06:** No visual feedback beyond the timestamp updating when the refresh completes — silent. The border_title change is the confirmation that the keystroke worked.

### Timer & Worker
- **D-07:** Use Textual's `self.set_interval(self._config.refresh_interval, self._trigger_worktree_refresh)` in `JoyApp.on_mount()`. The interval callback calls `self._load_worktrees()` (the same `@work(thread=True)` worker already used for the initial load). No new thread management.
- **D-08:** If a refresh is already in progress when the timer fires or `r` is pressed, Textual's `@work` creates a new worker — this is acceptable for a 30s interval. If deduplication becomes important (very short intervals), wrap in a guard flag; defer that complexity unless needed.

### Scroll Preservation
- **D-09:** Before `scroll.remove_children()` in `WorktreePane.set_worktrees()`, save `scroll.scroll_y`. After `call_after_refresh`, restore with `scroll.scroll_to(y=saved_y, animate=False)`. This keeps the user's scroll position stable across every periodic rebuild (REFR-05).

### Claude's Discretion
- Exact Rich markup string for stale vs. normal border_title (color constant, icon glyph — keep consistent with existing Nerd Font vocabulary).
- Whether to use a separate 1-second `set_interval` for the live countdown display, or only update the border_title on each 30s refresh tick. A 1-second tick keeps relative timestamps live; skip it if it causes visible noise.
- Whether to expose `border_title` updates via a method on `WorktreePane` (e.g., `set_refresh_label(text: str, stale: bool)`) or push a formatted string directly from `JoyApp._set_worktrees`. Keep it simple — whichever requires fewer lines.
- `r` binding label in Footer: "Refresh" or "Refresh data" (max ~12 chars visible).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope
- `.planning/ROADMAP.md` §"Phase 10: Background Refresh Engine" — Goal, requirements REFR-01 through REFR-05, success criteria
- `.planning/PROJECT.md` — Core value, v1.1 milestone context, snappy/minimal constraint

### Prior phases this phase extends
- `.planning/phases/09-worktree-pane/09-CONTEXT.md` — D-03 (set_worktrees is the only timer entry point), D-07 (single Static per row for cheap rebuilds), D-14 (resize-responsiveness is Phase 10's concern), D-17 (stale-data indicator responsibility lands here)
- `.planning/phases/07-git-worktree-discovery/07-CONTEXT.md` — D-02 (silent skip on errors — Phase 10 detects failure at the @work layer, not via discover_worktrees return value)

### Existing code this phase modifies
- `src/joy/app.py` — `JoyApp.on_mount()` (timer setup), `_load_worktrees()` worker (already exists — Phase 10 adds timer + `r` binding), `_set_worktrees()` (push timestamp + stale flag to pane)
- `src/joy/widgets/worktree_pane.py` — `WorktreePane.set_worktrees()` (add scroll preservation D-09), `border_title` update mechanism (D-01, D-03)
- `src/joy/models.py` — `Config.refresh_interval: int = 30` (already present from Phase 6 — no new fields expected)

### Testing baseline (regression)
- Full test suite (188+ tests) must remain green
- `tests/test_worktrees.py` — 16 Phase 7 tests must stay green
- Any app-level Textual tests — must pass with the new timer and `r` binding

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `JoyApp._load_worktrees()` (`src/joy/app.py`) — `@work(thread=True)` worker already implemented; Phase 10 wraps it with a timer and `r` binding, no new worker logic.
- `JoyApp._set_worktrees()` (`src/joy/app.py`) — already calls `WorktreePane.set_worktrees()`; extend to also update the border_title timestamp and stale flag.
- `WorktreePane.set_worktrees()` (`src/joy/widgets/worktree_pane.py`) — existing idempotent rebuild method; add scroll-save/restore around `remove_children()`.
- `Config.refresh_interval: int = 30` (`src/joy/models.py:99`) — timer interval already stored in config.
- `self.set_interval(seconds, callback)` — Textual built-in timer API; returns a handle that can be cancelled if needed.

### Established Patterns
- `@work(thread=True)` + `call_from_thread` — proven pattern for non-blocking background data load (used by `_load_data`, `_load_worktrees`, `_save_projects_bg`).
- App-level `BINDINGS` with `priority=True` — used by `shift+o` / `O` for `open_all_defaults`; same pattern applies to `r`.
- Inline CSS in `DEFAULT_CSS` class attribute — no external `.tcss` files.
- `border_title` attribute on `Widget` — already used by `WorktreePane` (`self.border_title = "Worktrees"`); update it to append timestamp suffix.

### Integration Points
- `JoyApp.on_mount()` — add `self.set_interval(self._config.refresh_interval, self._trigger_worktree_refresh)` after the initial `_load_data()` call.
- `JoyApp.BINDINGS` — add `Binding("r", "refresh_worktrees", "Refresh", priority=True)`.
- `JoyApp._set_worktrees()` — extend to call a timestamp-update helper after setting worktrees on the pane.
- `WorktreePane.set_worktrees()` — wrap the `scroll.remove_children()` / `scroll.mount(...)` block with scroll-position save and restore.
- `WorktreePane.border_title` — update on every refresh completion (and every second if a live countdown is implemented).

</code_context>

<specifics>
## Specific Ideas

- The ⚠ warning icon in the stale border_title matches the visual vocabulary the user accepted in Phase 9 for dirty/no-upstream indicators — use Nerd Font glyphs consistent with existing icon constants.
- "Silent" feedback on `r` press was explicitly chosen — do NOT add a notify() toast for manual refresh; the timestamp update is the confirmation.
- Border_title approach mirrors how lazygit/k9s show status in pane headers — already cited as the aesthetic reference in Phase 8/9.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-background-refresh-engine*
*Context gathered: 2026-04-13*
