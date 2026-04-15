"""Tests for joy.operations module -- subprocess-based object openers."""
from __future__ import annotations

from unittest.mock import patch, call

import pytest

from joy.models import Config, ObjectItem, ObjectType, PresetKind
from joy.operations import _OPENERS, open_object


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def make_item(kind: PresetKind, value: str) -> ObjectItem:
    return ObjectItem(kind=kind, value=value)


# ---------------------------------------------------------------------------
# Task 1: Standard openers -- STRING, URL, OBSIDIAN, FILE, WORKTREE
# ---------------------------------------------------------------------------


def test_copy_string_to_clipboard():
    """STRING type copies value to clipboard via pbcopy."""
    item = make_item(PresetKind.BRANCH, "feature/test")
    config = Config()
    with patch("joy.operations.subprocess.run") as mock_run:
        open_object(item=item, config=config)
    mock_run.assert_called_once_with(["pbcopy"], input=b"feature/test", check=True)


def test_open_url_in_browser():
    """URL type (generic) opens via open command."""
    item = make_item(PresetKind.MR, "https://gitlab.com/mr/1")
    config = Config()
    with patch("joy.operations.subprocess.run") as mock_run:
        open_object(item=item, config=config)
    mock_run.assert_called_once_with(["open", "https://gitlab.com/mr/1"], check=True)


def test_open_url_notion_desktop():
    """URL with notion.so hostname converts to notion:// scheme."""
    item = make_item(PresetKind.TICKET, "https://www.notion.so/page-123")
    config = Config()
    with patch("joy.operations.subprocess.run") as mock_run:
        open_object(item=item, config=config)
    mock_run.assert_called_once_with(["open", "notion://www.notion.so/page-123"], check=True)


def test_open_url_slack_desktop():
    """Slack URLs use plain open so macOS URL scheme handler navigates to the thread."""
    item = make_item(PresetKind.THREAD, "https://app.slack.com/client/T123/C456")
    config = Config()
    with patch("joy.operations.subprocess.run") as mock_run:
        open_object(item=item, config=config)
    mock_run.assert_called_once_with(
        ["open", "https://app.slack.com/client/T123/C456"], check=True
    )


def test_open_url_generic_no_special_handling():
    """URL type with generic domain opens via plain open command."""
    item = make_item(PresetKind.URL, "https://docs.example.com")
    config = Config()
    with patch("joy.operations.subprocess.run") as mock_run:
        open_object(item=item, config=config)
    mock_run.assert_called_once_with(["open", "https://docs.example.com"], check=True)


def test_open_obsidian_note():
    """OBSIDIAN type builds obsidian://open URI with vault and file."""
    item = make_item(PresetKind.NOTE, "project-notes/daily.md")
    config = Config(obsidian_vault="MyVault")
    with patch("joy.operations.subprocess.run") as mock_run:
        open_object(item=item, config=config)
    mock_run.assert_called_once_with(
        ["open", "obsidian://open?vault=MyVault&file=project-notes/daily.md"], check=True
    )


def test_open_obsidian_with_spaces():
    """OBSIDIAN type URL-encodes spaces in vault name and file path."""
    item = make_item(PresetKind.NOTE, "my notes/daily log.md")
    config = Config(obsidian_vault="My Vault")
    with patch("joy.operations.subprocess.run") as mock_run:
        open_object(item=item, config=config)
    called_args = mock_run.call_args[0][0]
    uri = called_args[1]
    assert "My%20Vault" in uri, f"Vault spaces not encoded: {uri}"
    assert "my%20notes/daily%20log.md" in uri, f"File spaces not encoded: {uri}"


def test_open_file_in_editor():
    """FILE type opens in configured editor via open -a."""
    item = make_item(PresetKind.FILE, "/path/to/file.py")
    config = Config(editor="Sublime Text")
    with patch("joy.operations.subprocess.run") as mock_run:
        open_object(item=item, config=config)
    mock_run.assert_called_once_with(
        ["open", "-a", "Sublime Text", "/path/to/file.py"], check=True
    )


def test_open_worktree_in_ide():
    """WORKTREE type opens path in configured IDE via open -a."""
    item = make_item(PresetKind.WORKTREE, "/Users/dev/worktrees/project")
    config = Config(ide="PyCharm")
    with patch("joy.operations.subprocess.run") as mock_run:
        open_object(item=item, config=config)
    mock_run.assert_called_once_with(
        ["open", "-a", "PyCharm", "/Users/dev/worktrees/project"], check=True
    )


def test_unregistered_type_raises(monkeypatch):
    """open_object raises ValueError when no opener is registered for a type."""
    # Temporarily clear the STRING opener and test with a STRING item
    original = _OPENERS.copy()
    _OPENERS.clear()
    try:
        item = make_item(PresetKind.BRANCH, "some-branch")
        config = Config()
        with pytest.raises(ValueError, match="No opener registered"):
            open_object(item=item, config=config)
    finally:
        _OPENERS.update(original)


# ---------------------------------------------------------------------------
# Task 2: iTerm2 opener
# ---------------------------------------------------------------------------


def test_open_iterm_opener_registered():
    """ITERM type has a registered opener."""
    assert ObjectType.ITERM in _OPENERS


def test_open_iterm_opener_is_callable():
    """The ITERM opener is a callable function."""
    assert callable(_OPENERS[ObjectType.ITERM])


def test_all_object_types_have_opener():
    """Every ObjectType member must have a registered opener."""
    for obj_type in ObjectType:
        assert obj_type in _OPENERS, f"No opener registered for {obj_type}"


@pytest.mark.macos_integration
def test_open_iterm_live():
    """Live test: creates a real iTerm2 session. Run manually with -m macos_integration."""
    item = make_item(PresetKind.TERMINALS, "joy-test-window")
    config = Config()
    # This calls real iTerm2 Python API -- iTerm2 must be installed
    open_object(item=item, config=config)
