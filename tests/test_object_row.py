"""Unit tests for ObjectRow dot indicator rendering and helper functions."""
from __future__ import annotations

import pytest

from joy.models import Config, ObjectItem, ObjectType, PresetKind
from joy.widgets.object_row import ObjectRow, _success_message, _truncate


# ---------------------------------------------------------------------------
# Dot indicator rendering tests (Tests 1-5)
# ---------------------------------------------------------------------------


def test_render_dot_filled_when_open_by_default_true():
    """Test 1: _render_text with open_by_default=True returns Text containing U+25CF."""
    item = ObjectItem(kind=PresetKind.BRANCH, value="main", open_by_default=True)
    text = ObjectRow._render_text(item)
    assert "\u25cf" in text.plain


def test_render_dot_empty_when_open_by_default_false():
    """Test 2: _render_text with open_by_default=False returns Text containing U+25CB."""
    item = ObjectItem(kind=PresetKind.BRANCH, value="main", open_by_default=False)
    text = ObjectRow._render_text(item)
    assert "\u25cb" in text.plain


def test_render_text_format():
    """Test 3: _render_text output format is '{dot} {icon}  {label}  {value}'."""
    item = ObjectItem(kind=PresetKind.BRANCH, value="main", open_by_default=True)
    text = ObjectRow._render_text(item)
    plain = text.plain
    # Should start with the filled dot
    assert plain[0] == "\u25cf"
    # Should have a space after the dot before the icon
    assert plain[1] == " "
    # Should contain "  branch  " (2 spaces between icon and label, 2 between label and value)
    assert "  branch  " in plain


def test_dot_style_bright_white_when_open_by_default_true():
    """Test 4: The dot span has style 'bright_white' when open_by_default=True."""
    item = ObjectItem(kind=PresetKind.BRANCH, value="main", open_by_default=True)
    text = ObjectRow._render_text(item)
    # The first span should be the dot with bright_white style
    spans = list(text._spans)
    assert len(spans) > 0
    first_span = spans[0]
    # Check the span covers position 0 (the dot character)
    assert first_span.start == 0
    assert first_span.end == 1
    # Style should contain bright_white
    assert "bright_white" in str(first_span.style)


def test_dot_style_grey50_when_open_by_default_false():
    """Test 5: The dot span has style 'grey50' when open_by_default=False."""
    item = ObjectItem(kind=PresetKind.BRANCH, value="main", open_by_default=False)
    text = ObjectRow._render_text(item)
    spans = list(text._spans)
    assert len(spans) > 0
    first_span = spans[0]
    assert first_span.start == 0
    assert first_span.end == 1
    assert "grey50" in str(first_span.style)


# ---------------------------------------------------------------------------
# refresh_indicator method (Test 6)
# ---------------------------------------------------------------------------


def test_refresh_indicator_calls_update(monkeypatch):
    """Test 6: refresh_indicator() calls self.update() with re-rendered text."""
    item = ObjectItem(kind=PresetKind.BRANCH, value="main", open_by_default=False)
    row = ObjectRow.__new__(ObjectRow)
    row.item = item
    row.index = 0

    called_with = []

    def mock_update(renderable):
        called_with.append(renderable)

    monkeypatch.setattr(row, "update", mock_update)

    # Toggle the item's open_by_default and call refresh_indicator
    row.item.open_by_default = True
    row.refresh_indicator()

    assert len(called_with) == 1
    # The update should have been called with a Text containing the filled dot
    updated_text = called_with[0]
    assert "\u25cf" in updated_text.plain


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
