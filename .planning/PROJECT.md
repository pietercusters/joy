# joy

## What This Is

`joy` is a keyboard-driven Python TUI for managing coding project artifacts. It gives developers an instant overview of all objects related to a project — branches, MRs, tickets, worktrees, notes, agents, and more — and lets them open any or all of them with a single keystroke. Installable globally via `uv`, configured per-machine in `~/.joy`.

## Core Value

Every artifact for the active project, openable instantly from one interface — no hunting through tabs, terminals, or bookmarks.

## Requirements

### Validated

**Phase 01 (Foundation):** Python package structure, TOML config/store, Config dataclass, Project/ObjectItem models, uv toolchain  
**Phase 02 (TUI Shell):** Two-pane Textual layout, JoyApp, ProjectList/ProjectDetail widgets, keyboard navigation  
**Phase 03 (Activation):** All 9 preset kind activations, `o`/`O`/Space/a/e/d bindings, macOS open+pbcopy+osascript integration  
**Phase 04 (CRUD):** New project modal, edit object, delete project with confirmation, ConfirmationModal  
**Phase 05 (Settings + Search + Distribution):** SettingsModal with 5 Config fields (`s` key), project filter mode (`/` key), `--version` CLI flag, README, version in TUI header — Validated 2026-04-12

### Active

**Core TUI**
- [ ] Two-pane main screen: project list (left) + project detail pane (right)
- [ ] Keyboard-driven navigation throughout (arrow keys, vim-style hjkl optional)
- [ ] Minimalistic, polished visual design with icons per object type
- [ ] Super-fast startup and response time

**Project Management**
- [ ] Create a new project (with pre-defined object form)
- [ ] Edit a project's objects
- [ ] Delete a project (with confirmation)
- [ ] First project auto-selected on open

**Object Types & Operations**
- [ ] `string` — copy to clipboard
- [ ] `url` — open in default browser or configured desktop app (Notion, Slack)
- [ ] `obsidian` — open file in configured Obsidian vault using the Obsidian URI scheme
- [ ] `file` — open in configured editor (e.g., Sublime)
- [ ] `git worktree` — open in configured IDE (e.g., PyCharm)
- [ ] `special string` (agents) — create or open named iTerm2 window via AppleScript (feasibility: research needed)

**Pre-defined Objects**
- [ ] `mr` (web url, multiple allowed) — open in browser
- [ ] `branch` (string, multiple allowed) — copy to clipboard
- [ ] `ticket` (url, multiple allowed) — open in Notion desktop
- [ ] `thread` (url, multiple allowed) — open in Slack desktop
- [ ] `file` (file, multiple allowed) — open in configured editor
- [ ] `note` (Obsidian file, multiple allowed) — open in Obsidian
- [ ] `worktree` (git worktree, one) — open in configured IDE
- [ ] `agents` (special string, one) — create/open named iTerm2 window
- [ ] `url` (url, multiple allowed) — open in browser

**Activation Operations**
- [ ] `o` — activate the selected object (performs its type-specific operation)
- [ ] `O` — activate all objects marked as "open by default" for this project, in display order
- [ ] `space` — toggle whether selected object is included in the "open by default" set
- [ ] `a` — add a new object (choose pre-defined or generic type, enter value)
- [ ] `e` — edit selected object
- [ ] `d` or `delete` — remove selected object (with confirmation)

**Global Configuration**
- [ ] Preferred IDE (for git worktrees)
- [ ] Obsidian vault path
- [ ] Preferred editor (for files)
- [ ] Terminal tool (for agents — e.g., iTerm2)
- [ ] Default object types to activate on `O` (global default, overridable per project)
- [ ] Edit global settings via a dedicated settings screen

**Installation & Distribution**
- [ ] Managed with `uv`, installable globally from git repo (`uv tool install git+...`)
- [ ] Data and config stored in `~/.joy/`
- [ ] Concise README covering installation and usage

### Out of Scope

- Cross-platform support (Linux, Windows) — macOS only; uses iTerm2, app-specific URL schemes
- Plugin/extension API — modular design supports future extensibility, but no external plugin interface in v1
- Multi-vault Obsidian support — single globally configured vault path
- Cloud sync or sharing of project configs
- Mouse interaction — keyboard-driven only for v1

## Context

- Personal developer tooling for Pieter's daily workflow
- macOS-only: leverages iTerm2 (AppleScript), Obsidian URI scheme, desktop app URL handlers (notion://, slack://)
- Objects with "multiple allowed" default to 1 on creation; user can add more of the same type
- The "open by default" set is configured per-project; the global default controls which object types are pre-selected when creating a new project
- Opening order for `O` follows the display order in the detail pane
- iTerm2 integration (agents object): joy should create a named window on project creation if it doesn't exist, and activate it by name on open — feasibility requires research into AppleScript/iTerm2 API

## Constraints

- **Tech stack**: Python, managed with `uv` — no other runtimes
- **Platform**: macOS only — relies on OS-level URL handlers and AppleScript
- **Install target**: `uv tool install git+<repo>` — must work as a globally installed tool
- **Config location**: `~/.joy/` — projects data, global settings, all state lives here
- **Design**: Minimalistic, snappy — no heavy dependencies that slow startup

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| macOS only for v1 | iTerm2, app URL schemes are macOS-specific; cross-platform is a future concern | — Pending |
| TUI library choice | Needs research — Textual is the likely pick for Python TUI in 2025, but startup time matters | — Pending |
| Data format for ~/.joy/ | TOML or JSON — needs decision during planning | — Pending |
| iTerm2 integration approach | AppleScript is the likely mechanism; feasibility research needed | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-12 — Phase 05 complete, milestone v1.0 fully executed*
