# Tests

## Running Tests

```
uv run pytest tests/ -x -q                        # default: excludes slow/snapshot/macos_integration
uv run pytest tests/ -m snapshot                   # snapshot baselines only
uv run pytest tests/ -m slow                       # Textual pilot tests only
uv run pytest tests/test_project_service.py -x -q  # single module
uv run pytest --snapshot-update                    # regenerate SVG baselines
```

## Test Isolation

**Session-scoped autouse fixture** in `conftest.py` patches all `joy.store` path constants (`JOY_DIR`, `PROJECTS_PATH`, `CONFIG_PATH`, `REPOS_PATH`, `ARCHIVE_PATH`) to a tmp directory. No test ever reads/writes `~/.joy/`.

```python
@pytest.fixture(autouse=True, scope="session")
def _isolated_store_paths(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("joy_store")
    mp = pytest.MonkeyPatch()
    mp.setattr("joy.store.JOY_DIR", tmp)
    # ... patches all 5 paths
```

## Three Test Layers

### 1. Backend Service Tests (fast, no TUI)

Plain pytest. Test services against model objects. No Textual, no pilot, no async.

```python
def test_sync_from_project(self):
    coord = PaneCoordinator()
    fake_wt = FakeWorktreePane()
    coord.sync_from_project(project, fake_wt, ...)
    assert fake_wt.last_sync_args == ("repo", "branch")
```

Files: `test_pane_coordinator.py`, `test_data_orchestrator.py`, `test_project_service.py`, `test_ports.py`, `test_models.py`, `test_store.py`

### 2. Widget Pilot Tests (async, Textual pilot)

Use `async with app.run_test() as pilot` to drive widgets. Data injected via `set_*()` methods. No `@patch` mocking of internals.

```python
@pytest.mark.asyncio
async def test_project_list_renders():
    app = _ProjectListTestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        pl = app.query_one(ProjectList)
        pl.set_projects(projects, repos)
        await pilot.pause(0.3)
        rows = app.query("ProjectRow")
        assert len(rows) >= 1
```

**Pattern:** Minimal `App` subclass mounting a single widget under test. Each test file defines its own `_<Widget>TestApp`.

Files: `test_widget_project_list.py`, `test_widget_project_detail.py`, `test_widget_worktree_pane.py`, `test_widget_terminal_pane.py`

### 3. Snapshot Tests (SVG baselines)

Use `snap_compare(JoyApp(), ...)` from `pytest-textual-snapshot`. Produces SVG files in `tests/__snapshots__/`.

```python
def test_snapshot_initial_render(snap_compare):
    assert snap_compare(JoyApp(), terminal_size=(120, 40))
```

For stateful screens, use `run_before` callbacks with `@patch.multiple("joy.store", ...)` to inject deterministic data.

Files: `test_snapshots.py`. Baselines in `tests/__snapshots__/test_snapshots/`.

## Fake Backends (`fakes.py`)

Four fake adapter classes conforming to `ports.py` Protocols via structural subtyping:

| Fake | Protocol | Key Behavior |
|------|----------|-------------|
| `FakeStorage` | `StoragePort` | Returns canned data, tracks `saved_projects` |
| `FakeGitData` | `GitDataPort` | Returns provided worktree list |
| `FakeTerminal` | `TerminalPort` | Returns provided sessions, no-ops for create/close |
| `FakeOpener` | `OpenerPort` | Tracks `opened` list for assertion |

**Important:** `fakes.py` does NOT import `joy.ports`. Protocol conformance is structural (duck typing). Conftest fixtures assert `isinstance(fake, XxxPort)` at creation time.

## Adding Tests for New Code

- **New service:** Plain pytest in `tests/test_new_service.py`. Use model objects directly.
- **New widget:** Async pilot test in `tests/test_widget_new_widget.py`. Create `_NewWidgetTestApp(App)`.
- **New adapter:** Mock subprocess/I/O. Follow `test_terminal_sessions.py` pattern.
- **Snapshot change:** Run `uv run pytest --snapshot-update` to regenerate baselines, visually inspect SVG diffs.

## Known Issues

- `test_refresh.py::test_terminal_load_on_mount` — pre-existing failure, unrelated to current codebase
- Snapshot tests for time-sensitive states may be flaky on slow CI (async timing)
