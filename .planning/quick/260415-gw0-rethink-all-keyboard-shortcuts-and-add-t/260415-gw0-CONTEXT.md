---
# Quick Task 260415-gw0: Rethink all keyboard shortcuts and add two rows of keyboard hints at the bottom - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Task Boundary

Rethink all keyboard shortcuts across the joy TUI and add two rows of keyboard hints at the bottom.

Full spec from user:

**Global shortcuts (pop-up/notify if data missing):**
- b — copy branch to clipboard
- m — open MR
- i — open worktree in IDE
- y — open ticket
- u — open note
- t — open thread
- h — open terminal/agent
- R — toggle auto-refresh
- Unchanged: O (open all defaults), s (settings), r (refresh worktrees), l (legend), q (quit), x (sync toggle), Tab, Escape

**Pane-specific shortcuts (applies to ProjectDetail/objects pane — NOT Worktrees pane):**
- e — edit selected entry
- n — add new item
- d — delete with confirmation prompt
- D — force delete without confirmation
- o — open selected item
- Unchanged: j/k, arrows, Enter, /, R

**Remove altogether:**
- a — add item (replaced by n)

**Two rows of keyboard hints at the bottom:**
- Row 1: pane-specific shortcuts for the focused pane
- Row 2: global shortcuts
- Do NOT hint: j/k, arrows, Enter, Escape, Tab (too obvious)

</domain>

<decisions>
## Implementation Decisions

### Hint label format
- Use verbose format: `key: Full label`
- Example: `b: Copy branch  m: Open MR  i: Open IDE  y: Ticket  u: Note  t: Thread`
- Global row example: `[global]  R: Auto-refresh  s: Settings  r: Refresh  l: Legend  q: Quit`

### Worktrees pane first hint row
- When Worktrees pane is focused: first row (pane hints) is empty/hidden
- Only global row shows — clean since no pane-specific actions apply to Worktrees

### Terminal pane n/d/D scope
- n (new), d (delete), D (force delete) only apply to the ProjectDetail/objects pane
- Terminal pane does NOT get these actions — no create/delete sessions via joy
- Terminal pane does get `e` for renaming a session

### Claude's Discretion
- Implementation approach for two-row footer (custom widget vs Textual Footer extension)
- How to handle the 'b' global shortcut when no branch context exists (use existing notify system)
- Exact labels for hint display (keep them concise but clear)

</decisions>

<specifics>
## Specific Ideas

- The existing `Binding("shift+o,O", ...)` stays as `O` global
- `a` binding in ProjectDetail is removed and replaced by `n`
- `o` in ProjectDetail stays (already exists) — the spec confirms it
- New globals b/m/i/y/u/t/h need to be added to JoyApp with actions that find the relevant object for the selected project and open/copy it
- The two-row footer replaces (or supplements) the current Textual `Footer` widget

</specifics>
