"""Tests for Phase 9: Worktree pane — grouped display, status indicators, empty states.

Wave 0 (RED phase): These tests define the contract that Plan 02 must satisfy.
All tests targeting WorktreeRow, GroupHeader, abbreviate_home, and middle_truncate
will fail until Plan 02 fills in the production code.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

from joy.app import JoyApp
from joy.models import Config, MRInfo, ObjectItem, PresetKind, Project, Repo, WorktreeInfo
from joy.widgets.worktree_pane import (
    ICON_CI_FAIL,
    ICON_CI_PASS,
    ICON_CI_PENDING,
    ICON_MR_DRAFT,
    ICON_MR_OPEN,
    WorktreePane,
    WorktreeRow,
    GroupHeader,
    abbreviate_home,
    middle_truncate,
)


# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------


def _sample_projects() -> list[Project]:
    """Minimal project data to satisfy store mocks."""
    return [
        Project(
            name="project-alpha",
            objects=[ObjectItem(kind=PresetKind.BRANCH, value="main")],
        ),
    ]


def _sample_worktrees() -> list[WorktreeInfo]:
    """Four WorktreeInfo covering both repos, both dirty/clean, both upstream states."""
    return [
        WorktreeInfo(
            repo_name="joy",
            branch="feat-z",
            path="/Users/pieter/Github/joy/wt/feat-z",
            is_dirty=True,
            has_upstream=True,
        ),
        WorktreeInfo(
            repo_name="joy",
            branch="feat-a",
            path="/Users/pieter/Github/joy/wt/feat-a",
            is_dirty=False,
            has_upstream=False,
        ),
        WorktreeInfo(
            repo_name="other",
            branch="develop",
            path="/Users/pieter/Github/other/wt/develop",
            is_dirty=False,
            has_upstream=True,
        ),
        WorktreeInfo(
            repo_name="other",
            branch="hotfix",
            path="/tmp/other/wt/hotfix",
            is_dirty=True,
            has_upstream=False,
        ),
    ]


def _sample_repos() -> list[Repo]:
    return [
        Repo(name="joy", local_path="/tmp/joy"),
        Repo(name="other", local_path="/tmp/other"),
    ]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_store_with_worktrees():
    """Mock store with two repos and four worktrees."""
    with (
        patch("joy.store.load_projects", return_value=_sample_projects()),
        patch("joy.store.load_config", return_value=Config()),
        patch("joy.store.load_repos", return_value=_sample_repos()),
        patch("joy.worktrees.discover_worktrees", return_value=_sample_worktrees()),
        patch("joy.mr_status.fetch_mr_data", return_value={}),
    ):
        yield


@pytest.fixture
def mock_store_empty_repos():
    """Mock store with no repos and no worktrees."""
    with (
        patch("joy.store.load_projects", return_value=_sample_projects()),
        patch("joy.store.load_config", return_value=Config()),
        patch("joy.store.load_repos", return_value=[]),
        patch("joy.worktrees.discover_worktrees", return_value=[]),
        patch("joy.mr_status.fetch_mr_data", return_value={}),
    ):
        yield


@pytest.fixture
def mock_store_repos_no_worktrees():
    """Mock store with repos but no worktrees."""
    with (
        patch("joy.store.load_projects", return_value=_sample_projects()),
        patch("joy.store.load_config", return_value=Config()),
        patch("joy.store.load_repos", return_value=_sample_repos()),
        patch("joy.worktrees.discover_worktrees", return_value=[]),
        patch("joy.mr_status.fetch_mr_data", return_value={}),
    ):
        yield


# ---------------------------------------------------------------------------
# Unit tests: pure functions (no Textual app)
# ---------------------------------------------------------------------------


def test_path_abbreviation():
    """D-13: abbreviate_home replaces leading home dir with ~."""
    import os
    home = os.path.expanduser("~")
    # Normal path inside home
    assert abbreviate_home(f"{home}/Github/joy") == "~/Github/joy"
    # Path outside home is returned verbatim
    assert abbreviate_home("/tmp/other/wt/hotfix") == "/tmp/other/wt/hotfix"
    # Exact home dir returns "~"
    assert abbreviate_home(home) == "~"


def test_middle_truncation():
    """D-14: middle_truncate preserves start and end for long paths."""
    # Short path (no truncation)
    short = "~/Github/joy/wt/feat-x"
    assert middle_truncate(short, 80) == short

    # Long path gets middle ellipsis preserving start and leaf
    long_path = "~/Projects/very/deeply/nested/repository/worktrees/feature-branch-with-long-name"
    result = middle_truncate(long_path, 40)
    assert len(result) <= 40
    assert result.startswith("~/")
    # Should contain ellipsis
    assert "\u2026" in result or "..." in result

    # Path with <= 3 segments gets right-truncated
    short_seg = "~/Github/feat-branch-with-a-very-very-very-very-very-long-name-that-exceeds-width"
    result2 = middle_truncate(short_seg, 30)
    assert len(result2) <= 30


def test_grouping_by_repo():
    """WKTR-02a: Worktrees from two repos produce two GroupHeaders."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield WorktreePane()

    import asyncio

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            await pane.set_worktrees(_sample_worktrees())
            await pilot.pause(0.1)
            headers = pane.query(GroupHeader)
            assert len(headers) == 2

    asyncio.run(_run())


