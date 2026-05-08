"""Unit tests for propagation logic (MR auto-add).

Tests cover:
- MR auto-add (_propagate_mr_auto_add) (PROP-02)
- Immutability invariants (PROP-06, PROP-07, PROP-08)
"""
from __future__ import annotations

from datetime import date

import pytest

from joy.models import Config, MRInfo, ObjectItem, PresetKind, Project


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


# ---------------------------------------------------------------------------
# Minimal mock context for testing propagation methods
# ---------------------------------------------------------------------------

class _PropContext:
    """Minimal context that mimics the JoyApp interface used by propagation methods."""

    def __init__(self, projects: list[Project], sessions: list | None = None, config: Config | None = None) -> None:
        from joy.data_orchestrator import DataOrchestrator  # noqa: PLC0415
        self._projects = projects
        self._config = config if config is not None else Config()
        self._orchestrator = DataOrchestrator()


# ---------------------------------------------------------------------------
# Bound method helpers
# ---------------------------------------------------------------------------

def _get_propagate_mr(ctx: _PropContext):
    """Return bound _propagate_mr_auto_add for ctx."""
    from joy.app import JoyApp  # noqa: PLC0415
    return lambda mr_data: JoyApp._propagate_mr_auto_add(ctx, mr_data)


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

    def test_mr_auto_add_respects_default_open_kinds(self) -> None:
        """MR auto-add sets open_by_default=True when 'mr' in default_open_kinds."""
        project = _project_with_branch("joy", "feat-1")
        config = Config(default_open_kinds=["mr", "worktree"])
        ctx = _PropContext([project], config=config)
        mr = _mr_data("joy", "feat-1", "https://github.com/x/y/pull/42", 42)

        messages = _get_propagate_mr(ctx)(mr)

        assert len(project.objects) == 2
        new_obj = project.objects[-1]
        assert new_obj.kind == PresetKind.MR
        assert new_obj.open_by_default is True

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
