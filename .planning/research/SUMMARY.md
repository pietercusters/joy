# Research Summary: joy v1.1 Workspace Intelligence

**Project:** joy
**Domain:** Keyboard-driven Python TUI — live workspace dashboard
**Researched:** 2026-04-13
**Confidence:** HIGH (stack + architecture + pitfalls), MEDIUM (iTerm2 async integration, Claude detection)

---

## Executive Summary

joy v1.1 evolves from a static artifact launcher into a live workspace dashboard by adding a 2x2 pane layout, a background data-fetching engine, git worktree discovery, and an iTerm2 terminal session pane. The research is clear on the approach: the existing Textual + TOML stack requires only one new runtime dependency (`iterm2`, made optional), all git and MR/CI operations stay as raw subprocess calls, and Textual's `set_interval` + `@work(thread=True)` pattern handles periodic polling without touching the main thread.

The recommended build order is foundation-first: data models and config schema, then the git discovery module, then the 2x2 layout restructure (with stubs), then the worktree pane, then the refresh engine, then iTerm2 integration, then the terminal pane, and finally settings UI and the project-from-worktree flow. This sequence isolates the two highest-risk items — the layout restructure and the iTerm2 async integration — so each can be validated before the features that depend on them are built.

The principal risks are: (1) the iTerm2 `iterm2.run_until_complete()` vs Textual's event loop conflict (must use `Connection.async_create()` instead — non-negotiable), (2) blocking subprocess calls on the main thread causing UI freeze (must use `@work(thread=True)` + timeouts for every git/CLI call), and (3) refresh-triggered cursor jumps if pane rebuilds use `recompose=True` (must update in-place, preserving cursor by identity). All three have clear prevention patterns and must be designed in from the start.

---

## Stack Additions

### New Dependencies (v1.1 only adds one)

| Package | Version | Role | Notes |
|---------|---------|------|-------|
| `iterm2` | >=2.7 | iTerm2 Python API | Optional dependency — GPLv2+, lazy-import only |

Transitive deps: `protobuf` and `websockets`. Both must be lazy-imported inside the terminal pane's `on_mount()` to avoid 100-250ms startup regression.

**Everything else stays subprocess:**
- `git` via `asyncio.create_subprocess_exec` — worktree list, dirty checks, remote tracking
- `gh` via `asyncio.create_subprocess_exec` — PR status, CI checks (GitHub)
- `glab` via `asyncio.create_subprocess_exec` — MR status, CI pipelines (GitLab)

### Do NOT Add

| Package | Why Not |
|---------|---------|
| `GitPython` | Broken worktree support (issues open since 2017). Raw subprocess is simpler and more reliable. |
| `httpx` / `requests` | `gh` and `glab` CLIs handle auth + pagination. No HTTP library needed. |
| `trio` / `anyio` | Would conflict with Textual's asyncio architecture. |
| `pyperclip` | Rejected in v1.0. macOS `pbcopy` via subprocess is sufficient. |

### pyproject.toml Change

```toml
[project]
dependencies = [
    "tomli-w>=1.0",
    "textual>=8.2",
]

[project.optional-dependencies]
terminal = ["iterm2>=2.7"]
```

Make `iterm2` optional due to GPLv2+ license. Bundle it in the default install but document the option to omit it.

---

## Feature Table Stakes

### Worktree Pane — Must Have

| Feature | Display | Notes |
|---------|---------|-------|
| Branch name | Bold, line 1 | Primary identifier |
| Dirty indicator | `*` or colored dot | "Do I have uncommitted work?" |
| Ahead/behind remote | `↑3 ↓1` arrows | Show only when non-zero |
| Worktree path (abbreviated) | Dimmed, line 2 | Directory name only, not full path |
| No-remote indicator | `(local)` dimmed | Branch not pushed anywhere |

Row format: two-line. Line 1 = branch + status indicators. Line 2 = path + age, dimmed. Hard limit: 2 lines per row.

### Worktree Pane — Differentiators (Phase 4 polish)

- MR/PR status badge (requires `gh`/`glab` CLI integration)
- CI pass/fail/pending indicator (same CLI dependency as MR)
- Last commit age ("2h ago")

### Terminal Pane — Must Have

| Feature | Source | Notes |
|---------|--------|-------|
| Session/window name | `session.name` | Primary identity |
| Foreground process | `session.jobName` | What is running right now |
| Working directory | `session.path` | Requires iTerm2 shell integration |
| Enter to focus | `session.async_activate()` | The whole point of the pane |

