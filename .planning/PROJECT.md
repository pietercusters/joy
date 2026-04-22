# joy

## What This Is

`joy` is a keyboard-driven Python TUI for managing coding project artifacts. It gives developers a real-time workspace dashboard — all objects related to a project (branches, MRs, tickets, worktrees, notes, agents, and more) visible at a glance, plus live git worktree status, MR/CI badges, active iTerm2 sessions, and cross-pane intelligence that links worktrees and terminals to their project. Any artifact is openable with a single keystroke. Installable globally via `uv tool install git+<repo>`, configured per-machine in `~/.joy`.

v1.0 delivered the core artifact launcher. v1.1 transformed it into a live workspace dashboard with real-time git, MR/CI, and terminal state. v1.2 added cross-pane relationship intelligence (badge counts, bidirectional sync, auto-propagation). v1.3 unified the detail view and established a consistent per-kind keystroke dispatch table.

## Core Value

Every artifact for the active project, openable instantly from one keyboard-driven interface — no hunting through tabs, terminals, or bookmarks.

## Requirements

### Validated

- ✓ App shows a two-pane layout: project list (left) + project detail (right) — v1.0
- ✓ Keyboard navigation throughout (j/k + arrows, Escape, Enter) — v1.0
- ✓ Context-sensitive footer with key hints that update on focus change — v1.0
- ✓ Pressing Escape always navigates back; no focus traps — v1.0
- ✓ Status bar shows immediate feedback after every action — v1.0
- ✓ Nerd Font icons per object type for fast visual scanning — v1.0
- ✓ First project auto-selected on startup — v1.0
- ✓ `string` type copies to clipboard (pbcopy) — v1.0
- ✓ `url` type opens in browser; Notion/Slack URLs open desktop apps — v1.0
- ✓ `obsidian` type opens in configured vault via `obsidian://` URI — v1.0
- ✓ `file` type opens in configured editor — v1.0
- ✓ `git worktree` type opens in configured IDE — v1.0
- ✓ `special string` (agents) creates/focuses named iTerm2 window via AppleScript — v1.0
- ✓ All 9 preset kinds (mr, branch, ticket, thread, file, note, worktree, agents, url) — v1.0
- ✓ `o` activates selected object, `O` opens all open-by-default, `space` toggles default set — v1.0
- ✓ Create new project (n), add object (a), edit object (e), delete object (d), delete project (D) — v1.0
- ✓ SettingsModal via `s`: ide, editor, obsidian_vault, terminal, default_open_kinds — v1.0
- ✓ Project list filter via `/`: real-time substring match, Escape/Enter exit modes — v1.0
- ✓ Installable via `uv tool install git+https://github.com/pietercusters/joy` — v1.0
- ✓ `joy --version` outputs installed version — v1.0
- ✓ README with installation, setup, key bindings — v1.0
- ✓ All user data in `~/.joy/` (config.toml + projects.toml) — v1.0
- ✓ App displays a 2x2 grid layout with four panes and Tab/Shift+Tab cycling — v1.1
- ✓ Repo registry: add/remove repos via SettingsModal with auto-detected remote URL and forge — v1.1
- ✓ Worktree pane: live grouped display of all worktrees with dirty/no-remote indicators — v1.1
- ✓ Background auto-refresh (configurable interval, default 30s) with `r` for manual refresh — v1.1
- ✓ MR/CI badges on worktree rows via gh/glab CLI (PR number, draft status, CI pass/fail) — v1.1
- ✓ iTerm2 terminal pane: live session list with Claude agent detection, Enter to focus — v1.1
- ✓ Projects grouped by registered repo in project pane; unmatched projects in "Other" — v1.1
- ✓ README Prerequisites section: iTerm2 Python API, shell integration, gh, glab — v1.1
- ✓ RelationshipIndex: bidirectional Project↔Worktree and Project↔Agent matching — v1.2
- ✓ Cursor identity preservation (repo+branch / session_name) across DOM rebuilds — v1.2
- ✓ Live badge counts on ProjectRow (worktree count + agent count) updating per refresh — v1.2
- ✓ All 6 cross-pane sync directions (project↔worktree↔agent), `x` toggle, footer hint — v1.2
- ✓ MR auto-add propagation (URL-deduped) + agent stale marking/clearing — v1.2
- ✓ Worktree auto-remove after 2+ consecutive missing refreshes — v1.2
- ✓ ProjectDetail unified view: virtual rows for REPO, TERMINALS, resolver worktrees alongside stored objects — v1.3
- ✓ Per-kind DISPATCH table routes all quick-open shortcuts — no scattered if/else — v1.3
- ✓ REPO virtual row: `r` copies repo name or prompts assignment — v1.3
- ✓ Test isolation: autouse session fixture patches all ~/.joy/ paths to tmp dir — v1.3
- ✓ iTerm2 tab-close on project delete/archive; tabs only via explicit `h` press — v1.3
- ✓ clear_selection() on sync no-match (cursor=-1); unlinked items remain fully openable — v1.3
- ✓ Project archive/unarchive: `a`/`A` bindings, archive.toml cold storage, ArchiveBrowserModal — v1.3
- ✓ Project list icon ribbon: status dot (g cycles idle/prio/hold), 6-icon presence ribbon, MR strip — v1.3
- ✓ New-project modal: single screen with name input, optional repo ListView, branch ListView — v1.3

### Active

(None — planning next milestone)

### Out of Scope

