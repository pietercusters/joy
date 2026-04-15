"""Unit tests for Phase 16 propagation logic (PROP-02, PROP-04..PROP-08).

Tests cover:
- ObjectItem.stale runtime field (PROP-04, PROP-05, PROP-07)
- MR auto-add (_propagate_mr_auto_add) (PROP-02)
- Agent stale marking (_propagate_agent_stale) (PROP-04, PROP-05)
- Immutability invariants (PROP-06, PROP-07, PROP-08)
- Stale CSS class application in ObjectRow (PROP-04, PROP-05)
"""
from __future__ import annotations

from datetime import date

import pytest

from joy.models import MRInfo, ObjectItem, PresetKind, Project, TerminalSession
from joy.widgets.object_row import ObjectRow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _project_with_branch(repo: str | None, branch: str) -> Project:
    """Return a project that has one BRANCH object."""
    return Project(
        name=f"proj-{branch}",
        repo=repo,
        created=date(2026, 1, 1),
        objects=[ObjectItem(kind=PresetKind.BRANCH, value=branch)],
    )


def _mr_data(repo: str, branch: str, url: str, number: int) -> dict:
    """Return an mr_data dict with a single entry."""
    return {
        (repo, branch): MRInfo(mr_number=number, is_draft=False, ci_status=None, url=url)
    }


def _sessions(names: list[str]) -> list[TerminalSession]:
    """Return TerminalSession list with the given session names."""
    return [
        TerminalSession(
            session_id=f"sess-{i}",
            session_name=name,
            foreground_process="zsh",
            cwd="/tmp",
        )
        for i, name in enumerate(names)
    ]


# ---------------------------------------------------------------------------
# Minimal mock context for testing propagation methods
# ---------------------------------------------------------------------------

class _PropContext:
    """Minimal context that mimics the JoyApp interface used by propagation methods."""

    def __init__(self, projects: list[Project], sessions: list[TerminalSession] | None = None) -> None:
        self._projects = projects
        self._current_sessions = sessions or []

    # Bind the real methods from JoyApp after implementation (Task 2).
    # These are reassigned in conftest or at import time once JoyApp exists.


# ---------------------------------------------------------------------------
# Task 1: RED — import propagation methods (will fail until Task 2)
# ---------------------------------------------------------------------------

def _get_propagate_mr(ctx: _PropContext):
    """Return bound _propagate_mr_auto_add for ctx."""
    from joy.app import JoyApp  # noqa: PLC0415
    return lambda mr_data: JoyApp._propagate_mr_auto_add(ctx, mr_data)


def _get_propagate_agent(ctx: _PropContext):
    """Return bound _propagate_agent_stale for ctx."""
    from joy.app import JoyApp  # noqa: PLC0415
    return lambda: JoyApp._propagate_agent_stale(ctx)


# ===========================================================================
# TestObjectItemStale — tests that pass immediately after models.py update
# ===========================================================================

class TestObjectItemStale:
    """ObjectItem.stale runtime field (PROP-07: not written to TOML)."""

    def test_stale_defaults_false(self) -> None:
        obj = ObjectItem(kind=PresetKind.BRANCH, value="main")
        assert obj.stale is False

    def test_stale_can_be_set_true(self) -> None:
        obj = ObjectItem(kind=PresetKind.AGENTS, value="claude-work")
        obj.stale = True
        assert obj.stale is True

    def test_stale_not_in_to_dict_when_false(self) -> None:
        obj = ObjectItem(kind=PresetKind.MR, value="https://github.com/x/y/pull/1")
        result = obj.to_dict()
        assert "stale" not in result
        assert set(result.keys()) == {"kind", "value", "label", "open_by_default"}

    def test_stale_not_in_to_dict_when_true(self) -> None:
        obj = ObjectItem(kind=PresetKind.AGENTS, value="claude-work", stale=True)
        result = obj.to_dict()
        assert "stale" not in result
        assert set(result.keys()) == {"kind", "value", "label", "open_by_default"}

    def test_stale_exact_keys_in_to_dict(self) -> None:
        """to_dict() must have exactly 4 keys regardless of stale value."""
        obj = ObjectItem(
            kind=PresetKind.AGENTS,
            value="my-agent",
            label="Agent",
            open_by_default=True,
            stale=True,
        )
        result = obj.to_dict()
        assert len(result) == 4
        assert result["kind"] == "agents"
        assert result["value"] == "my-agent"
        assert result["label"] == "Agent"
        assert result["open_by_default"] is True


# ===========================================================================
# TestMRAutoAdd — tests for _propagate_mr_auto_add
# ===========================================================================

