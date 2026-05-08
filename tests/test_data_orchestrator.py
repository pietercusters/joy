"""Tests for DataOrchestrator service (Phase 19, SRVC-02, TEST-02).

All tests are pure Python — no TUI, no Textual, no pilot.
"""
from __future__ import annotations

from joy.data_orchestrator import DataOrchestrator
from joy.models import Config, MRInfo, ObjectItem, PresetKind, Project, Repo, TerminalSession, WorktreeInfo


# ---------------------------------------------------------------------------
# TestDataOrchestrator — readiness and relationship computation
# ---------------------------------------------------------------------------


class TestDataOrchestrator:
    def test_mark_worktrees_ready_sets_flag(self):
        orch = DataOrchestrator()
        wts = [WorktreeInfo(repo_name="r", branch="b", path="/p")]
        orch.mark_worktrees_ready(wts, mr_data={"k": "v"}, mr_authored=[1])
        assert orch._worktrees_ready is True
        assert orch.current_worktrees == wts
        assert orch.current_mr_data == {"k": "v"}
        assert orch.current_mr_authored == [1]

    def test_mark_sessions_ready_sets_flag(self):
        orch = DataOrchestrator()
        sessions = [TerminalSession(session_id="s1", session_name="dev", foreground_process="zsh", cwd="/")]
        orch.mark_sessions_ready(sessions)
        assert orch._sessions_ready is True
        assert orch.current_sessions == sessions

    def test_maybe_compute_waits_for_both(self):
        orch = DataOrchestrator()
        orch.mark_worktrees_ready([])
        result = orch.maybe_compute_relationships([], [])
        assert result is None  # sessions not ready

    def test_maybe_compute_returns_index(self):
        orch = DataOrchestrator()
        project = Project(name="p", objects=[ObjectItem(kind=PresetKind.WORKTREE, value="/wt")], repo="r")
        wts = [WorktreeInfo(repo_name="r", branch="main", path="/wt")]
        sessions = [TerminalSession(session_id="s1", session_name="dev", foreground_process="zsh", cwd="/", tab_id="t1")]
        repos = [Repo(name="r", local_path="/r")]

        orch.mark_worktrees_ready(wts)
        orch.mark_sessions_ready(sessions)
        result = orch.maybe_compute_relationships([project], repos)

        assert result is not None
        assert orch.rel_index is result
        assert result.worktrees_for(project) == wts

    def test_maybe_compute_resets_flags(self):
        orch = DataOrchestrator()
        orch.mark_worktrees_ready([])
        orch.mark_sessions_ready([])
        orch.maybe_compute_relationships([], [])
        assert orch._worktrees_ready is False
        assert orch._sessions_ready is False

    def test_maybe_compute_double_call_returns_none(self):
        orch = DataOrchestrator()
        orch.mark_worktrees_ready([])
        orch.mark_sessions_ready([])
        orch.maybe_compute_relationships([], [])
        result = orch.maybe_compute_relationships([], [])
        assert result is None


# ---------------------------------------------------------------------------
# TestMRAutoAdd — propagation logic
# ---------------------------------------------------------------------------


class TestMRAutoAdd:
    def _make_project(self, repo="myrepo", branch="feature"):
        return Project(
            name="proj",
            objects=[ObjectItem(kind=PresetKind.BRANCH, value=branch)],
            repo=repo,
        )

    def _make_mr_data(self, repo="myrepo", branch="feature", url="https://pr/1", number=1):
        return {(repo, branch): MRInfo(mr_number=number, is_draft=False, ci_status=None, url=url)}

    def test_mr_auto_add_appends_object(self):
        orch = DataOrchestrator()
        project = self._make_project()
        config = Config()
        messages = orch.propagate_mr_auto_add(self._make_mr_data(), [project], config)
        assert len(messages) == 1
        assert "Added PR #1" in messages[0]
        assert any(o.kind == PresetKind.MR and o.value == "https://pr/1" for o in project.objects)

    def test_mr_auto_add_respects_default_open(self):
        orch = DataOrchestrator()
        project = self._make_project()
        config = Config(default_open_kinds=["mr"])
        orch.propagate_mr_auto_add(self._make_mr_data(), [project], config)
        mr_obj = [o for o in project.objects if o.kind == PresetKind.MR][0]
        assert mr_obj.open_by_default is True

    def test_mr_dedup_skips_existing(self):
        orch = DataOrchestrator()
        project = self._make_project()
        project.objects.append(ObjectItem(kind=PresetKind.MR, value="https://pr/1"))
        config = Config()
        messages = orch.propagate_mr_auto_add(self._make_mr_data(), [project], config)
        assert len(messages) == 0

    def test_mr_no_repo_excluded(self):
        orch = DataOrchestrator()
        project = Project(name="norepo", objects=[ObjectItem(kind=PresetKind.BRANCH, value="feat")])
        config = Config()
        messages = orch.propagate_mr_auto_add(
            {("myrepo", "feat"): MRInfo(mr_number=1, is_draft=False, ci_status=None, url="https://pr/1")},
            [project], config,
        )
        assert len(messages) == 0

    def test_mr_no_matching_branch(self):
        orch = DataOrchestrator()
        project = self._make_project(branch="other")
        config = Config()
        messages = orch.propagate_mr_auto_add(self._make_mr_data(), [project], config)
        assert len(messages) == 0

    def test_empty_mr_data_no_messages(self):
        orch = DataOrchestrator()
        messages = orch.propagate_mr_auto_add({}, [], Config())
        assert messages == []


