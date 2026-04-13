---
phase: 12
slug: iterm2-integration-terminal-pane
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `uv run pytest tests/test_iterm2_pane.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_iterm2_pane.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | TERM-01 | — | N/A | unit | `uv run pytest tests/test_iterm2_pane.py::test_session_list -x -q` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | TERM-02 | — | N/A | unit | `uv run pytest tests/test_iterm2_pane.py::test_claude_grouping -x -q` | ❌ W0 | ⬜ pending |
| 12-01-03 | 01 | 1 | TERM-03 | — | N/A | manual | See Manual-Only Verifications | N/A | ⬜ pending |
| 12-01-04 | 01 | 2 | TERM-04 | — | N/A | unit | `uv run pytest tests/test_iterm2_pane.py::test_session_focus -x -q` | ❌ W0 | ⬜ pending |
| 12-01-05 | 01 | 2 | TERM-05 | — | N/A | unit | `uv run pytest tests/test_iterm2_pane.py::test_unavailable_state -x -q` | ❌ W0 | ⬜ pending |
| 12-01-06 | 01 | 2 | TERM-06 | — | N/A | unit | `uv run pytest tests/test_iterm2_pane.py::test_busy_waiting_indicator -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_iterm2_pane.py` — stubs for TERM-01 through TERM-06 (session listing, Claude grouping, focus, unavailable state, busy/waiting indicator)
- [ ] `tests/conftest.py` — mock iterm2 connection fixtures (already exists, may need new fixtures)

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| j/k navigation in terminal pane scrolls session list | TERM-03 | Requires live TUI render with keyboard interaction | Run `joy`, navigate to terminal pane, press j/k, verify cursor moves between sessions |
| Enter key focuses iTerm2 session and brings window to front | TERM-03 | Requires live iTerm2 + joy interaction | Run `joy` with multiple iTerm2 sessions open, press Enter on a session, verify iTerm2 window/tab focuses |
| Claude agent busy/waiting indicator updates in real-time | TERM-06 | Requires live Claude agent session | Run `joy` alongside an active Claude agent session, verify indicator reflects busy/waiting state |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
