---
phase: 9
slug: worktree-pane
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio 0.25 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_worktree_pane.py -x -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~10 seconds (quick) / ~30 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_worktree_pane.py -x -q`
- **After every plan wave:** Run `uv run pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

> Plans populate this table per task once created. One row per `<task>` in every PLAN.md.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 9-TBD   | TBD  | TBD  | WKTR-02/03/10 | —        | N/A             | TBD       | TBD               | ❌ W0       | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Requirement → Test Coverage (from RESEARCH §Validation Architecture)

| Req / Decision | Behavior | Test Type | Automated Command |
|----------------|----------|-----------|-------------------|
| WKTR-02a | Worktrees grouped under repo section headers | unit | `uv run pytest tests/test_worktree_pane.py::test_grouping_by_repo -x` |
| WKTR-02b | Repos with no active worktrees are hidden | unit | `uv run pytest tests/test_worktree_pane.py::test_empty_repos_hidden -x` |
| WKTR-02c | Repo sections ordered alphabetically (D-11) | unit | `uv run pytest tests/test_worktree_pane.py::test_repo_order_alphabetical -x` |
| WKTR-02d | Worktrees within repo ordered alphabetically (D-12) | unit | `uv run pytest tests/test_worktree_pane.py::test_worktree_order_alphabetical -x` |
| WKTR-03a | Row line 1 shows branch name | integration | `uv run pytest tests/test_worktree_pane.py::test_row_shows_branch -x` |
| WKTR-03b | Dirty indicator present when is_dirty=True | unit | `uv run pytest tests/test_worktree_pane.py::test_dirty_indicator_shown -x` |
| WKTR-03c | No-upstream indicator present when has_upstream=False | unit | `uv run pytest tests/test_worktree_pane.py::test_no_upstream_indicator_shown -x` |
| WKTR-03d | No indicators when clean + has upstream | unit | `uv run pytest tests/test_worktree_pane.py::test_clean_tracked_no_indicators -x` |
| WKTR-03e | Row line 2 shows abbreviated path | unit | `uv run pytest tests/test_worktree_pane.py::test_row_shows_abbreviated_path -x` |
| WKTR-10 | Pane is read-only (no cursor, no activation bindings) | integration | `uv run pytest tests/test_worktree_pane.py::test_pane_read_only -x` |
| D-01 | App loads worktrees via threaded worker | integration | `uv run pytest tests/test_worktree_pane.py::test_app_loads_worktrees -x` |
| D-05 | Loading... placeholder shown before data arrives | integration | `uv run pytest tests/test_worktree_pane.py::test_loading_placeholder -x` |
| D-13 | Path abbreviation replaces home dir with ~ | unit | `uv run pytest tests/test_worktree_pane.py::test_path_abbreviation -x` |
| D-14 | Middle-truncation for long paths | unit | `uv run pytest tests/test_worktree_pane.py::test_middle_truncation -x` |
| D-15 | Empty state: no repos registered | integration | `uv run pytest tests/test_worktree_pane.py::test_empty_state_no_repos -x` |
| D-16 | Empty state: repos exist but no worktrees | integration | `uv run pytest tests/test_worktree_pane.py::test_empty_state_no_worktrees -x` |
| D-03 | set_worktrees is idempotent (call twice, same result) | unit | `uv run pytest tests/test_worktree_pane.py::test_set_worktrees_idempotent -x` |
| REGRESSION | Existing 197 tests remain green | regression | `uv run pytest -q` |

---

## Wave 0 Requirements

- [ ] `tests/test_worktree_pane.py` — all Phase 9 unit + integration tests (new file, covers every row above)
- [ ] No new framework install (pytest + pytest-asyncio already configured)
- [ ] No new shared conftest fixtures — each test file defines locally per existing repo convention

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Nerd Font glyphs render as icons (not tofu) | WKTR-03 (visual) | Requires a Nerd-Font-capable terminal; headless pytest can assert codepoints but not glyph rendering | Launch `joy` in iTerm2 with a Nerd Font profile; confirm dirty rows show a filled circle and no-upstream rows show the cloud-off glyph |
| Focus border accent on Tab into pane | WKTR-10 (visual) | Inherited from Phase 8; integration-test coverage exists but visible focus color is a terminal-render concern | Launch `joy`, press Tab until the Worktrees pane border turns accent-colored |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
