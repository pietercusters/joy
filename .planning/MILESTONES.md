# Milestones

## v1.2 Cross-Pane Intelligence (Shipped: 2026-04-15)

**Phases completed:** 3 phases (14-16), 8 plans
**Stats:** 56 commits, 49 files changed, 7,916 insertions — 3,541 src LOC, 7,208 test LOC, 309 fast tests

**Key accomplishments:**

- `RelationshipIndex` pure-function resolver: bidirectional Project↔Worktree and Project↔Agent matching in O(n) with path precedence over branch matching; no I/O, fully tested
- Identity-based cursor preservation in WorktreePane and TerminalPane: cursor survives DOM rebuilds by tracking `(repo_name, branch)` and `session_name` with `min(saved_index, len-1)` clamp fallback
- Live worktree and agent badge counts on every ProjectRow (`[branch] N  [robot] M`), updating after each background refresh cycle via two-flag coordination pattern
- Cross-pane cursor sync: navigating any pane silently tracks all other panes to related items without stealing focus; `_is_syncing` guard prevents cascade loops
- Sync toggle: `x` key switches cross-pane sync on/off with dynamic footer label (Sync: on / Sync: off) via `check_action` + `refresh_bindings`
- Auto-add MR objects when background refresh detects a PR for a project's branch (URL-deduplicated); `_propagate_changes` batches mutations into a single TOML save
- Agent stale detection: AGENTS objects acquire `--stale` CSS class when session disappears from iTerm2; styling clears when session reappears; runtime-only field not serialized to TOML

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
