"""Git worktree discovery for registered repos. No UI, no persistence."""
from __future__ import annotations

import subprocess

from joy.models import Repo, WorktreeInfo


def _list_worktrees(repo_path: str) -> list[tuple[str, str]]:
    """List active worktrees via ``git worktree list --porcelain``.

    Returns a list of ``(path, branch)`` tuples.  Branch is the short name
    (``refs/heads/`` prefix stripped).  For detached HEAD the branch is
    ``"HEAD"``.  Returns ``[]`` on any subprocess error.
    """
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return []
    except (subprocess.TimeoutExpired, OSError):
        return []

    worktrees: list[tuple[str, str]] = []
    # Porcelain blocks are separated by blank lines
    blocks = result.stdout.strip().split("\n\n")
    for block in blocks:
        if not block.strip():
            continue
        path = ""
        branch = ""
        is_bare = False
        for line in block.splitlines():
            if line.startswith("worktree "):
                path = line[len("worktree ") :]
            elif line.startswith("branch "):
                ref = line[len("branch ") :]
                # Strip refs/heads/ prefix to get short branch name
                if ref.startswith("refs/heads/"):
                    branch = ref[len("refs/heads/") :]
                else:
                    branch = ref
            elif line == "detached":
                branch = "HEAD"
            elif line == "bare":
                is_bare = True
        if path and not is_bare:
            worktrees.append((path, branch))
    return worktrees


def _is_dirty(worktree_path: str) -> bool:
    """Check if a worktree has uncommitted changes to tracked files.

    Uses ``git diff-index --quiet HEAD --`` which exits 0 for clean, 1 for
    dirty.  Only checks tracked files — untracked files are NOT flagged.
    Returns ``False`` (assume clean) on any subprocess error.
    """
    try:
        result = subprocess.run(
            ["git", "-C", worktree_path, "diff-index", "--quiet", "HEAD", "--"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode != 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def _has_upstream(worktree_path: str) -> bool:
    """Check if the current branch tracks a remote upstream.

    Uses ``git rev-parse --abbrev-ref --symbolic-full-name @{u}`` which
    succeeds when an upstream is configured and fails (exit 128) when not.
    Returns ``False`` (assume no upstream) on any subprocess error.
    """
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                worktree_path,
                "rev-parse",
                "--abbrev-ref",
                "--symbolic-full-name",
                "@{u}",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, OSError):
        return False


def discover_worktrees(
    repos: list[Repo],
    branch_filter: list[str] | None = None,
) -> list[WorktreeInfo]:
    """Discover all active git worktrees across registered repos.

    Parameters
    ----------
    repos:
        List of :class:`Repo` objects (from ``load_repos()``).
    branch_filter:
        Exact branch names to **exclude** from results.  ``None`` or ``[]``
        means no filtering.  Uses exact string match per D-01 — no
        glob/fnmatch.

    Returns
    -------
    list[WorktreeInfo]
        All active worktrees across all valid repos, minus filtered branches.
        Per D-02, repos with missing paths or git errors are silently skipped.
    """
    filter_set = set(branch_filter) if branch_filter else set()
    results: list[WorktreeInfo] = []

    for repo in repos:
        worktrees = _list_worktrees(repo.local_path)
        # _list_worktrees returns [] on any error — invalid repos silently
        # skipped per D-02
        for path, branch in worktrees:
            if branch in filter_set:  # exact match per D-01
                continue
            results.append(
                WorktreeInfo(
                    repo_name=repo.name,
                    branch=branch,
                    path=path,
                    is_dirty=_is_dirty(path),
                    has_upstream=_has_upstream(path),
                )
            )

    return results
