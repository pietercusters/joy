---
phase: 05-settings-search-distribution
plan: 01
subsystem: settings
tags: [settings, modal, config, tui, textual]
dependency_graph:
  requires: []
  provides: [SettingsModal, JoyApp.action_settings, JoyApp._save_config_bg]
  affects: [src/joy/app.py, src/joy/screens/settings.py, src/joy/screens/__init__.py]
tech_stack:
  added: []
  patterns: [ModalScreen[Config | None], @work(thread=True) background save, push_screen with callback]
key_files:
  created:
    - src/joy/screens/settings.py
  modified:
    - src/joy/screens/__init__.py
    - src/joy/app.py
    - tests/test_screens.py
    - tests/test_tui.py
decisions:
  - Tab count to Save button is 5 (not 6 as plan specified) because field-ide already has focus on mount
  - Used list(SelectionList.selected) to ensure Config.default_open_kinds receives a plain list
metrics:
  duration: ~8 minutes
  completed: 2026-04-11T12:48:20Z
  tasks_completed: 2
  files_modified: 5
---

# Phase 5 Plan 01: Settings Modal Summary

**One-liner:** SettingsModal overlay for all 5 Config fields (ide, editor, obsidian_vault, terminal, default_open_kinds) wired to JoyApp via `s` binding with background TOML save.

## What Was Built

### Task 1: SettingsModal screen (TDD)

Created `src/joy/screens/settings.py` with `SettingsModal(ModalScreen[Config | None])`:
- 4 `Input` widgets (field-ide, field-editor, field-vault, field-terminal) pre-populated from passed `Config`
- 1 `SelectionList` (field-kinds) with all 9 `PresetKind` values as `(k.value, k.value, bool)` tuples
- `Button("Save Settings", variant="primary", id="btn-save")` triggers `_do_save()`
- `Escape` binding calls `action_cancel()` which dismisses with `None`
- `_do_save()` collects all field values into a new `Config` and dismisses with it
- SelectionList values passed as `k.value` (str) to ensure `.selected` returns `list[str]` matching `Config.default_open_kinds` type (T-05-01-03 mitigation)

Updated `src/joy/screens/__init__.py` to export `SettingsModal`.

### Task 2: JoyApp integration

Modified `src/joy/app.py`:
- Added `Binding("s", "settings", "Settings", priority=True)` to `BINDINGS`
- Added `action_settings()` that pushes `SettingsModal(self._config)` with callback
- Callback: on non-None result, updates `self._config`, calls `_save_config_bg()`, shows "Settings saved" toast
- Added `_save_config_bg()` `@work(thread=True, exit_on_error=False)` worker that calls `save_config(self._config)` (same pattern as `_save_projects_bg`)
- Added `SettingsModal` to import line from `joy.screens`

## Tests Added

| Test | File | What It Covers |
|------|------|----------------|
| test_settings_save_returns_config | test_screens.py | Save button dismisses modal with Config instance |
| test_settings_escape_returns_none | test_screens.py | Escape dismisses with None |
| test_settings_prepopulated | test_screens.py | Input fields show Config values on open |
| test_settings_kinds_prepopulated | test_screens.py | SelectionList shows pre-selected kinds |
| test_s_opens_settings_modal | test_tui.py | Pressing s makes SettingsModal the active screen |
| test_s_escape_no_save | test_tui.py | Escape from modal does not call save_config |
| test_s_save_persists_config | test_tui.py | Save button triggers save_config via worker |

**Test result:** 121 passed, 1 deselected (full suite green, +7 new tests)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed tab count to reach Save button**
- **Found during:** Task 1 test debugging (test_settings_save_returns_config failing)
- **Issue:** Plan specified "Tab 6 times" but field-ide already has focus on mount, so 5 tabs reach btn-save
- **Fix:** Corrected tab count from 6 to 5 in test_settings_save_returns_config and test_s_save_persists_config
- **Files modified:** tests/test_screens.py, tests/test_tui.py
- **Commit:** d9fd904 (Task 2 commit, both test files updated)

## Commits

| Hash | Task | Description |
|------|------|-------------|
| 6efef3f | Task 1 | feat(05-01): create SettingsModal screen with 4 Input fields + SelectionList + Save button |
| d9fd904 | Task 2 | feat(05-01): wire SettingsModal into JoyApp with s binding and save worker |

## Known Stubs

None. All Config fields are wired to real Input/SelectionList widgets and persisted via `save_config`.

## Threat Flags

None. No new network endpoints, auth paths, or trust boundaries introduced beyond what was planned in the plan's threat model.

## Self-Check: PASSED

Files verified:
- FOUND: src/joy/screens/settings.py
- FOUND: src/joy/screens/__init__.py (SettingsModal exported)
- FOUND: src/joy/app.py (action_settings, _save_config_bg, push_screen(SettingsModal))
- FOUND: tests/test_screens.py (4 SettingsModal tests)
- FOUND: tests/test_tui.py (3 integration tests)

Commits verified:
- FOUND: 6efef3f (Task 1 - SettingsModal screen)
- FOUND: d9fd904 (Task 2 - JoyApp integration)
