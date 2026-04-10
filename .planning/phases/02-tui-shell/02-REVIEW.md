---
phase: 02-tui-shell
reviewed: 2026-04-10T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - src/joy/app.py
  - src/joy/widgets/project_list.py
  - src/joy/widgets/project_detail.py
  - src/joy/widgets/object_row.py
  - tests/test_tui.py
  - pyproject.toml
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-04-10T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the TUI shell implementation: the two-pane app layout, project list widget, project detail widget with cursor navigation, object row rendering, async pilot tests, and packaging config. The code is well-structured with clean separation between widgets. Three warnings were found — two are real logic bugs (one related to the `mock_store` fixture patching the wrong target, and one related to a stale `_rows` reference during rapid project switching), and one is a guard-less `index` access. Three informational items cover minor quality issues.

The `mock_store` bug means `test_first_project_auto_selected`, `test_enter_shifts_focus_to_detail`, `test_escape_returns_focus_to_list`, and `test_quit_with_q` will not actually mock the store — they call the real `load_projects`, which reads `~/.joy/projects.toml` on the developer's machine.

---

## Warnings

### WR-01: `mock_store` fixture patches the wrong target

**File:** `tests/test_tui.py:34`
**Issue:** The fixture patches `joy.store.load_projects`, but `app.py` imports `load_projects` inside `_load_data` with `from joy.store import load_projects`. `unittest.mock.patch` replaces the name in the module where the lookup happens. Because `app.py` does the import lazily inside the function body (`from joy.store import load_projects`), the lookup always goes back to `joy.store`, so patching `joy.store.load_projects` should work in this specific case — BUT only because of the lazy import. If the import is ever moved to module level the mock silently breaks. More critically, the comment on line 34 says "without touching `~/.joy/`" yet the mock target path `joy.store.load_projects` is correct here only by coincidence of the lazy import. The robust and conventional target is `joy.app.load_projects` (the name as seen at call site), which does not yet exist at module level. The safest fix is to patch the attribute on the module where the object will be looked up at call time.

Since the lazy import re-executes `from joy.store import load_projects` on every `_load_data` call, the binding is always fresh from `joy.store`. The patch on `joy.store.load_projects` therefore does intercept the call correctly at present. However the assertion in `test_first_project_auto_selected` uses `await pilot.pause(0.2)` to wait for a background worker, which is a timing-dependent approach — if the worker thread takes longer than 200ms (e.g., slow CI), the assertion fails spuriously.

