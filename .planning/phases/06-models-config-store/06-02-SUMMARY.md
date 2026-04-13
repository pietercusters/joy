---
phase: 06-models-config-store
plan: "02"
subsystem: store
tags: [store, persistence, repo, subprocess, tdd]
dependency_graph:
  requires: [06-01]
  provides: [REPOS_PATH, load_repos, save_repos, get_remote_url, validate_repo_path]
  affects: [Phase 7, Phase 13]
tech_stack:
  added: [subprocess (stdlib)]
  patterns: [TDD red-green, atomic write, keyed TOML schema, subprocess with timeout]
key_files:
  created: []
  modified:
    - src/joy/store.py
    - tests/test_store.py
decisions:
  - "name is the TOML table key in [repos.<name>] schema — popped from to_dict() output before storing (per D-02)"
  - "get_remote_url uses list-form subprocess (never shell=True) per T-06-03 threat mitigation"
  - "test uses SSH URL directly to avoid git url.insteadOf HTTPS→SSH rewrite on developer machine"
metrics:
  duration_minutes: 8
  tasks_completed: 1
  files_modified: 2
  completed_date: "2026-04-13"
---

# Phase 06 Plan 02: Repo Store Persistence Summary

Repo CRUD persistence layer added to store.py with load_repos/save_repos (keyed TOML schema), get_remote_url (subprocess git with 5s timeout), and validate_repo_path (Path.is_dir()), completing the data layer for Phase 7 worktree discovery.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Add failing tests for repo store | 421f9d0 | tests/test_store.py |
| 1 (GREEN) | Add repo CRUD store functions to store.py | 4edabf7 | src/joy/store.py, tests/test_store.py |

## What Was Built

### Task 1: Repo CRUD store functions (TDD)

**RED phase (421f9d0):** Added 3 test classes to `tests/test_store.py`:

- `TestRepoStore` (8 tests): round-trip single/multiple repos, defaults, missing file returns [], creates nested directories, `[repos.name]` keyed schema, unknown field UserWarning, atomic write via os.replace
- `TestGetRemoteUrl` (4 tests): real git repo subprocess, plain dir returns "", nonexistent path returns "", git repo without remote returns ""
- `TestValidateRepoPath` (3 tests): existing dir True, nonexistent False, file-not-dir False

Also added `import subprocess` and `from joy.models import ... Repo` to test imports.

**GREEN phase (4edabf7):** Added to `src/joy/store.py`:

- `import subprocess` at top
- `Repo` added to `from joy.models import` line
- `REPOS_PATH = JOY_DIR / "repos.toml"` constant
- `_repos_to_toml(repos)`: converts list to `{"repos": {name: {...}}}` dict, pops name from to_dict() output so name is the TOML key not a field
- `_toml_to_repos(data)`: iterates `data["repos"]` items, emits `warnings.warn(UserWarning)` for unknown fields, skips them
- `load_repos(*, path)`: returns `[]` if missing, loads TOML, delegates to `_toml_to_repos`
- `save_repos(repos, *, path)`: delegates to `_repos_to_toml`, encodes, calls `_atomic_write`
- `get_remote_url(local_path)`: `subprocess.run(["git", "remote", "get-url", "origin"], cwd=local_path, timeout=5)`, returns stdout.strip() on returncode==0, else "" — never raises (catches TimeoutExpired, OSError)
- `validate_repo_path(local_path)`: `return Path(local_path).is_dir()`

## Verification

```
uv run pytest tests/test_store.py tests/test_models.py -x -q
82 passed in 0.12s

uv run pytest -x -q
167 passed, 1 deselected in 44.08s
```

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| name popped from to_dict() in _repos_to_toml | D-02: name IS the TOML table key [repos.joy] — storing it as a field too would be redundant. Different from _projects_to_toml which keeps name inside. |
| list-form subprocess, never shell=True | T-06-03: cwd is user-supplied; list form prevents shell injection. timeout=5 prevents hangs on unresponsive git operations. |
| test uses SSH URL directly | Global git config has url.insteadOf that rewrites HTTPS to SSH for github.com. Using SSH URL directly avoids flaky assertion based on local git config. |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test URL assertion failed due to git url.insteadOf rewrite**
- **Found during:** Task 1 GREEN phase (first test run)
- **Issue:** Developer's global git config has `url.git@github.com:.insteadOf=https://github.com/` which rewrites the HTTPS URL used in the test to SSH before git stores it. The test asserted the HTTPS URL back but git returned the SSH form.
- **Fix:** Changed `test_get_remote_url_real_git_repo` to use SSH URL (`git@github.com:test/repo.git`) as input — this form is not rewritten, so the assertion holds across machines with or without url rewrite config.
- **Files modified:** tests/test_store.py
- **Commit:** 4edabf7

## Known Stubs

None — all functions have real implementations. No placeholder data.

## Threat Flags

None — this plan adds persistence functions for a local file (`~/.joy/repos.toml`). The subprocess call uses list form (never shell=True), has a timeout, and catches all exceptions. No new network endpoints or auth paths introduced.

## Self-Check: PASSED

Files exist:
- FOUND: src/joy/store.py
- FOUND: tests/test_store.py
- FOUND: .planning/phases/06-models-config-store/06-02-SUMMARY.md

Commits exist:
- FOUND: 421f9d0 (test RED)
- FOUND: 4edabf7 (feat GREEN)
