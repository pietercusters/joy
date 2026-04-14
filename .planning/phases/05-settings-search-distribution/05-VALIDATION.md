---
phase: 5
slug: settings-search-distribution
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml (pytest section) or none — Wave 0 installs |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

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
| 5-01-01 | 01 | 1 | SETT-01 | — | N/A | unit | `uv run pytest tests/test_settings.py -x -q` | ❌ W0 | ⬜ pending |
| 5-01-02 | 01 | 1 | SETT-02 | — | N/A | unit | `uv run pytest tests/test_settings.py -x -q` | ❌ W0 | ⬜ pending |
| 5-01-03 | 01 | 1 | SETT-03 | — | N/A | unit | `uv run pytest tests/test_settings.py -x -q` | ❌ W0 | ⬜ pending |
| 5-02-01 | 02 | 1 | SETT-04 | — | N/A | manual | joy launched; `/` key opens filter input | N/A | ⬜ pending |
| 5-02-02 | 02 | 1 | PROJ-06 | — | N/A | unit | `uv run pytest tests/test_search.py -x -q` | ❌ W0 | ⬜ pending |
| 5-02-03 | 02 | 1 | MGMT-04 | — | N/A | manual | `J`/`K` reorders items; order persists after restart | N/A | ⬜ pending |
| 5-03-01 | 03 | 2 | DIST-01 | — | N/A | integration | `uv tool install . && joy --version` | N/A | ⬜ pending |
| 5-03-02 | 03 | 2 | DIST-03 | — | N/A | manual | README documents installation steps | N/A | ⬜ pending |
| 5-03-03 | 03 | 2 | DIST-04 | — | N/A | manual | README documents first-run setup and key usage | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_settings.py` — stubs for SETT-01, SETT-02, SETT-03
- [ ] `tests/test_search.py` — stubs for PROJ-06

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `/` key opens inline filter, Escape closes it | SETT-04 | Requires TUI interaction | Launch joy, press `/`, type substring, verify list filters; press Escape, verify list restores |
| `J`/`K` reorders objects, order persists | MGMT-04 | Requires TUI interaction + restart | Launch joy, press `J`/`K`, quit, relaunch, verify order unchanged |
| Settings screen opens, edits persist | SETT-05, SETT-06 | Requires TUI interaction | Open settings, change a field, save, relaunch, verify change persisted |
| `joy --version` outputs correct version | DIST-01 | CLI invocation | `uv tool install . && joy --version` outputs `0.1.0` or current version |
| README documents install + usage | DIST-03, DIST-04 | Documentation review | Read README.md, verify installation, first-run, and key bindings sections exist |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