def test_empty_repos_hidden():
    """WKTR-02b: Repos with no active worktrees produce no GroupHeader."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield WorktreePane()

    import asyncio

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            # Only worktrees from "alpha" repo; "beta" has none
            worktrees = [
                WorktreeInfo(
                    repo_name="alpha",
                    branch="feat-x",
                    path="/tmp/alpha/wt/feat-x",
                )
            ]
            await pane.set_worktrees(worktrees)
            await pilot.pause(0.1)
            header_texts = [str(h.content) for h in pane.query(GroupHeader)]
            assert not any("beta" in t.lower() for t in header_texts)

    asyncio.run(_run())


def test_repo_order_alphabetical():
    """WKTR-02c / D-11: Repo sections appear in case-insensitive alphabetical order."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield WorktreePane()

    import asyncio

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            worktrees = [
                WorktreeInfo(repo_name="Zeta", branch="main", path="/tmp/zeta/wt/main"),
                WorktreeInfo(repo_name="alpha", branch="main", path="/tmp/alpha/wt/main"),
                WorktreeInfo(repo_name="Mid", branch="main", path="/tmp/mid/wt/main"),
            ]
            await pane.set_worktrees(worktrees)
            await pilot.pause(0.1)
            headers = pane.query(GroupHeader)
            names = [str(h.content) for h in headers]
            lower_names = [n.lower() for n in names]
            assert lower_names == sorted(lower_names), f"Expected alphabetical order, got: {names}"

    asyncio.run(_run())


