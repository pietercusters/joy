---
phase: 20
slug: widget-tests-snapshots
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-08
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with pytest-textual-snapshot 1.1.0 |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -x -q --ignore=tests/test_snapshots.py` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --ignore=tests/test_snapshots.py`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 1 | TEST-04 | — | N/A | unit | `uv run pytest tests/fakes.py -x -q` | ❌ W0 | ⬜ pending |
| 20-02-01 | 02 | 1 | TEST-04 | — | N/A | integration | `uv run pytest tests/test_widget_project_list.py -x -q` | ❌ W0 | ⬜ pending |
| 20-02-02 | 02 | 1 | TEST-04 | — | N/A | integration | `uv run pytest tests/test_widget_worktree_pane.py -x -q` | ❌ W0 | ⬜ pending |
| 20-02-03 | 02 | 1 | TEST-04 | — | N/A | integration | `uv run pytest tests/test_widget_terminal_pane.py -x -q` | ❌ W0 | ⬜ pending |
| 20-02-04 | 02 | 1 | TEST-04 | — | N/A | integration | `uv run pytest tests/test_widget_project_detail.py -x -q` | ❌ W0 | ⬜ pending |
| 20-03-01 | 03 | 2 | TEST-05 | — | N/A | snapshot | `uv run pytest tests/test_snapshots.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/fakes.py` — FakeBackend adapters for all Protocol ports
- [ ] `pytest-textual-snapshot` installed as dev dependency
- [ ] pytest version compatible with pytest-textual-snapshot (pytest<9)

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Snapshot visual review | TEST-05 | SVG baselines need human eye-check on first creation | Review generated SVGs in tests/snapshot_tests_output/ |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
