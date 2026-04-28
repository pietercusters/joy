---
phase: quick-260428-qtn
plan: 01
type: tdd
wave: 1
depends_on: []
files_modified:
  - src/joy/app.py
  - tests/test_propagation.py
autonomous: true
requirements: []

must_haves:
  truths:
    - "Manually added objects whose kind is in default_open_kinds get open_by_default=True"
    - "Manually added objects whose kind is NOT in default_open_kinds get open_by_default=False"
    - "Auto-added MR objects get open_by_default=True when 'mr' is in default_open_kinds"
    - "Auto-added MR objects get open_by_default=False when 'mr' is NOT in default_open_kinds"
  artifacts:
    - path: "src/joy/app.py"
      provides: "Both code paths set open_by_default from config"
      contains: "default_open_kinds"
    - path: "tests/test_propagation.py"
      provides: "Tests for default_open_kinds propagation"
      contains: "default_open_kinds"
  key_links:
    - from: "src/joy/app.py:_start_add_object_loop"
      to: "self._config.default_open_kinds"
      via: "preset.value in self._config.default_open_kinds"
      pattern: "preset\\.value in self\\._config\\.default_open_kinds"
    - from: "src/joy/app.py:_propagate_mr_auto_add"
      to: "self._config.default_open_kinds"
      via: "PresetKind.MR.value in self._config.default_open_kinds"
      pattern: "PresetKind\\.MR\\.value in self\\._config\\.default_open_kinds"
---

<objective>
Auto-set open_by_default on new objects based on the user's default_open_kinds config setting.

Purpose: Currently, manually added objects and auto-linked MR objects always get open_by_default=False, ignoring the user's configured default_open_kinds. This means users must manually toggle open_by_default for every new object of a kind they always want opened.

Output: Two code paths in app.py updated, tests proving both paths respect default_open_kinds.
</objective>

<execution_context>
@/Users/pieter/Github/joy/.claude/get-shit-done/workflows/execute-plan.md
@/Users/pieter/Github/joy/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/260428-qtn-auto-set-open-by-default-on-new-linked-o/260428-qtn-CONTEXT.md

<interfaces>
<!-- Key types and contracts the executor needs. -->

From src/joy/models.py:
```python
class PresetKind(str, Enum):
    MR = "mr"
    BRANCH = "branch"
    TICKET = "ticket"
    THREAD = "thread"
    FILE = "file"
    NOTE = "note"
    WORKTREE = "worktree"
    TERMINALS = "terminals"
    URL = "url"
    REPO = "repo"

@dataclass
class ObjectItem:
    kind: PresetKind
    value: str
    label: str = ""
    open_by_default: bool = False

@dataclass
class Config:
    default_open_kinds: list[str] = field(
        default_factory=lambda: ["worktree", "terminals"]
    )
```

From tests/test_propagation.py:
```python
class _PropContext:
    """Minimal context that mimics the JoyApp interface used by propagation methods."""
    def __init__(self, projects: list[Project], sessions: list | None = None) -> None:
        self._projects = projects
        self._current_sessions = sessions or []

def _get_propagate_mr(ctx: _PropContext):
    """Return bound _propagate_mr_auto_add for ctx."""
    from joy.app import JoyApp
    return lambda mr_data: JoyApp._propagate_mr_auto_add(ctx, mr_data)
```

Note: _PropContext does NOT currently have a `_config` attribute. It must be extended.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add tests for default_open_kinds on MR auto-add propagation</name>
  <files>tests/test_propagation.py</files>
  <behavior>
    - Test: MR auto-add with "mr" in default_open_kinds sets open_by_default=True
    - Test: MR auto-add with "mr" NOT in default_open_kinds sets open_by_default=False
    - Test: Existing test_mr_auto_add_appends_object (line 66) updated to use _PropContext with config
  </behavior>
  <action>
1. Extend `_PropContext.__init__` to accept an optional `config` parameter (defaulting to `Config()` from `joy.models`). Store as `self._config`. Add `Config` to the import from `joy.models` at the top of the file.

