"""Tests for git worktree discovery module."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from joy.models import Repo, WorktreeInfo
from joy.worktrees import discover_worktrees


# ---------------------------------------------------------------------------
# Test fixture helpers — real git repos in temp directories
# ---------------------------------------------------------------------------


def _init_git_repo(path: Path) -> None:
    """Initialize a git repo with an initial commit at the given path."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    (path / "README.md").write_text("init")
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=path, capture_output=True, check=True
    )


def _add_worktree(repo_path: Path, wt_path: Path, branch: str) -> None:
    """Add a linked worktree at wt_path for the given branch."""
    subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(wt_path)],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )


def _make_dirty(wt_path: Path) -> None:
    """Create a tracked file modification to make the worktree dirty."""
    readme = wt_path / "README.md"
    readme.write_text(readme.read_text() + "\nmodified")


def _setup_upstream(repo_path: Path, branch: str) -> None:
    """Create a bare remote and set upstream tracking for the given branch."""
    remote_path = repo_path.parent / (repo_path.name + "-remote.git")
    subprocess.run(
        ["git", "init", "--bare", str(remote_path)],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "remote", "add", "origin", str(remote_path)],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "push", "-u", "origin", branch],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDiscoverWorktrees:
    """Comprehensive tests for discover_worktrees covering WKTR-01, 04, 05, 06 + D-01, D-02."""

    # --- WKTR-01: Worktree discovery ---

    def test_single_repo_one_worktree(self, tmp_path: Path) -> None:
        """Single repo with only main worktree returns one WorktreeInfo."""
        repo_dir = tmp_path / "myrepo"
        _init_git_repo(repo_dir)
        repos = [Repo(name="myrepo", local_path=str(repo_dir))]

        result = discover_worktrees(repos)

        assert len(result) == 1
        wt = result[0]
        assert wt.repo_name == "myrepo"
        assert wt.branch == "main" or wt.branch == "master"
        assert wt.path == str(repo_dir)

    def test_single_repo_multiple_worktrees(self, tmp_path: Path) -> None:
        """Single repo with linked worktrees returns all worktrees."""
        repo_dir = tmp_path / "myrepo"
        _init_git_repo(repo_dir)
        wt_feat = tmp_path / "wt-feature"
        _add_worktree(repo_dir, wt_feat, "feature-x")

        repos = [Repo(name="myrepo", local_path=str(repo_dir))]
        result = discover_worktrees(repos)

        assert len(result) == 2
        branches = {wt.branch for wt in result}
        assert "feature-x" in branches

    def test_multiple_repos(self, tmp_path: Path) -> None:
        """Multiple repos — returns worktrees from all repos combined."""
        repo_a = tmp_path / "repo-a"
        repo_b = tmp_path / "repo-b"
        _init_git_repo(repo_a)
        _init_git_repo(repo_b)

        repos = [
            Repo(name="alpha", local_path=str(repo_a)),
            Repo(name="beta", local_path=str(repo_b)),
        ]
        result = discover_worktrees(repos)

        assert len(result) == 2
        repo_names = {wt.repo_name for wt in result}
        assert repo_names == {"alpha", "beta"}

    def test_empty_repo_list(self) -> None:
        """Empty repo list returns empty list."""
        result = discover_worktrees([])
        assert result == []

    def test_repo_with_only_main_worktree(self, tmp_path: Path) -> None:
        """Repo with only main worktree (no extra) returns the main worktree."""
        repo_dir = tmp_path / "solo"
        _init_git_repo(repo_dir)
        repos = [Repo(name="solo", local_path=str(repo_dir))]

        result = discover_worktrees(repos)

        assert len(result) == 1
        assert result[0].repo_name == "solo"
        assert result[0].path == str(repo_dir)

    # --- WKTR-04: Dirty detection ---

    def test_clean_worktree_not_dirty(self, tmp_path: Path) -> None:
        """Clean worktree has is_dirty=False."""
        repo_dir = tmp_path / "clean"
        _init_git_repo(repo_dir)
        repos = [Repo(name="clean", local_path=str(repo_dir))]

        result = discover_worktrees(repos)

        assert len(result) == 1
        assert result[0].is_dirty is False

    def test_staged_change_is_dirty(self, tmp_path: Path) -> None:
        """Worktree with uncommitted staged change has is_dirty=True."""
        repo_dir = tmp_path / "staged"
        _init_git_repo(repo_dir)
        # Modify a tracked file and stage it (but don't commit)
        (repo_dir / "README.md").write_text("staged change")
        subprocess.run(
            ["git", "add", "README.md"], cwd=repo_dir, capture_output=True, check=True
        )

        repos = [Repo(name="staged", local_path=str(repo_dir))]
        result = discover_worktrees(repos)

        assert len(result) == 1
        assert result[0].is_dirty is True

    def test_unstaged_modification_is_dirty(self, tmp_path: Path) -> None:
        """Worktree with unstaged modification has is_dirty=True."""
        repo_dir = tmp_path / "unstaged"
        _init_git_repo(repo_dir)
        _make_dirty(repo_dir)

        repos = [Repo(name="unstaged", local_path=str(repo_dir))]
        result = discover_worktrees(repos)

        assert len(result) == 1
        assert result[0].is_dirty is True

    def test_untracked_file_not_dirty(self, tmp_path: Path) -> None:
        """Worktree with untracked file only has is_dirty=False.

        git diff-index only checks tracked files; untracked files are NOT flagged.
        """
        repo_dir = tmp_path / "untracked"
        _init_git_repo(repo_dir)
        (repo_dir / "newfile.txt").write_text("untracked content")

        repos = [Repo(name="untracked", local_path=str(repo_dir))]
        result = discover_worktrees(repos)

        assert len(result) == 1
        assert result[0].is_dirty is False

    # --- WKTR-05: Upstream tracking ---

    def test_branch_with_upstream_has_upstream_true(self, tmp_path: Path) -> None:
        """Branch with upstream tracking ref has has_upstream=True."""
        repo_dir = tmp_path / "upstream"
        _init_git_repo(repo_dir)
        _setup_upstream(repo_dir, "main")

        repos = [Repo(name="upstream", local_path=str(repo_dir))]
        result = discover_worktrees(repos)

        assert len(result) == 1
        assert result[0].has_upstream is True

    def test_branch_without_upstream_has_upstream_false(self, tmp_path: Path) -> None:
        """Branch with no upstream (local-only, never pushed) has has_upstream=False."""
        repo_dir = tmp_path / "noupstream"
        _init_git_repo(repo_dir)
        # No remote configured — main has no upstream

        repos = [Repo(name="noupstream", local_path=str(repo_dir))]
        result = discover_worktrees(repos)

        assert len(result) == 1
        assert result[0].has_upstream is False

    # --- WKTR-06: Branch filter ---

    def test_filter_excludes_matching_branches(self, tmp_path: Path) -> None:
        """Worktrees on branches matching filter are excluded."""
        repo_dir = tmp_path / "filtered"
        _init_git_repo(repo_dir)
        wt_feat = tmp_path / "wt-feature"
        _add_worktree(repo_dir, wt_feat, "feature-y")

        repos = [Repo(name="filtered", local_path=str(repo_dir))]
        result = discover_worktrees(repos, branch_filter=["main"])

        # Only feature-y should remain, main is filtered out
        assert len(result) == 1
        assert result[0].branch == "feature-y"

    def test_filter_exact_match_not_substring(self, tmp_path: Path) -> None:
        """Filter uses exact match per D-01 — 'main' does NOT exclude 'main-feature'."""
        repo_dir = tmp_path / "exact"
        _init_git_repo(repo_dir)
        wt_main_feat = tmp_path / "wt-main-feature"
        _add_worktree(repo_dir, wt_main_feat, "main-feature")

        repos = [Repo(name="exact", local_path=str(repo_dir))]
        result = discover_worktrees(repos, branch_filter=["main"])

        # main is filtered, but main-feature is NOT (exact match only)
        branches = {wt.branch for wt in result}
        assert "main-feature" in branches
        assert "main" not in branches

    def test_empty_filter_returns_all(self, tmp_path: Path) -> None:
        """Empty filter list means no filtering — all worktrees returned."""
        repo_dir = tmp_path / "nofilter"
        _init_git_repo(repo_dir)
        wt_feat = tmp_path / "wt-dev"
        _add_worktree(repo_dir, wt_feat, "dev")

        repos = [Repo(name="nofilter", local_path=str(repo_dir))]
        result = discover_worktrees(repos, branch_filter=[])

        assert len(result) == 2

    # --- D-02: Error handling ---

    def test_nonexistent_repo_path_silently_skipped(self, tmp_path: Path) -> None:
        """Repo with nonexistent local_path is silently skipped."""
        # One valid repo, one invalid
        valid_repo = tmp_path / "valid"
        _init_git_repo(valid_repo)

        repos = [
            Repo(name="bad", local_path="/nonexistent/path/12345"),
            Repo(name="good", local_path=str(valid_repo)),
        ]
        result = discover_worktrees(repos)

        assert len(result) == 1
        assert result[0].repo_name == "good"

    def test_all_repos_invalid_returns_empty(self) -> None:
        """All repos invalid returns empty list (no exception raised)."""
        repos = [
            Repo(name="bad1", local_path="/nonexistent/path/aaa"),
            Repo(name="bad2", local_path="/nonexistent/path/bbb"),
        ]
        result = discover_worktrees(repos)
        assert result == []