def test_worktree_order_alphabetical():
    """WKTR-02d / D-12: Worktrees within a repo appear sorted case-insensitively."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield WorktreePane()

    import asyncio

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            worktrees = [
                WorktreeInfo(repo_name="alpha", branch="feat-z", path="/tmp/alpha/wt/feat-z"),
                WorktreeInfo(repo_name="alpha", branch="feat-a", path="/tmp/alpha/wt/feat-a"),
                WorktreeInfo(repo_name="alpha", branch="Develop", path="/tmp/alpha/wt/develop"),
            ]
            await pane.set_worktrees(worktrees)
            await pilot.pause(0.1)
            rows = pane.query(WorktreeRow)
            # Extract branch names from each row's content
            branch_names = [str(row.content).split("\n")[0].strip() for row in rows]
            lower_names = [n.lower() for n in branch_names]
            assert lower_names == sorted(lower_names), f"Expected sorted branches, got: {branch_names}"

    asyncio.run(_run())


def test_row_shows_branch():
    """WKTR-03a: WorktreeRow rendered text contains the branch name."""
    wt = WorktreeInfo(
        repo_name="joy",
        branch="feat-my-feature",
        path="/Users/pieter/Github/joy/wt/feat-my-feature",
    )
    row = WorktreeRow(wt)
    content = str(row.content)
    assert "feat-my-feature" in content


def test_dirty_indicator_shown():
    """WKTR-03b: WorktreeRow for is_dirty=True contains the dirty glyph (U+F111)."""
    wt = WorktreeInfo(
        repo_name="joy",
        branch="feat-dirty",
        path="/tmp/joy/wt/feat-dirty",
        is_dirty=True,
        has_upstream=True,
    )
    row = WorktreeRow(wt)
    content = str(row.content)
    assert "\uf111" in content, f"Expected dirty glyph in: {repr(content)}"


def test_no_upstream_indicator_shown():
    """WKTR-03c: WorktreeRow for has_upstream=False contains the no-upstream glyph (U+F0BE1)."""
    wt = WorktreeInfo(
        repo_name="joy",
        branch="feat-no-upstream",
        path="/tmp/joy/wt/feat-no-upstream",
        is_dirty=False,
        has_upstream=False,
    )
    row = WorktreeRow(wt)
    content = str(row.content)
    assert "\U000f0be1" in content, f"Expected no-upstream glyph in: {repr(content)}"


def test_clean_tracked_no_indicators():
    """WKTR-03d: WorktreeRow for clean + has_upstream=True shows neither indicator glyph."""
    wt = WorktreeInfo(
        repo_name="joy",
        branch="feat-clean",
        path="/tmp/joy/wt/feat-clean",
        is_dirty=False,
        has_upstream=True,
    )
    row = WorktreeRow(wt)
    content = str(row.content)
    assert "\uf111" not in content, f"Dirty glyph should not appear: {repr(content)}"
    assert "\U000f0be1" not in content, f"No-upstream glyph should not appear: {repr(content)}"


def test_row_shows_abbreviated_path():
    """WKTR-03e: WorktreeRow shows home-abbreviated path on line 2."""
    wt = WorktreeInfo(
        repo_name="joy",
        branch="feat-x",
        path="/Users/pieter/Github/joy/wt/feat-x",
    )
    row = WorktreeRow(wt)
    content = str(row.content)
    assert "~/Github/joy/wt/feat-x" in content, f"Expected abbreviated path in: {repr(content)}"


def test_set_worktrees_idempotent():
    """D-03: Calling set_worktrees twice with same data produces identical DOM children."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield WorktreePane()

    import asyncio

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            worktrees = _sample_worktrees()

            await pane.set_worktrees(worktrees)
            await pilot.pause(0.1)
            count_first = len(pane.query(WorktreeRow))
            header_first = len(pane.query(GroupHeader))

            await pane.set_worktrees(worktrees)
            await pilot.pause(0.1)
            count_second = len(pane.query(WorktreeRow))
            header_second = len(pane.query(GroupHeader))

            assert count_first == count_second, (
                f"Row count changed: {count_first} -> {count_second}"
            )
            assert header_first == header_second, (
                f"Header count changed: {header_first} -> {header_second}"
            )

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Integration tests (Textual pilot, async)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_loading_placeholder(mock_store_with_worktrees):
    """D-05: Before worker completes, pane contains a 'Loading' Static."""
    from textual.widgets import Static

    app = JoyApp()
    async with app.run_test() as pilot:
        # Check immediately — before waiting for workers
        pane = app.query_one("#worktrees-pane")
        statics = pane.query(Static)
        texts = [str(s.content).lower() for s in statics]
        assert any("loading" in t for t in texts), (
            f"Expected 'Loading' placeholder, found: {texts}"
        )


