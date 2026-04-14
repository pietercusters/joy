---
phase: 4
slug: crud
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 0 | MGMT-01 | — | N/A | unit | `uv run pytest tests/test_screens.py -x -q` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 1 | PROJ-04 | — | N/A | integration | `uv run pytest tests/test_tui.py -x -q` | ✅ | ⬜ pending |
| 4-02-01 | 02 | 1 | PROJ-05 | — | N/A | integration | `uv run pytest tests/test_tui.py -x -q` | ✅ | ⬜ pending |
| 4-03-01 | 03 | 1 | MGMT-02 | — | N/A | integration | `uv run pytest tests/test_tui.py -x -q` | ✅ | ⬜ pending |
| 4-04-01 | 04 | 1 | MGMT-03 | — | N/A | integration | `uv run pytest tests/test_tui.py -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_screens.py` — modal unit test stubs for NameInputModal, PresetPickerModal, ValueInputModal, ConfirmationModal
- [ ] `tests/test_tui.py` — integration test stubs for CRUD operations (create project, add/edit/delete object, delete project)

*Existing test infrastructure (pytest) detected. Wave 0 adds new test files only.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| j/k navigation in PresetPickerModal while Input has focus | PROJ-05 | Requires real terminal input focus routing | Launch joy, press `a`, type in filter field, press j/k, verify ListView moves |
| `delete` key binding works in macOS Terminal vs iTerm2 | MGMT-03 | Terminal emulator key code differences | Test in both Terminal.app and iTerm2 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
