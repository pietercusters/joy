---
phase: 15
slug: cross-pane-selection-sync
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-14
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-asyncio |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_sync.py -x -q` |
| **Full suite command** | `uv run pytest -m "not slow and not macos_integration" -q` |
| **Estimated runtime** | ~5 seconds (unit tests); ~15 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_sync.py -x -q`
- **After every plan wave:** Run `uv run pytest -m "not slow and not macos_integration" -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 0 | SYNC-01..09 | — | N/A | unit | `uv run pytest tests/test_sync.py -x -q` | ❌ W0 | ⬜ pending |
| 15-02-01 | 02 | 1 | SYNC-01, SYNC-02 | — | N/A | unit | `uv run pytest tests/test_sync.py::test_sync_project_to_worktree tests/test_sync.py::test_sync_project_to_terminal -x -q` | ❌ W0 | ⬜ pending |
| 15-02-02 | 02 | 1 | SYNC-03, SYNC-04 | — | N/A | unit | `uv run pytest tests/test_sync.py::test_sync_worktree_to_project tests/test_sync.py::test_sync_worktree_to_terminal -x -q` | ❌ W0 | ⬜ pending |
| 15-02-03 | 02 | 1 | SYNC-05, SYNC-06 | — | N/A | unit | `uv run pytest tests/test_sync.py::test_sync_agent_to_project tests/test_sync.py::test_sync_agent_to_worktree -x -q` | ❌ W0 | ⬜ pending |
| 15-02-04 | 02 | 1 | SYNC-07 | — | N/A | unit | `uv run pytest tests/test_sync.py::test_sync_does_not_steal_focus -x -q` | ❌ W0 | ⬜ pending |
| 15-03-01 | 03 | 2 | SYNC-08, SYNC-09 | — | N/A | unit + pilot | `uv run pytest tests/test_sync.py::test_toggle_sync_footer_visibility tests/test_sync.py::test_toggle_sync_key -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_sync.py` — stubs for SYNC-01 through SYNC-09 (all new; no existing test covers Phase 15 requirements)

*No conftest changes needed — existing `tests/conftest.py` fixtures are sufficient. pytest-asyncio already installed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Footer shows "Sync: on" / "Sync: off" correctly after toggle | SYNC-09 | Visual verification of TUI footer display | Launch `uv run joy`, press `x` to toggle — confirm footer label changes between "Sync: on" and "Sync: off" |
| Cursor movement does not steal focus from active pane | SYNC-07 | Focus state is hard to assert without TUI pilot | Navigate using `j/k` in each pane — observe that only the current pane responds to keyboard input, other pane cursors move silently |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
