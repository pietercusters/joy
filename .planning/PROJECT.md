# joy

## What This Is

`joy` is a keyboard-driven Python TUI for managing coding project artifacts. It gives developers a real-time workspace dashboard — all objects related to a project (branches, MRs, tickets, worktrees, notes, agents, and more) visible at a glance, plus live git worktree status, MR/CI badges, active iTerm2 sessions, and cross-pane cursor sync. Any artifact is openable with a single keystroke. Installable globally via `uv tool install git+<repo>`, configured per-machine in `~/.joy`.

v1.0 delivered the core artifact launcher. v1.1 transformed it into a live workspace dashboard with real-time git, MR/CI, and terminal state. v1.2 added cross-pane intelligence: relationship-aware cursor sync, badge counts, and live data propagation.

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
- ✓ Relationship resolver computes Project↔Worktree and Project↔Agent matches (path-first, then branch) — v1.2
- ✓ WorktreePane and TerminalPane cursors preserved by identity across DOM rebuilds triggered by refresh — v1.2
- ✓ Project rows display live worktree and agent badge counts, updated after each refresh cycle — v1.2
- ✓ Cross-pane cursor sync: navigating any pane silently tracks all other panes to related items — v1.2
- ✓ Focus never stolen during sync operations; `x` toggles sync on/off with footer label — v1.2
- ✓ MR objects auto-added when background refresh detects a new PR for a project's branch — v1.2
- ✓ Agent objects marked stale (visually dimmed) when session disappears from iTerm2; clears on reappearance — v1.2
- ✗ Worktree auto-remove from project when worktree disappears — dropped (D-01): WorktreePane handles live display
- ✗ Worktree object moves between projects when branch changes — dropped (D-01): WorktreePane handles live display

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
- MR auto-remove on PR close — ambiguous semantics; auto-add only (PROP-09)
- Sync toggle state persists across restarts — ephemeral is fine (SYNC-10)
- Real-time file watching on ~/.joy/ TOML — 30s refresh is sufficient (PERF-01)

## Context

- Personal developer tooling for Pieter's daily workflow
- macOS-only: leverages iTerm2 (Python API + AppleScript), Obsidian URI scheme, desktop app URL handlers
- v1.0 shipped 2026-04-12: 5 phases, 15 plans, ~3,641 LOC Python, 131 tests
- v1.1 shipped 2026-04-14: 8 phases, 19 plans, 3,606 src LOC + 5,883 test LOC, 276 fast tests passing
- v1.2 shipped 2026-04-15: 3 phases (14-16), 8 plans, 3,541 src LOC + 7,208 test LOC, 309 fast tests passing
- Tech stack: Python 3.11+, Textual 8.x, tomllib (stdlib), tomli_w, iterm2>=2.15 — minimal dependencies
- Data format: TOML in `~/.joy/` — human-editable, repos stored in separate `repos.toml`
- New in v1.1: iterm2 Python package added for terminal pane; gh/glab CLIs required at runtime (not installed dependencies)
- New in v1.2: resolver.py (pure-function RelationshipIndex); ObjectItem.stale runtime field (not serialized)

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
| Pure-function resolver (compute_relationships) | No I/O, no app state — fully unit-testable; feeds RelationshipIndex consumed by badges and sync | ✓ Good — clean boundary |
| Two-flag gate for relationship computation | `_worktrees_ready + _sessions_ready` ensures both workers complete before index is computed | ✓ Good — prevents partial-data badges |
| Path precedence over branch for worktree matching | When a worktree's path is registered on a project, that beats branch name matching — unambiguous | ✓ Good — D-04 |
| _is_syncing boolean guard for cross-pane sync | Single boolean at app level; all cursor handlers check it first to prevent sync cascade loops | ✓ Good — simple and correct |
| sync_to() never calls .focus() | Focus non-steal enforced by API design, not convention — sync updates cursor without touching focus | ✓ Good — SYNC-07 |
| Drop PROP-01/PROP-03 (worktree auto-remove/move) | WorktreePane already shows live worktree state; redundant object mutation adds confusion not value | ✓ Good — D-01 |
| stale field not serialized to TOML | ObjectItem.to_dict() uses explicit key list — runtime fields never accidentally leak to disk | ✓ Good — D-07 |
| Batched TOML save per propagation cycle | `_propagate_changes` gates on `mr_added` boolean — at most one save per cycle regardless of change count | ✓ Good — avoids write amplification |

## Evolution

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-15 after v1.2 milestone — Cross-Pane Intelligence shipped*
