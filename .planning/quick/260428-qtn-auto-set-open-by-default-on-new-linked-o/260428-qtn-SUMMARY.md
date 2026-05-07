---
status: complete
---

# Quick Task 260428-qtn: auto-set open_by_default — Summary

**Completed:** 2026-04-28
**Commits:** 91edd70 (RED), 91a1eb1 (GREEN)

## Changes

### src/joy/app.py
- `_propagate_mr_auto_add` (line 326): Changed `open_by_default=False` to `open_by_default=PresetKind.MR.value in self._config.default_open_kinds`
- `_start_add_object_loop` (line 691): Changed `ObjectItem(kind=preset, value=value)` to include `open_by_default=preset.value in self._config.default_open_kinds`

### tests/test_propagation.py
- Extended `_PropContext` with optional `_config` parameter (defaults to `Config()`)
- Added `test_mr_auto_add_respects_default_open_kinds`: verifies MR auto-add sets `open_by_default=True` when `PresetKind.MR.value` is in config

## Verification
- 4/4 must-haves passed
- 30 tests passing (1 pre-existing failure unrelated)