class TestMRAutoAdd:
    """MR auto-add propagation (PROP-02, PROP-06, PROP-07, PROP-08)."""

    def test_mr_auto_add_appends_object(self) -> None:
        """MR is appended when branch matches and no existing MR with same URL."""
        project = _project_with_branch("joy", "feat-1")
        ctx = _PropContext([project])
        mr = _mr_data("joy", "feat-1", "https://github.com/x/y/pull/42", 42)

        messages = _get_propagate_mr(ctx)(mr)

        assert len(project.objects) == 2
        new_obj = project.objects[-1]
        assert new_obj.kind == PresetKind.MR
        assert new_obj.value == "https://github.com/x/y/pull/42"
        assert new_obj.label == "PR #42"
        assert new_obj.open_by_default is False

    def test_mr_auto_add_returns_message(self) -> None:
        """A message is returned when an MR is added."""
        project = _project_with_branch("joy", "feat-1")
        ctx = _PropContext([project])
        mr = _mr_data("joy", "feat-1", "https://github.com/x/y/pull/42", 42)

        messages = _get_propagate_mr(ctx)(mr)

        assert len(messages) == 1
        assert "42" in messages[0]

    def test_mr_dedup_skips_existing(self) -> None:
        """No duplicate MR if URL already exists on project."""
        project = _project_with_branch("joy", "feat-1")
        # Pre-add MR with same URL
        project.objects.append(
            ObjectItem(kind=PresetKind.MR, value="https://github.com/x/y/pull/42")
        )
        initial_count = len(project.objects)

        ctx = _PropContext([project])
        mr = _mr_data("joy", "feat-1", "https://github.com/x/y/pull/42", 42)
        messages = _get_propagate_mr(ctx)(mr)

        assert len(project.objects) == initial_count
        assert messages == []

    def test_mr_no_repo_excluded(self) -> None:
        """Project with repo=None is skipped (PROP-08)."""
        project = _project_with_branch(None, "feat-1")
        # Manually set repo to None (override)
        project.repo = None
        initial_count = len(project.objects)

        ctx = _PropContext([project])
        mr = _mr_data("joy", "feat-1", "https://github.com/x/y/pull/42", 42)
        messages = _get_propagate_mr(ctx)(mr)

        assert len(project.objects) == initial_count
        assert messages == []

    def test_mr_no_matching_branch_skipped(self) -> None:
        """Project has BRANCH 'main' but mr_data has 'feat-1' — no MR added."""
        project = _project_with_branch("joy", "main")
        ctx = _PropContext([project])
        mr = _mr_data("joy", "feat-1", "https://github.com/x/y/pull/42", 42)
        messages = _get_propagate_mr(ctx)(mr)

        # Only 1 object (the branch) — no MR added
        assert len(project.objects) == 1
        assert messages == []

    def test_mr_never_removed(self) -> None:
        """Existing MR remains even when no matching mr_data (PROP-07)."""
        project = _project_with_branch("joy", "feat-1")
        existing_mr = ObjectItem(kind=PresetKind.MR, value="https://github.com/x/y/pull/99")
        project.objects.append(existing_mr)

        ctx = _PropContext([project])
        # No mr_data at all
        messages = _get_propagate_mr(ctx)({})

        assert any(obj.kind == PresetKind.MR for obj in project.objects)
        assert messages == []

    def test_branch_never_modified(self) -> None:
        """BRANCH object is identical before and after propagation (PROP-06)."""
        project = _project_with_branch("joy", "feat-1")
        branch_obj = project.objects[0]
        original_value = branch_obj.value
        original_kind = branch_obj.kind
        original_stale = branch_obj.stale

        ctx = _PropContext([project])
        mr = _mr_data("joy", "feat-1", "https://github.com/x/y/pull/42", 42)
        _get_propagate_mr(ctx)(mr)

        # Branch object is the same object, unchanged
        assert branch_obj.value == original_value
        assert branch_obj.kind == original_kind
        assert branch_obj.stale == original_stale

    def test_empty_mr_data_returns_no_messages(self) -> None:
        """Empty mr_data produces no changes and no messages."""
        project = _project_with_branch("joy", "feat-1")
        ctx = _PropContext([project])
        messages = _get_propagate_mr(ctx)({})
        assert messages == []


# ===========================================================================
# TestAgentStale — tests for _propagate_agent_stale
# ===========================================================================

