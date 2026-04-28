---
phase: quick
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/test_propagation.py
  - tests/test_sync.py
autonomous: true
requirements: [tech-debt-cleanup]

must_haves:
  truths:
    - "All 10 previously failing tests are resolved (6 deleted, 4 fixed)"
    - "All remaining tests in test_propagation.py pass"
    - "All tests in test_sync.py pass"
    - "No other tests regress"
  artifacts:
    - path: "tests/test_propagation.py"
      provides: "MR auto-add tests only (terminal auto-remove class deleted)"
      contains: "class TestMRAutoAdd"
    - path: "tests/test_sync.py"
      provides: "Cross-pane sync tests with tab_id-based terminal matching"
      contains: "iterm_tab_id"
  key_links: []
---

<objective>
Fix 10 known failing tests (tech debt from v1.3): delete 6 obsolete tests in test_propagation.py that test a removed method, and update 4 tests in test_sync.py to use the current tab_id-based terminal matching instead of the old TERMINALS-name matching.

Purpose: Clear tech debt so the test suite is green before starting v1.4 milestone.
Output: Two modified test files, zero failing tests.
</objective>

<execution_context>
@.claude/get-shit-done/workflows/execute-plan.md
@.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@tests/test_propagation.py
@tests/test_sync.py
@src/joy/resolver.py (current tab_id matching logic — lines 76-108)
@src/joy/models.py (Project.iterm_tab_id, TerminalSession.tab_id)
</context>

<interfaces>
<!-- Key contracts the executor needs from models.py and resolver.py -->

From src/joy/models.py:
```python
@dataclass
class Project:
    name: str
    objects: list[ObjectItem] = field(default_factory=list)
    created: date = field(default_factory=date.today)
    repo: str | None = None
    status: str = "idle"
    iterm_tab_id: str | None = None  # <-- terminal matching key

@dataclass
class TerminalSession:
    session_id: str
    session_name: str
    foreground_process: str
    cwd: str
    tab_id: str = ""  # <-- terminal matching key
    is_claude: bool = False
```

From src/joy/resolver.py (compute_relationships, Pass 1 + Pass 3):
```python
# Pass 1: tab_id-based project lookup
if project.iterm_tab_id:
    tab_id_to_project[project.iterm_tab_id] = project

# Pass 3: match sessions to projects by tab_id
for session in sessions:
    matched = tab_id_to_project.get(session.tab_id) if session.tab_id else None
```
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Delete obsolete TestTerminalAutoRemove from test_propagation.py</name>
  <files>tests/test_propagation.py</files>
  <action>
In tests/test_propagation.py:

1. Update the module docstring (line 1) to remove "terminal auto-remove" reference. New docstring:
   ```python
   """Unit tests for propagation logic (MR auto-add).

   Tests cover:
   - MR auto-add (_propagate_mr_auto_add) (PROP-02)
   - Immutability invariants (PROP-06, PROP-07, PROP-08)
   """
   ```

2. Delete the `_sessions` helper function (lines 38-48) — only used by TestTerminalAutoRemove.

3. Delete the `_get_propagate_terminal_remove` helper function (lines 73-76) — references non-existent `JoyApp._propagate_terminal_auto_remove`.

4. Delete the entire `TestTerminalAutoRemove` class (lines 193-290) — all 6 tests reference the removed method.

5. Remove the `TerminalSession` import from the imports line (line 14) since it is no longer used in this file. The import line should become:
   ```python
   from joy.models import MRInfo, ObjectItem, PresetKind, Project
   ```

Keep all of TestMRAutoAdd and its helpers (`_project_with_branch`, `_mr_data`, `_PropContext`, `_get_propagate_mr`) untouched.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && uv run python -m pytest tests/test_propagation.py -v --tb=short 2>&1</automated>
  </verify>
  <done>8 tests in TestMRAutoAdd pass. TestTerminalAutoRemove class, _sessions helper, and _get_propagate_terminal_remove helper are all gone. No TerminalSession import remains.</done>
