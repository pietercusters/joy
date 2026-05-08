"""Snapshot baseline tests for joy TUI (Phase 20, TEST-05).

Uses pytest-textual-snapshot's snap_compare fixture to capture SVG renderings
of key TUI screens. Baselines stored in tests/snapshot_tests_output/.

IMPORTANT: snap_compare is a sync fixture -- do NOT use @pytest.mark.asyncio.
The run_before async callback is handled internally by snap_compare.

Store functions are patched to return deterministic test data. This is the
pragmatic exception for snapshot tests (RESEARCH.md Pitfall 2): JoyApp
doesn't accept injected backends, so store-level @patch is necessary.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

from joy.app import JoyApp
from joy.models import Config, ObjectItem, PresetKind, Project

pytestmark = pytest.mark.snapshot


_PROJECTS = [
    Project(name="project-alpha", objects=[
        ObjectItem(kind=PresetKind.BRANCH, value="main"),
        ObjectItem(kind=PresetKind.MR, value="https://gitlab.com/owner/repo/-/merge_requests/1", label="MR #1"),
    ]),
    Project(name="project-beta", objects=[
        ObjectItem(kind=PresetKind.TICKET, value="https://notion.so/123", label="TICK-1"),
        ObjectItem(kind=PresetKind.URL, value="https://docs.example.com", label="Docs"),
    ]),
]


def _mock_store():
    """Patch store module functions to return deterministic test data."""
    return patch.multiple(
        "joy.store",
        load_projects=lambda **kw: list(_PROJECTS),
        load_config=lambda **kw: Config(),
        load_repos=lambda **kw: [],
    )


def test_snapshot_initial_render(snap_compare):
    """Snapshot baseline: initial render with two projects loaded."""
    with _mock_store():
        assert snap_compare(JoyApp(), terminal_size=(120, 40))


def test_snapshot_project_selected(snap_compare):
    """Snapshot baseline: first project selected, detail pane populated."""
    async def run_before(pilot):
        await pilot.pause(0.3)
        await pilot.app.workers.wait_for_complete()
        await pilot.press("enter")
        await pilot.pause(0.2)

    with _mock_store():
        assert snap_compare(JoyApp(), run_before=run_before, terminal_size=(120, 40))


def test_snapshot_sync_active(snap_compare):
    """Snapshot baseline: app loaded with default view (worktree/terminal panes visible)."""
    async def run_before(pilot):
        await pilot.pause(0.3)
        await pilot.app.workers.wait_for_complete()
        await pilot.pause(0.2)

    with _mock_store():
        assert snap_compare(JoyApp(), run_before=run_before, terminal_size=(120, 40))