# ---------------------------------------------------------------------------
# TestStaleTabHealing
# ---------------------------------------------------------------------------


class TestStaleTabHealing:
    def test_stale_tab_healed(self):
        orch = DataOrchestrator()
        project = Project(name="p", iterm_tab_id="dead-tab")
        sessions = [TerminalSession(session_id="s1", session_name="x", foreground_process="zsh", cwd="/")]
        healed = orch.heal_stale_tabs([project], sessions, live_tab_ids={"live-tab"})
        assert project.iterm_tab_id is None
        assert healed == ["p"]

    def test_live_tab_not_healed(self):
        orch = DataOrchestrator()
        project = Project(name="p", iterm_tab_id="live-tab")
        sessions = [TerminalSession(session_id="s1", session_name="x", foreground_process="zsh", cwd="/")]
        healed = orch.heal_stale_tabs([project], sessions, live_tab_ids={"live-tab"})
        assert project.iterm_tab_id == "live-tab"
        assert healed == []

    def test_no_sessions_returns_empty(self):
        orch = DataOrchestrator()
        project = Project(name="p", iterm_tab_id="tab")
        healed = orch.heal_stale_tabs([project], None, live_tab_ids=set())
        assert healed == []
        assert project.iterm_tab_id == "tab"  # not cleared

    def test_returns_healed_names(self):
        orch = DataOrchestrator()
        p1 = Project(name="a", iterm_tab_id="dead1")
        p2 = Project(name="b", iterm_tab_id="live")
        p3 = Project(name="c", iterm_tab_id="dead2")
        sessions = [TerminalSession(session_id="s1", session_name="x", foreground_process="zsh", cwd="/")]
        healed = orch.heal_stale_tabs([p1, p2, p3], sessions, live_tab_ids={"live"})
        assert healed == ["a", "c"]


# ---------------------------------------------------------------------------
# TestLinkedWorktreeSets
# ---------------------------------------------------------------------------


class TestLinkedWorktreeSets:
    def test_computes_linked_paths(self):
        orch = DataOrchestrator()
        project = Project(name="p", objects=[ObjectItem(kind=PresetKind.WORKTREE, value="/wt/feat")])
        wts = [WorktreeInfo(repo_name="r", branch="feat", path="/wt/feat")]
        paths, branches = orch.compute_linked_worktree_sets([project], wts)
        assert "/wt/feat" in paths

    def test_computes_linked_branches(self):
        orch = DataOrchestrator()
        project = Project(name="p", objects=[ObjectItem(kind=PresetKind.BRANCH, value="feat")], repo="r")
        wts = [WorktreeInfo(repo_name="r", branch="feat", path="/wt/feat")]
        paths, branches = orch.compute_linked_worktree_sets([project], wts)
        assert ("r", "feat") in branches

    def test_no_matches_returns_empty(self):
        orch = DataOrchestrator()
        paths, branches = orch.compute_linked_worktree_sets([], [])
        assert paths == set()
        assert branches == set()


# ---------------------------------------------------------------------------
# TestBuildTabGroups
# ---------------------------------------------------------------------------


class TestBuildTabGroups:
    def test_builds_ordered_groups(self):
        orch = DataOrchestrator()
        p1 = Project(name="a", iterm_tab_id="t1")
        p2 = Project(name="b", iterm_tab_id="t2")
        result = orch.build_tab_groups([p1, p2], live_tab_ids={"t1", "t2"})
        assert result == [("a", "t1"), ("b", "t2")]

    def test_skips_dead_tabs(self):
        orch = DataOrchestrator()
        p1 = Project(name="a", iterm_tab_id="t1")
        p2 = Project(name="b", iterm_tab_id="dead")
        result = orch.build_tab_groups([p1, p2], live_tab_ids={"t1"})
        assert result == [("a", "t1")]
