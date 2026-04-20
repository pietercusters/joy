---
phase: quick-260420-ak5
plan: "01"
subsystem: screens
tags: [modal, new-project, tdd, repo-picker, branch-picker]
dependency_graph:
  requires: []
  provides: [NewProjectModal, NewProjectResult]
  affects: [src/joy/app.py, src/joy/screens/__init__.py]
tech_stack:
  added: []
  patterns: [TDD red-green, ModalScreen, ListView.Selected event routing, subprocess git branch]
key_files:
  created:
    - src/joy/screens/new_project.py
  modified:
    - src/joy/screens/__init__.py
    - src/joy/app.py
    - tests/test_screens.py
decisions:
  - "Branch list built as _branch_options list + _CUSTOM_BRANCH_SENTINEL as last item; on_list_view_selected uses index into all_options to detect sentinel"
  - "on_input_submitted guarded by event.input.id == 'branch-input' so Enter on name-input does not auto-confirm"
  - "NameInputModal import retained in app.py — still used by rename flows in project_list.py, terminal_pane.py, and settings.py"
metrics:
  duration_minutes: 20
  completed: "2026-04-20T05:53:13Z"
  tasks_completed: 3
  files_changed: 4
---

# Quick Task 260420-ak5: Extend New-Project Modal — Summary

**One-liner:** Multi-field NewProjectModal with name Input, repo ListView, and branch ListView (5 recent + custom sentinel) replaces single-field NameInputModal in action_new_project().

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 (RED) | Failing tests for NewProjectModal | b4180e8 | tests/test_screens.py |
| 1 (GREEN) | Implement NewProjectModal + NewProjectResult | 79724eb | src/joy/screens/new_project.py |
| 2 | Wire modal into app.py and screens/__init__.py | af80be4 | src/joy/screens/__init__.py, src/joy/app.py |
| 3 | Unit tests (written in Task 1 TDD RED) | b4180e8 | tests/test_screens.py |

## What Was Built

`NewProjectResult` is a dataclass with `name: str`, `repo: str | None`, `branch: str | None`.

`NewProjectModal(ModalScreen[NewProjectResult | None])` accepts `repos: list[Repo]` and shows:
- **Name** — plain `Input(id="name-input")`
- **Repo (optional)** — `ListView(id="repo-list")` with one item per repo + a `(none)` item
- **Branch** — `ListView(id="branch-list")` with up to 5 recently checked-out branches (via `git branch --sort=-committerdate`) plus `(type custom…)` sentinel; selecting the sentinel hides the list and shows `Input(id="branch-input")` for free-text entry

`ctrl+n` confirms (validates non-empty name, then dismisses with result). `Escape` dismisses with `None`. Enter on `#branch-input` also confirms after storing the custom branch value.

`action_new_project()` in `app.py` now:
- Pushes `NewProjectModal(repos=self._repos)` instead of `NameInputModal()`
- Creates `Project(name=result.name, repo=result.repo)` with the selected repo pre-filled
- Appends a `ObjectItem(kind=PresetKind.BRANCH, value=result.branch)` if a branch was selected

## Tests

6 new tests added to `tests/test_screens.py` under `# NewProjectModal tests`:
- `test_new_project_modal_escape_returns_none`
- `test_new_project_modal_confirm_name_only`
- `test_new_project_modal_empty_name_rejected`
- `test_new_project_modal_repo_selection`
- `test_new_project_modal_branch_selection` (uses monkeypatch)
- `test_new_project_modal_custom_branch` (uses monkeypatch)

All 26 tests in `test_screens.py` pass (20 pre-existing + 6 new).

## TDD Gate Compliance

- RED gate commit: `b4180e8` — `test(quick-260420-ak5): add failing tests for NewProjectModal (RED)`
- GREEN gate commit: `79724eb` — `feat(quick-260420-ak5): implement NewProjectModal and NewProjectResult (GREEN)`
- REFACTOR: not needed — implementation was clean from the start

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all fields are wired to real data sources (repos from `self._repos`, branches from live `git branch` subprocess).

## Threat Surface Scan

`_fetch_recent_branches` runs `subprocess.run(["git", "branch", ...], cwd=None, timeout=5)`. This is covered by T-ak5-01 and T-ak5-02 in the plan's threat model — list-form prevents shell injection, timeout=5 mitigates DoS. No new surface beyond what the plan documented.

## Self-Check

Files exist:
- src/joy/screens/new_project.py — FOUND
- src/joy/screens/__init__.py — FOUND (modified)
- src/joy/app.py — FOUND (modified)
- tests/test_screens.py — FOUND (modified)

Commits exist:
- b4180e8 — FOUND
- 79724eb — FOUND
- af80be4 — FOUND

## Self-Check: PASSED
