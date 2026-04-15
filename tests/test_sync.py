"""Tests for Phase 15 cross-pane selection sync (SYNC-01..09)."""
from __future__ import annotations

import pytest
from dataclasses import dataclass, field

from joy.resolver import RelationshipIndex, compute_relationships
from joy.models import ObjectItem, PresetKind, Project, Repo, TerminalSession, WorktreeInfo


# ---------------------------------------------------------------------------
# Stub row classes — minimal pure-Python stand-ins for real Textual row widgets
# ---------------------------------------------------------------------------


@dataclass
class FakeRow:
    """Minimal stand-in for WorktreeRow — only the identity fields used by sync_to."""

    repo_name: str
    branch: str
    path: str = ""


@dataclass
class FakeSessionRow:
    """Minimal stand-in for SessionRow — only session_name used by sync_to."""

    session_name: str


@dataclass
class FakeProjectRow:
    """Minimal stand-in for ProjectRow — holds a Project object with .name."""

    project: Project


# ---------------------------------------------------------------------------
# Fake pane base — mirrors the _cursor/_rows/sync_to pattern that Plan 02 will add
# ---------------------------------------------------------------------------


class FakeSyncablePane:
    """Base stub pane with _cursor and _rows. sync_to() is not yet implemented.

    Plan 02 will add sync_to() to the real WorktreePane, TerminalPane, and
    ProjectList classes. These fakes replicate the pattern so tests can assert
    on _cursor mutations without instantiating Textual widgets.
    """

    def __init__(self, rows: list) -> None:
        self._rows = rows
        self._cursor: int = -1

    def _update_highlight_silent(self) -> None:
        """No-op stand-in for _update_highlight() — no DOM in tests."""
        pass

    def sync_to(self, *args, **kwargs) -> None:
        pytest.fail("not implemented — Plan 02 will implement sync_to()")


class FakeWorktreePane(FakeSyncablePane):
    """Fake WorktreePane for SYNC-01, SYNC-06 cursor-position tests."""

    def sync_to(self, repo_name: str, branch: str) -> None:
        pytest.fail("not implemented — Plan 02 will add WorktreePane.sync_to(repo_name, branch)")


class FakeTerminalPane(FakeSyncablePane):
    """Fake TerminalPane for SYNC-02, SYNC-04 cursor-position tests."""

    def sync_to(self, session_name: str) -> None:
        pytest.fail("not implemented — Plan 02 will add TerminalPane.sync_to(session_name)")


class FakeProjectList(FakeSyncablePane):
    """Fake ProjectList for SYNC-03, SYNC-05 cursor-position tests."""

    def sync_to(self, project_name: str) -> None:
        pytest.fail("not implemented — Plan 02 will add ProjectList.sync_to(project_name)")


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------


def _make_project_with_worktree(
    name: str, repo: str, wt_path: str, agents_session: str | None = None
) -> Project:
    objects = [ObjectItem(kind=PresetKind.WORKTREE, value=wt_path, label="wt")]
    if agents_session is not None:
        objects.append(ObjectItem(kind=PresetKind.AGENTS, value=agents_session, label="agents"))
    return Project(name=name, repo=repo, objects=objects)


def _make_worktree(repo_name: str, branch: str, path: str) -> WorktreeInfo:
    return WorktreeInfo(repo_name=repo_name, branch=branch, path=path)


def _make_session(session_id: str, session_name: str) -> TerminalSession:
    return TerminalSession(
        session_id=session_id,
        session_name=session_name,
        foreground_process="zsh",
        cwd="/tmp",
    )


# ---------------------------------------------------------------------------
# SYNC-01: project → worktree sync
# ---------------------------------------------------------------------------


def test_sync_project_to_worktree():
    """SYNC-01: selecting a project moves WorktreePane cursor to the matching worktree row.

    After Plan 02 implements WorktreePane.sync_to(repo_name, branch):
    - Cursor moves to the row whose (repo_name, branch) matches the project's worktree.
    - When no row matches, cursor stays at original position (no-op).
    """
    # Build resolver with project -> worktree relationship
    proj = _make_project_with_worktree("myproject", "myrepo", "/Users/dev/wt/feat-x")
    wt = _make_worktree("myrepo", "feat-x", "/Users/dev/wt/feat-x")
    index = compute_relationships([proj], [wt], [], [])

    # Build fake pane: 3 rows, target at index 1
    row0 = FakeRow(repo_name="other-repo", branch="main", path="/Users/dev/other")
    row1 = FakeRow(repo_name="myrepo", branch="feat-x", path="/Users/dev/wt/feat-x")
    row2 = FakeRow(repo_name="third-repo", branch="develop", path="/Users/dev/third")
    pane = FakeWorktreePane([row0, row1, row2])

    worktrees = index.worktrees_for(proj)
    assert len(worktrees) == 1, "resolver must find the worktree"

    # Happy path: sync_to should move cursor to index 1
    # (fails RED until Plan 02 adds sync_to implementation)
    pane.sync_to(worktrees[0].repo_name, worktrees[0].branch)

    # Assertions run only if sync_to doesn't fail (Plan 02 GREEN)
    assert pane._cursor == 1  # target row at index 1

    # No-match case: cursor stays at 0
    pane._cursor = 0
    pane.sync_to("nonexistent-repo", "nonexistent-branch")
    assert pane._cursor == 0  # cursor unchanged