@pytest.mark.asyncio
async def test_app_loads_worktrees(mock_store_with_worktrees):
    """D-01: After worker completes with mocked discover_worktrees, pane contains WorktreeRow widgets."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        pane = app.query_one("#worktrees-pane")
        rows = pane.query(WorktreeRow)
        assert len(rows) == 4, f"Expected 4 WorktreeRow widgets, got: {len(rows)}"


@pytest.mark.asyncio
async def test_empty_state_no_repos(mock_store_empty_repos):
    """D-15: When load_repos returns [] and discover_worktrees returns [], pane shows 'No repos registered'."""
    from textual.widgets import Static

    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        pane = app.query_one("#worktrees-pane")
        statics = pane.query(Static)
        texts = [str(s.content).lower() for s in statics]
        assert any("no repos" in t for t in texts), (
            f"Expected 'No repos registered' message, found: {texts}"
        )


@pytest.mark.asyncio
async def test_empty_state_no_worktrees(mock_store_repos_no_worktrees):
    """D-16: When repos exist but discover_worktrees returns [], pane shows 'No active worktrees'."""
    from textual.widgets import Static

    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        pane = app.query_one("#worktrees-pane")
        statics = pane.query(Static)
        texts = [str(s.content).lower() for s in statics]
        assert any("no active worktrees" in t for t in texts), (
            f"Expected 'No active worktrees' message, found: {texts}"
        )


@pytest.mark.asyncio
async def test_pane_interactive(mock_store_with_worktrees):
    """WKTR-10 updated: WorktreePane has cursor BINDINGS; pane has can_focus=True."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        pane = app.query_one("#worktrees-pane")
        # BINDINGS must include cursor and activate keys
        binding_keys = [b.key for b in WorktreePane.BINDINGS]
        assert "j" in binding_keys, f"Expected 'j' binding, got: {binding_keys}"
        assert "k" in binding_keys, f"Expected 'k' binding, got: {binding_keys}"
        assert "enter" in binding_keys, f"Expected 'enter' binding, got: {binding_keys}"
        assert "escape" in binding_keys, f"Expected 'escape' binding, got: {binding_keys}"
        # Pane must be focusable (for Tab cycling)
        assert pane.can_focus is True, "WorktreePane must have can_focus=True"


# ---------------------------------------------------------------------------
# Phase 11 Plan 02: MR row rendering, pane wiring, app integration
# ---------------------------------------------------------------------------


def _sample_mr_info(
    mr_number: int = 42,
    is_draft: bool = False,
    ci_status: str | None = "pass",
    author: str = "@pieter",
    last_commit_hash: str = "abc1234",
    last_commit_msg: str = "fix: login redirect",
    url: str = "https://github.com/example/repo/pull/42",
) -> MRInfo:
    return MRInfo(
        mr_number=mr_number,
        is_draft=is_draft,
        ci_status=ci_status,
        author=author,
        last_commit_hash=last_commit_hash,
        last_commit_msg=last_commit_msg,
        url=url,
    )


# ---------------------------------------------------------------------------
# build_content MR rendering tests (unit, no Textual app needed)
# ---------------------------------------------------------------------------


def test_build_content_no_mr_unchanged():
    """Phase 9 layout preserved: no MR -> path on line 2, no MR number."""
    content = WorktreeRow.build_content("feat-x", False, True, "~/path", mr_info=None)
    text = str(content)
    lines = text.split("\n")
    assert "~/path" in lines[1], f"Expected path on line 2, got: {lines[1]}"
    assert "!" not in text, f"MR number should not appear: {text}"


def test_build_content_mr_number_shown():
    """MR number appears as !N in content when MRInfo is present."""
    content = WorktreeRow.build_content(
        "feat-x", False, True, "~/path", mr_info=_sample_mr_info(mr_number=42)
    )
    assert "!42" in str(content)


def test_build_content_mr_open_icon():
    """Open MR shows ICON_MR_OPEN."""
    content = WorktreeRow.build_content(
        "feat-x", False, True, "~/path", mr_info=_sample_mr_info(is_draft=False)
    )
    assert ICON_MR_OPEN in str(content)


def test_build_content_mr_draft_icon():
    """Draft MR shows ICON_MR_DRAFT but not ICON_MR_OPEN."""
    content = WorktreeRow.build_content(
        "feat-x", False, True, "~/path", mr_info=_sample_mr_info(is_draft=True)
    )
    text = str(content)
    assert ICON_MR_DRAFT in text
    assert ICON_MR_OPEN not in text


def test_build_content_ci_pass():
    """CI pass shows ICON_CI_PASS."""
    content = WorktreeRow.build_content(
        "feat-x", False, True, "~/path", mr_info=_sample_mr_info(ci_status="pass")
    )
    assert ICON_CI_PASS in str(content)


