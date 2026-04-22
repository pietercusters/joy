# Phase 17: Fix iTerm2 Integration Bugs - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 17-fix-iterm2-integration-bugs-from-quick-260416-of2-remove-aut
**Areas discussed:** Archive close behavior, Stale-heal notification, Test isolation scope, Archive modal simplification, Project↔Tab model clarification

---

## Archive Close Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Always close the tab | Archive always closes the whole iTerm2 tab | ✓ |
| Keep the choice modal | Keep ARCHIVE_WITH_CLOSE vs ARCHIVE_ONLY options | |

**User's choice:** Always close the tab
**Notes:** Consistent with stated behavior "when a project is archived, the whole tab will close"

---

## Stale-Heal Notification

| Option | Description | Selected |
|--------|-------------|----------|
| Silent — no notification | Clear stale tab_id silently | |
| Notify — show status bar message | Show "'ProjectName' tab closed — press h to relink" | ✓ |

**User's choice:** Notify
**Notes:** Makes it discoverable when iTerm2 tab was closed externally

---

## Test Isolation Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Autouse session fixture in conftest.py | One fixture patches all store paths for entire session | ✓ |
| Autouse function fixture per test | Fresh isolated directory per test | |

**User's choice:** Autouse session fixture in conftest.py
**Notes:** Zero test files need changes — isolation is automatic

---

## Archive Modal Simplification

| Option | Description | Selected |
|--------|-------------|----------|
| Simplify to ConfirmationModal | Remove ArchiveModal/ArchiveChoice entirely | ✓ |
| Keep ArchiveModal, remove ARCHIVE_ONLY | ArchiveModal stays but only has Enter/Esc | |

**User's choice:** Simplify to ConfirmationModal
**Notes:** Less code; consistent with delete project flow

---

## Project↔Tab Model Clarification

**User clarification (freeform):** Project ↔ iTerm2 Tab is a one-to-one relationship. The Terminal pane still shows all sessions. Closing a single session from the Terminal pane must still work.

**Decision recorded:** `close_session` stays for Terminal pane per-session close; new `close_tab` added for project-level delete/archive.

---

## Claude's Discretion

- Exact notification wording beyond the format "'name' tab closed — press h to relink"
- Whether to delete `archive_modal.py` entirely or keep empty stub
- `monkeypatch` vs `unittest.mock.patch` for conftest fixture
- Function vs session scope downgrade if inter-test state bleed is observed