# ---------------------------------------------------------------------------
# SYNC-02: project → terminal sync
# ---------------------------------------------------------------------------


def test_sync_project_to_terminal():
    """SYNC-02: selecting a project moves TerminalPane cursor to the matching session row.

    After Plan 02 implements TerminalPane.sync_to(session_name):
    - Cursor moves to the row whose session_name matches.
    - When no row matches, cursor stays at original position.
    """
    # Build resolver with project -> agent relationship
    proj = Project(
        name="myproject",
        repo="myrepo",
        objects=[ObjectItem(kind=PresetKind.AGENTS, value="myrepo-agents", label="agents")],
    )
    session = _make_session("s1", "myrepo-agents")
    index = compute_relationships([proj], [], [session], [])

    # Build fake pane: 3 rows, target at index 1
    row0 = FakeSessionRow(session_name="other-session")
    row1 = FakeSessionRow(session_name="myrepo-agents")
    row2 = FakeSessionRow(session_name="third-session")
    pane = FakeTerminalPane([row0, row1, row2])

    agents = index.agents_for(proj)
    assert len(agents) == 1, "resolver must find the agent session"

    # Happy path: sync_to should move cursor to index 1
    pane.sync_to(agents[0].session_name)
    assert pane._cursor == 1

    # No-match case: cursor stays at 0
    pane._cursor = 0
    pane.sync_to("no-such-session")
    assert pane._cursor == 0  # cursor unchanged


# ---------------------------------------------------------------------------
# SYNC-03: worktree → project sync
# ---------------------------------------------------------------------------


def test_sync_worktree_to_project():
    """SYNC-03: selecting a worktree moves ProjectList cursor to the owning project row.

    After Plan 02 implements ProjectList.sync_to(project_name):
    - Cursor moves to the row whose project.name matches.
    - When no row matches, cursor stays at original position.
    """
    proj_a = _make_project_with_worktree("proj-a", "repo-a", "/tmp/wt-a")
    wt_a = _make_worktree("repo-a", "feat-a", "/tmp/wt-a")
    index = compute_relationships([proj_a], [wt_a], [], [])

    # Build fake pane: 3 rows, target at index 1
    proj_other = Project(name="other-project")
    row0 = FakeProjectRow(project=proj_other)
    row1 = FakeProjectRow(project=proj_a)
    proj_third = Project(name="third-project")
    row2 = FakeProjectRow(project=proj_third)
    pane = FakeProjectList([row0, row1, row2])

    matched_project = index.project_for_worktree(wt_a)
    assert matched_project is not None, "resolver must find the owning project"

    # Happy path: sync_to should move cursor to index 1
    pane.sync_to(matched_project.name)
    assert pane._cursor == 1

    # No-match case: cursor stays at 0
    pane._cursor = 0
    pane.sync_to("no-such-project")
    assert pane._cursor == 0  # cursor unchanged


# ---------------------------------------------------------------------------
# SYNC-04: worktree → terminal sync (via shared project)
# ---------------------------------------------------------------------------


def test_sync_worktree_to_terminal():
    """SYNC-04: selecting a worktree moves TerminalPane cursor to the agent session of the owning project.

    After Plan 02: when a worktree row is highlighted, find its project via
    project_for_worktree(), then find agents_for(project) and sync TerminalPane.
    """
    # Project owns both a worktree and an agent session
    proj = _make_project_with_worktree(
        "myproject", "myrepo", "/tmp/wt-feat", agents_session="myrepo-agents"
    )
    wt = _make_worktree("myrepo", "feat", "/tmp/wt-feat")
    session = _make_session("s1", "myrepo-agents")
    index = compute_relationships([proj], [wt], [session], [])

    # Build terminal pane: 3 rows, target at index 1
    row0 = FakeSessionRow(session_name="other-session")
    row1 = FakeSessionRow(session_name="myrepo-agents")
    row2 = FakeSessionRow(session_name="third-session")
    pane = FakeTerminalPane([row0, row1, row2])

    matched_project = index.project_for_worktree(wt)
    assert matched_project is not None
    agents = index.agents_for(matched_project)
    assert len(agents) == 1

    # Happy path: sync_to should move cursor to index 1
    pane.sync_to(agents[0].session_name)
    assert pane._cursor == 1


# ---------------------------------------------------------------------------
# SYNC-05: agent → project sync
# ---------------------------------------------------------------------------


