# Phase 12: iTerm2 Integration & Terminal Pane - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Fill the stub `TerminalPane` with live iTerm2 session data: enumerate all active iTerm2 sessions via the iTerm2 Python API, detect Claude agent sessions (grouped at top), display each session on a single line, and let the user navigate with j/k + Enter to focus any session in iTerm2.

Out of scope: AppleScript window-creation flow for the `agents` object type (already works), repo registry UI (Phase 13), any changes to WorktreePane or MR status (Phase 11), multiple terminal app support.

</domain>

<decisions>
## Implementation Decisions

### API / Data Source
- **D-01:** Use the `iterm2` PyPI package as a **required** (not optional) third dependency alongside `textual` and `tomli_w`. Add to `pyproject.toml` dependencies. Rationale: success criterion 1 requires foreground process name and working directory — AppleScript alone cannot provide this; the Python API is necessary.
- **D-02:** Fetch sessions in a `@work(thread=True)` worker (`_load_terminal()`) using `asyncio.run(main)` in the thread. The iterm2 package's `run_until_complete()` owns a short-lived event loop in the background thread; Textual's main event loop is unaffected.
- **D-03:** When the iTerm2 Python API is inaccessible (iTerm2 not running, Python API not enabled in prefs, connection refused), catch the exception and call `set_sessions(None)` — pane shows a centered muted "iTerm2 unavailable" message. Never crash. Consistent with Phase 7 D-02 silent-skip contract.
- **D-04:** A new `TerminalSession` dataclass in `models.py` (alongside `WorktreeInfo`, `MRInfo`): `session_id: str`, `session_name: str`, `foreground_process: str`, `cwd: str`. Pure data, no iterm2 objects in models.

### Session Row Layout
- **D-05:** Single-line rows. Format: `[icon]  [session_name]  [busy/waiting indicator]  [process]  [cwd]`. Truncated to fit pane width. Diverges from WorktreePane's 2-line rows intentionally — session names are the primary identifier and a single line scans faster for a list of terminal sessions. `height: 1` per row.
- **D-06:** Two groups: **"Claude"** (Claude agent sessions, at top) and **"Other"** (all other sessions, below). GroupHeaders use the same `GroupHeader(Static)` pattern from `project_detail.py`. When a group is empty, its header is omitted (same as Phase 9 D-10 for repos with no worktrees).
- **D-07:** Nerd Font icon constants: `ICON_SESSION` for regular sessions, `ICON_CLAUDE` for Claude sessions. Busy indicator `●` (or suitable Nerd Font glyph), waiting indicator `○`. Add constants alongside existing icon constants in `terminal_pane.py`.

### Claude Detection
- **D-08:** A session is classified as **Claude** if `foreground_process` (the process basename) equals `"claude"` (case-sensitive, exact match). No session-name convention required.
- **D-09:** **Busy vs waiting**: if `foreground_process == "claude"` → busy indicator (Claude CLI actively running). If the foreground process is the shell (`zsh`, `bash`, `fish`) → waiting indicator (Claude not running, session is idle at prompt). This requires iTerm2 shell integration to be installed (foreground process tracking). Document as prerequisite in Phase 13 README.
- **D-10:** Claude sessions that are busy sort before waiting ones within the "Claude" group. Within each sub-group, alphabetical by session name.

### Navigation Model
- **D-11:** Follow the `ProjectDetail` pattern exactly: `_cursor: int`, `_rows: list[SessionRow]`, `--highlight` CSS class. `GroupHeader` rows are NOT in `_rows` (not navigable). BINDINGS on `TerminalPane`: `j`/`down` = cursor down, `k`/`up` = cursor up, `enter` = focus session in iTerm2.
- **D-12:** On Enter: call `session.async_activate()` (or equivalent iterm2 API call to focus the window/tab containing the session) in a `@work(thread=True)` worker with `asyncio.run()`. Same threading pattern as the fetch worker.
- **D-13:** Escape on `TerminalPane` returns focus to the previous pane in Tab order (Projects pane) — same pattern as `ProjectDetail.action_focus_list()`. Implement as `action_focus_projects()` or generic `action_focus_prev()`.
- **D-14:** When no sessions are available (empty list or API unavailable), `_cursor = -1`, no highlight, j/k/Enter are no-ops.

### Refresh Integration
- **D-15:** `r` key and the background timer both refresh terminal sessions alongside worktrees. Add a parallel `_load_terminal()` `@work(thread=True)` worker. `JoyApp.action_refresh_worktrees()` calls both workers. The interval timer calls both. Independent workers — iTerm2 API failure does not affect worktree refresh.
- **D-16:** `TerminalPane.border_title` follows the Phase 10 stale-indicator pattern: shows last-refresh timestamp; turns warning color if the API is unavailable or last fetch failed. Implementation: push a title string from the app to the pane (same as `set_refresh_label()` in WorktreePane).
- **D-17:** Scroll position preservation on refresh: same pattern as Phase 9 D-09 — save `scroll_y` before `remove_children()`, restore after rebuild.