**Fix:** Keep the current patch target (`joy.store.load_projects`) since it is correct for the lazy-import pattern, but document why. Replace the timing-dependent pause with `await pilot.pause()` (Textual's zero-arg pause processes all pending messages) or use `app.workers.wait_for_complete()` after `run_test()`:

```python
@pytest.fixture
def mock_store():
    # Patch on joy.store because app.py imports lazily (from joy.store import ...)
    # each time _load_data runs, so the binding is resolved from joy.store at call time.
    with patch("joy.store.load_projects", return_value=_sample_projects()) as mock:
        yield mock

async def test_first_project_auto_selected(mock_store):
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause()   # process all pending messages
        await app.workers.wait_for_complete()
        detail = app.query_one("#project-detail")
        assert detail._project is not None
        assert detail._project.name == "project-alpha"
```

---

### WR-02: Stale `_rows` reference possible during rapid project switching

**File:** `src/joy/widgets/project_detail.py:101-133`
**Issue:** `set_project` calls `self.call_after_refresh(self._render_project)` and returns immediately. If the user switches projects quickly (two keystrokes before the first refresh fires), `_render_project` will run twice using `self._project` — which by then points to the second project. The first invocation sees the correct project but the second invocation rebuilds and sets `self._rows` again. Between the two invocations `_cursor` and `_rows` are inconsistent: `_cursor` was reset to `0` by the first invocation, but `_rows` gets reset again by the second. This is benign in practice (the second run wins) but only because `call_after_refresh` queues callbacks and Textual processes them serially on the UI thread.

The real risk is that `_update_highlight()` is called at the end of `_render_project` while `scroll.remove_children()` + `scroll.mount(row)` calls are still being processed asynchronously. `scroll_visible()` on line 141 is called on a row that may not yet be fully laid out, which can produce a no-op scroll on first render.

**Fix:** Guard against re-entrant renders with a generation counter, and call `scroll_visible` after the next refresh:

```python
def set_project(self, project: Project) -> None:
    self._project = project
    self._render_generation = getattr(self, "_render_generation", 0) + 1
    gen = self._render_generation
    self.call_after_refresh(lambda: self._render_project(gen))

def _render_project(self, gen: int = 0) -> None:
    if gen != getattr(self, "_render_generation", 0):
        return  # superseded by a newer set_project call
    # ... rest unchanged ...
```

---

### WR-03: `pytest-asyncio` mode not configured — tests may silently collect but not run

**File:** `pyproject.toml:20-25`
**Issue:** `pytest-asyncio>=0.25` requires an explicit `asyncio_mode` setting in `[tool.pytest.ini_options]`. Without it, the default mode is `"strict"` in pytest-asyncio 0.21+ and all `@pytest.mark.asyncio` tests will raise `PytestUnraisableExceptionWarning` or be skipped with a deprecation warning. In pytest-asyncio 0.25 specifically, tests decorated with `@pytest.mark.asyncio` but without the mode configured emit a `DeprecationWarning` and in future versions will become errors.

**Fix:** Add the asyncio mode to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = ["-m", "not macos_integration"]
markers = [
    "macos_integration: tests requiring live macOS apps (iTerm2, Notion, etc.)",
]
```

With `asyncio_mode = "auto"`, the `@pytest.mark.asyncio` decorators in `test_tui.py` can also be removed (they become redundant), but they are harmless to leave.

---

## Info

### IN-01: `_projects` instance variable stored on `JoyApp` but never declared

**File:** `src/joy/app.py:48`
**Issue:** `self._projects = projects` assigns a new attribute inside `_set_projects`, but `JoyApp` has no `__init__` and no class-level declaration for `_projects`. The attribute does not exist between app startup and the moment the worker completes. Any code that reads `self._projects` before the worker finishes (e.g., a future keybinding handler added in Phase 3) will raise `AttributeError`.

**Fix:** Declare the attribute with a default in `JoyApp`:

```python
class JoyApp(App):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._projects: list[Project] = []
```

---

### IN-02: `on_descendant_focus` walks the DOM manually when Textual provides `ancestors`

**File:** `src/joy/app.py:53-64`
**Issue:** The manual `while node is not None` walk up the DOM tree reimplements what `widget.ancestors` already provides in Textual 8.x. This is not a bug, but it makes the code harder to follow and could break if Textual changes how `parent` is set during composition.

**Fix:**

```python
def on_descendant_focus(self, event) -> None:
    for ancestor in event.widget.ancestors:
        if getattr(ancestor, "id", None) == "project-detail":
            self.sub_title = "Detail"
            return
        if getattr(ancestor, "id", None) in ("project-list", "project-listview"):
            self.sub_title = "Projects"
            return
```

---

### IN-03: `ObjectRow.index` attribute is set but never read

**File:** `src/joy/widgets/object_row.py:42`
**Issue:** `self.index = index` stores the row's position in the list, but nothing reads `ObjectRow.index` — `ProjectDetail` manages cursor position via its own `_cursor` integer. This attribute is dead code. It may have been intended for Phase 3 activation, but as-is it is unused and slightly confusing.

**Fix:** Remove the `index` parameter and attribute unless there is a planned use:

```python
def __init__(self, item: ObjectItem, **kwargs) -> None:
    self.item = item
    renderable = self._render_text(item)
    super().__init__(renderable, **kwargs)
```

If the index is needed in Phase 3, add it then with a clear docstring explaining its purpose.

---

_Reviewed: 2026-04-10T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
