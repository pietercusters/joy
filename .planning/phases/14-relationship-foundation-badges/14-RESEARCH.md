# Phase 14: Relationship Foundation & Badges - Research

**Researched:** 2026-04-14
**Domain:** Python dataclass resolver, Textual widget badge rendering, cursor identity preservation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Resolver module**
- D-01: New standalone module `src/joy/resolver.py` — pure functions only (no I/O, no side effects)
- D-02: Entry point: `compute_relationships(projects, worktrees, sessions, repos) -> RelationshipIndex`
- D-03: `RelationshipIndex` is a dataclass with four query methods: `.worktrees_for(project)`, `.agents_for(project)`, `.project_for_worktree(wt)`, `.project_for_agent(session_name)`
- D-04: Matching logic:
  - Project ↔ Worktree: project has a WORKTREE object whose value matches `wt.path` (path match), OR project has a BRANCH object whose value matches `wt.branch` AND `project.repo == wt.repo_name` (branch match). Path-based match takes precedence.
  - Project ↔ Agent: project has an AGENTS object whose value matches `session.session_name` (exact string match)
- D-05: Projects with no `repo` field are excluded from branch-based worktree matching; path-based match still applies if worktree path appears as an object value
- D-06: `RelationshipIndex` is stored on `JoyApp` as `self._rel_index: RelationshipIndex | None = None`

**Refresh coordination**
- D-07: Resolver computed after both worktrees and sessions loaded for the cycle. App tracks `_worktrees_ready: bool` and `_sessions_ready: bool`. `_maybe_compute_relationships()` runs only when both are True, then resets both flags.
- D-08: `_maybe_compute_relationships()` calls `compute_relationships(...)`, stores result on `self._rel_index`, then calls `_update_badges()` to push counts to ProjectList

**Badge appearance**
- D-09: Badge counts on `ProjectRow` using Nerd Font icons + numbers, appended after project name. Reuse `ICON_BRANCH` (`\ue0a0`) for worktree count, `ICON_CLAUDE` (`\U000f1325`) for agent count
- D-10: Both counts always shown, even when zero (consistent row width)
- D-11: `ProjectRow` receives counts via `set_counts(wt_count: int, agent_count: int)` method. `_update_badges()` in app iterates all rows and calls this after RelationshipIndex is computed

**Cursor preservation**
- D-12: Both `WorktreePane` and `TerminalPane` must preserve cursor across DOM rebuilds:
  - `WorktreePane`: cursor identity = `(repo_name, branch)` tuple
  - `TerminalPane`: cursor identity = `session_name` (add `session_name` field to `SessionRow`)
- D-13: Before `remove_children()`, each pane saves the current identity. After rebuilding rows, searches for the identity and sets `self._cursor` to that index
- D-14: Fallback when item is gone: `min(saved_index, len(new_rows) - 1)`. Never reset to 0 unless list was previously empty.

### Claude's Discretion
- Internal data structure of `RelationshipIndex` (dicts, sets, etc.)
- Whether `_maybe_compute_relationships` uses flags, counters, or asyncio.gather
- Exact spacing/padding of badge counts in ProjectRow content string

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FOUND-01 | Relationship resolver computes Project ↔ Worktree matches (by worktree path or branch name within same repo) | resolver.py pure function module pattern; matching logic from D-04/D-05 |
| FOUND-02 | Relationship resolver computes Project ↔ Agent matches (by iTerm2 session name matching agents object value) | Same resolver; AGENTS PresetKind exists in models.py |
| FOUND-03 | WorktreePane cursor is preserved by identity (repo+branch) across DOM rebuilds triggered by refresh | WorktreeRow already stores `repo_name` and `branch` attributes; pattern confirmed in codebase |
| FOUND-04 | TerminalPane cursor is preserved by identity (session name) across DOM rebuilds triggered by refresh | SessionRow currently stores only `session_id`; needs `session_name` field added |
| BADGE-01 | Project rows display count of active related worktrees | ProjectRow needs `set_counts()` + content rebuild; icon constants reusable from terminal_pane.py |
| BADGE-02 | Project rows display count of active related agent sessions | Same `set_counts()` call; ICON_CLAUDE already imported in terminal_pane.py |
| BADGE-03 | Badge counts update after each background refresh cycle | `_maybe_compute_relationships()` → `_update_badges()` wired into `_set_worktrees` and `_set_terminal_sessions` callbacks |

