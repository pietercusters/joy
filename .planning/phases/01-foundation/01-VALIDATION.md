---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-10
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ~9.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (Wave 0 — create from scratch) |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | — | — | N/A | infra | `uv run pytest --co -q` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | OBJ-01..07, PRESET-01..09 | — | N/A | unit | `uv run pytest tests/test_models.py -x -q` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 1 | DIST-02 | — | N/A | unit | `uv run pytest tests/test_store.py -x -q` | ❌ W0 | ⬜ pending |
| 1-04-01 | 04 | 2 | OBJ-01 | — | N/A | unit | `uv run pytest tests/test_operations.py::test_copy_string -x` | ❌ W0 | ⬜ pending |
| 1-04-02 | 04 | 2 | OBJ-02, OBJ-03 | — | N/A | unit | `uv run pytest tests/test_operations.py::test_open_url_browser tests/test_operations.py::test_open_url_notion -x` | ❌ W0 | ⬜ pending |
| 1-04-03 | 04 | 2 | OBJ-04 | — | N/A | unit | `uv run pytest tests/test_operations.py::test_open_obsidian -x` | ❌ W0 | ⬜ pending |
| 1-04-04 | 04 | 2 | OBJ-05 | — | N/A | unit | `uv run pytest tests/test_operations.py::test_open_file -x` | ❌ W0 | ⬜ pending |
| 1-04-05 | 04 | 2 | OBJ-06 | — | N/A | unit | `uv run pytest tests/test_operations.py::test_open_worktree -x` | ❌ W0 | ⬜ pending |
| 1-04-06 | 04 | 2 | OBJ-07 | T-1-01 | AppleScript strings escape double quotes for iTerm2 window names | unit + integration | `uv run pytest tests/test_operations.py::test_open_iterm -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — with `[tool.pytest.ini_options]` section: `testpaths = ["tests"]`, custom markers (`macos_integration`)
- [ ] `tests/__init__.py` — empty marker
- [ ] `tests/conftest.py` — shared fixtures: `tmp_joy_dir`, `sample_project`, `sample_config`
- [ ] `tests/test_models.py` — stub test functions for model creation, PRESET_MAP
- [ ] `tests/test_store.py` — stub test functions for round-trip, atomic write
- [ ] `tests/test_operations.py` — stub test functions for all 7 operation types
- [ ] `uv add --dev pytest` — install test framework

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| iTerm2 window created/focused | OBJ-07 | Requires live iTerm2 + AppleScript | Run `uv run pytest tests/test_operations.py -m macos_integration -v` with iTerm2 open |
| Notion desktop app opens | OBJ-03 | Requires Notion desktop installed | Manually call `open_object(notion_item, config)` and verify Notion focuses |
| Slack desktop app opens | OBJ-03 | Requires Slack desktop installed | Manually call `open_object(slack_item, config)` and verify Slack focuses |
| Obsidian vault opens | OBJ-04 | Requires Obsidian + configured vault | Manually call `open_object(obsidian_item, config)` with vault path set |
