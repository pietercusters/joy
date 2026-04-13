# joy

## What This Is

`joy` is a keyboard-driven Python TUI for managing coding project artifacts. It gives developers an instant overview of all objects related to a project — branches, MRs, tickets, worktrees, notes, agents, and more — and lets them open any or all of them with a single keystroke. Installable globally via `uv tool install git+<repo>`, configured per-machine in `~/.joy`.

v1.0 shipped: full CRUD, settings modal, project filter, `--version` CLI flag, and README. The core value — instant artifact access from one keyboard-driven interface — is fully delivered.

## Core Value

Every artifact for the active project, openable instantly from one interface — no hunting through tabs, terminals, or bookmarks.

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

### Active

- ✓ App displays a 2x2 grid layout with four panes and Tab cycling across them (PANE-01, PANE-02) — v1.1 Phase 8

### Out of Scope

- Cross-platform support (Linux, Windows) — macOS only; uses iTerm2, app-specific URL schemes, AppleScript
- Plugin/extension API — modular design supports future extensibility, but no external plugin interface in v1
- Multi-vault Obsidian support — single globally configured vault path
- Cloud sync or sharing of project configs
- Mouse interaction — keyboard-driven only
- Object reordering (J/K) — deferred per D-13; not worth complexity for personal use case
- Configurable keybindings — ship opinionated defaults; premature complexity

## Context

- Personal developer tooling for Pieter's daily workflow
- macOS-only: leverages iTerm2 (AppleScript), Obsidian URI scheme, desktop app URL handlers (notion://, slack://)
- v1.0 shipped 2026-04-12: 5 phases, 15 plans, 3,641 LOC Python, 131 tests passing
- Tech stack: Python 3.11+, Textual 8.x, tomllib (stdlib), tomli_w — minimal dependencies
- Data format: TOML in `~/.joy/` — human-editable, no comments lost (joy owns files)

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
| AppleScript for iTerm2 | Officially deprecated by iTerm2 (bug fixes only) but needed features are stable | ⚠️ Revisit — monitor iTerm2 releases |
| hatchling as build backend | Battle-tested, well-documented, works perfectly with uv | ✓ Good |
| Python >=3.11 requirement | tomllib in stdlib; macOS ships 3.12+ via Xcode CLT | ✓ Good |
| No argparse for --version | `sys.argv` direct check — zero overhead for normal TUI launches | ✓ Good |
| Defer MGMT-04 (J/K reorder) | Personal tool; ordering rarely changes; complexity not worth it | ✓ Good — D-13 |
| Escape via on_key not BINDING for filter | Avoids conflict with ModalScreen Escape handling | ✓ Good |
| Canonical list separate from display list | Filter reads app._projects, not display list — prevents restoring filtered subset | ✓ Good |

## Evolution

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-13 after Phase 8 (4-pane layout) — v1.1 Workspace Intelligence milestone*