</phase_requirements>

---

## Summary

Phase 14 is a well-scoped internal plumbing phase with all key decisions already locked in CONTEXT.md. The technical work divides cleanly into three independent slices: (1) the pure-function resolver module, (2) cursor identity preservation in WorktreePane and TerminalPane, and (3) badge rendering on ProjectRow and the app-level wiring that drives badge updates.

The existing codebase is a strong foundation. The `_cursor/_rows/_update_highlight()` pattern is fully established in all four panes. `WorktreeRow` already stores `repo_name` and `branch` as instance attributes, so WorktreePane cursor preservation is straightforward. `SessionRow` stores only `session_id` today — adding `session_name` is the only structural change needed for TerminalPane preservation. The pure-module pattern (`worktrees.py`, `terminal_sessions.py`, `mr_status.py`) gives a clear template for `resolver.py`.

The largest design question is Claude's Discretion: the internal data structure of `RelationshipIndex`. The recommendation is two-pass dict construction (project → list of worktrees/agents, and inverse maps) using `dict` keyed by id/path/name — both O(n) build and O(1) lookup, no special dependencies.

**Primary recommendation:** Three plans in sequence — (1) resolver + tests, (2) cursor preservation in both panes + tests, (3) badge wiring in ProjectRow/ProjectList/app + tests. Plans 1 and 2 are independent and can be parallelised.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| dataclasses (stdlib) | Python 3.11+ | `RelationshipIndex` container | Zero-dep, matches existing models.py pattern |
| typing (stdlib) | Python 3.11+ | Type annotations | Existing codebase uses `from __future__ import annotations` + stdlib typing throughout |
| textual | ^8.2 | TUI widget updates (badge rendering) | Already installed project dependency |
| rich.text.Text | bundled with textual | Badge content string building | Already used in `WorktreeRow.build_content()` and `SessionRow._build_content()` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | ^9.0 | Unit tests for resolver and cursor logic | All tests in this phase |
| asyncio (stdlib) | Python 3.11+ | TUI integration tests using `asyncio.run(_run())` pattern | Textual pilot tests — mirrors existing test_worktree_pane_cursor.py and test_terminal_pane.py |

**No new dependencies required for this phase.** [VERIFIED: pyproject.toml inspection]

---

## Architecture Patterns

### Recommended Project Structure (changes only)
```
src/joy/
├── resolver.py          # NEW — pure function module (D-01)
├── app.py               # MODIFIED — add _rel_index, _worktrees_ready, _sessions_ready, _maybe_compute_relationships(), _update_badges()
├── widgets/
│   ├── project_list.py  # MODIFIED — ProjectRow.set_counts(), ProjectList.update_badges()
│   ├── worktree_pane.py # MODIFIED — cursor identity preservation by (repo_name, branch)
│   └── terminal_pane.py # MODIFIED — add session_name to SessionRow, cursor identity preservation
tests/
└── test_resolver.py     # NEW — pure unit tests for compute_relationships()
```

### Pattern 1: Pure-Function Module (resolver.py)

**What:** A standalone module with a single public entry point returning a rich result object. No I/O, no side effects. Fully testable with no mocking.

**When to use:** Any cross-cutting computation that must be testable in isolation and reusable by downstream phases (15, 16).

