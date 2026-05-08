"""Tests for PaneCoordinator sync service (Phase 19, SRVC-01, TEST-01).

All tests are pure Python — no TUI, no Textual, no pilot.
Uses fake pane objects and real RelationshipIndex from resolver.
"""
from __future__ import annotations

from joy.models import ObjectItem, PresetKind, Project, Repo, TerminalSession, WorktreeInfo
from joy.pane_coordinator import PaneCoordinator
from joy.resolver import compute_relationships


# ---------------------------------------------------------------------------
# Fake pane helpers
# ---------------------------------------------------------------------------


class FakeWorktreePane:
    def __init__(self):
        self.synced_to: tuple[str, str] | None = None
        self.cleared = False

    def sync_to(self, repo_name: str, branch: str) -> bool:
        self.synced_to = (repo_name, branch)
        return True

    def clear_selection(self) -> None:
        self.cleared = True


class FakeTerminalPane:
    def __init__(self):
        self.synced_to: str | None = None
        self.cleared = False

    def sync_to(self, session_name: str) -> bool:
        self.synced_to = session_name
        return True

    def clear_selection(self) -> None:
        self.cleared = True


class FakeProjectList:
    def __init__(self):
        self.synced_to: str | None = None

    def sync_to(self, project_name: str) -> bool:
        self.synced_to = project_name
        return True


class FakeDetailPane:
    def __init__(self):
        self.set_project_calls: list[tuple] = []

    def set_project(self, project, resolver_worktrees=None, resolver_terminals=None):
        self.set_project_calls.append((project, resolver_worktrees, resolver_terminals))


class NoMatchWorktreePane(FakeWorktreePane):
    """A worktree pane that never finds a match."""
    def sync_to(self, repo_name: str, branch: str) -> bool:
        self.synced_to = (repo_name, branch)
        return False


class NoMatchTerminalPane(FakeTerminalPane):
    """A terminal pane that never finds a match."""
    def sync_to(self, session_name: str) -> bool:
        self.synced_to = session_name
        return False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_index():
    """Build a RelationshipIndex with one project linked to a worktree and terminal."""
    project = Project(
        name="myproject",
        objects=[
            ObjectItem(kind=PresetKind.WORKTREE, value="/tmp/wt/feature"),
            ObjectItem(kind=PresetKind.BRANCH, value="feature-x"),
        ],
        repo="myrepo",
        iterm_tab_id="tab-1",
    )
    repos = [Repo(name="myrepo", local_path="/tmp/repo")]
    worktrees = [
        WorktreeInfo(repo_name="myrepo", branch="feature-x", path="/tmp/wt/feature"),
    ]
    sessions = [
        TerminalSession(session_id="s1", session_name="dev-session", foreground_process="zsh", cwd="/tmp", tab_id="tab-1"),
    ]
    return compute_relationships([project], worktrees, sessions, repos), project, worktrees, sessions


def _make_empty_index():
    """Build a RelationshipIndex with no matches."""
    return compute_relationships([], [], [], [])


# ---------------------------------------------------------------------------
# TestPaneCoordinator
# ---------------------------------------------------------------------------


