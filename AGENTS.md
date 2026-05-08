# AGENTS.md

## Overview

**joy** is a keyboard-driven Python TUI for managing coding project artifacts. macOS only. Built with Python 3.11+, Textual 8.x, TOML config (`~/.joy/`). Minimal dependencies: `textual`, `tomli-w`, `iterm2`.

## Commands

```
uv sync                              # install deps
uv run joy                           # run the app
uv run pytest tests/ -x -q           # run tests (excludes slow/snapshot by default)
uv run pytest tests/ -m snapshot     # run snapshot tests only
uv run pytest tests/ -m slow         # run slow Textual pilot tests
uv run pytest --snapshot-update      # regenerate snapshot baselines
```

## Architecture

Ports & Adapters (hexagonal). Five layers, strictly ordered:

```
models.py          Pure dataclasses. No I/O, no imports beyond stdlib.
    |
services           Pure Python business logic. Zero Textual imports.
  project_service.py   Project CRUD
  data_orchestrator.py Background data coordination, relationship computation
  pane_coordinator.py  Cross-pane selection sync (6 directions)
  resolver.py          Bidirectional relationship index (project <-> worktree/terminal)
    |
ports.py           Protocol contracts (@runtime_checkable). Service boundaries.
  StoragePort      load/save projects, config, repos, archives
  GitDataPort      discover_worktrees()
  TerminalPort     fetch_sessions(), create/close/rename sessions
  OpenerPort       open_object()
  SyncablePane     sync_to(), clear_selection()
    |
adapters           I/O implementations. Subprocess, filesystem, network.
  store.py         TOML read/write (~/.joy/)
  operations.py    Type-dispatched subprocess openers (@opener decorator)
  worktrees.py     Git CLI worktree discovery
  mr_status.py     gh/glab CLI for MR/CI status
  terminal_sessions.py  iTerm2 Python API session management
    |
app.py + widgets/  Textual UI. Composition root. Background workers.

Note: services and adapters are NOT subdirectories — all modules are flat
under src/joy/. The layers above are conceptual groupings.
```

**Dependency rule:** Each layer imports only from layers above it. Widgets never import adapters. Services never import Textual.

## Key Patterns

**Services are pure Python.** No Textual imports. Receive data, return results. `app.py` owns all `@work(thread=True)` decorators and Textual lifecycle.

**Protocol-first testing.** Define contracts in `ports.py`. Implement fakes in `tests/fakes.py` (structural subtyping, no ports import). Widget tests inject data via `set_*()` methods, not constructor DI.

**Message-driven pane communication.** Widgets emit `Message` subclasses (e.g., `ProjectList.ProjectHighlighted`, `WorktreePane.WorktreeHighlighted`). `app.py` handles messages and delegates to `PaneCoordinator` for cross-pane sync.

**Cursor pattern.** All panes use integer `_cursor` index, CSS `.--highlight` class on the active row, boundary clamping (no wraparound). Navigation: j/k/up/down.

**Dispatch table.** `dispatch.py` defines a `DISPATCH` dict mapping each `PresetKind` to a 4-state `KindConfig` (exists_openable, exists_not_openable, missing_auto_create, missing_needs_input). Add new kinds here only.

**Atomic writes.** `store.py` uses `tempfile.mkstemp` + `os.replace` for crash-safe TOML persistence.

**Virtual rows.** `ProjectDetail` synthesizes REPO, TERMINALS, and resolver worktree rows at render time. These are read-only `ObjectItem` instances, never persisted.

## Project Structure

```
src/joy/
  app.py              Textual App, composition root, @work workers
  models.py           Dataclasses: Project, ObjectItem, Config, Repo, WorktreeInfo, etc.
  ports.py            Protocol contracts (5 protocols)
  dispatch.py         Keystroke dispatch table (DISPATCH dict)
  store.py            TOML persistence (~/.joy/)
  operations.py       Subprocess openers (open_object dispatcher)
  worktrees.py        Git worktree discovery
  mr_status.py        MR/CI status via gh/glab
  terminal_sessions.py iTerm2 session management
  resolver.py         Relationship index computation
  data_orchestrator.py Data loading coordination service
  pane_coordinator.py  Cross-pane sync service
  project_service.py   Project CRUD service
  hooks.py            Claude Code hook installation
  widgets/            Textual widget classes (see widgets/AGENTS.md)
  screens/            Modal screens (see screens/AGENTS.md)
tests/
  conftest.py         Fixtures + session-scoped ~/.joy/ isolation
  fakes.py            FakeStorage, FakeGitData, FakeTerminal, FakeOpener
  test_*.py           Per-module tests
```

## Testing Strategy

Three layers:

1. **Backend service tests** (fast, no TUI): `test_pane_coordinator.py`, `test_data_orchestrator.py`, `test_project_service.py`. Plain pytest, pure Python assertions.
2. **Widget pilot tests** (`test_widget_*.py`): Textual `async with app.run_test() as pilot`. Data injected via `set_*()` methods. No `@patch`. Marked `asyncio`.
3. **Snapshot tests** (`test_snapshots.py`): `snap_compare(JoyApp(), ...)` produces SVG baselines. Marked `snapshot`. Use `--snapshot-update` to regenerate.

**Test isolation:** Session-scoped autouse fixture patches all `joy.store` path constants to a tmp directory. No test reads/writes `~/.joy/`.

**Markers:** `slow` (Textual pilot), `snapshot` (SVG baselines), `macos_integration` (live apps). Default run excludes all three.

## Constraints

- **macOS only.** Uses `open`, `pbcopy`, `osascript`, iTerm2 Python API. No cross-platform.
- **No heavy deps.** Startup must be fast. Only textual + tomli_w + iterm2 beyond stdlib.
- **All subprocess calls use list form.** Never `shell=True`. Security requirement.
- **Config lives in `~/.joy/`.** Four TOML files: projects, config, repos, archive.
- **Keyboard only.** No mouse interaction. Every action has a key binding.