**Example — `RelationshipIndex` internal structure:**
```python
# Source: codebase analysis — models.py patterns, worktrees.py module pattern [VERIFIED: codebase]
from __future__ import annotations
from dataclasses import dataclass, field
from joy.models import Project, WorktreeInfo, TerminalSession

@dataclass
class RelationshipIndex:
    # Internal dicts (Claude's Discretion — these are implementation details)
    _wt_for_project: dict[int, list[WorktreeInfo]] = field(default_factory=dict)  # id(project) -> worktrees
    _ag_for_project: dict[int, list[TerminalSession]] = field(default_factory=dict)
    _project_for_wt: dict[tuple[str, str], Project] = field(default_factory=dict)  # (repo_name, branch) -> project
    _project_for_wt_path: dict[str, Project] = field(default_factory=dict)         # path -> project
    _project_for_agent: dict[str, Project] = field(default_factory=dict)            # session_name -> project

    def worktrees_for(self, project: Project) -> list[WorktreeInfo]:
        return self._wt_for_project.get(id(project), [])

    def agents_for(self, project: Project) -> list[TerminalSession]:
        return self._ag_for_project.get(id(project), [])

    def project_for_worktree(self, wt: WorktreeInfo) -> Project | None:
        # Path match takes precedence (D-04)
        return self._project_for_wt_path.get(wt.path) or self._project_for_wt.get((wt.repo_name, wt.branch))

    def project_for_agent(self, session_name: str) -> Project | None:
        return self._project_for_agent.get(session_name)
```

**Note:** Using `id(project)` as dict key works because `_projects` list in `JoyApp` stores the same object references throughout a session. Phases 15/16 will consume the same reference. Alternative: use `project.name` as key (stable string, survives across calls). Using `project.name` is safer and more readable — recommended for implementation.

### Pattern 2: Matching Logic Implementation

**What:** Two-pass construction of `RelationshipIndex`.

**When to use:** Inside `compute_relationships()` function body.

**Matching logic (D-04, D-05):**
```python
# Source: CONTEXT.md D-04/D-05 [VERIFIED: codebase — PresetKind.WORKTREE, PresetKind.BRANCH, PresetKind.AGENTS in models.py]
from joy.models import PresetKind

def compute_relationships(
    projects: list[Project],
    worktrees: list[WorktreeInfo],
    sessions: list[TerminalSession],
    repos: list[Repo],
) -> RelationshipIndex:
    index = RelationshipIndex()

    # --- Build lookup maps from project objects ---
    # path -> project (WORKTREE kind objects)
    path_to_project: dict[str, Project] = {}
    # (repo_name, branch) -> project (BRANCH kind objects, only when project.repo is set)
    branch_to_project: dict[tuple[str, str], Project] = {}
    # session_name -> project (AGENTS kind objects)
    agent_to_project: dict[str, Project] = {}

    for project in projects:
        for obj in project.objects:
            if obj.kind == PresetKind.WORKTREE:
                path_to_project[obj.value] = project
            elif obj.kind == PresetKind.BRANCH and project.repo is not None:
                # D-05: excluded from branch matching if no repo
                branch_to_project[(project.repo, obj.value)] = project
            elif obj.kind == PresetKind.AGENTS:
                agent_to_project[obj.value] = project

    # --- Match worktrees to projects ---
    for wt in worktrees:
        # Path match takes precedence (D-04)
        matched = path_to_project.get(wt.path)
        if matched is None:
            matched = branch_to_project.get((wt.repo_name, wt.branch))
        if matched is not None:
            index._wt_for_project.setdefault(matched.name, []).append(wt)
            # Inverse maps
            index._project_for_wt_path[wt.path] = matched  # for path-matched
            index._project_for_wt[(wt.repo_name, wt.branch)] = matched

    # --- Match sessions to projects ---
    for session in sessions:
        matched = agent_to_project.get(session.session_name)
        if matched is not None:
            index._ag_for_project.setdefault(matched.name, []).append(session)
            index._project_for_agent[session.session_name] = matched

    return index
```

**Note on key choice:** Using `project.name` as dict key (not `id(project)`) is recommended — name is a stable string, survives identity changes across Python sessions, and reads clearly in tests.