2. Update the existing `test_mr_auto_add_appends_object` test: the default Config has `default_open_kinds=["worktree", "terminals"]` which does NOT include "mr", so the existing assertion `assert new_obj.open_by_default is False` remains correct. No change needed to this test -- it already covers the "mr NOT in default_open_kinds" case once the code change lands.

3. Add a new test `test_mr_auto_add_respects_default_open_kinds` in `TestMRAutoAdd`:
   ```python
   def test_mr_auto_add_respects_default_open_kinds(self) -> None:
       """MR auto-add sets open_by_default=True when 'mr' in default_open_kinds."""
       project = _project_with_branch("joy", "feat-1")
       config = Config(default_open_kinds=["mr", "worktree"])
       ctx = _PropContext([project], config=config)
       mr = _mr_data("joy", "feat-1", "https://github.com/x/y/pull/42", 42)

       messages = _get_propagate_mr(ctx)(mr)

       assert len(project.objects) == 2
       new_obj = project.objects[-1]
       assert new_obj.kind == PresetKind.MR
       assert new_obj.open_by_default is True
   ```

4. RED: Run tests -- the new test MUST fail (open_by_default will be False because app.py still hardcodes it). The existing test should still pass.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && uv run pytest tests/test_propagation.py -x -v 2>&1 | tail -20</automated>
  </verify>
  <done>New test exists and FAILS (red) because app.py still hardcodes open_by_default=False in _propagate_mr_auto_add. Existing tests still pass. _PropContext accepts config parameter.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement open_by_default from config in both code paths</name>
  <files>src/joy/app.py</files>
  <behavior>
    - _propagate_mr_auto_add uses self._config.default_open_kinds to set open_by_default
    - _start_add_object_loop uses self._config.default_open_kinds to set open_by_default
  </behavior>
  <action>
1. In `src/joy/app.py`, method `_propagate_mr_auto_add` (around line 322-327), change:
   ```python
   open_by_default=False,
   ```
   to:
   ```python
   open_by_default=PresetKind.MR.value in self._config.default_open_kinds,
   ```

2. In `src/joy/app.py`, method `_start_add_object_loop` (around line 691), change:
   ```python
   obj = ObjectItem(kind=preset, value=value)
   ```
   to:
   ```python
   obj = ObjectItem(kind=preset, value=value, open_by_default=preset.value in self._config.default_open_kinds)
   ```

3. GREEN: Run all tests -- every test including the new one from Task 1 MUST pass.

4. Run the full test suite to ensure no regressions.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && uv run pytest tests/test_propagation.py -x -v && uv run pytest tests/ -x --timeout=10 2>&1 | tail -30</automated>
  </verify>
  <done>Both code paths use self._config.default_open_kinds to set open_by_default. All tests pass including the new test_mr_auto_add_respects_default_open_kinds. No regressions in full test suite.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

No new trust boundaries introduced. Both code paths already exist and the change only reads from an existing in-memory config object (self._config).

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-qtn-01 | T (Tampering) | default_open_kinds config | accept | Config is loaded from user's own ~/.joy/config.toml at startup. User controls their own config file. No external input vector. |
</threat_model>

<verification>
- `uv run pytest tests/test_propagation.py -v` -- all propagation tests pass
- `uv run pytest tests/ -x --timeout=10` -- full suite passes, no regressions
- Grep confirms both code paths reference `default_open_kinds`:
  - `grep -n "default_open_kinds" src/joy/app.py` shows 2 new occurrences (lines ~326 and ~691)
</verification>

<success_criteria>
- MR auto-add propagation sets open_by_default based on config.default_open_kinds
- Manual object add sets open_by_default based on config.default_open_kinds
- All existing tests pass without modification (except _PropContext extension)
- New test proves MR auto-add respects the setting
</success_criteria>

<output>
After completion, create `.planning/quick/260428-qtn-auto-set-open-by-default-on-new-linked-o/260428-qtn-SUMMARY.md`
</output>
