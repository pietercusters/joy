---
phase: quick
plan: 260415-jab
type: execute
wave: 1
depends_on: []
files_modified:
  - src/joy/app.py
autonomous: true
requirements: []

must_haves:
  truths:
    - "Pressing 'i' in JoyApp always opens the IDE on the first detected worktree for the active project"
    - "Pressing Enter on a worktree row still opens the MR URL when an MR is present (unchanged)"
    - "The 'i' shortcut is visible in the footer"
  artifacts:
    - path: "src/joy/app.py"
      provides: "action_open_ide method and 'i' binding in BINDINGS"
  key_links:
    - from: "'i' keypress"
      to: "subprocess.run(['open', '-a', ide, wt.path])"
      via: "action_open_ide -> _rel_index.worktrees_for(project)"
---

<objective>
Add a global 'i' keybinding to JoyApp that always opens the IDE on the first detected worktree for the active project, regardless of whether an MR is present on that branch.

Purpose: Enter on a worktree row now opens the MR URL when an MR is detected (intentional behaviour from quick task 260414-qk4). Users lost the ability to open the IDE from the worktree pane when an MR exists. The 'i' binding restores that capability as a direct, always-available shortcut.

Output: `action_open_ide` method in JoyApp + 'i' entry in BINDINGS.
</objective>

<execution_context>
@/Users/pieter/Github/joy/.claude/get-shit-done/workflows/execute-plan.md
@/Users/pieter/Github/joy/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/joy/app.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add 'i' → open IDE binding to JoyApp</name>
  <files>src/joy/app.py</files>
  <action>
1. In the BINDINGS list (lines 51-59), add a new entry after the existing bindings:
   `Binding("i", "open_ide", "Open IDE", priority=True),`

2. Add the `action_open_ide` method to JoyApp. Place it near `action_open_all_defaults` or any other app-level open action for logical grouping. The method must:
   - Get the currently active project from `self.query_one(ProjectDetail)._project`
   - If `_project` is None, return early (nothing to open)
   - Get the IDE from `self._config.ide` (fallback to `"Cursor"` if empty)
   - If `self._rel_index` is None, return early (worktrees not loaded yet)
   - Call `worktrees = self._rel_index.worktrees_for(self.query_one(ProjectDetail)._project)`
   - If worktrees is empty, return early (no worktree detected)
   - Use `wt = worktrees[0]` — the first detected worktree for the project
   - Run in a background worker thread (use `@work(thread=True)` decorator) to avoid blocking the UI:
     ```python
     import subprocess
     subprocess.run(["open", "-a", ide, wt.path], check=False)
     ```
   - Note: `subprocess` is already imported in `worktree_pane.py`; check if it needs to be imported in `app.py` (it currently may not be — add the import if missing).

3. The method signature:
   ```python
   @work(thread=True)
   def action_open_ide(self) -> None:
       """Open the IDE on the first detected worktree for the active project ('i' binding)."""
   ```

Do NOT change `action_activate_row` in `worktree_pane.py` — the Enter → MR URL behaviour is intentional.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && /Users/pieter/.nvm/versions/node/v22.17.1/bin/node -e "process.exit(0)" && python -m pytest tests/ -x -q --ignore=tests/tui 2>&1 | tail -20</automated>
  </verify>
  <done>
- 'i' appears in BINDINGS with `priority=True`
- `action_open_ide` method exists, retrieves project + worktree via `_rel_index`, opens IDE via subprocess in a worker thread
- All existing tests pass (no regressions)
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| config → subprocess | IDE name from ~/.joy/config.toml is passed to `open -a` |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-jab-01 | Tampering | subprocess call with `ide` value | accept | IDE value comes from user-owned ~/.joy/config.toml; user controls their own config. No sanitisation needed for a personal macOS-only tool. |
| T-jab-02 | Tampering | wt.path passed to `open -a` | accept | Worktree paths are detected from local git repositories on the user's own machine. Path is filesystem-local, no network exposure. |
</threat_model>

<verification>
Manual smoke test after implementation:
1. Open joy with a project that has a detected worktree AND an MR on its branch
2. Navigate to that project
3. Press Enter on the worktree row → MR URL should open in browser (unchanged)
4. Press 'i' → IDE should open at the worktree path
5. Verify 'i' hint is visible in the footer
</verification>

<success_criteria>
- Pressing 'i' opens the IDE on the active project's first detected worktree in all cases
- Pressing Enter on a worktree with an MR still opens the MR URL (no regression)
- Footer shows 'i — Open IDE' hint
- All unit tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/260415-jab-fix-opening-ide-on-worktree-fails-when-m/260415-jab-SUMMARY.md`
</output>
