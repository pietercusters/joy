---
phase: quick
plan: 260428-kxu
type: execute
wave: 1
depends_on: []
files_modified:
  - src/joy/widgets/icons.py
  - src/joy/screens/legend.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "ICON_MR_MERGED constant exists in icons.py with codepoint U+EAC3"
    - "Legend shows separate entries for MR merged (purple) and MR closed (dim)"
    - "Worktree pane legend section includes MR merged entry"
  artifacts:
    - path: "src/joy/widgets/icons.py"
      provides: "ICON_MR_MERGED constant"
      contains: "ICON_MR_MERGED"
    - path: "src/joy/screens/legend.py"
      provides: "Split merged/closed legend entries in both _PROJECT_MR and _WORKTREE_ICONS"
      contains: "ICON_MR_MERGED"
  key_links:
    - from: "src/joy/screens/legend.py"
      to: "src/joy/widgets/icons.py"
      via: "import ICON_MR_MERGED"
      pattern: "from joy.widgets.icons import.*ICON_MR_MERGED"
---

<objective>
Add a dedicated purple merged MR icon (ICON_MR_MERGED) to the icon constants and update
the legend modal to show separate entries for "MR merged" (purple) and "MR closed" (dim)
instead of the current combined "MR closed / merged" entry.

Purpose: Distinguish merged MRs from closed MRs visually in the legend, preparing for
future rendering that uses the merged state.
Output: Updated icons.py with new constant, updated legend.py with split entries.
</objective>

<execution_context>
@/Users/pieter/Github/joy/.claude/get-shit-done/workflows/execute-plan.md
@/Users/pieter/Github/joy/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/joy/widgets/icons.py
@src/joy/screens/legend.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add ICON_MR_MERGED and update legend entries</name>
  <files>src/joy/widgets/icons.py, src/joy/screens/legend.py</files>
  <action>
1. In `src/joy/widgets/icons.py`, add after line 6 (ICON_MR_CLOSED):
   ```python
   ICON_MR_MERGED  = "\ueac3"   # nf-cod-git_merge
   ```
   Keep the column alignment consistent with the other constants.

2. In `src/joy/screens/legend.py`:
   a. Update the import on line 13 to include ICON_MR_MERGED:
      ```python
      ICON_MR_OPEN, ICON_MR_DRAFT, ICON_MR_CLOSED, ICON_MR_MERGED,
      ```
   b. Replace the single "MR closed / merged" entry in `_PROJECT_MR` (line 41) with two entries:
      ```python
      (f"[purple]{ICON_MR_MERGED}[/purple]", "MR merged"),
      (f"[dim]{ICON_MR_CLOSED}[/dim]",       "MR closed"),
      ```
      Place the merged entry BEFORE the closed entry (merged is more common/important).
   c. In `_WORKTREE_ICONS` (around line 66-74), add an MR merged entry after the MR draft entry (line 71):
      ```python
      (f"[purple]{ICON_MR_MERGED}[/purple]", "MR merged"),
      ```
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && python -c "from joy.widgets.icons import ICON_MR_MERGED; assert ICON_MR_MERGED == '\ueac3'; print('OK: icon constant')" && python -c "from joy.screens.legend import _PROJECT_MR, _WORKTREE_ICONS; assert any('merged' in label.lower() for _, label in _PROJECT_MR); assert any('closed' in label.lower() and 'merged' not in label.lower() for _, label in _PROJECT_MR); assert any('merged' in label.lower() for _, label in _WORKTREE_ICONS); print('OK: legend entries')"</automated>
  </verify>
  <done>
    - ICON_MR_MERGED exists in icons.py with codepoint U+EAC3
    - _PROJECT_MR has separate "MR merged" (purple) and "MR closed" (dim) entries
    - _WORKTREE_ICONS includes "MR merged" (purple) entry
    - All existing imports and references remain intact
  </done>
</task>

</tasks>

<verification>
- `python -c "from joy.widgets.icons import ICON_MR_MERGED"` succeeds
- Legend modal shows distinct merged (purple) and closed (dim) entries
- No import errors across the codebase
</verification>

<success_criteria>
- ICON_MR_MERGED constant defined and importable
- Legend splits merged/closed into two distinct visual entries
- Purple styling applied to merged icon in legend
- Existing tests pass (no regressions)
</success_criteria>

<output>
After completion, create `.planning/quick/260428-kxu-add-purple-merged-closed-mr-icon-and-upd/260428-kxu-SUMMARY.md`
</output>