### Pattern 3: Cursor Identity Preservation

**What:** Save cursor identity before DOM rebuild, restore by searching for the saved identity after rebuild.

**When to use:** `WorktreePane.set_worktrees()` and `TerminalPane.set_sessions()`.

**WorktreePane pattern (FOUND-03):**
```python
# Source: codebase analysis — WorktreeRow already stores .repo_name and .branch [VERIFIED: worktree_pane.py line 142-143]
async def set_worktrees(self, worktrees, ...):
    # Save identity before rebuild
    saved_identity: tuple[str, str] | None = None
    saved_index = self._cursor
    if 0 <= self._cursor < len(self._rows):
        row = self._rows[self._cursor]
        saved_identity = (row.repo_name, row.branch)

    scroll = self.query_one("#worktree-scroll", _WorktreeScroll)
    saved_scroll_y = scroll.scroll_y
    await scroll.remove_children()

    # ... build new_rows as before ...

    self._rows = new_rows
    # Restore cursor (D-13, D-14)
    if saved_identity is not None and new_rows:
        for i, row in enumerate(new_rows):
            if (row.repo_name, row.branch) == saved_identity:
                self._cursor = i
                break
        else:
            # Item gone: clamp to saved index (D-14)
            self._cursor = min(saved_index, len(new_rows) - 1)
    elif new_rows:
        self._cursor = 0
    else:
        self._cursor = -1
    self._update_highlight()
    # ... scroll restore as before ...
```

**TerminalPane pattern (FOUND-04):**
```python
# Source: codebase analysis — SessionRow currently stores only session_id [VERIFIED: terminal_pane.py line 111]
# Requires adding session_name to SessionRow.__init__

class SessionRow(Static):
    def __init__(self, session: TerminalSession, *, is_claude=False, is_busy=False, **kwargs):
        self.session_id = session.session_id
        self.session_name = session.session_name  # ADD THIS LINE
        ...

async def set_sessions(self, sessions, ...):
    # Save identity before rebuild
    saved_name: str | None = None
    saved_index = self._cursor
    if 0 <= self._cursor < len(self._rows):
        saved_name = self._rows[self._cursor].session_name

    # ... remove_children, build new_rows ...

    # Restore cursor
    if saved_name is not None and new_rows:
        for i, row in enumerate(new_rows):
            if row.session_name == saved_name:
                self._cursor = i
                break
        else:
            self._cursor = min(saved_index, len(new_rows) - 1)
    elif new_rows:
        self._cursor = 0
    else:
        self._cursor = -1
```

### Pattern 4: Badge Rendering in ProjectRow

**What:** `ProjectRow` builds its content string from project name + badge counts. `set_counts()` rebuilds the content string and calls `self.update()` to trigger a re-render.

**When to use:** After resolver computes counts; called by `ProjectList.update_badges()`.

**Example:**
```python
# Source: codebase analysis — ProjectRow currently builds content in __init__ [VERIFIED: project_list.py line 63-65]
# Icons reused from existing constants — ICON_BRANCH from worktree_pane.py, ICON_CLAUDE from terminal_pane.py

from joy.widgets.worktree_pane import ICON_BRANCH
from joy.widgets.terminal_pane import ICON_CLAUDE

class ProjectRow(Static):
    def __init__(self, project: Project, **kwargs) -> None:
        self.project = project
        self._wt_count: int = 0
        self._agent_count: int = 0
        super().__init__(self._build_content(), **kwargs)

    def _build_content(self) -> str:
        # D-10: always show both counts, even when zero
        return f" {self.project.name}  {ICON_BRANCH} {self._wt_count}  {ICON_CLAUDE} {self._agent_count}"

    def set_counts(self, wt_count: int, agent_count: int) -> None:
        self._wt_count = wt_count
        self._agent_count = agent_count
        self.update(self._build_content())
```

