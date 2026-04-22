# Quick Task 260420-ket: remove-dimmed-selection-clear-on-no-match - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Task Boundary

Remove the dimmed-selection concept added in quick-260420-izh entirely.

New sync behavior when no match is found: clear the target pane's selection
(cursor = -1, no row highlighted). Unlinked items are fully selectable and
openable — full yellow accent, Enter works normally.

This reverts the "dimmed grey outline" approach and replaces it with
"no selection" as the empty state.

</domain>

<decisions>
## Implementation Decisions

### When sync finds no match in a target pane
- Set cursor to -1 and remove all `--highlight` classes (clear selection entirely)
- No dimmed border, no muted CSS, no toast guard — pane simply shows no highlighted row

### Navigating into a pane with no selection (cursor=-1)
- Pressing j / down-arrow jumps to item 0 immediately
- Same behavior as entering the pane fresh for the first time

### Unlinked item drives other panes
- When T2 (no project link) is selected in Terminal pane, both Project pane AND Worktree pane clear their selection (cursor=-1)
- Same rule applies symmetrically: an unlinked worktree clears both Project and Terminal panes

### Fully remove from quick-260420-izh
- Remove `_is_dimmed: bool` attribute from WorktreePane and TerminalPane
- Remove `set_dimmed()` method from both panes
- Remove `--dim-selection` CSS rules from both panes (including the :focus-within variant)
- Remove toast guards from `action_activate_row` and `action_focus_session`
- Remove `_is_dimmed` guard from `action_open_ide` in app.py
- All `_sync_from_*` methods in app.py: replace `set_dimmed()` calls with `clear_selection()` calls (or inline cursor=-1 + remove --highlight)

### Claude's Discretion
- Whether to add a `clear_selection()` helper method or inline the cursor reset directly in `_sync_from_*`
- Exact naming of any new helper

</decisions>

<specifics>
## Specific Ideas

- The `sync_to()` bool return (added in izh) can be kept — it's still useful to know if a match was found
- `clear_selection()` if added should be a simple: `self._cursor = -1; [r.remove_class("--highlight") for r in self._rows]`

</specifics>
