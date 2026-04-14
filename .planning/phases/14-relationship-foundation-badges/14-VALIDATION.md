---
phase: 14
slug: relationship-foundation-badges
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-14
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0+ with pytest-asyncio |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_resolver.py tests/test_project_list.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~10s fast suite / ~60s with slow TUI tests |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_resolver.py tests/test_project_list.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds (fast suite)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 0 | FOUND-01 | — | N/A | unit | `uv run pytest tests/test_resolver.py -x -q` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 0 | FOUND-02 | — | N/A | unit | `uv run pytest tests/test_resolver.py -x -q` | ❌ W0 | ⬜ pending |
| 14-01-03 | 01 | 1 | FOUND-01, FOUND-02 | — | N/A | unit | `uv run pytest tests/test_resolver.py -x -q` | ❌ W0 | ⬜ pending |
| 14-02-01 | 02 | 0 | FOUND-03 | — | N/A | slow TUI | `uv run pytest tests/test_worktree_pane_cursor.py -m slow -x` | ❌ W0 | ⬜ pending |
| 14-02-02 | 02 | 0 | FOUND-04 | — | N/A | slow TUI | `uv run pytest tests/test_terminal_pane.py -m slow -x` | ✅ (add test) | ⬜ pending |
| 14-03-01 | 03 | 0 | BADGE-01, BADGE-02 | — | N/A | unit | `uv run pytest tests/test_project_list.py -x -q` | ❌ W0 | ⬜ pending |
| 14-03-02 | 03 | 1 | BADGE-01, BADGE-02, BADGE-03 | — | N/A | unit | `uv run pytest tests/test_project_list.py tests/test_resolver.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_resolver.py` — stubs for FOUND-01, FOUND-02, BADGE-03 (resolver logic)
- [ ] `tests/test_project_list.py` — stubs for BADGE-01, BADGE-02 (ProjectRow.set_counts)
- [ ] New cursor identity test in `tests/test_worktree_pane_cursor.py` — covers FOUND-03
- [ ] New cursor identity test in `tests/test_terminal_pane.py` — covers FOUND-04

*Existing infrastructure (pytest, pytest-asyncio, conftest.py) covers all phase requirements — no framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Badge icons render with Nerd Font glyphs in terminal | BADGE-01, BADGE-02 | Visual — requires Nerd Font patched terminal | Launch `joy`, verify `⠋ N  N` pattern appears on each project row |
| Badges update after background refresh without user action | BADGE-03 | Timing — requires observing live refresh cycle | Launch `joy`, wait for refresh, verify counts change without pressing any key |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