**Note on `Static.update()`:** `Static` inherits `.update(content)` from Textual which triggers a re-render without DOM rebuild. This is the correct pattern — no `remove_children()` needed. [VERIFIED: Textual Static widget API — Static.update() is the established update method used in existing codebase e.g., project_detail.py]

### Pattern 5: App-Level Badge Wiring

**What:** `_maybe_compute_relationships()` and `_update_badges()` in `JoyApp`. Two boolean flags on app track which workers have completed.

**Refresh coordination (D-07, D-08):**
```python
# In JoyApp.__init__:
self._worktrees_ready: bool = False
self._sessions_ready: bool = False
self._rel_index: RelationshipIndex | None = None

# In _set_worktrees():
self._worktrees_ready = True
# ... existing code ...
self._maybe_compute_relationships()

# In _set_terminal_sessions():
self._sessions_ready = True
# ... existing code ...
self._maybe_compute_relationships()

def _maybe_compute_relationships(self) -> None:
    if not (self._worktrees_ready and self._sessions_ready):
        return
    self._worktrees_ready = False
    self._sessions_ready = False
    from joy.resolver import compute_relationships  # noqa: PLC0415
    # Need current worktrees and sessions — store them on app during set calls
    self._rel_index = compute_relationships(
        self._projects, self._current_worktrees, self._current_sessions, self._repos
    )
    self._update_badges()

def _update_badges(self) -> None:
    if self._rel_index is None:
        return
    self.query_one(ProjectList).update_badges(self._rel_index)
```

**Important:** This pattern requires storing the raw worktrees and sessions lists on `JoyApp` during `_set_worktrees` and `_set_terminal_sessions` so `_maybe_compute_relationships` can access them. Add `self._current_worktrees: list[WorktreeInfo] = []` and `self._current_sessions: list[TerminalSession] = []` to `JoyApp.__init__`.

### Anti-Patterns to Avoid

- **Triggering resolver in background thread:** `_maybe_compute_relationships()` is called from `_set_worktrees` / `_set_terminal_sessions` which are already on the main thread (via `call_from_thread`). The resolver is pure and fast (O(n) scan) — run it synchronously on the main thread. No need for a worker.
- **Resetting cursor to 0 in fallback:** D-14 says clamp to `min(saved_index, len-1)`. Only reset to 0 when the pane was previously empty (saved_identity was None because `_cursor == -1`).
- **Using rich.Text for badge content in ProjectRow:** The current `ProjectRow` passes a plain string to `Static.__init__`. Badge content is simple (name + two icons + two numbers) — a plain f-string is sufficient. Use `rich.Text` only if styling (colors, bold) is needed on individual badge segments. D-09 says "appended after project name" — a plain string works.
- **Cross-importing icon constants between widgets:** Both `ICON_BRANCH` and `ICON_CLAUDE` need to be accessible in `project_list.py`. Import them at the top of `project_list.py` from their respective widget modules. This is a one-way dependency (project_list imports from worktree_pane and terminal_pane); it does not create a circular import because those modules do not import from project_list.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Content update without DOM rebuild | Custom reactive attribute + re-compose | `Static.update(content)` | Already wired in Textual; existing codebase uses it (project_detail.py) |
| Async flag coordination | asyncio.Event or asyncio.gather | Two simple booleans + gate check | Workers call callbacks on main thread sequentially — no real concurrency, no asyncio primitives needed |
| Cursor restore logic | Abstract base class or mixin | Inline save/restore in each pane's `set_*` method | Only two panes need it; shared mixin adds complexity for no gain |

---

## Common Pitfalls

### Pitfall 1: Ready Flags Not Reset on Each Cycle
**What goes wrong:** `_worktrees_ready` and `_sessions_ready` are set to True but never reset. On the first cycle they work. On subsequent cycles, whichever flag was set first is already True from the last cycle, so `_maybe_compute_relationships()` fires on the first callback, with stale data from the other worker.
**Why it happens:** The gate `if not (both ready): return` is only meaningful if flags reset after each cycle.
**How to avoid:** Reset both flags to False inside `_maybe_compute_relationships()` before returning (D-07 says "then resets both flags").
**Warning signs:** Badges show stale counts after the second refresh cycle.

