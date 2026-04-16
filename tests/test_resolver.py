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


def make_project(name: str, objects=None, repo=None, iterm_tab_id=None) -> Project:
    return Project(name=name, objects=objects or [], repo=repo, iterm_tab_id=iterm_tab_id)


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
# Test 5: terminal session matched by tab_id on project
# ---------------------------------------------------------------------------


def test_compute_relationships_terminal_by_tab_id():
    """Sessions matched to projects via Project.iterm_tab_id == TerminalSession.tab_id."""
    proj_d = make_project("proj-d", iterm_tab_id="tab-uuid-001")
    sessions = [
        TerminalSession(
            session_id="s1", session_name="claude-joy",
            foreground_process="zsh", cwd="/tmp", tab_id="tab-uuid-001",
        )
    ]

    index = compute_relationships([proj_d], [], sessions, [])

    assert index.terminals_for(proj_d) == [sessions[0]]
    assert index.project_for_terminal("claude-joy") is proj_d


# ---------------------------------------------------------------------------
# Test 5b: TERMINALS object NO LONGER matches sessions (tab_id replaces it)
# ---------------------------------------------------------------------------


def test_compute_relationships_terminals_object_no_longer_matches():
    """PresetKind.TERMINALS objects are ignored by resolver — tab_id matching only."""
    proj = make_project(
        "proj-legacy",
        objects=[ObjectItem(kind=PresetKind.TERMINALS, value="claude-joy")],
    )
    sessions = [make_session("s1", "claude-joy")]

    index = compute_relationships([proj], [], sessions, [])

    # Should NOT match because there's no iterm_tab_id on the project
    assert index.terminals_for(proj) == []
    assert index.project_for_terminal("claude-joy") is None


# ---------------------------------------------------------------------------
# Test 5c: sessions with non-matching tab_id fall through
# ---------------------------------------------------------------------------


def test_compute_relationships_terminal_no_match_by_tab_id():
    """Sessions whose tab_id doesn't match any project fall through."""
    proj = make_project("proj-x", iterm_tab_id="tab-AAA")
    sessions = [
        TerminalSession(
            session_id="s1", session_name="orphan",
            foreground_process="zsh", cwd="/tmp", tab_id="tab-BBB",
        )
    ]

    index = compute_relationships([proj], [], sessions, [])

    assert index.terminals_for(proj) == []
    assert index.project_for_terminal("orphan") is None


# ---------------------------------------------------------------------------
# Test 5d: multiple sessions in same tab matched to same project
# ---------------------------------------------------------------------------


def test_compute_relationships_multiple_sessions_same_tab():
    """All sessions with matching tab_id are associated to the project."""
    proj = make_project("proj-multi", iterm_tab_id="tab-MULTI")
    sessions = [
        TerminalSession(
            session_id="s1", session_name="main",
            foreground_process="zsh", cwd="/tmp", tab_id="tab-MULTI",
        ),
        TerminalSession(
            session_id="s2", session_name="split",
            foreground_process="vim", cwd="/tmp", tab_id="tab-MULTI",
        ),
    ]

    index = compute_relationships([proj], [], sessions, [])

    assert len(index.terminals_for(proj)) == 2


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
