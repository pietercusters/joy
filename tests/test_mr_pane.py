"""Tests for MR pane widget."""
from __future__ import annotations

import pytest
from unittest.mock import patch

from joy.models import MRDetail
from joy.widgets.mr_pane import MRPane, MRRow


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_detail(
    mr_number: int = 42,
    title: str = "Fix login redirect",
    is_draft: bool = False,
    ci_status: str | None = "pass",
    review_status: str | None = "approved",
    url: str = "https://github.com/owner/repo/pull/42",
    repo_name: str = "myrepo",
    branch: str = "feat-login",
    is_review_request: bool = False,
) -> MRDetail:
    return MRDetail(
        mr_number=mr_number,
        title=title,
        is_draft=is_draft,
        ci_status=ci_status,
        review_status=review_status,
        url=url,
        repo_name=repo_name,
        branch=branch,
        is_review_request=is_review_request,
    )


# ---------------------------------------------------------------------------
# Tests: MRRow.build_content
# ---------------------------------------------------------------------------


class TestMRRowBuildContent:
    """Test MRRow.build_content with various MRDetail inputs."""

    def test_open_mr_with_pass_and_approved(self) -> None:
        detail = _make_detail(ci_status="pass", review_status="approved")
        text = MRRow.build_content(detail)
        plain = text.plain
        assert "!42" in plain
        assert "Fix login redirect" in plain
        assert "myrepo" in plain
        assert "Approved" in plain

    def test_draft_mr(self) -> None:
        detail = _make_detail(is_draft=True, ci_status=None, review_status=None)
        text = MRRow.build_content(detail)
        plain = text.plain
        assert "!42" in plain

    def test_ci_fail(self) -> None:
        detail = _make_detail(ci_status="fail", review_status=None)
        text = MRRow.build_content(detail)
        # CI fail icon should be present (verified by style, not easily by plain text)
        assert text.plain  # non-empty

    def test_ci_pending(self) -> None:
        detail = _make_detail(ci_status="pending", review_status=None)
        text = MRRow.build_content(detail)
        assert text.plain

    def test_changes_requested(self) -> None:
        detail = _make_detail(review_status="changes_requested")
        text = MRRow.build_content(detail)
        assert "Changes" in text.plain

    def test_review_required(self) -> None:
        detail = _make_detail(review_status="review_required")
        text = MRRow.build_content(detail)
        assert "Pending" in text.plain

    def test_no_ci_no_review(self) -> None:
        detail = _make_detail(ci_status=None, review_status=None)
        text = MRRow.build_content(detail)
        plain = text.plain
        assert "!42" in plain
        assert "Approved" not in plain
        assert "Changes" not in plain
        assert "Pending" not in plain


# ---------------------------------------------------------------------------
# Tests: MRPane.set_mr_data (async widget tests)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_store():
    """Mock store to avoid filesystem access."""
    from joy.models import Config, Project
    with patch("joy.store.load_projects", return_value=[Project(name="test")]), \
         patch("joy.store.load_config", return_value=Config()), \
         patch("joy.store.load_repos", return_value=[]), \
         patch("joy.worktrees.discover_worktrees", return_value=[]):
        yield


@pytest.mark.asyncio
async def test_set_mr_data_with_both_sections(mock_store) -> None:
    """set_mr_data with authored and review_requests shows both sections."""
    from joy.app import JoyApp
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()

        mr_pane = app.query_one(MRPane)
        authored = [_make_detail(mr_number=10, title="My PR")]
        reviews = [_make_detail(mr_number=20, title="Review PR", is_review_request=True)]
        await mr_pane.set_mr_data(authored, reviews)

        assert len(mr_pane._rows) == 2
        assert mr_pane._rows[0].mr_number == 10
        assert mr_pane._rows[1].mr_number == 20


@pytest.mark.asyncio
async def test_set_mr_data_empty_shows_empty_state(mock_store) -> None:
    """set_mr_data with empty lists shows empty state."""
    from joy.app import JoyApp
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()

        mr_pane = app.query_one(MRPane)
        await mr_pane.set_mr_data([], [])

        assert len(mr_pane._rows) == 0
        assert mr_pane._cursor == -1


@pytest.mark.asyncio
async def test_set_mr_data_only_authored(mock_store) -> None:
    """set_mr_data with only authored MRs shows only My MRs section."""
    from joy.app import JoyApp
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()

        mr_pane = app.query_one(MRPane)
        authored = [
            _make_detail(mr_number=10, title="PR A"),
            _make_detail(mr_number=20, title="PR B"),
        ]
        await mr_pane.set_mr_data(authored, [])

        assert len(mr_pane._rows) == 2
        # Sorted by mr_number desc: 20 first, then 10
        assert mr_pane._rows[0].mr_number == 20
        assert mr_pane._rows[1].mr_number == 10


@pytest.mark.asyncio
async def test_cursor_navigation(mock_store) -> None:
    """j/k navigation moves cursor through MR rows."""
    from joy.app import JoyApp
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()

        mr_pane = app.query_one(MRPane)
        authored = [
            _make_detail(mr_number=10, title="PR A"),
            _make_detail(mr_number=20, title="PR B"),
        ]
        await mr_pane.set_mr_data(authored, [])

        # Focus MR pane
        mr_pane.focus()
        await pilot.pause(0.1)

        # Initial cursor is 0 (first population)
        assert mr_pane._cursor == 0

        # Move down
        await pilot.press("j")
        await pilot.pause(0.05)
        assert mr_pane._cursor == 1

        # Move up
        await pilot.press("k")
        await pilot.pause(0.05)
        assert mr_pane._cursor == 0

        # Can't go above 0
        await pilot.press("k")
        await pilot.pause(0.05)
        assert mr_pane._cursor == 0