### Pitfall 2: `set_sessions` Called with `None` When iTerm2 Unavailable
**What goes wrong:** `_set_terminal_sessions(None)` is called when iTerm2 fetch fails. If the `_sessions_ready` flag is set inside `_set_terminal_sessions` regardless of whether sessions is None, `_maybe_compute_relationships()` will be called with `self._current_sessions = None`, crashing `compute_relationships`.
**Why it happens:** The existing `_set_terminal_sessions` handles None early-return in the pane, but the app-level flag must be set carefully.
**How to avoid:** Set `self._current_sessions = sessions or []` (treat None as empty list) before setting `_sessions_ready = True`. The resolver should accept an empty list gracefully.
**Warning signs:** AttributeError or TypeError when iTerm2 is not running.

### Pitfall 3: Cursor Identity Lost When Row Order Changes
**What goes wrong:** WorktreePane sorts worktrees: non-default first, then default; alphabetical within. TerminalPane sorts: Claude first (busy before waiting), then Other alphabetically. After a refresh, a new session appears that sorts before the currently-highlighted one — the saved `session_name` is found at a different index, but the identity search correctly finds it. This is the CORRECT behavior. The pitfall is searching only by index (old approach) which would land on the wrong row.
**Why it happens:** Index-based restore was the original pattern in `set_worktrees` and `set_sessions`. Phase 14 replaces it with identity-based restore.
**How to avoid:** Always search `new_rows` for the saved identity string/tuple, then set `self._cursor` to the found index. Only fall back to clamped-index when identity is not found.
**Warning signs:** After a refresh adds a new session, the highlighted row is the wrong one.

### Pitfall 4: Badge Icons Not Available in project_list.py
**What goes wrong:** `ICON_BRANCH` is defined in `worktree_pane.py` and `ICON_CLAUDE` is defined in `terminal_pane.py`. Importing them in `project_list.py` creates a module-level import of widget modules. This is fine architecturally but must be verified against circular import risk.
**Why it happens:** Textual widget modules import from `joy.models` — not from each other. Adding `from joy.widgets.worktree_pane import ICON_BRANCH` to `project_list.py` only imports that module's top-level code, which has no import of `project_list`.
**How to avoid:** Confirm import order with a quick `python -c "from joy.widgets.project_list import ProjectRow"` after adding the imports. Alternatively, define a shared `joy/icons.py` constants module to avoid widget cross-dependencies.
**Warning signs:** `ImportError: circular import`.

### Pitfall 5: `Static.update()` Signature
**What goes wrong:** Calling `self.update(content)` where content is a plain string works. But if content is a `rich.Text` object with markup, passing it as the first positional argument to `Static.update()` may behave differently depending on Textual version.
**Why it happens:** `Static` inherits `update(content)` — in Textual 8.x, `content` can be str or `RenderableType` (Text, etc.).
**How to avoid:** For badge content, use a plain f-string. Avoid rich markup in badge strings unless styling is required. [ASSUMED — Textual 8.x Static.update() accepts both str and Text; confirm with a quick test if rich.Text with styled segments is needed]

---

## Code Examples

Verified patterns from existing codebase:

### Existing `Static.update()` Usage
```python
# Source: project_detail.py — same pattern for content updates [VERIFIED: codebase]
# The Static.update() method is the standard Textual way to update widget content
# without a DOM rebuild. Used in this project already.
self.update(new_content)
```

### Existing Icon Constant Pattern
```python
# Source: worktree_pane.py lines 21-22 [VERIFIED: codebase]
ICON_BRANCH = "\ue0a0"           # nf-pl-branch

# Source: terminal_pane.py line 28 [VERIFIED: codebase]
ICON_CLAUDE = "\U000f1325"   # nf-md-robot (AI/robot glyph)
```

