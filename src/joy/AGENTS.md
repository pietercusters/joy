# src/joy — Core Application

## Module Roles

### Models (`models.py`)
Pure dataclasses. Zero I/O, zero imports beyond stdlib. All other modules import from here.

- `ObjectType` — Operation-facing enum: STRING, URL, OBSIDIAN, FILE, WORKTREE, ITERM
- `PresetKind` — User-facing enum: MR, BRANCH, TICKET, THREAD, FILE, NOTE, WORKTREE, TERMINALS, URL, REPO
- `PRESET_MAP` — Maps PresetKind to ObjectType (determines open behavior)
- `ObjectItem` — Single project artifact (kind + value + label + open_by_default)
- `Project` — Name + list[ObjectItem] + created date
- `Config` — User settings (ide, editor, obsidian_vault, terminal, default_open_kinds, refresh_interval, branch_filter)
- `Repo` — Registered git repo (name, local_path, remote_url, forge)
- `WorktreeInfo` — Discovered git worktree with dirty/upstream/MR status
- `TerminalSession` — iTerm2 session with Claude agent detection
- `MRInfo` — Merge request metadata (mr_number, is_draft, ci_status, url, is_open)

### Services (Pure Python, Zero Textual)

**`project_service.py`** — Project CRUD. `create_project()`, `remove_project()`, `find_project()`, `has_project()`. Takes/returns model objects. `app.py` handles persistence via store.py. Archive/unarchive logic lives in `app.py` directly.

**`data_orchestrator.py`** — Coordinates background data loading. Tracks `_worktrees_ready` / `_sessions_ready` flags. Computes relationships when both are ready. Manages MR auto-add propagation and stale-tab healing.

**`pane_coordinator.py`** — Cross-pane selection sync (6 directions: project<->worktree, project<->terminal, worktree<->terminal). Uses `syncing()` context manager to prevent infinite loops. Operates on duck-typed panes with `sync_to()` / `clear_selection()`.

**`resolver.py`** — `RelationshipIndex` class: bidirectional Project<->Worktree and Project<->Terminal matching via branch names and session names. `compute_relationships()` builds the index.

### Ports (`ports.py`)
Five `@runtime_checkable` Protocol classes defining service boundaries. Used for:
1. Documenting contracts between layers
2. `isinstance()` checks in test fixtures
3. Enabling structural subtyping (fakes don't import ports)

### Adapters (I/O Implementations)

**`store.py`** — TOML read/write for `~/.joy/` (projects.toml, config.toml, repos.toml, archive.toml). Uses `_atomic_write()` (tempfile + os.replace). Path constants are module-level for test patching.

**`operations.py`** — `@opener` decorator registers handlers per `ObjectType`. `open_object()` dispatches. All subprocess calls use list form (never `shell=True`).

**`worktrees.py`** — Calls `git worktree list --porcelain` per repo. Parses output into `WorktreeInfo` objects with dirty/upstream status.

**`mr_status.py`** — Calls `gh pr list` / `glab mr list` via `ThreadPoolExecutor` for concurrent multi-repo fetching. Returns `MRInfo` objects.

**`terminal_sessions.py`** — Connects to iTerm2 Python API. Returns `tuple[list[TerminalSession], set[str]] | None` where the set is `live_tab_ids`. Claude detection is per-session via `TerminalSession.is_claude` / `TerminalSession.claude_state`. Lazy-imports `iterm2` inside `@work` to avoid import failure when iTerm2 is unavailable.

### Dispatch (`dispatch.py`)
Table-driven keystroke routing. `DISPATCH` dict maps `PresetKind` to `KindConfig` with 4 boolean states. To add a new object kind: add entry to `DISPATCH`, add enum value to `PresetKind`, add mapping to `PRESET_MAP`.

### App (`app.py`)
Textual `App` subclass. Composition root. Responsibilities:
- Mounts 6 panes + HintBar in a 3x2 grid
- Instantiates services: `ProjectService`, `DataOrchestrator`, `PaneCoordinator`
- Runs all I/O in `@work(thread=True)` background workers
- Handles widget `Message` events and delegates to services
- Manages refresh timer and status label

## Adding a New Object Kind

1. Add enum value to `PresetKind` in `models.py`
2. Add mapping in `PRESET_MAP` (PresetKind -> ObjectType)
3. Add entry in `DISPATCH` dict in `dispatch.py`
4. Add icon in `widgets/icons.py`
5. If new ObjectType needed: add to `ObjectType` enum, register `@opener` in `operations.py`

## Adding a New Service

1. Create `src/joy/new_service.py` — pure Python, no Textual imports
2. Define methods that take/return model objects
3. Instantiate in `app.py.__init__()`
4. Delegate from `app.py` message handlers / @work methods
5. Add Protocol to `ports.py` if the service crosses a boundary
6. Add tests in `tests/test_new_service.py` (plain pytest, no TUI)
