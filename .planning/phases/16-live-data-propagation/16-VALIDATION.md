---
phase: 16
slug: live-data-propagation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-15
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-asyncio |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/test_models.py tests/test_resolver.py tests/test_refresh.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds (excluding slow/macos_integration marks) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_models.py tests/test_resolver.py tests/test_refresh.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | PROP-04, PROP-05 | — | N/A | unit | `uv run pytest tests/test_models.py -k stale -x -q` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | PROP-02, PROP-06, PROP-07, PROP-08 | — | N/A | unit | `uv run pytest tests/test_refresh.py -k propagate -x -q` | ❌ W0 | ⬜ pending |
| 16-02-01 | 02 | 2 | PROP-04, PROP-05 | — | N/A | unit | `uv run pytest tests/test_object_row.py -k stale -x -q` | ❌ W0 | ⬜ pending |
| 16-02-02 | 02 | 2 | PROP-02 | — | N/A | integration | `uv run pytest tests/test_refresh.py -k mr_auto_add -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_models.py` — stale field tests: `stale` attr exists, defaults False, not serialized by `to_dict()`
- [ ] `tests/test_refresh.py` — propagation tests: MR auto-add dedup by URL, agent stale marking/clearing, projects without `repo` excluded
- [ ] `tests/test_object_row.py` — stale CSS class tests: `--stale` applied when `item.stale=True`, removed when False

*Existing `tests/conftest.py` and test infrastructure cover the framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Status bar notification fires on MR auto-add | PROP-02 | Requires live app.notify() path; no unit harness for Textual notify | Run joy, have a project with a branch+worktree; trigger MR detection; confirm "⊕ Added PR #N to {project}" appears in status bar |
| Agent stale dimming visible in TUI | PROP-04, PROP-05 | CSS rendering requires live Textual app | Run joy, kill an iTerm2 session; confirm the AGENTS object row dims/italics; restore session; confirm normal styling returns |
| No duplicate MR objects after multiple refreshes | PROP-06 | Dedup logic tested in unit tests, but visual confirmation in TUI validates end-to-end | Run joy with MR detected project; trigger multiple refreshes; confirm only one MR object exists |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