### Claude's Discretion
- Exact Nerd Font codepoints for `ICON_SESSION`, `ICON_CLAUDE`, busy/waiting glyphs.
- Whether `_load_terminal()` calls `iterm2.run_until_complete()` or uses `asyncio.run()` directly with the iterm2 connection API — choose whatever is cleaner given the iterm2 package's API surface.
- Truncation strategy for long session names / cwd paths (suggest right-truncate session name, abbreviate cwd with `~` prefix like Phase 9 D-13).
- Exact `TerminalSession` field names (e.g., `foreground_process` vs `fg_process`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope
- `.planning/ROADMAP.md` §"Phase 12: iTerm2 Integration & Terminal Pane" — Goal, requirements TERM-01 through TERM-06, success criteria (4 items)
- `.planning/PROJECT.md` — Core value, snappy/minimal constraint, macOS-only platform, 2-dep philosophy (now extended to 3)

### Prior phases this phase extends
- `.planning/phases/08-4-pane-layout/08-CONTEXT.md` — D-08/D-09/D-10 (stub TerminalPane, focusable, no bindings yet → Phase 12 adds bindings), D-11/D-12 (border focus indicator pattern)
- `.planning/phases/09-worktree-pane/09-CONTEXT.md` — D-03 (`set_worktrees()` sole-API pattern → apply as `set_sessions()`), D-06 (VerticalScroll + GroupHeader + Static rows), D-09 (GroupHeader CSS), D-13/D-14 (path abbreviation), D-15/D-16 (empty/unavailable state messages)
- `.planning/phases/10-background-refresh-engine/10-CONTEXT.md` — D-01/D-03 (border_title timestamp + stale warning pattern), D-05 (`r` key app-level binding with priority=True), D-07 (`set_interval` refresh timer), D-09 (scroll position preservation)

### Navigation pattern reference
- `src/joy/widgets/project_detail.py` — `ProjectDetail` class: `_cursor`, `_rows`, `--highlight` CSS, `action_cursor_up/down`, BINDINGS pattern. **Replicate this for TerminalPane.**

### Existing code this phase modifies
- `src/joy/widgets/terminal_pane.py` — Stub widget to be fully implemented (replaces "coming soon" placeholder)
- `src/joy/models.py` — Add `TerminalSession` dataclass
- `src/joy/app.py` — Add `_load_terminal()` worker, extend `action_refresh_worktrees()` to also call `_load_terminal()`, extend timer callback, wire `set_sessions()` via `call_from_thread`

### New module
- `src/joy/terminal_sessions.py` (or similar) — `fetch_sessions() -> list[TerminalSession] | None`. Uses `iterm2` package. Returns `None` on API unavailable. No iterm2 objects leak outside this module.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GroupHeader(Static)` from `src/joy/widgets/project_detail.py:50-61` — identical CSS and behavior; import and reuse directly in `terminal_pane.py`.
- `ProjectDetail._cursor` / `_rows` / `--highlight` / `action_cursor_up/down` pattern — replicate verbatim; see `src/joy/widgets/project_detail.py:103-179`.
- `JoyApp._load_worktrees()` (`src/joy/app.py:111-124`) — `@work(thread=True)` with try/except; `_load_terminal()` follows the same structure.
- `WorktreePane.set_refresh_label(timestamp, stale)` — extend or copy pattern for `TerminalPane.set_refresh_label()`.
- Existing Nerd Font icon constants in `src/joy/widgets/worktree_pane.py` (`ICON_DIRTY`, `ICON_NO_UPSTREAM`, `ICON_BRANCH`) — add terminal icon constants in `terminal_pane.py` following the same `\uXXXX` string constant pattern.
- `operations.py:_open_iterm()` — existing AppleScript for focusing named windows; for Phase 12 the iterm2 Python API's `session.async_activate()` replaces this for session-level focus (not window-name-based).

### Established Patterns
- Pure data in `models.py`, I/O in separate modules — `TerminalSession` in models.py, fetch logic in `terminal_sessions.py`.
- `@work(thread=True, exit_on_error=False)` + `call_from_thread` — no changes to threading model.
- Try/except per-unit silent-skip (Phase 7 D-02 contract) — `fetch_sessions()` returns `None` on any exception, never raises.
- Empty/unavailable state: centered muted `Static` with `content-align: center middle; color: $text-muted; text-style: dim;`.

### Integration Points
- `JoyApp.on_mount()` — add `self._load_terminal()` call alongside existing `_load_worktrees()` (or chain after).
- `JoyApp.action_refresh_worktrees()` — extend to call `self._load_terminal()` as well.
- `JoyApp._refresh_timer` callback — extend to call `self._load_terminal()`.
- `TerminalPane.set_sessions(sessions: list[TerminalSession] | None)` — sole public API; called via `call_from_thread`. `None` triggers unavailable state; empty list triggers empty-state message.

</code_context>

<specifics>
## Specific Ideas

- Navigation follows `ProjectDetail` exactly — user explicitly asked for the same pattern. Reuse that code rather than reimplementing from scratch.
- Single-line rows (not 2-line like WorktreePane) — user preference for terminal session display.
- "Claude" / "Other" group labels — not "Agents" / "Terminals".

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 12-iterm2-integration-terminal-pane*
*Context gathered: 2026-04-13*