def test_build_content_ci_fail():
    """CI fail shows ICON_CI_FAIL."""
    content = WorktreeRow.build_content(
        "feat-x", False, True, "~/path", mr_info=_sample_mr_info(ci_status="fail")
    )
    assert ICON_CI_FAIL in str(content)


def test_build_content_ci_pending():
    """CI pending shows ICON_CI_PENDING."""
    content = WorktreeRow.build_content(
        "feat-x", False, True, "~/path", mr_info=_sample_mr_info(ci_status="pending")
    )
    assert ICON_CI_PENDING in str(content)


def test_build_content_ci_none_blank():
    """CI None shows no CI icon at all."""
    content = WorktreeRow.build_content(
        "feat-x", False, True, "~/path", mr_info=_sample_mr_info(ci_status=None)
    )
    text = str(content)
    assert ICON_CI_PASS not in text
    assert ICON_CI_FAIL not in text
    assert ICON_CI_PENDING not in text


def test_build_content_mr_author_on_line2():
    """MR present -> line 2 shows @author."""
    content = WorktreeRow.build_content(
        "feat-x", False, True, "~/path", mr_info=_sample_mr_info(author="@pieter")
    )
    lines = str(content).split("\n")
    assert "@pieter" in lines[1], f"Expected @pieter on line 2, got: {lines[1]}"


def test_build_content_mr_commit_on_line2():
    """MR present -> line 2 shows commit hash + message."""
    content = WorktreeRow.build_content(
        "feat-x", False, True, "~/path",
        mr_info=_sample_mr_info(last_commit_hash="abc1234", last_commit_msg="fix: login redirect"),
    )
    lines = str(content).split("\n")
    assert "abc1234" in lines[1], f"Expected commit hash on line 2, got: {lines[1]}"
    assert "fix: login redirect" in lines[1], f"Expected commit msg on line 2, got: {lines[1]}"


def test_build_content_no_mr_path_on_line2():
    """No MR -> line 2 shows abbreviated path (Phase 9 behavior preserved)."""
    content = WorktreeRow.build_content(
        "feat-x", False, True, "~/Github/joy", mr_info=None
    )
    lines = str(content).split("\n")
    assert "~/Github/joy" in lines[1], f"Expected path on line 2, got: {lines[1]}"


# ---------------------------------------------------------------------------
# WorktreeRow constructor test
# ---------------------------------------------------------------------------


def test_worktree_row_accepts_mr_info():
    """WorktreeRow constructor accepts mr_info keyword and renders MR number."""
    wt = WorktreeInfo(
        repo_name="joy",
        branch="feat-x",
        path="/tmp/joy/wt/feat-x",
    )
    row = WorktreeRow(wt, mr_info=_sample_mr_info(mr_number=42))
    assert "!42" in str(row.content)


# ---------------------------------------------------------------------------
# set_worktrees with mr_data test (async, minimal Textual app)
# ---------------------------------------------------------------------------


def test_set_worktrees_with_mr_data():
    """set_worktrees passes MRInfo from mr_data dict to matching WorktreeRow."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield WorktreePane()

    import asyncio

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            worktrees = [
                WorktreeInfo(
                    repo_name="joy",
                    branch="feat-z",
                    path="/tmp/joy/wt/feat-z",
                ),
            ]
            mr_data = {("joy", "feat-z"): _sample_mr_info(mr_number=42)}
            await pane.set_worktrees(worktrees, mr_data=mr_data)
            await pilot.pause(0.1)
            rows = pane.query(WorktreeRow)
            assert len(rows) == 1
            assert "!42" in str(rows[0].content), (
                f"Expected !42 in row content, got: {str(rows[0].content)}"
            )

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# set_refresh_label mr_error test
# ---------------------------------------------------------------------------


def test_refresh_label_mr_error():
    """set_refresh_label with mr_error=True adds warning to border_title."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield WorktreePane()

    import asyncio

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            pane.set_refresh_label("5s ago", mr_error=True)
            assert "\u26a0" in pane.border_title or "mr" in pane.border_title.lower(), (
                f"Expected warning in border_title, got: {pane.border_title}"
            )

    asyncio.run(_run())