- Cross-platform support (Linux, Windows) — macOS only; uses iTerm2, app-specific URL schemes, AppleScript
- Plugin/extension API — modular design supports future extensibility, but no external plugin interface in v1
- Multi-vault Obsidian support — single globally configured vault path
- Cloud sync or sharing of project configs
- Mouse interaction — keyboard-driven only
- Object reordering (J/K) — deferred per D-13; not worth complexity for personal use case
- Configurable keybindings — ship opinionated defaults; premature complexity
- New project from discovered worktree — dropped (FLOW-03); manual project creation is sufficient
- Dim non-matching rows in sync — user explicitly excluded; spatial memory preserved
- MR auto-remove on PR close — ambiguous semantics; auto-add only
- Sync toggle persists across restarts (SYNC-10) — ephemeral is fine
- Real-time file watching on ~/.joy/ TOML (PERF-01) — 30s refresh sufficient

## Context

- Personal developer tooling for Pieter's daily workflow
- macOS-only: leverages iTerm2 (Python API + AppleScript), Obsidian URI scheme, desktop app URL handlers
- v1.0 shipped 2026-04-12: 5 phases, 15 plans, ~3,641 LOC Python, 131 tests
- v1.1 shipped 2026-04-14: 8 phases, 19 plans, 3,606 src LOC + 5,883 test LOC, 276 fast tests passing
- v1.2 shipped 2026-04-15: 3 phases, 8 plans, cross-pane intelligence
- v1.3 shipped 2026-04-22: 1 phase (17) + 21 quick tasks, 6,180 src LOC + 7,923 test LOC
- Tech stack: Python 3.11+, Textual 8.x, tomllib (stdlib), tomli_w, iterm2>=2.15 — minimal dependencies
- Data format: TOML in `~/.joy/` — human-editable; repos.toml, archive.toml added in v1.1/v1.3
- Pre-existing test failures: test_propagation.py::TestTerminalAutoRemove (references non-existent method), test_sync.py terminal sync (4 tests) — known tech debt

## Constraints

- **Tech stack**: Python, managed with `uv` — no other runtimes
- **Platform**: macOS only — relies on OS-level URL handlers and AppleScript
- **Install target**: `uv tool install git+<repo>` — must work as a globally installed tool
- **Config location**: `~/.joy/` — projects data, global settings, all state lives here
- **Design**: Minimalistic, snappy — no heavy dependencies that slow startup

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| macOS only for v1 | iTerm2, app URL schemes are macOS-specific; cross-platform is future concern | ✓ Good — no issues |
| Textual 8.x as TUI library | Only serious Python TUI option in 2025-2026; built-in ListView, CSS layout, async-native | ✓ Good — no regrets |
| TOML for ~/.joy/ data | Human-editable, stdlib read (tomllib), lightweight write (tomli_w) | ✓ Good — clean schema |
| AppleScript for iTerm2 (v1.0 path) | Officially deprecated but needed features are stable | ⚠️ Revisit — v1.1 switched to iTerm2 Python API |
| iTerm2 Python API for terminal pane | Direct session enumeration; AppleScript can't introspect sessions | ✓ Good — graceful fallback when unavailable |
| hatchling as build backend | Battle-tested, well-documented, works perfectly with uv | ✓ Good |
| Python >=3.11 requirement | tomllib in stdlib; macOS ships 3.12+ via Xcode CLT | ✓ Good |
| No argparse for --version | `sys.argv` direct check — zero overhead for normal TUI launches | ✓ Good |
| Defer MGMT-04 (J/K reorder) | Personal tool; ordering rarely changes; complexity not worth it | ✓ Good — D-13 |
| Escape via on_key not BINDING for filter | Avoids conflict with ModalScreen Escape handling | ✓ Good |
| Canonical list separate from display list | Filter reads app._projects, not display list — prevents restoring filtered subset | ✓ Good |
| list-form subprocess for all external calls | Never shell=True — prevents injection; consistent across git, gh, glab, osascript | ✓ Good — security |
| lazy import of iterm2 in worker thread | iterm2 package not available in all envs; catch-all exception returns None gracefully | ✓ Good |
| cursor/_rows/--highlight pattern in panes | Consistent cursor pattern replicated across WorktreePane, TerminalPane, ProjectList | ✓ Good — convention |
| Dropped FLOW-03 (new-project-from-worktree) | Manual project creation sufficient; auto-create from worktree adds scope without clear value | ✓ Good — D-03 |
| Slow test exclusion via pytest.mark.slow | TUI/filter tests take ~240s; exclude by default, run with -m slow when needed | ✓ Good — dev velocity |
| ArchivedProject wraps Project + archived_at | archive.toml uses keyed schema; object stripping is caller responsibility | ✓ Good — clean separation |
| Tab creation on explicit h-key only | Auto-sync tab creation removed — user controls when tabs exist | ✓ Good — v1.3 D-01 |
| clear_selection() replaces dimmed state | Unlinked items remain fully openable; no confusing disabled state | ✓ Good — v1.3 D-02 |
| DISPATCH table per kind in dispatch.py | Keystroke routing as data (4-state per kind) eliminates app.py if/else sprawl | ✓ Good — v1.3 D-03 |
| Virtual rows in ProjectDetail | REPO, TERMINALS, resolver worktrees assembled at render time — no persistence mutation | ✓ Good — v1.3 D-04 |
| Session-scoped fixture for test isolation | Patches all 5 ~/.joy/ constants once per session; no per-test overhead | ✓ Good — v1.3 D-05 |

## Evolution

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-22 after v1.3 milestone — Unified Object View, DISPATCH table, iTerm2 tab hardening, icon ribbon, archive browser, test isolation*
