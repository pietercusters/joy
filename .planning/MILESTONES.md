# Milestones

## v1.3 Unified Object View (Shipped: 2026-04-22)

**Phases completed:** 1 phase (17), 3 plans + 21 quick tasks

**Key accomplishments:**

- Virtual row assembly in ProjectDetail: REPO, TERMINALS, and resolver-matched worktrees appear alongside stored ObjectItems in a unified detail view
- Per-kind DISPATCH table in dispatch.py routes all quick-open shortcuts (b, m, i, y, u, t, h, r) — replaces scattered if/else in app.py
- REPO virtual row assigned `r` shortcut: copies repo name when set, prompts assignment when not
- Session-scoped autouse pytest fixture patches all 5 ~/.joy/ path constants to tmp directory — no test can touch real user data
- iTerm2 tab-close on project delete/archive; tabs only created via explicit `h` press (auto-sync removed)
- `clear_selection()` replaces dimmed-state concept — cross-pane sync clears cursor on no-match; unlinked items remain fully openable

---

## v1.2 Cross-Pane Intelligence (Shipped: 2026-04-15)

**Phases completed:** 3 phases (14-16), 8 plans, all complete

**Key accomplishments:**

- RelationshipIndex: pure-function bidirectional worktree↔project and agent↔project matching with O(n) two-pass dict construction
- Identity-based cursor preservation in WorktreePane and TerminalPane: survives DOM rebuilds via (repo+branch) / session_name tracking
- Live badge counts on every ProjectRow (worktree count + agent count), updating after each background refresh
- All 6 cross-pane sync directions wired (SYNC-01..06): selecting project/worktree/agent drives the other two panes with `_is_syncing` guard
- `x` toggle for cross-pane sync on/off with Footer hint — sync state visible at all times
- MR auto-add propagation (URL-deduped) + agent stale marking/clearing with transition-only notifications

---

## v1.1 Workspace Intelligence (Shipped: 2026-04-14)

**Phases completed:** 8 phases, 19 plans, 30 tasks

**Key accomplishments:**

- RED phase (421f9d0):
- WorktreeInfo dataclass with repo_name, branch, path, is_dirty, has_upstream fields -- data contract for worktree discovery
- discover_worktrees function with git porcelain parsing, dirty detection via diff-index, upstream tracking via rev-parse, and exact-match branch filtering
- TerminalPane and WorktreePane stub widgets with 9 RED-phase tests defining the 4-pane grid layout and Tab focus cycling contract
- Refactored JoyApp from Horizontal 2-pane to Grid 2x2 layout with Tab/Shift+Tab focus cycling across all four panes and accent-border focus indicators
- One-liner:
- One-liner:
- User approved worktree pane rendering — grouped rows, Nerd Font icons, focus border, and read-only behavior all confirmed correct
- WorktreePane extended with scroll-position preservation across DOM rebuilds and a set_refresh_label() method that updates border_title with timestamp and stale-state warning glyph
- JoyApp wired with set_interval background timer, r keybinding, relative timestamp display via set_refresh_label, and stale-data detection with warning glyph — delivering the core phase goal of automatic background refresh without UI freezes
- MRInfo dataclass and mr_status.py fetch module with GitHub (gh) and GitLab (glab) CLI integration for MR/PR status and CI pipeline results
- Extended WorktreeRow with MR/CI badges on line 1 and author+commit on line 2, wired fetch_mr_data into app.py background worker, with 14 new TDD tests
- One-liner:
- Constants (per D-07):
- `_load_terminal()` worker wired into JoyApp — terminal pane refreshes in parallel with worktrees on mount, r key, and timer; border_title shows timestamp and stale state independently
- Added Project.repo optional field with backward-compatible TOML serialization and initialized JoyApp._repos for downstream Wave 2 plans
- Full rewrite of ProjectList from ListView to VerticalScroll/GroupHeader/cursor pattern with repo-based project grouping and filter mode compatibility
- Extended SettingsModal with a Repos section featuring j/k cursor navigation, path-validated add via PathInputModal, and confirmation-gated remove with independent persistence via save_repos
- Added Prerequisites section to README documenting iTerm2 Python API, shell integration, gh CLI, and glab CLI setup requirements

---

## v1.0 MVP (Shipped: 2026-04-12)

**Phases completed:** 5 phases, 15 plans, 18 tasks

**Key accomplishments:**

- Atomic TOML persistence layer (tomllib/tomli_w) with keyed schema, atomic writes, and test-isolation via path parameterization — zero-dependency data layer
- Two-pane Textual TUI: ProjectList + ProjectDetail with grouped ObjectRows (Nerd Font icons), j/k cursor navigation, and context-sensitive Header/Footer
- Core value delivered: `o` opens selected object, `O` opens all defaults, `space` toggles default set — all via background workers with toast feedback
- Full CRUD: new project (n), add/edit/delete objects (a/e/d), delete project (D) via modal forms with confirmation dialogs
- SettingsModal (`s`) for all 5 Config fields, real-time project filter (`/`), `--version` CLI flag, full README — globally installable via `uv tool install`

---
