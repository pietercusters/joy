---
phase: 07-git-worktree-discovery
reviewed: 2026-04-13T12:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/joy/models.py
  - src/joy/worktrees.py
  - tests/test_models.py
  - tests/test_worktrees.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 7: Code Review Report

**Reviewed:** 2026-04-13T12:00:00Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Phase 7 introduces git worktree discovery: a `WorktreeInfo` dataclass in `models.py` and a new `worktrees.py` module that shells out to `git` to enumerate worktrees, check dirty status, and detect upstream tracking. Tests use real git repos in temporary directories.

The code is well-structured overall. Error handling is solid -- all subprocess calls use `capture_output=True`, `timeout=5`, and catch `TimeoutExpired`/`OSError`. The branch filter correctly uses exact-match set lookup. Two warnings are worth addressing: a missing-branch edge case in porcelain parsing that could produce a `WorktreeInfo` with an empty branch name, and a test helper that assumes the default branch is `main`. Two minor info-level items are noted for consistency.

## Warnings

### WR-01: Empty branch name passes through when porcelain block has no branch line

**File:** `src/joy/worktrees.py:51-52`
**Issue:** In `_list_worktrees`, if a porcelain block contains a `worktree <path>` line but no `branch` line and is not `detached` or `bare`, the `branch` variable remains `""` (empty string). The tuple `(path, "")` is appended to the results list, which produces a `WorktreeInfo` with `branch=""`. While this scenario is unlikely in normal git operation, corrupted worktree state or future git format changes could trigger it. An empty branch name is semantically ambiguous -- it is not "HEAD" (detached) and not an actual branch.

**Fix:** Skip worktree entries where branch is empty. Replace line 51-52:
```python
        if path and not is_bare:
            worktrees.append((path, branch))
```
with:
```python
        if path and branch and not is_bare:
            worktrees.append((path, branch or "HEAD"))
```
Or more explicitly, treat missing branch as detached HEAD:
```python
        if path and not is_bare:
            worktrees.append((path, branch or "HEAD"))
```
The choice depends on whether "unknown branch" should be treated as detached HEAD or silently skipped. Skipping (first option) is the safer default since the consumer may not expect empty strings.

### WR-02: Test helper `_setup_upstream` assumes default branch is `main`

**File:** `tests/test_worktrees.py:57-76`
**Issue:** The `_setup_upstream` helper pushes a specific branch to the remote. The tests call `_setup_upstream(repo_dir, "main")` on line 213, but `git init` may create a default branch named `master` instead of `main` depending on the git configuration (`init.defaultBranch`). While the `_init_git_repo` helper does not explicitly set `init.defaultBranch`, the tests at lines 99-100 already hedge for this (`assert wt.branch == "main" or wt.branch == "master"`). However, `test_branch_with_upstream_has_upstream_true` (line 209) hardcodes `_setup_upstream(repo_dir, "main")` -- if the system default is `master`, the push will fail because branch `main` does not exist.

**Fix:** Set `init.defaultBranch` explicitly in `_init_git_repo` to eliminate environment dependency:
```python
def _init_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=path, capture_output=True, check=True,
    )
    # ... rest unchanged
```
This ensures all test repos use `main` consistently, making the hardcoded `"main"` references in filter tests and upstream tests correct regardless of the developer's global git config.

## Info

### IN-01: WorktreeInfo lacks `to_dict()` unlike sibling dataclasses

**File:** `src/joy/models.py:136-144`
**Issue:** All other dataclasses in `models.py` (`ObjectItem`, `Project`, `Config`, `Repo`) implement a `to_dict()` method for TOML serialization. `WorktreeInfo` does not. This is likely intentional since `WorktreeInfo` is transient (computed at runtime, not persisted), but the inconsistency may cause confusion for future contributors who expect all model classes to be serializable.

**Fix:** Either add a brief docstring comment explaining why `to_dict()` is omitted (e.g., "Transient -- not persisted to TOML"), or add `to_dict()` for API consistency:
```python
def to_dict(self) -> dict:
    """Serialize to a dict (for display/debugging -- not persisted to TOML)."""
    return {
        "repo_name": self.repo_name,
        "branch": self.branch,
        "path": self.path,
        "is_dirty": self.is_dirty,
        "has_upstream": self.has_upstream,
    }
```

### IN-02: No `__all__` export list in worktrees.py

**File:** `src/joy/worktrees.py:1`
**Issue:** The module exposes `discover_worktrees` as its public API while `_list_worktrees`, `_is_dirty`, and `_has_upstream` are internal (underscore-prefixed). Adding `__all__ = ["discover_worktrees"]` would make the public surface explicit and prevent accidental exposure via wildcard imports.

**Fix:** Add after the imports:
```python
__all__ = ["discover_worktrees"]
```

---

_Reviewed: 2026-04-13T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
