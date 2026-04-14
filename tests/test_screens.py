"""Unit tests for the four modal screen classes in joy.screens."""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Input, SelectionList, Static

from joy.models import Config, PresetKind, Repo
from joy.screens import ConfirmationModal, NameInputModal, PresetPickerModal, ValueInputModal
from joy.screens.settings import SettingsModal, _RepoListWidget


class ModalTestApp(App):
    """Minimal app for testing modal screens."""

    def compose(self) -> ComposeResult:
        yield Static("test")


# ---------------------------------------------------------------------------
# NameInputModal tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_name_input_submit_returns_name():
    """NameInputModal returns the typed name on Enter."""
    result_holder: list[str | None] = []
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await app.push_screen(NameInputModal(), result_holder.append)
        await pilot.pause(0.1)
        for ch in "my-project":
            await pilot.press(ch)
        await pilot.press("enter")
        await pilot.pause(0.1)
    assert result_holder == ["my-project"]


@pytest.mark.asyncio
async def test_name_input_escape_returns_none():
    """NameInputModal returns None on Escape."""
    result_holder: list[str | None] = []
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await app.push_screen(NameInputModal(), result_holder.append)
        await pilot.pause(0.1)
        await pilot.press("escape")
        await pilot.pause(0.1)
    assert result_holder == [None]


@pytest.mark.asyncio
async def test_name_input_empty_rejected():
    """NameInputModal does not dismiss on empty input; modal stays open."""
    result_holder: list[str | None] = []
    dismissed = False

    def on_dismiss(result: str | None) -> None:
        nonlocal dismissed
        dismissed = True
        result_holder.append(result)

    app = ModalTestApp()
    async with app.run_test() as pilot:
        await app.push_screen(NameInputModal(), on_dismiss)
        await pilot.pause(0.1)
        # Press Enter with empty input
        await pilot.press("enter")
        await pilot.pause(0.1)
        # Modal should still be open (not dismissed)
        assert not dismissed, "Modal should not have been dismissed on empty input"
        # Clean up: escape to close
        await pilot.press("escape")
        await pilot.pause(0.1)


# ---------------------------------------------------------------------------
# PresetPickerModal tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_preset_picker_shows_all_presets():
    """PresetPickerModal lists all 9 PresetKind values on open."""
    from textual.widgets import ListView
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await app.push_screen(PresetPickerModal(), lambda _: None)
        await pilot.pause(0.1)
        # Query from the currently active screen (the modal)
        listview = app.screen.query_one("#preset-list", ListView)
        # All 9 presets shown by default
        assert len(list(listview.children)) == 9


@pytest.mark.asyncio
async def test_preset_picker_filter():
    """PresetPickerModal filters list when user types 'br' to show only 'branch'."""
    from textual.widgets import Label, ListView
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await app.push_screen(PresetPickerModal(), lambda _: None)
        await pilot.pause(0.1)
        # Type "br" to filter
        await pilot.press("b")
        await pilot.press("r")
        await pilot.pause(0.1)
        # Query from the currently active screen (the modal)
        listview = app.screen.query_one("#preset-list", ListView)
        children = list(listview.children)
        assert len(children) == 1
        # The remaining item should be "branch"
        label = children[0].query_one(Label)
        assert "branch" in str(label.content)


@pytest.mark.asyncio
async def test_preset_picker_escape_returns_none():
    """PresetPickerModal returns None on Escape."""
    result_holder: list[PresetKind | None] = []
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await app.push_screen(PresetPickerModal(), result_holder.append)
        await pilot.pause(0.1)
        await pilot.press("escape")
        await pilot.pause(0.1)
    assert result_holder == [None]


# ---------------------------------------------------------------------------
# ValueInputModal tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_value_input_add_mode():
    """ValueInputModal in add mode returns typed value on Enter."""
    result_holder: list[str | None] = []
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await app.push_screen(ValueInputModal(PresetKind.BRANCH), result_holder.append)
        await pilot.pause(0.1)
        for ch in "feature/new":
            await pilot.press(ch)
        await pilot.press("enter")
        await pilot.pause(0.1)
    assert result_holder == ["feature/new"]


@pytest.mark.asyncio
async def test_value_input_edit_mode():
    """ValueInputModal in edit mode returns pre-populated value on Enter."""
    result_holder: list[str | None] = []
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await app.push_screen(
            ValueInputModal(PresetKind.BRANCH, existing_value="main"),
            result_holder.append,
        )
        await pilot.pause(0.1)
        # Press Enter without changing the value -> should return "main"
        await pilot.press("enter")
        await pilot.pause(0.1)
    assert result_holder == ["main"]


@pytest.mark.asyncio
async def test_value_input_empty_rejected():
    """ValueInputModal does not dismiss on empty input."""
    dismissed = False

    def on_dismiss(result: str | None) -> None:
        nonlocal dismissed
        dismissed = True

    app = ModalTestApp()
    async with app.run_test() as pilot:
        await app.push_screen(ValueInputModal(PresetKind.BRANCH), on_dismiss)
        await pilot.pause(0.1)
        # Press Enter with empty input
        await pilot.press("enter")
        await pilot.pause(0.1)
        assert not dismissed, "Modal should not have been dismissed on empty input"
        # Clean up
        await pilot.press("escape")
        await pilot.pause(0.1)