### Existing Pure Module Pattern
```python
# Source: worktrees.py — entire module is pure functions [VERIFIED: codebase]
# No class, no I/O in function signatures, subprocess only inside helpers
def discover_worktrees(repos: list[Repo], branch_filter: list[str] | None = None) -> list[WorktreeInfo]:
    ...
```

### Existing Cursor Save/Restore Pattern (from ProjectList.action_rename_project)
```python
# Source: project_list.py lines 241-246 [VERIFIED: codebase]
# This shows the existing identity-by-object-reference pattern for cursor restore.
# Phase 14 applies the same principle but by string/tuple identity.
def _restore_cursor() -> None:
    for i, row in enumerate(self._rows):
        if row.project is project:
            self.select_index(i)
            break
self.call_after_refresh(_restore_cursor)
```

### Existing `call_from_thread` to `async` Callback Pattern
```python
# Source: app.py lines 141-142 [VERIFIED: codebase]
# Workers push data to UI via call_from_thread. _set_worktrees and _set_terminal_sessions
# are both called this way. _maybe_compute_relationships() will be called from these
# methods — it runs on the main thread, no call_from_thread needed inside it.
self.app.call_from_thread(self._set_worktrees, worktrees, repo_count, branch_filter, mr_data, mr_failed)
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0+ with pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_resolver.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

**Note:** TUI tests using `asyncio.run(_run())` pattern (NOT `@pytest.mark.asyncio`) — see existing test_worktree_pane_cursor.py and test_terminal_pane.py for the established pattern. Tests are marked `@pytest.mark.slow` per project convention and filtered out by default (`addopts = ["-m", "not slow"]`). Pure resolver unit tests are NOT slow (no TUI) and run in the default suite.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FOUND-01 | `compute_relationships()` matches worktrees by path and branch | unit | `uv run pytest tests/test_resolver.py -x -q` | ❌ Wave 0 |
| FOUND-02 | `compute_relationships()` matches agents by session_name | unit | `uv run pytest tests/test_resolver.py -x -q` | ❌ Wave 0 |
| FOUND-03 | WorktreePane cursor stays on same (repo_name, branch) after set_worktrees rebuild | slow TUI | `uv run pytest tests/test_worktree_pane_cursor.py -m slow -x` | ❌ Wave 0 |
| FOUND-04 | TerminalPane cursor stays on same session_name after set_sessions rebuild | slow TUI | `uv run pytest tests/test_terminal_pane.py -m slow -x` | ✅ (add new test) |
| BADGE-01 | ProjectRow.set_counts() updates worktree badge count in content | unit | `uv run pytest tests/test_project_list.py -x -q` | ❌ Wave 0 |
| BADGE-02 | ProjectRow.set_counts() updates agent badge count in content | unit | `uv run pytest tests/test_project_list.py -x -q` | ❌ Wave 0 |
| BADGE-03 | Badge counts update when both refresh workers complete | unit (mock) | `uv run pytest tests/test_resolver.py -x -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_resolver.py tests/test_project_list.py -x -q` (fast unit tests only)
- **Per wave merge:** `uv run pytest -x -q` (full suite including slow TUI tests if marked correctly)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_resolver.py` — covers FOUND-01, FOUND-02, BADGE-03 (resolver logic)
- [ ] `tests/test_project_list.py` — covers BADGE-01, BADGE-02 (ProjectRow.set_counts)
- [ ] New test in `tests/test_worktree_pane_cursor.py` — covers FOUND-03 (cursor identity preserve after rebuild)
- [ ] New test in `tests/test_terminal_pane.py` — covers FOUND-04 (cursor identity preserve after rebuild)

---

## Open Questions