def test_sync_agent_to_project():
    """SYNC-05: selecting an agent session moves ProjectList cursor to the owning project.

    Mirror of SYNC-03 but triggered from agent->project path.
    """
    proj = Project(
        name="myproject",
        repo="myrepo",
        objects=[ObjectItem(kind=PresetKind.AGENTS, value="myrepo-agents", label="agents")],
    )
    session = _make_session("s1", "myrepo-agents")
    index = compute_relationships([proj], [], [session], [])

    # Build fake project list: 3 rows, target at index 1
    proj_other = Project(name="other-project")
    row0 = FakeProjectRow(project=proj_other)
    row1 = FakeProjectRow(project=proj)
    proj_third = Project(name="third-project")
    row2 = FakeProjectRow(project=proj_third)
    pane = FakeProjectList([row0, row1, row2])

    matched_project = index.project_for_agent(session.session_name)
    assert matched_project is not None

    # Happy path: sync_to should move cursor to index 1
    pane.sync_to(matched_project.name)
    assert pane._cursor == 1

    # No-match case: cursor stays at 0
    pane._cursor = 0
    pane.sync_to("no-such-project")
    assert pane._cursor == 0  # cursor unchanged


# ---------------------------------------------------------------------------
# SYNC-06: agent → worktree sync (via shared project)
# ---------------------------------------------------------------------------


def test_sync_agent_to_worktree():
    """SYNC-06: selecting an agent session moves WorktreePane cursor to the project's worktree.

    Mirror of SYNC-01 but triggered from agent->worktree path.
    """
    proj = _make_project_with_worktree(
        "myproject", "myrepo", "/tmp/wt-feat", agents_session="myrepo-agents"
    )
    wt = _make_worktree("myrepo", "feat", "/tmp/wt-feat")
    session = _make_session("s1", "myrepo-agents")
    index = compute_relationships([proj], [wt], [session], [])

    # Build fake worktree pane: 3 rows, target at index 1
    row0 = FakeRow(repo_name="other-repo", branch="main", path="/tmp/other")
    row1 = FakeRow(repo_name="myrepo", branch="feat", path="/tmp/wt-feat")
    row2 = FakeRow(repo_name="third-repo", branch="develop", path="/tmp/third")
    pane = FakeWorktreePane([row0, row1, row2])

    matched_project = index.project_for_agent(session.session_name)
    assert matched_project is not None
    worktrees = index.worktrees_for(matched_project)
    assert len(worktrees) == 1

    # Happy path: sync_to should move cursor to index 1
    pane.sync_to(worktrees[0].repo_name, worktrees[0].branch)
    assert pane._cursor == 1


# ---------------------------------------------------------------------------
# SYNC-07: sync_to does not steal focus
# ---------------------------------------------------------------------------


def test_sync_does_not_steal_focus():
    """SYNC-07: sync_to() moves the cursor but does NOT call focus().

    This test verifies that the sync_to method exists on the real widget classes
    after Plan 02 implements it. The full focus-non-interference assertion is
    deferred to Plan 02 GREEN phase.

    TODO (Plan 02 GREEN): assert that calling sync_to() on real WorktreePane,
    TerminalPane, and ProjectList does NOT set app.focused or call .focus().
    """
    # For now: verify the real widget classes will have sync_to after Plan 02.
    # Import may fail if Textual requires a display — guarded with try/except.
    # Plan 02 will add sync_to to these classes; at that point this import succeeds.
    try:
        from joy.widgets.worktree_pane import WorktreePane
        from joy.widgets.terminal_pane import TerminalPane
        from joy.widgets.project_list import ProjectList

        # After Plan 02 GREEN: these attributes must exist
        # For now: fail to confirm RED state until Plan 02 adds sync_to
        pytest.fail(
            "not implemented yet — Plan 02 will add sync_to to WorktreePane, "
            "TerminalPane, and ProjectList. This test becomes green in Plan 02."
        )
    except ImportError:
        pytest.skip("Textual widget import failed (display not available)")


# ---------------------------------------------------------------------------
# SYNC-08: toggle sync key binding
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_toggle_sync_key():
    """SYNC-08: pressing 'x' toggles sync mode on/off.

    Requires TUI pilot (app.run_async + Pilot.press). Stub — Plan 03 will
    implement the full TUI pilot test with app.check_action() verification.
    """
    pytest.fail("not implemented — requires TUI pilot in Plan 03")


# ---------------------------------------------------------------------------
# SYNC-09: toggle sync footer visibility
# ---------------------------------------------------------------------------


def test_toggle_sync_footer_visibility():
    """SYNC-09: footer shows 'Sync: on' / 'Sync: off' based on sync toggle state.

    Requires app.check_action() and footer label inspection. Stub — Plan 03
    will implement full footer visibility test.
    """
    pytest.fail("not implemented — requires app.check_action() in Plan 03")
