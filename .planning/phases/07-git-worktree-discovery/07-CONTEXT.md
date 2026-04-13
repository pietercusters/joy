# Phase 7: Git Worktree Discovery - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

A standalone pure-logic Python module that discovers all active git worktrees across registered repos, checks dirty and upstream tracking status per worktree, and applies branch filters. No UI. Consumed by Phase 9 (Worktree Pane display) and Phase 10 (Background Refresh Engine).

</domain>

<decisions>
## Implementation Decisions

### Branch Filter Matching
- **D-01:** Exact string match only — `branch == filter_value`. No fnmatch/glob patterns. The default `["main", "testing"]` covers the common case; users add exact branch names they want filtered. Simpler, predictable, no surprise matches.

### Error Handling
- **D-02:** Silent skip — when a registered repo path is missing, inaccessible, or any git subprocess fails, omit that repo's worktrees from results entirely. Return partial results for other repos. Phase 10 (background refresh caller) can log a warning if needed; this module stays pure.

### Claude's Discretion
- **WorktreeInfo model location:** Place `WorktreeInfo` dataclass in `models.py` alongside `Repo` — consistent with the established pattern (pure data in models.py, I/O in separate modules). Phase 9 imports it for display, Phase 10 for caching.
- **Git command strategy:** Use `git worktree list --porcelain` for discovery, `git -C <path> diff-index --quiet HEAD --` for dirty detection, `git -C <path> rev-parse --abbrev-ref --symbolic-full-name @{u}` for upstream tracking. These are stable plumbing commands designed for scripting.
- **Module file name:** `src/joy/worktrees.py` — matches the domain name.
- **Public API shape:** A single function `discover_worktrees(repos: list[Repo], branch_filter: list[str]) -> list[WorktreeInfo]`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` §Phase 7 — Goal, success criteria, requirements WKTR-01, WKTR-04, WKTR-05, WKTR-06

### Existing data models and patterns
- `src/joy/models.py` — `Repo` dataclass, `Config.branch_filter` (this phase adds `WorktreeInfo` to this file)
- `src/joy/store.py` — subprocess calling pattern (`get_remote_url`, `validate_repo_path`), atomic write pattern, `load_repos()` which provides the repo list input

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Repo(name, local_path, remote_url, forge)` in `models.py` — the input type for discovery
- `Config.branch_filter: list[str]` in `models.py` — the filter list to apply
- `load_repos(path=REPOS_PATH) -> list[Repo]` in `store.py` — how callers get repos to pass in
- `subprocess.run(["git", ...], capture_output=True, text=True)` pattern from `store.py:get_remote_url` — exact pattern to follow for git calls

### Established Patterns
- Pure data in `models.py` (no I/O), I/O in separate modules — `WorktreeInfo` goes in models.py, discovery logic in `worktrees.py`
- `subprocess.run` with `capture_output=True, text=True, check=False` — callers inspect returncode
- Tests in `tests/` with pytest; real subprocess calls (no mocking git), use temp dirs for isolation

### Integration Points
- Phase 9 (Worktree Pane) imports `WorktreeInfo` from `models.py` and calls `discover_worktrees()` from `worktrees.py`
- Phase 10 (Background Refresh) calls `discover_worktrees()` on a timer; silent-skip behavior means partial results on transient errors are safe

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for git plumbing commands and pytest fixture patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-git-worktree-discovery*
*Context gathered: 2026-04-13*