1. **Icon import strategy for project_list.py**
   - What we know: `ICON_BRANCH` lives in `worktree_pane.py`, `ICON_CLAUDE` lives in `terminal_pane.py`. These are widget modules, not utility modules.
   - What's unclear: Whether cross-importing widget constants creates any structural debt or future circular import risk.
   - Recommendation: Either import directly (verify no circular import — none expected based on current dependency graph), or define `src/joy/icons.py` as a shared constants module. The icons module is a cleaner long-term solution given Phase 16 may also need these constants. However, it adds a file that wasn't part of the discussion. Defer to planner: inline import is acceptable for Phase 14 scope.

2. **`_current_worktrees` and `_current_sessions` storage on JoyApp**
   - What we know: `_set_worktrees` receives `worktrees: list[WorktreeInfo]`, `_set_terminal_sessions` receives `sessions: list[TerminalSession] | None`. Currently these are not stored on the app — they're passed directly to pane widgets.
   - What's unclear: Whether storing them on the app is acceptable given the "single source of truth" principle (panes own their display data).
   - Recommendation: Store `self._current_worktrees` and `self._current_sessions` on `JoyApp` during each respective set callback. These are transient inputs to the resolver, not authoritative data — the pane still owns the display state. This is the simplest approach that avoids requiring the pane to expose its internal data back to the app.

---

## Environment Availability

Step 2.6: SKIPPED — phase is code/config-only changes to existing Python modules. No new external dependencies, services, CLIs, or runtimes.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `Static.update()` in Textual 8.x accepts both str and rich.Text as first argument | Code Examples, Pitfall 5 | If only one type is accepted, badge content string must be adjusted to match |
| A2 | `id(project)` or `project.name` as dict key is stable across a single app session (no project list rebuild mid-refresh) | Architecture Patterns Pattern 1 | If projects list is rebuilt (new objects), inverse lookups would fail; use `project.name` as key for safety |

**Mitigation for A2:** Use `project.name` (not `id(project)`) as the dict key in `RelationshipIndex` internal maps. `project.name` is a stable string that survives list rebuilds. The conftest.py sample project shows names are unique (enforced by action_new_project). [VERIFIED: app.py line 315 — duplicate name check enforced on creation]

---

## Sources

### Primary (HIGH confidence)
- Codebase — `src/joy/models.py`: PresetKind.WORKTREE, BRANCH, AGENTS confirmed; WorktreeInfo fields repo_name/branch/path confirmed; TerminalSession.session_name confirmed [VERIFIED: codebase read]
- Codebase — `src/joy/widgets/worktree_pane.py`: WorktreeRow stores repo_name/branch as instance attributes (lines 142-143); ICON_BRANCH defined (line 21) [VERIFIED: codebase read]
- Codebase — `src/joy/widgets/terminal_pane.py`: SessionRow stores only session_id (line 111); ICON_CLAUDE defined (line 28) [VERIFIED: codebase read]
- Codebase — `src/joy/widgets/project_list.py`: ProjectRow builds content as plain string in `__init__` (line 65); `_rows` + `_cursor` + `_update_highlight()` pattern [VERIFIED: codebase read]
- Codebase — `src/joy/app.py`: `_set_worktrees` and `_set_terminal_sessions` are async, called via `call_from_thread` from background workers [VERIFIED: codebase read]
- Codebase — `tests/`: asyncio.run(_run()) pattern for TUI tests; `@pytest.mark.slow` convention; `uv run pytest` as test runner [VERIFIED: codebase read]
- `pyproject.toml`: test configuration, `addopts = ["-m", "not slow and not macos_integration"]` [VERIFIED: codebase read]

### Secondary (MEDIUM confidence)
- None required for this phase — all patterns verified directly in codebase

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; existing packages verified in pyproject.toml
- Architecture: HIGH — all patterns verified from live codebase; matching logic directly from CONTEXT.md locked decisions
- Pitfalls: HIGH — derived from reading the actual current code (e.g., `set_sessions` currently resets cursor to 0; `SessionRow` currently lacks `session_name`; flag reset pattern is a real gotcha)

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (stable Python/Textual stack — 30 day window)
