---
phase: 3
slug: activation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio 0.25 |
| **Config file** | `pyproject.toml` → `[tool.pytest.ini_options]`, `asyncio_mode = "auto"` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 3-W0-01 | W0 | 0 | ACT-04 | — | N/A | unit (render check) | `uv run pytest tests/test_object_row.py -x` | ❌ W0 | ⬜ pending |
| 3-W0-02 | W0 | 0 | ACT-01, ACT-02, ACT-03, CORE-05 | — | N/A | unit (Textual pilot) | `uv run pytest tests/test_tui.py -x` | ❌ W0 | ⬜ pending |
| 3-W0-03 | W0 | 0 | ACT-03 | — | N/A | integration (temp file) | `uv run pytest tests/test_store.py -x` | ❌ W0 | ⬜ pending |
| 3-01-01 | 01 | 1 | ACT-04 | — | N/A | unit (render check) | `uv run pytest tests/test_object_row.py -x -q` | ❌ W0 | ⬜ pending |
| 3-02-01 | 02 | 2 | ACT-01 | — | markup=False on notify | unit (mock subprocess) | `uv run pytest tests/test_tui.py -k "open_object" -x` | ❌ W0 | ⬜ pending |
| 3-02-02 | 02 | 2 | ACT-01 | — | N/A | unit (Textual pilot) | `uv run pytest tests/test_tui.py -k "no_object" -x` | ❌ W0 | ⬜ pending |
| 3-03-01 | 03 | 2 | ACT-03 | — | N/A | unit (Textual pilot) | `uv run pytest tests/test_tui.py -k "toggle" -x` | ❌ W0 | ⬜ pending |
| 3-03-02 | 03 | 2 | ACT-03 | — | N/A | integration (temp file) | `uv run pytest tests/test_store.py -k "toggle" -x` | ❌ W0 | ⬜ pending |
| 3-04-01 | 04 | 3 | ACT-02 | — | markup=False on notify | unit (mock subprocess) | `uv run pytest tests/test_tui.py -k "open_all" -x` | ❌ W0 | ⬜ pending |
| 3-04-02 | 04 | 3 | ACT-02 | — | N/A | unit (Textual pilot) | `uv run pytest tests/test_tui.py -k "no_defaults" -x` | ❌ W0 | ⬜ pending |
| 3-05-01 | 05 | 3 | CORE-05 | — | markup=False on notify | unit (mock notify) | `uv run pytest tests/test_tui.py -k "notify" -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_object_row.py` — unit tests for `ObjectRow._render_text()` / render dot indicator (`●`/`○`) (ACT-04)
- [ ] `tests/test_tui.py` — extend with activation tests: `o`, `O`, `space` bindings + toast assertions (ACT-01, ACT-02, ACT-03, CORE-05)
- [ ] `tests/test_store.py` — add toggle round-trip test (ACT-03)

Note: `tests/conftest.py` already has `sample_project` and `sample_config` fixtures with full object coverage. No conftest changes needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| iTerm2 window actually opens and is named correctly | ACT-01 (iterm type) | Requires live iTerm2, AppleScript execution | Run `joy`, select a project with an iterm-type object, press `o`, verify window opens |
| Bulk `O` opens multiple apps sequentially | ACT-02 | Requires live subprocess calls | Configure project with 2+ default objects, press `O`, verify all open |
| Rich color of `●` accent vs `○` muted | ACT-04 | Visual assertion, no automated color check | Visually inspect the TUI: filled dot should be accent/bright, empty dot muted |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