# ---------------------------------------------------------------------------
# ConfirmationModal tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirmation_enter_returns_true():
    """ConfirmationModal returns True on Enter."""
    result_holder: list[bool] = []
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await app.push_screen(
            ConfirmationModal(title="Delete Project", prompt="Delete project 'test'?"),
            result_holder.append,
        )
        await pilot.pause(0.1)
        await pilot.press("enter")
        await pilot.pause(0.1)
    assert result_holder == [True]


@pytest.mark.asyncio
async def test_confirmation_escape_returns_false():
    """ConfirmationModal returns False on Escape."""
    result_holder: list[bool] = []
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await app.push_screen(
            ConfirmationModal(title="Delete Object", prompt="Delete branch 'main'?"),
            result_holder.append,
        )
        await pilot.pause(0.1)
        await pilot.press("escape")
        await pilot.pause(0.1)
    assert result_holder == [False]


# ---------------------------------------------------------------------------
# SettingsModal tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_settings_save_returns_config():
    """SettingsModal returns a Config instance when Save button is pressed."""
    result_holder: list[Config | None] = []
    app = ModalTestApp()
    async with app.run_test(size=(100, 60)) as pilot:
        await app.push_screen(SettingsModal(Config()), result_holder.append)
        await pilot.pause(0.1)
        # Tab 6 times from field-ide (already focused) to reach btn-save:
        # field-ide -> field-editor -> field-vault -> field-terminal -> field-kinds -> repo-list-widget -> btn-save
        for _ in range(6):
            await pilot.press("tab")
        await pilot.pause(0.1)
        await pilot.press("enter")
        await pilot.pause(0.1)
    assert len(result_holder) == 1
    assert isinstance(result_holder[0], Config)
    # Don't assert specific field values -- that belongs in test_settings_prepopulated


@pytest.mark.asyncio
async def test_settings_escape_returns_none():
    """SettingsModal returns None on Escape."""
    result_holder: list[Config | None] = []
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await app.push_screen(SettingsModal(Config()), result_holder.append)
        await pilot.pause(0.1)
        await pilot.press("escape")
        await pilot.pause(0.1)
    assert result_holder == [None]


@pytest.mark.asyncio
async def test_settings_prepopulated():
    """SettingsModal Input fields show values from the provided Config."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await app.push_screen(SettingsModal(Config(ide="VSCode", editor="vim")), lambda _: None)
        await pilot.pause(0.1)
        assert app.screen.query_one("#field-ide", Input).value == "VSCode"
        assert app.screen.query_one("#field-editor", Input).value == "vim"


@pytest.mark.asyncio
async def test_settings_kinds_prepopulated():
    """SettingsModal SelectionList shows pre-selected kinds from Config."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await app.push_screen(
            SettingsModal(Config(default_open_kinds=["worktree"])),
            lambda _: None,
        )
        await pilot.pause(0.1)
        selected = app.screen.query_one("#field-kinds", SelectionList).selected
        assert list(selected) == ["worktree"]


# ---------------------------------------------------------------------------
# SettingsModal Repos section tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_settings_repos_section_visible():
    """SettingsModal shows a Repos section label when repos are provided."""
    repos = [Repo(name="my-repo", local_path="/tmp/my-repo")]
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await app.push_screen(SettingsModal(Config(), repos=repos), lambda _: None)
        await pilot.pause(0.1)
        # Find all Static widgets with "Repos" text
        statics = app.screen.query(Static)
        texts = [s.content for s in statics]
        assert any("Repos" in t for t in texts), "Should show 'Repos' label"


@pytest.mark.asyncio
async def test_settings_repos_list_shows_repos():
    """SettingsModal shows repo names in the _RepoListWidget when repos are passed."""
    repos = [
        Repo(name="alpha", local_path="/tmp/alpha"),
        Repo(name="beta", local_path="/tmp/beta"),
    ]
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await app.push_screen(SettingsModal(Config(), repos=repos), lambda _: None)
        await pilot.pause(0.1)
        widget = app.screen.query_one("#repo-list-widget", _RepoListWidget)
        assert len(widget._rows) == 2
        assert widget._rows[0].repo.name == "alpha"
        assert widget._rows[1].repo.name == "beta"


@pytest.mark.asyncio
async def test_settings_repos_empty_message():
    """SettingsModal shows 'No repos registered' when repos list is empty."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await app.push_screen(SettingsModal(Config(), repos=[]), lambda _: None)
        await pilot.pause(0.1)
        widget = app.screen.query_one("#repo-list-widget", _RepoListWidget)
        assert len(widget._rows) == 0
        # Check the "No repos registered" message is present
        statics = widget.query(Static)
        texts = [s.content for s in statics]
        assert any("No repos registered" in t for t in texts)


@pytest.mark.asyncio
async def test_settings_save_still_returns_config_with_repos():
    """Save button still returns Config when repos section is present (regression)."""
    repos = [Repo(name="test-repo", local_path="/tmp/test-repo")]
    result_holder: list[Config | None] = []
    app = ModalTestApp()
    async with app.run_test(size=(100, 60)) as pilot:
        await app.push_screen(
            SettingsModal(Config(), repos=repos), result_holder.append
        )
        await pilot.pause(0.1)
        # Tab 6 times: ide -> editor -> vault -> terminal -> kinds -> repo-list -> btn-save
        for _ in range(6):
            await pilot.press("tab")
        await pilot.pause(0.1)
        await pilot.press("enter")
        await pilot.pause(0.1)
    assert len(result_holder) == 1
    assert isinstance(result_holder[0], Config)