### Terminal Pane — Differentiator

- Claude agent detection: `commandLine` contains "claude" — show busy/waiting indicator
- Sticky state: maintain "Claude was foreground" for 5s to avoid flicker during tool use

### Repo Registry — Must Have

- Add/remove repos in settings modal
- Fields: local path + optional remote URL
- Auto-deduce remote from `git remote get-url origin`
- Auto-detect forge type (github.com vs gitlab.com in URL)
- Validate path exists on save

### What to Defer to v1.2+

- Interactive worktree creation/deletion from joy
- Terminal session creation from joy
- Worktree-to-terminal-session linking
- CI/MR status if CLI orchestration proves complex
- Auto-discovery of repos on disk (slow, finds unwanted repos)

### Anti-Features

- Auto-fetching from remote (triggers auth prompts, network ops, side effects)
- Showing all git branches (only worktrees — joy is not a branch manager)
- More than 3-4 status indicators per row (visual noise)
- Full filesystem paths (use abbreviated forms)
- Modal for status info (status is inline; modals are for mutations only)

---

## Architecture Decisions

### Layout: CSS Grid (not nested Horizontal/Vertical)

Replace `Horizontal(ProjectList, ProjectDetail)` with a `Container` using `layout: grid; grid-size: 2 2`:

```
grid-columns: 1fr 2fr   (preserves existing left/right ratio)
grid-rows: 2fr 1fr      (top row is primary, bottom is glanceable)
grid-gutter: 1          (visual separator)
```

Compose order: ProjectList (top-left), ProjectDetail (top-right), TerminalPane (bottom-left), WorktreePane (bottom-right).

**This must be one atomic change.** Do it with stub panes before any real content, because it touches DOM structure and invalidates existing CSS selectors.

### Background Polling: set_timer (not set_interval) + @work(thread=True)

Use `set_timer` (single-fire) at the **end** of each refresh cycle, not `set_interval` (fixed-schedule). This prevents timer stacking when a refresh takes longer than the interval.

```
App.on_mount()
  └─ _schedule_next_refresh()           set_timer(30s)
       └─ _do_refresh()                 @work(thread=True, exclusive=True)
            ├─ discover_worktrees()     subprocess.run per registered repo
            │   └─ call_from_thread()  → WorktreePane.set_worktrees()
            ├─ query_iterm2_sessions()  @work(async) via iTerm2 Python API
            │   └─ direct UI update   → TerminalPane.set_sessions()
            └─ _schedule_next_refresh() reschedule for next cycle
```

Key rules:
- `@work(exclusive=True)` on all refresh workers — cancels previous if still running
- `asyncio.Semaphore(4)` to cap concurrent subprocess calls
- Mandatory `timeout=10` on every subprocess call
- `call_from_thread()` to push results from thread worker to UI
- For async (iTerm2) worker: direct UI update is safe (already on main thread)

### iTerm2 Integration: async_create() Only

Never use `iterm2.run_until_complete()` inside Textual — it creates a second event loop and crashes. Use `iterm2.Connection.async_create()` which attaches to the running loop.

Connection lifecycle:
1. `on_mount()` fires `_connect_iterm2()` (async worker, fire-and-forget)
2. Each refresh cycle: if connection exists, query; if query fails, set to None
3. Next refresh after failure: re-attempt connection with exponential backoff
4. `iterm2` import is lazy — inside `on_mount()` of TerminalPane only

### Data Flow: Direct Widget Method Calls (consistent with v1.0)

Background workers push data to panes via explicit method calls (`set_worktrees()`, `set_sessions()`), not reactive attributes with `recompose=True`. This matches v1.0's `ProjectList.set_projects()` pattern.

Panes update in-place: save cursor position (by branch name / session ID), clear+rebuild children, restore cursor. Never reset to position #1.

### New Modules

| File | Responsibility |
|------|---------------|
| `src/joy/workspace.py` | Git discovery: worktree list, dirty checks, remote tracking — all blocking subprocess |
| `src/joy/terminal.py` | iTerm2 bridge: connection management, session querying, Claude detection |
| `src/joy/widgets/worktree_pane.py` | WorktreePane widget + WorktreeRow (two-line display) |
| `src/joy/widgets/terminal_pane.py` | TerminalPane widget + TerminalRow (one-line display) |

