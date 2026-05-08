# Screens

Textual `ModalScreen` subclasses for overlay dialogs. Pushed onto the screen stack, dismissed with Escape or explicit action.

## Screens

| Screen | File | Purpose | Returns |
|--------|------|---------|---------|
| `SettingsModal` | `settings.py` | Edit config (ide, editor, vault, terminal, repos) | `Config \| None` |
| `NewProjectModal` | `new_project.py` | Create project: name + optional repo + branch | `NewProjectResult \| None` |
| `NameInputModal` | `name_input.py` | Single text input (rename project/session) | `str \| None` |
| `ValueInputModal` | `value_input.py` | Single text input for object values | `str \| None` |
| `PresetPickerModal` | `preset_picker.py` | Select object kind from PresetKind list | `PresetKind \| None` |
| `ConfirmationModal` | `confirmation.py` | Yes/No confirmation dialog | `bool` |
| `LegendModal` | `legend.py` | Read-only key binding reference | None |
| `ArchiveBrowserModal` | `archive_browser.py` | Browse and unarchive projects | `ArchivedProject \| None` |
| `RepoPickerModal` | `repo_picker.py` | Select repo from registered repos | `str \| None` (repo name) |

## Pattern

All modals follow the same structure:

```python
class MyModal(ModalScreen[ReturnType]):
    BINDINGS = [("escape", "dismiss_modal", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Title", id="title")
            yield Input(id="value")
            yield Button("OK", id="ok")

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.dismiss(self.query_one("#value", Input).value)
```

- Inherit from `ModalScreen[T]` with typed return
- `self.dismiss(result)` returns to the caller
- `app.push_screen(MyModal(), callback=self._on_result)` to invoke
- Escape always dismisses without result

## Adding a New Modal

1. Create `src/joy/screens/new_modal.py` with `ModalScreen[T]` subclass
2. Add import to `screens/__init__.py` and `__all__`
3. Invoke from `app.py` via `self.push_screen(NewModal(), callback=...)`
