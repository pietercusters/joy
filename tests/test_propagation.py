"""Unit tests for propagation logic (MR auto-add, terminal auto-remove).

Tests cover:
- MR auto-add (_propagate_mr_auto_add) (PROP-02)
- Terminal auto-remove (_propagate_terminal_auto_remove)
- Immutability invariants (PROP-06, PROP-07, PROP-08)
"""
from __future__ import annotations

from datetime import date

import pytest

from joy.models import MRInfo, ObjectItem, PresetKind, Project, TerminalSession


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


# ---------------------------------------------------------------------------
# Bound method helpers
# ---------------------------------------------------------------------------

def _get_propagate_mr(ctx: _PropContext):
    """Return bound _propagate_mr_auto_add for ctx."""
    from joy.app import JoyApp  # noqa: PLC0415
    return lambda mr_data: JoyApp._propagate_mr_auto_add(ctx, mr_data)


def _get_propagate_terminal_remove(ctx: _PropContext):
    """Return bound _propagate_terminal_auto_remove for ctx."""
    from joy.app import JoyApp  # noqa: PLC0415
    return lambda: JoyApp._propagate_terminal_auto_remove(ctx)


# ===========================================================================
# TestMRAutoAdd -- tests for _propagate_mr_auto_add
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
        """Project has BRANCH 'main' but mr_data has 'feat-1' -- no MR added."""
        project = _project_with_branch("joy", "main")
        ctx = _PropContext([project])
        mr = _mr_data("joy", "feat-1", "https://github.com/x/y/pull/42", 42)
        messages = _get_propagate_mr(ctx)(mr)

        # Only 1 object (the branch) -- no MR added
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

        ctx = _PropContext([project])
        mr = _mr_data("joy", "feat-1", "https://github.com/x/y/pull/42", 42)
        _get_propagate_mr(ctx)(mr)

        # Branch object is the same object, unchanged
        assert branch_obj.value == original_value
        assert branch_obj.kind == original_kind

    def test_empty_mr_data_returns_no_messages(self) -> None:
        """Empty mr_data produces no changes and no messages."""
        project = _project_with_branch("joy", "feat-1")
        ctx = _PropContext([project])
        messages = _get_propagate_mr(ctx)({})
        assert messages == []


# ===========================================================================
# TestTerminalAutoRemove -- tests for _propagate_terminal_auto_remove
# ===========================================================================

class TestTerminalAutoRemove:
    """Terminal auto-remove propagation."""

    def test_terminal_removed_when_session_absent(self) -> None:
        """TERMINALS object removed when session name not in active sessions."""
        project = Project(
            name="test",
            objects=[ObjectItem(kind=PresetKind.TERMINALS, value="claude-work")],
        )
        ctx = _PropContext([project], sessions=_sessions(["other-session"]))

        messages = _get_propagate_terminal_remove(ctx)()

        assert len(project.objects) == 0
        assert len(messages) == 1
        assert "claude-work" in messages[0]

    def test_terminal_kept_when_session_present(self) -> None:
        """TERMINALS object kept when session name is in active sessions."""
        project = Project(
            name="test",
            objects=[ObjectItem(kind=PresetKind.TERMINALS, value="claude-work")],
        )
        ctx = _PropContext([project], sessions=_sessions(["claude-work"]))

        messages = _get_propagate_terminal_remove(ctx)()

        assert len(project.objects) == 1
        assert messages == []

    def test_no_removal_when_sessions_empty(self) -> None:
        """Terminal objects NOT removed when sessions list is empty (timing guard)."""
        project = Project(
            name="test",
            objects=[ObjectItem(kind=PresetKind.TERMINALS, value="claude-work")],
        )
        ctx = _PropContext([project], sessions=[])

        messages = _get_propagate_terminal_remove(ctx)()

        # Timing guard: empty sessions = iTerm2 hiccup, skip removal
        assert len(project.objects) == 1
        assert messages == []

    def test_multiple_projects_terminals_removed(self) -> None:
        """Terminal auto-remove applies across all projects."""
        p1 = Project(
            name="p1",
            objects=[ObjectItem(kind=PresetKind.TERMINALS, value="sess-a")],
        )
        p2 = Project(
            name="p2",
            objects=[ObjectItem(kind=PresetKind.TERMINALS, value="sess-b")],
        )
        ctx = _PropContext([p1, p2], sessions=_sessions(["sess-a"]))

        messages = _get_propagate_terminal_remove(ctx)()

        assert len(p1.objects) == 1  # sess-a is active -- kept
        assert len(p2.objects) == 0  # sess-b is absent -- removed
        assert len(messages) == 1
        assert "sess-b" in messages[0]

    def test_non_terminal_objects_not_removed(self) -> None:
        """BRANCH and MR objects are not affected by terminal auto-remove."""
        project = Project(
            name="test",
            objects=[
                ObjectItem(kind=PresetKind.BRANCH, value="main"),
                ObjectItem(kind=PresetKind.MR, value="https://github.com/x/y/pull/1"),
                ObjectItem(kind=PresetKind.TERMINALS, value="absent-session"),
            ],
        )
        ctx = _PropContext([project], sessions=_sessions(["other"]))

        messages = _get_propagate_terminal_remove(ctx)()

        # Terminal removed but branch and MR kept
        assert len(project.objects) == 2
        kinds = {obj.kind for obj in project.objects}
        assert PresetKind.BRANCH in kinds
        assert PresetKind.MR in kinds
        assert PresetKind.TERMINALS not in kinds

    def test_removal_message_includes_project_name(self) -> None:
        """Removal message includes both session name and project name."""
        project = Project(
            name="my-project",
            objects=[ObjectItem(kind=PresetKind.TERMINALS, value="gone-session")],
        )
        ctx = _PropContext([project], sessions=_sessions(["other"]))

        messages = _get_propagate_terminal_remove(ctx)()

        assert len(messages) == 1
        assert "gone-session" in messages[0]
        assert "my-project" in messages[0]