Modified: `app.py` (layout + refresh engine), `models.py` (RepoConfig, WorktreeInfo, SessionInfo, Config extensions), `store.py` (repos array-of-tables), `screens/settings.py` (repo registry UI).

### Config Schema Addition

```toml
refresh_interval = 30   # seconds, new field in [config] section

[[repos]]
name = "joy"
local_path = "/Users/pieter/Github/joy"
remote_url = "https://github.com/pietercusters/joy"
branch_filter = ""
```

No new files. Repos stored in `~/.joy/config.toml` as TOML array-of-tables. Worktree and session data is in-memory only (ephemeral, cheap to re-derive).

---

## Critical Pitfalls

Ordered by consequence severity.

### 1. IT-1 (CRITICAL): Wrong iTerm2 Event Loop Usage

Never call `iterm2.run_until_complete()` inside Textual — instant `RuntimeError: This event loop is already running`. Use `await iterm2.Connection.async_create()` in an async worker. Prototype this integration before writing any terminal pane UI.

### 2. BP-1 (CRITICAL): Subprocess Calls on Main Thread

`subprocess.run()` on the main thread freezes the TUI. 10 repos x 500ms = 5s UI freeze every 30s. All git and CLI calls must use `@work(thread=True)` with `asyncio.Semaphore(4)` to cap concurrency, and `timeout=10` on every call.

### 3. TL-1 (CRITICAL): Layout Restructure Breaks Existing Code

Changing from `Horizontal(A, B)` to a 2x2 grid changes the DOM and invalidates CSS selectors and `query_one()` calls. Must be done as one atomic change with stub panes, running the full test suite immediately after.

### 4. BP-6 (HIGH): Cursor Reset on Background Refresh

Using `recompose=True` or rebuilding from scratch resets cursor to row #1 every 30 seconds. Preserve cursor position by identity (branch name, session ID), not by index. Build this into the first refresh implementation — retrofitting is harder.

### 5. BP-5 (HIGH): Refresh Timer Stacking

`set_interval(30)` fires on schedule regardless of how long the previous refresh took. Use `set_timer(30)` at the end of each cycle instead. Pair with `@work(exclusive=True)` as a belt-and-suspenders guard.

### 6. IT-3 (HIGH): iterm2 License Conflict

The `iterm2` package is GPLv2+. Make it an optional dependency. Use `try: import iterm2` with a graceful AppleScript fallback for basic session listing. Document the optional install.

### 7. WD-1 + WD-2 (HIGH): Porcelain Parsing Edge Cases

`git worktree list --porcelain` output has three shapes: normal, bare (no HEAD/branch), detached (no branch). A parser that assumes `branch` is always present will crash on bare repos and detached HEADs. Handle all three shapes from the first line of parsing code.

**Additional pitfalls to keep in mind:**
- BP-4: No `shell=True` in subprocess, always set `GIT_SSH_COMMAND="ssh -o BatchMode=yes"` to prevent SSH prompts hanging workers
- BP-2: GitHub API rate limiting — poll active repo at 30s, others at 5-minute intervals
- BP-3: `gh`/`glab` may not be installed or authenticated — probe with `shutil.which()` on startup, fail gracefully
- IT-4: iTerm2 async exceptions are silently swallowed — wrap every API call in try/except
- CD-1: Claude runs as `node`, not `claude` — use `commandLine` not `jobName` for detection

---

## Build Order

Dependencies flow strictly from top to bottom. No phase should start before the one above it ships.

### Phase 1: Models + Config + Store

**Rationale:** Everything depends on `RepoConfig`, `WorktreeInfo`, `SessionInfo`, and the extended `Config`. Zero UI risk. Fully testable in isolation.
**Delivers:** TOML round-trip for `[[repos]]` array-of-tables, `refresh_interval` config field, all data model dataclasses.
**Avoids:** Retrofitting models into half-built panes.
**Research flag:** Standard patterns — skip research phase.

### Phase 2: workspace.py — Git Worktree Discovery

**Rationale:** Pure data-fetching logic with no Textual dependency. Easiest to test with mocked subprocess. Unblocks WorktreePane entirely.
**Delivers:** `discover_worktrees()`, `_check_dirty()`, `_check_remote_tracking()`, `_parse_worktree_porcelain()` — all with proper edge case handling (bare, detached, locked, unreachable paths).
**Avoids:** WD-1, WD-2, WD-3, WD-5 (porcelain edge cases built in from day one).
**Research flag:** Standard patterns — skip research phase.

