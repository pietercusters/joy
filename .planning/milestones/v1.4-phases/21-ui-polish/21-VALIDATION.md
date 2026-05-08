---
phase: 21
slug: ui-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-08
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with pytest-textual-snapshot |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -x -q --ignore=tests/test_snapshots.py --ignore=tests/test_refresh.py` |
| **Full suite command** | `uv run pytest tests/ -x -q --ignore=tests/test_refresh.py` |
| **Estimated runtime** | ~40 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --ignore=tests/test_snapshots.py --ignore=tests/test_refresh.py`
- **After every plan wave:** Run `uv run pytest tests/ -x -q --ignore=tests/test_refresh.py`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 40 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 1 | UIPOL-01 | — | N/A | manual | Visual inspection of all 5 panes | N/A | ⬜ pending |
| 21-02-01 | 02 | 2 | UIPOL-02 | — | N/A | snapshot | `uv run pytest tests/test_snapshots.py -m snapshot --snapshot-update` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual consistency of spacing/alignment/truncation across 5 panes | UIPOL-01 | CSS visual output requires human eye-check | Run `joy`, tab through all panes, verify spacing/alignment |
| Focus indicator consistency when tabbing | UIPOL-02 | Focus behavior requires interactive testing | Tab/Shift+Tab through all panes, verify border color changes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 40s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
