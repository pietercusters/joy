"""Unit tests for ObjectRow 3-column layout, refresh_indicator, and helper functions."""
from __future__ import annotations

import pytest

from joy.models import Config, ObjectItem, ObjectType, PresetKind
from joy.widgets.object_row import ObjectRow, PRESET_ICONS, _success_message, _truncate


# ---------------------------------------------------------------------------
# 3-column compose() tests (Tests 1-6)
# ---------------------------------------------------------------------------


def test_compose_yields_three_static_children():
    """Test 1: ObjectRow.compose() yields 3 Static children with correct CSS classes."""
    item = ObjectItem(kind=PresetKind.BRANCH, value="main")
    row = ObjectRow(item, index=0)
    children = list(row.compose())
    assert len(children) == 3
    assert "col-icon" in children[0].classes
    assert "col-value" in children[1].classes
    assert "col-kind" in children[2].classes


def _get_content(widget):
    """Extract the content string from a Static widget (access name-mangled __content)."""
    return str(widget._Static__content)


def test_col_icon_contains_correct_preset_icon():
    """Test 2: col-icon child contains the correct PRESET_ICON for the item's kind."""
    item = ObjectItem(kind=PresetKind.MR, value="https://example.com/mr/1")
    row = ObjectRow(item, index=0)
    children = list(row.compose())
    icon_widget = children[0]
    expected_icon = PRESET_ICONS[PresetKind.MR]
    assert expected_icon in _get_content(icon_widget)


def test_col_value_contains_label_when_set():
    """Test 3a: col-value contains item.label when label is set."""
    item = ObjectItem(kind=PresetKind.BRANCH, value="feature/xyz", label="My Branch")
    row = ObjectRow(item, index=0)
    children = list(row.compose())
    value_widget = children[1]
    assert "My Branch" in _get_content(value_widget)


def test_col_value_contains_value_when_no_label():
    """Test 3b: col-value contains item.value when label is empty."""
    item = ObjectItem(kind=PresetKind.BRANCH, value="feature/xyz")
    row = ObjectRow(item, index=0)
    children = list(row.compose())
    value_widget = children[1]
    assert "feature/xyz" in _get_content(value_widget)


def test_col_kind_contains_kind_value():
    """Test 4: col-kind child contains item.kind.value (e.g., 'branch')."""
    item = ObjectItem(kind=PresetKind.BRANCH, value="main")
    row = ObjectRow(item, index=0)
    children = list(row.compose())
    kind_widget = children[2]
    assert "branch" in _get_content(kind_widget)


def test_no_dot_indicator_in_compose():
    """Test 5: No dot indicator (U+25CF/U+25CB) appears anywhere in the composed children."""
    item = ObjectItem(kind=PresetKind.BRANCH, value="main", open_by_default=True)
    row = ObjectRow(item, index=0)
    children = list(row.compose())
    all_text = "".join(_get_content(c) for c in children)
    assert "\u25cf" not in all_text
    assert "\u25cb" not in all_text


def test_refresh_indicator_updates_col_value():
    """Test 6: refresh_indicator() updates the col-value child by querying .col-value Static."""
    from unittest.mock import MagicMock, patch
    from textual.widgets import Static

    item = ObjectItem(kind=PresetKind.BRANCH, value="main", label="Main Branch")
    row = ObjectRow(item, index=0)

    # Mock query_one to return a mock Static widget
    mock_static = MagicMock(spec=Static)
    row.query_one = MagicMock(return_value=mock_static)

    row.refresh_indicator()

    row.query_one.assert_called_once_with(".col-value", Static)
    mock_static.update.assert_called_once_with("Main Branch")


# ---------------------------------------------------------------------------
# _truncate helper (Tests 7-8)
# ---------------------------------------------------------------------------


def test_truncate_short_string_unchanged():
    """Test 7: _truncate('short') returns 'short' unchanged."""
    assert _truncate("short") == "short"


def test_truncate_long_string_truncated():
    """Test 8: _truncate('a' * 50) returns first 37 chars + '...' (40 chars total)."""
    long_str = "a" * 50
    result = _truncate(long_str)
    assert len(result) == 40
    assert result == "a" * 37 + "..."


# ---------------------------------------------------------------------------
# _success_message helper (Tests 9-16)
# ---------------------------------------------------------------------------


def test_success_message_string_type(sample_config):
    """Test 9: _success_message for STRING type returns 'Copied: {display}'."""
    item = ObjectItem(kind=PresetKind.BRANCH, value="feature/my-branch", label="My Branch")
    msg = _success_message(item, sample_config)
    assert msg == "Copied: My Branch"


def test_success_message_url_notion(sample_config):
    """Test 10: _success_message for URL type with notion.so returns 'Opened in Notion: {display}'."""
    item = ObjectItem(kind=PresetKind.MR, value="https://notion.so/ticket-123", label="Ticket")
    msg = _success_message(item, sample_config)
    assert msg == "Opened in Notion: Ticket"


def test_success_message_url_slack(sample_config):
    """Test 11: _success_message for URL type with slack.com returns 'Opened in Slack: {display}'."""
    item = ObjectItem(kind=PresetKind.THREAD, value="https://app.slack.com/archives/123", label="Thread")
    msg = _success_message(item, sample_config)
    assert msg == "Opened in Slack: Thread"


def test_success_message_url_generic(sample_config):
    """Test 12: _success_message for URL type (generic) returns 'Opened: {display}'."""
    item = ObjectItem(kind=PresetKind.URL, value="https://docs.example.com", label="Docs")
    msg = _success_message(item, sample_config)
    assert msg == "Opened: Docs"


def test_success_message_obsidian(sample_config):
    """Test 13: _success_message for OBSIDIAN type returns 'Opened in Obsidian: {display}'."""
    item = ObjectItem(kind=PresetKind.NOTE, value="project-notes/daily.md", label="Daily Notes")
    msg = _success_message(item, sample_config)
    assert msg == "Opened in Obsidian: Daily Notes"


def test_success_message_file(sample_config):
    """Test 14: _success_message for FILE type returns 'Opened in {config.editor}: {display}'."""
    item = ObjectItem(kind=PresetKind.FILE, value="/path/to/file.py", label="Main file")
    msg = _success_message(item, sample_config)
    assert msg == f"Opened in {sample_config.editor}: Main file"


def test_success_message_worktree(sample_config):
    """Test 15: _success_message for WORKTREE type returns 'Opened in {config.ide}: {display}'."""
    item = ObjectItem(kind=PresetKind.WORKTREE, value="/Users/dev/worktrees/project", label="Worktree")
    msg = _success_message(item, sample_config)
    assert msg == f"Opened in {sample_config.ide}: Worktree"


def test_success_message_iterm(sample_config):
    """Test 16: _success_message for ITERM type returns 'Opened in iTerm2: {display}'."""
    item = ObjectItem(kind=PresetKind.AGENTS, value="project-agents", label="Agents")
    msg = _success_message(item, sample_config)
    assert msg == "Opened in iTerm2: Agents"