### Phase 3: 2x2 Layout Restructure (Structural — Highest Risk)

**Rationale:** Changes the DOM and CSS foundations. Must happen before new panes are built, with stub widgets, so regressions in existing ProjectList/ProjectDetail behavior surface early.
**Delivers:** 2x2 CSS grid with stub TerminalPane ("Terminal — coming soon") and stub WorktreePane ("Worktrees — coming soon"). All existing functionality unchanged. Focus cycling across 4 panes working.
**Avoids:** TL-1 (atomic change), TL-2 (focus model designed upfront), TL-4 (binding ownership documented).
**Research flag:** Standard patterns — skip research phase.

### Phase 4: WorktreePane

**Rationale:** Simpler than TerminalPane (no async API, no external connection). Establishes widget patterns (two-line row, in-place updates, cursor preservation) that TerminalPane will follow.
**Delivers:** WorktreePane with branch/dirty/path display, j/k navigation, Enter to open in IDE. WorktreeRow with two-line format.
**Avoids:** BP-6 (cursor preservation by branch name from the start).
**Research flag:** Standard patterns — skip research phase.

### Phase 5: Background Refresh Engine

**Rationale:** Needs WorktreePane to exist so refresh results have somewhere to go. Establishes the polling pattern that both panes share.
**Delivers:** `set_timer`-based refresh loop, `@work(thread=True, exclusive=True)` dispatch, `r` keybinding, last-updated indicator, timer pause/resume around modals.
**Avoids:** BP-1 (thread workers), BP-4 (timeouts + no shell=True), BP-5 (set_timer not set_interval), BP-2 (tiered poll cadence for gh/glab).
**Research flag:** Standard patterns — skip research phase.

### Phase 6: iTerm2 Integration (terminal.py)

**Rationale:** Highest-risk component. Build in isolation before TerminalPane UI so the async integration is validated on its own. The stub TerminalPane from Phase 3 shows "Connecting..." while this is being developed.
**Delivers:** `Connection.async_create()` wired into app, session enumeration, Claude detection via `commandLine`, graceful degradation when iTerm2 not running or API disabled, exponential backoff reconnection.
**Avoids:** IT-1 (async_create only), IT-2 (graceful degradation), IT-3 (optional dependency), IT-4 (try/except on every API call), IT-6 (lazy import), IT-7 (handle None for shell integration vars), CD-1 (commandLine not jobName).
**Research flag:** NEEDS PROTOTYPING — `Connection.async_create()` is documented for REPL use but not officially validated inside Textual's event loop. Prototype before building the pane.

### Phase 7: TerminalPane

**Rationale:** Depends on Phase 6 (data source) and Phase 5 (refresh wiring). Cannot be meaningfully built without both.
**Delivers:** TerminalPane with session name/process/directory display, Enter to focus session (`session.async_activate()`), Claude busy/waiting indicator, connection status dot.
**Avoids:** IT-5 (re-fetch app object before each enumeration), CD-2 (screen content read only for selected session), CD-3 (combine signals, no screen-content-only matching).
**Research flag:** Claude "busy vs waiting" detection needs empirical prototyping — the commandLine heuristic must be validated against real Claude Code sessions.

### Phase 8: Settings + Repo Registry + Project Grouping

**Rationale:** Polish and integration features that depend on everything working. Lowest implementation risk, highest dependency count.
**Delivers:** Repo registry UI in settings modal (add/edit/remove), refresh interval setting, project list grouping by repo with "Other" bucket, "New project from worktree" modal enhancement.
**Avoids:** WD-4 (deduplicate repos via git-common-dir in registry), MP-1/MP-3 (auth probe on startup per platform).
**Research flag:** Standard patterns — skip research phase.

### Phase Ordering Rationale

- Phases 1-2 are pure logic with no UI dependencies — fast to build, easy to test, unblock everything downstream.
- Phase 3 is first structural change because it restructures the entire layout foundation; doing it later risks cascading regressions.
- Phase 4 before Phase 5 because the refresh engine needs a real pane to push data to.
- Phase 6 before Phase 7 because the iTerm2 connection must be validated before building the UI that depends on it.
- Phase 8 last because it is polish and depends on all panes existing.

---

## Open Questions

These need prototyping or empirical validation before the phase that uses them can be called "done."