class TestPaneCoordinator:
    def test_sync_from_project_matches_worktree(self):
        rel_index, project, _, _ = _make_index()
        coord = PaneCoordinator()
        wt_pane = FakeWorktreePane()
        term_pane = FakeTerminalPane()

        coord.sync_from_project(project, rel_index, wt_pane, term_pane)

        assert wt_pane.synced_to == ("myrepo", "feature-x")
        assert not wt_pane.cleared

    def test_sync_from_project_matches_terminal(self):
        rel_index, project, _, _ = _make_index()
        coord = PaneCoordinator()
        wt_pane = FakeWorktreePane()
        term_pane = FakeTerminalPane()

        coord.sync_from_project(project, rel_index, wt_pane, term_pane)

        assert term_pane.synced_to == "dev-session"
        assert not term_pane.cleared

    def test_sync_from_project_clears_unmatched_panes(self):
        empty_index = _make_empty_index()
        unlinked = Project(name="unlinked")
        coord = PaneCoordinator()
        wt_pane = FakeWorktreePane()
        term_pane = FakeTerminalPane()

        coord.sync_from_project(unlinked, empty_index, wt_pane, term_pane)

        assert wt_pane.cleared
        assert term_pane.cleared

    def test_sync_from_project_clears_on_no_match(self):
        rel_index, project, _, _ = _make_index()
        coord = PaneCoordinator()
        wt_pane = NoMatchWorktreePane()
        term_pane = NoMatchTerminalPane()

        coord.sync_from_project(project, rel_index, wt_pane, term_pane)

        assert wt_pane.cleared
        assert term_pane.cleared

    def test_sync_from_worktree_finds_project(self):
        rel_index, project, worktrees, _ = _make_index()
        coord = PaneCoordinator()
        project_list = FakeProjectList()
        detail_pane = FakeDetailPane()
        term_pane = FakeTerminalPane()

        coord.sync_from_worktree(worktrees[0], rel_index, project_list, detail_pane, term_pane)

        assert project_list.synced_to == "myproject"
        assert len(detail_pane.set_project_calls) == 1
        assert detail_pane.set_project_calls[0][0].name == "myproject"

    def test_sync_from_worktree_syncs_terminal(self):
        rel_index, _, worktrees, _ = _make_index()
        coord = PaneCoordinator()
        project_list = FakeProjectList()
        detail_pane = FakeDetailPane()
        term_pane = FakeTerminalPane()

        coord.sync_from_worktree(worktrees[0], rel_index, project_list, detail_pane, term_pane)

        assert term_pane.synced_to == "dev-session"

    def test_sync_from_worktree_clears_when_no_project(self):
        empty_index = _make_empty_index()
        unlinked_wt = WorktreeInfo(repo_name="other", branch="main", path="/tmp/other")
        coord = PaneCoordinator()
        project_list = FakeProjectList()
        detail_pane = FakeDetailPane()
        term_pane = FakeTerminalPane()

        coord.sync_from_worktree(unlinked_wt, empty_index, project_list, detail_pane, term_pane)

        assert term_pane.cleared
        assert project_list.synced_to is None

    def test_sync_from_session_finds_project(self):
        rel_index, _, _, _ = _make_index()
        coord = PaneCoordinator()
        project_list = FakeProjectList()
        detail_pane = FakeDetailPane()
        wt_pane = FakeWorktreePane()

        coord.sync_from_session("dev-session", rel_index, project_list, detail_pane, wt_pane)

        assert project_list.synced_to == "myproject"
        assert len(detail_pane.set_project_calls) == 1

    def test_sync_from_session_syncs_worktree(self):
        rel_index, _, _, _ = _make_index()
        coord = PaneCoordinator()
        project_list = FakeProjectList()
        detail_pane = FakeDetailPane()
        wt_pane = FakeWorktreePane()

        coord.sync_from_session("dev-session", rel_index, project_list, detail_pane, wt_pane)

        assert wt_pane.synced_to == ("myrepo", "feature-x")

    def test_sync_from_session_clears_when_no_project(self):
        empty_index = _make_empty_index()
        coord = PaneCoordinator()
        project_list = FakeProjectList()
        detail_pane = FakeDetailPane()
        wt_pane = FakeWorktreePane()

        coord.sync_from_session("unknown", empty_index, project_list, detail_pane, wt_pane)

        assert wt_pane.cleared
        assert project_list.synced_to is None

    def test_syncing_context_manager(self):
        coord = PaneCoordinator()
        assert not coord.is_syncing
        with coord.syncing():
            assert coord.is_syncing
        assert not coord.is_syncing

    def test_syncing_clears_on_exception(self):
        coord = PaneCoordinator()
        try:
            with coord.syncing():
                raise RuntimeError("test")
        except RuntimeError:
            pass
        assert not coord.is_syncing
