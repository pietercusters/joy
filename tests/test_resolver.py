"""Tests for the cross-pane relationship resolver (Phase 14, Plan 01).

All tests are pure Python — no TUI, no I/O, no mocking needed.
"""
from __future__ import annotations

import pytest

from joy.models import ObjectItem, PresetKind, Project, Repo, TerminalSession, WorktreeInfo
from joy.resolver import RelationshipIndex, compute_relationships


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def make_project(name: str, objects=None, repo=None) -> Project:
    return Project(name=name, objects=objects or [], repo=repo)


def make_worktree(repo_name: str, branch: str, path: str) -> WorktreeInfo:
    return WorktreeInfo(repo_name=repo_name, branch=branch, path=path)


def make_session(session_id: str, session_name: str) -> TerminalSession:
    return TerminalSession(
        session_id=session_id,
        session_name=session_name,
        foreground_process="zsh",
        cwd="/tmp",
    )


# ---------------------------------------------------------------------------
# Test 1: worktree matched by WORKTREE path object
# ---------------------------------------------------------------------------


def test_compute_relationships_worktree_by_path():
    proj_a = make_project(
        "proj-a",
        objects=[ObjectItem(kind=PresetKind.WORKTREE, value="/tmp/wt-a")],
    )
    worktrees = [make_worktree("repo-a", "feat-x", "/tmp/wt-a")]

    index = compute_relationships([proj_a], worktrees, [], [])

    assert index.worktrees_for(proj_a) == [worktrees[0]]
    assert index.project_for_worktree(worktrees[0]) is proj_a


# ---------------------------------------------------------------------------
# Test 2: worktree matched by BRANCH object + project.repo
# ---------------------------------------------------------------------------


def test_compute_relationships_worktree_by_branch():
    proj_b = make_project(
        "proj-b",
        objects=[ObjectItem(kind=PresetKind.BRANCH, value="feat-y")],
        repo="repo-b",
    )
    worktrees = [make_worktree("repo-b", "feat-y", "/tmp/wt-b")]

    index = compute_relationships([proj_b], worktrees, [], [])

    assert index.worktrees_for(proj_b) == [worktrees[0]]
    assert index.project_for_worktree(worktrees[0]) is proj_b


# ---------------------------------------------------------------------------
# Test 3: path match takes precedence over branch match (D-04)
# ---------------------------------------------------------------------------


def test_compute_relationships_path_takes_precedence_over_branch():
    proj_a = make_project(
        "proj-a",
        objects=[
            ObjectItem(kind=PresetKind.WORKTREE, value="/tmp/wt-shared"),
            ObjectItem(kind=PresetKind.BRANCH, value="feat-y"),
        ],
        repo="repo-shared",
    )
    proj_b = make_project(
        "proj-b",
        objects=[ObjectItem(kind=PresetKind.BRANCH, value="feat-y")],
        repo="repo-shared",
    )
    worktrees = [make_worktree("repo-shared", "feat-y", "/tmp/wt-shared")]

    index = compute_relationships([proj_a, proj_b], worktrees, [], [])

    # Path match wins — proj_a owns this worktree
    assert index.project_for_worktree(worktrees[0]) is proj_a


# ---------------------------------------------------------------------------
# Test 4: projects with no repo excluded from branch-based matching (D-05)
# ---------------------------------------------------------------------------


def test_compute_relationships_no_repo_excludes_branch_match():
    proj_c = make_project(
        "proj-c",
        objects=[ObjectItem(kind=PresetKind.BRANCH, value="feat-z")],
        repo=None,  # no repo — must not match by branch
    )
    worktrees = [make_worktree("repo-c", "feat-z", "/tmp/wt-c")]

    index = compute_relationships([proj_c], worktrees, [], [])

    assert index.worktrees_for(proj_c) == []


# ---------------------------------------------------------------------------
# Test 5: agent session matched by AGENTS object value = session_name
# ---------------------------------------------------------------------------


def test_compute_relationships_agent_by_session_name():
    proj_d = make_project(
        "proj-d",
        objects=[ObjectItem(kind=PresetKind.TERMINALS, value="claude-joy")],
    )
    sessions = [make_session("s1", "claude-joy")]

    index = compute_relationships([proj_d], [], sessions, [])

    assert index.terminals_for(proj_d) == [sessions[0]]
    assert index.project_for_terminal("claude-joy") is proj_d


# ---------------------------------------------------------------------------
# Test 6: no match returns empty / None
# ---------------------------------------------------------------------------


def test_compute_relationships_no_match_returns_empty():
    proj_e = make_project("proj-e")  # no objects at all

    index = compute_relationships([proj_e], [], [], [])

    assert index.worktrees_for(proj_e) == []
    assert index.terminals_for(proj_e) == []
    assert index.project_for_worktree(make_worktree("r", "b", "/p")) is None
    assert index.project_for_terminal("no-match") is None


# ---------------------------------------------------------------------------
# Test 7: empty inputs don't crash
# ---------------------------------------------------------------------------


def test_compute_relationships_empty_inputs():
    index = compute_relationships([], [], [], [])
    assert isinstance(index, RelationshipIndex)