</task>

<task type="auto">
  <name>Task 2: Update 4 failing sync tests to use tab_id-based terminal matching</name>
  <files>tests/test_sync.py</files>
  <action>
In tests/test_sync.py, the resolver now matches terminals via `project.iterm_tab_id == session.tab_id` instead of matching `PresetKind.TERMINALS` object value against session name. Update the 4 failing tests and their helpers:

1. Update `_make_session` helper (line 117-123) to accept a `tab_id` parameter:
   ```python
   def _make_session(session_id: str, session_name: str, tab_id: str = "") -> TerminalSession:
       return TerminalSession(
           session_id=session_id,
           session_name=session_name,
           foreground_process="zsh",
           cwd="/tmp",
           tab_id=tab_id,
       )
   ```

2. Update `_make_project_with_worktree` helper (line 104-110) to accept an optional `iterm_tab_id` parameter:
   ```python
   def _make_project_with_worktree(
       name: str, repo: str, wt_path: str, agents_session: str | None = None,
       iterm_tab_id: str | None = None,
   ) -> Project:
       objects = [ObjectItem(kind=PresetKind.WORKTREE, value=wt_path, label="wt")]
       if agents_session is not None:
           objects.append(ObjectItem(kind=PresetKind.TERMINALS, value=agents_session, label="agents"))
       return Project(name=name, repo=repo, objects=objects, iterm_tab_id=iterm_tab_id)
   ```

3. Fix `test_sync_project_to_terminal` (SYNC-02, line 170):
   - Add `iterm_tab_id="tab1"` to the Project constructor
   - Change session creation to: `session = _make_session("s1", "myrepo-agents", tab_id="tab1")`
   The TERMINALS object can stay (it controls display behavior), but matching now happens via tab_id.

4. Fix `test_sync_worktree_to_terminal` (SYNC-04, line 247):
   - Add `iterm_tab_id="tab1"` to `_make_project_with_worktree` call
   - Change session creation to: `session = _make_session("s1", "myrepo-agents", tab_id="tab1")`

5. Fix `test_sync_agent_to_project` (SYNC-05, line 282):
   - Add `iterm_tab_id="tab1"` to the Project constructor
   - Change session creation to: `session = _make_session("s1", "myrepo-agents", tab_id="tab1")`

6. Fix `test_sync_agent_to_worktree` (SYNC-06, line 321):
   - Add `iterm_tab_id="tab1"` to `_make_project_with_worktree` call
   - Change session creation to: `session = _make_session("s1", "myrepo-agents", tab_id="tab1")`

Do NOT change any passing tests (SYNC-01, SYNC-03, SYNC-07 through SYNC-13). They do not involve terminal matching and are unaffected.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && uv run python -m pytest tests/test_sync.py -v --tb=short 2>&1</automated>
  </verify>
  <done>All 16 tests in test_sync.py pass (the 4 previously failing SYNC-02, SYNC-04, SYNC-05, SYNC-06 now use tab_id matching). The 1 deselected slow test (SYNC-08) is not counted.</done>
</task>

</tasks>

<verification>
Run the full test suite to confirm zero regressions:

```bash
cd /Users/pieter/Github/joy && uv run python -m pytest tests/ -v --tb=short 2>&1
```

Expected: 0 failures. The 10 previously failing tests are resolved (6 deleted, 4 fixed).
</verification>

<success_criteria>
- `uv run python -m pytest tests/test_propagation.py` — 8 passed, 0 failed
- `uv run python -m pytest tests/test_sync.py` — 16 passed, 0 failed (1 deselected)
- `uv run python -m pytest tests/` — full suite green, no regressions
- No references to `_propagate_terminal_auto_remove` remain in test files
- All 4 sync tests use `iterm_tab_id`/`tab_id` for terminal matching
</success_criteria>

<output>
After completion, create `.planning/quick/260428-gka-remove-the-tech-debt/260428-gka-SUMMARY.md`
</output>
