---
status: diagnosed
phase: 01-foundation
source: 01-01-SUMMARY.md, 01-02-SUMMARY.md, 01-03-SUMMARY.md
started: 2026-04-10T18:35:00Z
updated: 2026-04-10T19:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Run `uv run joy` — prints "Not yet implemented", exits cleanly (no errors, no tracebacks)
result: pass

### 2. Full test suite passes
expected: Run `uv run pytest tests/ -q` — all 60 tests pass, 0 failures
result: issue
reported: "All pass, but there's one test that actually opens a iterm2 window. That should not happen."
severity: major

### 3. Data model round-trip via Python
expected: |
  Run in Python:
    from joy.models import Project, ObjectItem, PresetKind
    p = Project(name="test", objects=[ObjectItem(kind=PresetKind.MR, value="https://example.com", label="MR")])
    d = p.to_dict()
    assert d["objects"][0]["kind"] == "mr"
    print("ok")
  Prints "ok" with no errors.
result: pass

### 4. TOML persistence round-trip
expected: |
  Run in Python (using tmp path):
    import tempfile, pathlib
    from joy.models import Project, ObjectItem, PresetKind
    from joy.store import save_projects, load_projects
    tmp = pathlib.Path(tempfile.mkdtemp()) / "projects.toml"
    p = Project(name="myproject", objects=[ObjectItem(kind=PresetKind.BRANCH, value="main")])
    save_projects([p], path=tmp)
    loaded = load_projects(path=tmp)
    assert loaded[0].name == "myproject"
    assert loaded[0].objects[0].kind == PresetKind.BRANCH
    print("ok")
  Prints "ok" and the TOML file contains `[projects.myproject]`.
result: issue
reported: "ModuleNotFoundError: No module named 'tomli_w'"
severity: major

### 5. Operations dispatch (mocked)
expected: |
  Run `uv run pytest tests/test_operations.py -q` — all 15 tests pass, including
  string→pbcopy, URL→open, notion URL→notion:// scheme, slack URL→open -a Slack,
  obsidian→obsidian:// URI, file→open -a editor, worktree→open -a IDE,
  iterm→osascript, and the all-openers-registered test.
result: pass

## Summary

total: 5
passed: 3
issues: 2
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "All tests pass without opening real system windows (iTerm2, etc.)"
  status: fixed
  reason: "User reported: All pass, but there's one test that actually opens a iterm2 window. That should not happen."
  severity: major
  test: 2
  root_cause: "test_open_iterm_live in tests/test_operations.py:181 was missing @pytest.mark.macos_integration decorator. Already fixed in commit 4623c6b which added the marker and pyproject.toml addopts exclusion."
  artifacts:
    - path: "tests/test_operations.py"
      issue: "test_open_iterm_live was missing macos_integration marker (now fixed)"
    - path: "pyproject.toml"
      issue: "addopts now excludes macos_integration tests by default"
  missing: []
  debug_session: ""
- truth: "TOML persistence round-trip works: save_projects/load_projects round-trips correctly"
  status: not_a_bug
  reason: "User reported: ModuleNotFoundError: No module named 'tomli_w'"
  severity: major
  test: 4
  root_cause: "User ran plain `python` instead of `uv run python`. tomli_w is correctly declared as a dependency in pyproject.toml and is available in the uv venv (v1.2.0). No code change needed — use `uv run python` to access project dependencies."
  artifacts: []
  missing: []
  debug_session: ""