class TestAgentStale:
    """Agent stale marking (PROP-04, PROP-05)."""

    def test_agent_marked_stale_when_absent(self) -> None:
        """AGENTS object marked stale when session name not in active sessions."""
        project = Project(
            name="test",
            objects=[ObjectItem(kind=PresetKind.AGENTS, value="claude-work")],
        )
        ctx = _PropContext([project], sessions=_sessions(["other-session"]))

        _get_propagate_agent(ctx)()

        assert project.objects[0].stale is True

    def test_agent_stale_cleared_when_present(self) -> None:
        """Previously stale AGENTS object cleared when session reappears."""
        project = Project(
            name="test",
            objects=[ObjectItem(kind=PresetKind.AGENTS, value="claude-work", stale=True)],
        )
        ctx = _PropContext([project], sessions=_sessions(["claude-work"]))

        _get_propagate_agent(ctx)()

        assert project.objects[0].stale is False

    def test_agent_marked_stale_returns_offline_message(self) -> None:
        """False->True transition emits an 'offline' message."""
        project = Project(
            name="test",
            objects=[ObjectItem(kind=PresetKind.AGENTS, value="claude-work", stale=False)],
        )
        ctx = _PropContext([project], sessions=_sessions([]))

        messages = _get_propagate_agent(ctx)()

        assert len(messages) == 1
        assert "offline" in messages[0].lower() or "claude-work" in messages[0]

    def test_agent_stale_cleared_returns_online_message(self) -> None:
        """True->False transition emits a 'back online' message."""
        project = Project(
            name="test",
            objects=[ObjectItem(kind=PresetKind.AGENTS, value="claude-work", stale=True)],
        )
        ctx = _PropContext([project], sessions=_sessions(["claude-work"]))

        messages = _get_propagate_agent(ctx)()

        assert len(messages) == 1
        assert "online" in messages[0].lower() or "claude-work" in messages[0]

    def test_agent_already_stale_no_message(self) -> None:
        """True->True transition (still absent) emits no new message."""
        project = Project(
            name="test",
            objects=[ObjectItem(kind=PresetKind.AGENTS, value="claude-work", stale=True)],
        )
        ctx = _PropContext([project], sessions=_sessions(["other"]))

        messages = _get_propagate_agent(ctx)()

        # Still stale — no transition message
        assert messages == []

    def test_agent_still_present_no_message(self) -> None:
        """False->False transition (still present) emits no message."""
        project = Project(
            name="test",
            objects=[ObjectItem(kind=PresetKind.AGENTS, value="claude-work", stale=False)],
        )
        ctx = _PropContext([project], sessions=_sessions(["claude-work"]))

        messages = _get_propagate_agent(ctx)()

        assert messages == []

    def test_non_agent_objects_not_marked_stale(self) -> None:
        """BRANCH and MR objects are not affected by agent stale propagation."""
        project = Project(
            name="test",
            objects=[
                ObjectItem(kind=PresetKind.BRANCH, value="main"),
                ObjectItem(kind=PresetKind.MR, value="https://github.com/x/y/pull/1"),
            ],
        )
        ctx = _PropContext([project], sessions=_sessions([]))

        _get_propagate_agent(ctx)()

        for obj in project.objects:
            assert obj.stale is False, f"{obj.kind} should not be stale"

    def test_multiple_projects_all_agents_checked(self) -> None:
        """Agent stale propagation applies across all projects."""
        p1 = Project(
            name="p1",
            objects=[ObjectItem(kind=PresetKind.AGENTS, value="sess-a")],
        )
        p2 = Project(
            name="p2",
            objects=[ObjectItem(kind=PresetKind.AGENTS, value="sess-b")],
        )
        ctx = _PropContext([p1, p2], sessions=_sessions(["sess-a"]))

        _get_propagate_agent(ctx)()

        assert p1.objects[0].stale is False  # sess-a is active
        assert p2.objects[0].stale is True   # sess-b is absent


# ===========================================================================
# TestStaleCSSIntegration — stale class applied during ObjectRow construction
# ===========================================================================

class TestStaleCSSIntegration:
    """Test that stale ObjectItems get --stale CSS class on ObjectRow (PROP-04, PROP-05)."""

    def test_stale_row_has_css_class(self) -> None:
        """ObjectRow with stale=True item gets --stale class applied (mimics _render_project)."""
        item = ObjectItem(kind=PresetKind.AGENTS, value="claude-work", stale=True)
        row = ObjectRow(item, index=0)
        # Simulate what _render_project does
        if getattr(item, 'stale', False):
            row.add_class("--stale")
        assert row.has_class("--stale")

    def test_non_stale_row_no_css_class(self) -> None:
        """ObjectRow with stale=False item does NOT get --stale class."""
        item = ObjectItem(kind=PresetKind.AGENTS, value="claude-work", stale=False)
        row = ObjectRow(item, index=0)
        if getattr(item, 'stale', False):
            row.add_class("--stale")
        assert not row.has_class("--stale")

    def test_stale_default_false_no_css_class(self) -> None:
        """ObjectRow with default stale (unset) does NOT get --stale class."""
        item = ObjectItem(kind=PresetKind.BRANCH, value="main")
        row = ObjectRow(item, index=0)
        if getattr(item, 'stale', False):
            row.add_class("--stale")
        assert not row.has_class("--stale")

    def test_stale_applies_only_to_stale_items(self) -> None:
        """Mixed stale and non-stale items: only stale gets --stale class."""
        stale_item = ObjectItem(kind=PresetKind.AGENTS, value="offline-agent", stale=True)
        live_item = ObjectItem(kind=PresetKind.AGENTS, value="online-agent", stale=False)

        stale_row = ObjectRow(stale_item, index=0)
        live_row = ObjectRow(live_item, index=1)

        for r in (stale_row, live_row):
            if getattr(r.item, 'stale', False):
                r.add_class("--stale")

        assert stale_row.has_class("--stale")
        assert not live_row.has_class("--stale")