| Question | Phase | How to Validate |
|----------|-------|----------------|
| Does `iterm2.Connection.async_create()` coexist cleanly with Textual's asyncio event loop? | 6 | Write a 50-line spike: Textual app that connects to iTerm2 via async_create and prints session count. Run it. If it works, build the pane. If not, fall back to subprocess + osascript. |
| What does Claude Code's `commandLine` look like in iTerm2? Does it include "claude" reliably? | 7 | Check `session.async_get_variable("commandLine")` while Claude Code is running. Log the raw value. |
| Does `jobName` ever show "claude" rather than "node" for Claude Code? | 7 | Same spike — log both `jobName` and `commandLine` for a running Claude Code session. |
| How long does a full refresh take with 5 registered repos (worktree list + dirty check per worktree)? | 5 | Measure empirically. If >5s, add more aggressive concurrency or skip dirty checks for inactive repos. |
| Does protobuf import cause measurable startup regression? | 6 | `time joy` before and after adding the lazy import. Must stay under 500ms. |
| Does `set_timer` at end of cycle create any UX problem vs `set_interval`? | 5 | Manual test: trigger a slow refresh, verify the next cycle starts 30s after completion, not 30s after start. |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack additions | HIGH | iterm2 package verified on PyPI. async_create() verified in source. Subprocess patterns are stdlib. |
| Features | MEDIUM-HIGH | Pattern research from lazygit, lazyworktree, k9s. iTerm2 variables verified in official docs. Claude detection heuristics are unverified. |
| Architecture | HIGH (layout + refresh), MEDIUM (iTerm2 async) | CSS grid and @work patterns verified in Textual 8.x docs. iTerm2 async_create() is "designed for" but not officially documented as Textual-compatible. |
| Pitfalls | HIGH | Most CRITICAL and HIGH pitfalls verified from primary sources (iTerm2 connection.py source, official git porcelain docs, Python subprocess docs). |

**Overall confidence:** HIGH for the worktree stack. MEDIUM for the terminal/iTerm2 stack — specifically the async integration and Claude detection.

### Gaps to Address

- **iTerm2 async compatibility:** Must prototype `Connection.async_create()` inside a running Textual app before Phase 6 begins. If it fails, fallback is osascript (less data, no `path` variable, no Claude detection) — acceptable MVP but weaker.
- **Claude detection format:** The exact `commandLine` value for a running Claude Code session is unknown until measured. The detection heuristic in Phase 7 must be written empirically.
- **Refresh performance with real repos:** The 30s interval assumes git operations stay fast. Large repos with many worktrees may need dirty-check throttling. Measure in Phase 5 before deciding the final polling model.
- **GitHub rate limit impact:** At 30s intervals with multiple repos, rate limit consumption is calculable but hasn't been tested with real `gh pr list` calls. Phase 5's tiered cadence design must be validated empirically.

---

## Sources

### Primary (HIGH confidence)
- iTerm2 Python API v0.26: https://iterm2.com/python-api/
- iTerm2 connection.py source: https://github.com/gnachman/iTerm2/blob/master/api/library/python/iterm2/iterm2/connection.py
- iTerm2 session variables: https://iterm2.com/documentation-variables.html
- Textual CSS Grid: https://textual.textualize.io/styles/grid/
- Textual Workers: https://textual.textualize.io/guide/workers/
- Textual Timer API: https://textual.textualize.io/api/timer/
- Textual Reactivity: https://textual.textualize.io/guide/reactivity/
- git-worktree --porcelain: https://git-scm.com/docs/git-worktree
- git-status --porcelain: https://git-scm.com/docs/git-status
- gh pr list --json: https://cli.github.com/manual/gh_pr_list
- glab mr list --json: https://docs.gitlab.com/cli/mr/list/
- GitHub rate limits: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- Python asyncio subprocess: https://docs.python.org/3/library/asyncio-subprocess.html
- iterm2 PyPI (GPLv2+, v2.15): https://pypi.org/project/iterm2/

### Secondary (MEDIUM confidence)
- LazyWorktree (UX patterns): https://github.com/chmouel/lazyworktree
- Lazygit branches panel: https://github.com/jesseduffield/lazygit
- k9s configuration (refresh patterns): https://k9scli.io/topics/config/
- GitPython worktree issues (why not to use): https://github.com/gitpython-developers/GitPython/issues/719
- glab auth token issues: https://gitlab.com/gitlab-org/cli/-/issues

---

*Research completed: 2026-04-13*
*Ready for roadmap: yes*
