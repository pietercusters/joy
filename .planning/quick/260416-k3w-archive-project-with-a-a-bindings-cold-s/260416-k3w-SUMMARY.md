---
phase: quick-260416-k3w
plan: "01"
subsystem: archive
tags: [archive, persistence, toml, modal, keyboard-bindings]
dependency_graph:
  requires: []
  provides: [archive-feature, ArchivedProject-model, archive-toml-store]
  affects: [project-list, app, screens]
tech_stack:
  added: []
  patterns: [keyed-toml-schema, atomic-write, modal-screen, background-worker, tdd]
key_files:
  created:
    - src/joy/models.py (ArchivedProject dataclass)
    - src/joy/store.py (archive persistence functions)
    - src/joy/screens/archive_modal.py (ArchiveModal + ArchiveChoice)
    - src/joy/screens/archive_browser.py (ArchiveBrowserModal)
    - tests/test_archive.py (8 tests)
  modified:
    - src/joy/screens/__init__.py (export new screens)
    - src/joy/widgets/project_list.py (a/A bindings + action handlers)
    - src/joy/app.py (workers + ArchivedProject import + pane hints)
decisions:
  - ArchivedProject is a separate dataclass wrapping Project + archived_at datetime; Project model stays clean
  - archive.toml uses keyed schema [archive.{name}] mirroring projects.toml pattern
  - ArchiveModal uses Static display + BINDINGS only (no Button widgets), matching ConfirmationModal style
  - ArchiveBrowserModal dismisses with ArchivedProject | None; caller owns persistence logic
  - Stripping WORKTREE/TERMINALS is caller responsibility in action_archive_project, not in store
metrics:
  duration_minutes: 20
  completed_at: "2026-04-16T13:03:39Z"
  tasks_completed: 3
  files_modified: 8
---

# Phase quick-260416-k3w Plan 01: Project Archive/Unarchive Summary

**One-liner:** Archive projects to `~/.joy/archive.toml` cold storage via `a`/`A` bindings with ArchiveModal (3-option confirm) and ArchiveBrowserModal (two-section browser with branch-matching).

## What Was Built

### ArchivedProject model + archive.toml persistence (Task 1)
- `ArchivedProject` dataclass added to `models.py`: wraps `Project` + `archived_at: datetime`
- `ARCHIVE_PATH = JOY_DIR / "archive.toml"` constant in `store.py`
- Four new store functions: `_archived_to_toml`, `_toml_to_archived`, `load_archived_projects`, `save_archived_projects`
- Uses keyed schema `[archive.{project-name}]`, atomic writes via `_atomic_write`, offset-aware datetime (`tomli_w` serializes natively)
- Missing file returns `[]` (graceful first-archive handling)

### ArchiveModal + ArchiveBrowserModal screens (Task 2)
- `ArchiveModal(ModalScreen[ArchiveChoice])`: three bindings (Enter=archive+close, a=archive-only, Esc=cancel); no Button widgets, Static display only
- `ArchiveChoice(str, Enum)`: ARCHIVE_WITH_CLOSE, ARCHIVE_ONLY, CANCEL
- `ArchiveBrowserModal(ModalScreen[ArchivedProject | None])`: two-section layout (Active Branch / Other); cursor navigation (up/down/j/k); `u` to unarchive; Esc to close
- Section headers shown — makes the branch-match signal obvious to the user
- Branch matching: compares BRANCH object values against `active_branches` set passed at construction time

### ProjectList bindings + JoyApp workers (Task 3)
- `Binding("a", "archive_project", "Archive")` and `Binding("A", "open_archive_browser", "Archives")` added to ProjectList.BINDINGS
- `action_archive_project`: guard check → push ArchiveModal → on choice: strip objects → optionally close sessions → remove from projects → save → append to archive → refresh list
- `action_open_archive_browser`: load archive → build active_branches from `_current_worktrees` → push ArchiveBrowserModal → on result: append to projects → save → remove from archive → refresh list
- `_close_sessions_bg(@work thread)`: iterates sessions calling `close_session(session_id, force=False)`
- `_append_to_archive_bg(@work thread)`: load → append → save atomically
- `_remove_from_archive_bg(@work thread)`: load → filter by project name → save atomically
- `_PANE_HINTS["project-list"]` updated with `a: Archive  A: Archives`

## Decisions Made

1. **ArchivedProject wraps Project** — keeps `Project` model clean; `archived_at` lives only in `ArchivedProject`
2. **Keyed schema `[archive.{name}]`** — mirrors `projects.toml` pattern; top-level key `archive` distinguishes from projects
3. **No Button widgets in modals** — pure Static + BINDINGS, matching `ConfirmationModal` style
4. **Caller owns persistence** — `ArchiveBrowserModal` returns `ArchivedProject | None`; `action_open_archive_browser` does the store operations
5. **Object stripping in action handler** — not in store; store persists whatever it receives (callers can archive full or stripped projects)

## Deviations from Plan

None — plan executed exactly as written. The plan checker findings were all applied correctly:
- `PresetKind` added to `project_list.py` imports
- `ArchiveModal` uses Static + BINDINGS only (no Buttons)
- `ArchiveBrowserModal` is `ModalScreen[ArchivedProject | None]`
- `ARCHIVE_PATH = JOY_DIR / "archive.toml"` in store
- `ArchivedProject` imported at top level in `app.py` (not string-quoted)

## Known Stubs

None — all data is wired from real `archive.toml` storage.

## Threat Flags

None — no new network endpoints or auth paths introduced. Archive operations are local filesystem reads/writes to `~/.joy/archive.toml`.

## Self-Check

Files created/modified:
- `src/joy/models.py` — ArchivedProject dataclass present
- `src/joy/store.py` — ARCHIVE_PATH, load_archived_projects, save_archived_projects present
- `src/joy/screens/archive_modal.py` — ArchiveModal, ArchiveChoice present
- `src/joy/screens/archive_browser.py` — ArchiveBrowserModal present
- `src/joy/screens/__init__.py` — exports updated
- `src/joy/widgets/project_list.py` — a/A bindings and action handlers present
- `src/joy/app.py` — workers and pane hints updated
- `tests/test_archive.py` — 8 tests, all passing

Commits:
- a8f68a3: feat(quick-260416-k3w): add ArchivedProject model and archive.toml persistence
- 57e18ad: feat(quick-260416-k3w): add ArchiveModal and ArchiveBrowserModal screens
- 851e3dc: feat(quick-260416-k3w): wire a/A bindings and archive background workers
- 594e4cd: feat(quick-260416-k3w): add project archive/unarchive with a/A bindings and archive.toml cold storage

## Self-Check: PASSED
