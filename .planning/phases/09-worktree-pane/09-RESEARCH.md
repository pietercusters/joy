# Phase 9: Worktree Pane - Research

**Researched:** 2026-04-13
**Domain:** Textual 8.x widget implementation, rich.Text rendering, threaded data loading
**Confidence:** HIGH

## Summary

Phase 9 fills the existing `WorktreePane` stub (bottom-right of the 2x2 grid from Phase 8) with grouped worktree rows, status indicators, and empty-state messaging. All visual and behavioral decisions are locked in CONTEXT.md D-01 through D-18. The implementation pattern mirrors the existing `ProjectDetail` widget's `GroupHeader` + `ObjectRow` architecture but with a simpler read-only, cursor-less variant.

The research confirms all required Textual APIs exist and work as expected in the installed version (8.2.3). The `remove_children()` + `mount()` idempotent rebuild pattern is established in `ProjectDetail._render_project()`, and will transfer directly. Nerd Font codepoints for dirty (`U+F111`) and no-upstream (`U+F0BE1`) indicators are verified. Path abbreviation and middle-truncation should be implemented as pure functions operating at row-build time, using `self.content_size.width` for available width.

**Primary recommendation:** Mirror the ProjectDetail rebuild pattern exactly. Keep WorktreeRow as a `Static` subclass with height 2, embed both lines via `\n` in `rich.Text`, and pre-truncate paths before building the Text object rather than relying on Rich's overflow behavior.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** App-owned data load, push to pane. `JoyApp` gains a `@work(thread=True)` worker (`_load_worktrees`) that calls `discover_worktrees(repos, config.branch_filter)` and invokes `worktree_pane.set_worktrees(list)` via `call_from_thread`. Mirrors the existing `ProjectList.set_projects` pattern. The pane stays purely presentational.
- **D-02:** Initial load fires from `JoyApp._set_projects` (`src/joy/app.py:82`) -- i.e., after projects + config have landed from `_load_data`. Rationale: we need `config.branch_filter` to pass to `discover_worktrees()`, and `_set_projects` is the existing synchronization point where config is guaranteed available. Pane shows "Loading..." placeholder until that fires.
- **D-03:** Public pane API is a single method: `WorktreePane.set_worktrees(worktrees: list[WorktreeInfo]) -> None`. Idempotent -- clears existing row DOM and rebuilds from the new list. Phase 10's refresh timer will call the same method on each tick.
- **D-04:** Repos list input: `WorktreePane.set_worktrees` receives only the flat `list[WorktreeInfo]` from `discover_worktrees()`. Grouping happens inside the pane (by `worktree.repo_name`).
- **D-05:** Between first paint and the initial `set_worktrees` call, the pane displays a centered, muted "Loading..." Static -- same styling as the Phase 8 "coming soon" placeholder. The placeholder widget is replaced on the first `set_worktrees` call.
- **D-06:** Row container widget: `VerticalScroll` holding `GroupHeader(Static)` + `WorktreeRow(Static)` children. Same pattern as `ProjectDetail`.
- **D-07:** Each worktree row is a single `Static` containing a `rich.Text` with an embedded `\n`. Line 1: branch + indicators. Line 2: abbreviated path. Row `height: 2`.
- **D-08:** Status indicators use Nerd Font glyphs. Dirty: nf-fa-circle. No-upstream: nf-fa-cloud_off. Branch icon prefix: nf-pl-branch.
- **D-09:** Group headers reuse the `GroupHeader(Static)` pattern from `ProjectDetail`.
- **D-10:** Hide repos with zero worktrees (natural from grouping).
- **D-11:** Repo sections ordered alphabetically by `Repo.name` (case-insensitive).
- **D-12:** Worktrees within repo ordered alphabetically by `branch` (case-insensitive).
- **D-13:** Path abbreviation: replace leading `Path.home()` with `~`. No other transformations.
- **D-14:** Middle-truncation with ellipsis for paths wider than pane. Preserves `~/` prefix and leaf segment.
- **D-15:** Empty state for no repos: `"No repos registered. Add one via settings."`
- **D-16:** Empty state for repos but no worktrees: `"No active worktrees. (filtered: {branch_filter})"`
- **D-17:** All-repos-errored collapsed into D-16.
- **D-18:** Empty-state styling matches Phase 8 "coming soon" stub.

### Claude's Discretion
- Exact color for dirty indicator (suggest `$warning` or orange).
- Whether branch-icon prefix is included or omitted on line 1.
- Middle-truncation algorithm specifics.
- Module layout: inline in `worktree_pane.py` or extracted to sibling.
- Internal CSS ids/class names.
- Whether to keep `BINDINGS = []` line.

### Deferred Ideas (OUT OF SCOPE)
- Background refresh timer (Phase 10)
- MR/CI indicators (Phase 11)
- Per-repo git error surfacing (changes Phase 7 D-02 contract)
- Repo registry UI (Phase 13)
- Selection cursor / activation on rows (explicitly non-goal)
- Per-worktree Claude/terminal indicator (Phase 12)
- Resize-responsive truncation recomputation (Phase 10 handles incidentally)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WKTR-02 | Worktrees are grouped under repo section headers; repos with no active worktrees are hidden | GroupHeader pattern from ProjectDetail (line 50-61), alphabetical ordering via `sorted()` with `key=str.lower`, natural empty-repo hiding from grouping-only-over-present-repos |
| WKTR-03 | Each worktree row shows branch name and dirty/no-remote indicators on line 1, abbreviated path on line 2 | Single Static with rich.Text + embedded `\n`, height:2 CSS, verified Nerd Font codepoints (U+F111 dirty, U+F0BE1 no-upstream, U+E0A0 branch), `Path.home()` abbreviation + middle-truncation |
| WKTR-10 | Worktree pane is read-only -- no selection cursor, no keyboard interaction beyond scrolling | VerticalScroll provides scrolling by default, no BINDINGS on pane, `can_focus=True` already set from Phase 8 for Tab cycling |
</phase_requirements>

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| textual | 8.2.3 | TUI framework | Already installed. VerticalScroll, Static, Widget APIs verified. [VERIFIED: `uv run python -c "import textual; print(textual.__version__)"` returns 8.2.3] |
| rich | (textual dep) | rich.Text for styled two-line rows | Already installed as textual dependency. Text with embedded `\n`, styled spans, `no_wrap=True` all verified. [VERIFIED: runtime import test] |

### Supporting (already installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tomli_w | >=1.0 | TOML writing | Not directly used in this phase (no persistence changes) |

**No new dependencies required.** This phase only adds widget code consuming existing data.

## Architecture Patterns

### Recommended Project Structure (no new files needed)
```
src/joy/
  widgets/
    worktree_pane.py   # <-- MODIFY: fill stub with rows, headers, empty states
  app.py               # <-- MODIFY: add _load_worktrees worker + _set_worktrees
```

### Pattern 1: Idempotent Rebuild via remove_children() + mount()
**What:** Clear all children from a VerticalScroll container, then mount new GroupHeader and row widgets. This is the same pattern used in `ProjectDetail._render_project()`.
**When to use:** Every call to `set_worktrees()`.
**API signatures verified:**
```python
# Both return awaitables but can be called synchronously (fire-and-forget)
# [VERIFIED: inspect.signature and existing usage in project_detail.py]
Widget.remove_children(selector='*') -> AwaitRemove
Widget.mount(*widgets, before=None, after=None) -> AwaitMount
```
**Example (from existing code, project_detail.py lines 142-164):**
```python
# Source: src/joy/widgets/project_detail.py
scroll = self.query_one("#detail-scroll", _DetailScroll)
scroll.remove_children()  # sync call, no await needed
for kind in GROUP_ORDER:
    items = grouped.get(kind, [])
    if not items:
        continue
    scroll.mount(GroupHeader(GROUP_LABELS[kind]))
    for item in items:
        row = ObjectRow(item, index=row_index)
        scroll.mount(row)
```

### Pattern 2: Threaded Worker + call_from_thread
**What:** `@work(thread=True)` decorated method runs I/O in a thread, then `self.app.call_from_thread()` pushes results to the main thread for DOM updates.
**When to use:** Loading worktree data (calls `discover_worktrees()` which invokes git subprocess).
**API signatures verified:**
```python
# [VERIFIED: inspect.signature on Textual 8.2.3]
@work(method=None, *, name='', group='default', exit_on_error=True, exclusive=False, description=None, thread=False)
App.call_from_thread(callback, *args, **kwargs) -> ReturnType
```
**Example (from existing code, app.py lines 73-80):**
```python
# Source: src/joy/app.py
@work(thread=True)
def _load_data(self) -> None:
    from joy.store import load_config, load_projects
    projects = load_projects()
    config = load_config()
    self.app.call_from_thread(self._set_projects, projects, config)
```

### Pattern 3: Single Static with rich.Text for Multi-line Rows
**What:** Use `rich.Text` with embedded `\n` inside a `Static` widget with `height: 2` CSS to create a two-line row as a single DOM node.
**When to use:** Every WorktreeRow.
**Verified behaviors:**
- `rich.Text(no_wrap=True, overflow='ellipsis')` with `\n` correctly creates two logical lines [VERIFIED: runtime test]
- `Static.content` returns the original renderable (str or Text) for test assertions [VERIFIED: runtime test]
- `Static.update(new_content)` replaces content in-place [VERIFIED: inspect.signature]
- `str(static.content)` on a rich.Text returns `text.plain` [VERIFIED: runtime test]
- All Nerd Font icons have `cell_len == 1` per Rich's width calculation [VERIFIED: `rich.cells.cell_len`]

### Pattern 4: GroupHeader Reuse
**What:** Import and reuse `GroupHeader` from `project_detail.py` for repo section headers.
**Source:** `src/joy/widgets/project_detail.py` lines 50-61
```python
class GroupHeader(Static):
    DEFAULT_CSS = """
    GroupHeader {
        width: 1fr;
        height: 1;
        color: $text-muted;
        text-style: bold;
        padding: 0 1;
    }
    """
```
**Note:** GroupHeader is currently defined in `project_detail.py`. For Phase 9, it can either be imported from there or duplicated. Importing is cleaner but creates a cross-widget dependency. Given the codebase convention of one widget per file, importing from a sibling widget file is acceptable. [ASSUMED: design choice for planner]

### Anti-Patterns to Avoid
- **Awaiting mount()/remove_children() inside set_worktrees:** The existing pattern discards the AwaitMount/AwaitRemove. Awaiting would require making `set_worktrees` async, breaking the `call_from_thread` contract (which expects a sync callable). [VERIFIED: existing pattern in project_detail.py]
- **Building one Static per line:** D-07 explicitly requires a single Static per row with embedded `\n`. Two Statics per row would double the DOM node count and break the "refresh-cheapness" goal for Phase 10.
- **Relying on Rich overflow for path truncation:** Rich's `overflow='ellipsis'` truncates from the right, but D-14 requires middle-truncation. Pre-truncate the path string before building the Text. [VERIFIED: Rich renders overflow at right edge, not middle]
- **Using VerticalScroll.can_focus=False:** VerticalScroll defaults to `can_focus=True`. The Phase 8 stub already has focus working. Do not disable focus on the inner scroll container -- but it should be `can_focus=False` to avoid stealing focus from the parent WorktreePane, same as `_DetailScroll` pattern. [VERIFIED: VerticalScroll.can_focus is True by default; ProjectDetail uses _DetailScroll(VerticalScroll, can_focus=False)]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Scrolling in pane | Custom scroll logic | `VerticalScroll` container | Built-in Textual container, handles mouse wheel, arrow keys in scroll context |
| Styled multi-line text | Manual ANSI escape sequences | `rich.Text` with spans | Rich handles style stacking, color resolution, cell width calculation |
| Thread-safe DOM updates | Manual threading/locking | `@work(thread=True)` + `call_from_thread` | Textual's built-in thread safety mechanism, proven in existing codebase |
| Group header styling | Custom CSS per phase | `GroupHeader(Static)` from project_detail.py | Already exists, tested, consistent visual language |

**Key insight:** Every building block this phase needs already exists in the codebase or Textual's standard library. The implementation is composition, not invention.

## Nerd Font Icon Codepoints

| Icon Name | Codepoint | Python Literal | Purpose | Verified |
|-----------|-----------|----------------|---------|----------|
| nf-fa-circle | U+F111 | `"\uf111"` | Dirty indicator | [VERIFIED: `rich.cells.cell_len('\uf111') == 1`] |
| nf-md-cloud_off | U+F0BE1 | `"\U000f0be1"` | No-upstream indicator | [VERIFIED: `rich.cells.cell_len('\U000f0be1') == 1`, east_asian_width='A'] |
| nf-pl-branch | U+E0A0 | `"\ue0a0"` | Branch prefix icon | [VERIFIED: already in `PRESET_ICONS[PresetKind.BRANCH]` in object_row.py] |

**Important note on nf-md-cloud_off (U+F0BE1):** This codepoint is in the Supplementary Private Use Area-B (beyond BMP, > U+FFFF). It requires `\U000f0be1` notation in Python (8-digit uppercase escape). The CONTEXT.md D-08 references "nf-fa-cloud_off" but FontAwesome does not have a cloud_off glyph -- the correct Nerd Font glyph is `nf-md-cloud_off` from the Material Design icon set at U+F0BE1. [VERIFIED: Nerd Fonts cheat sheet lookup, Python ord/cell_len tests]

**Cell width:** All three icons measure as 1 cell wide per `rich.cells.cell_len()`. This means icon alignment calculations can treat each icon as exactly 1 character wide. [VERIFIED: runtime test]

## Textual API Details for This Phase

### Widget Sizing for Middle-Truncation
```python
# Available sizing properties on Widget: [VERIFIED: dir() + property inspection]
Widget.size          # property -> Size(width, height) -- content area size
Widget.content_size  # property -> Size -- content area size (same as size)
Widget.content_region # property -> Region -- absolute region minus padding and border
Widget.container_size # property -> Size -- parent container size
```

For middle-truncation, use `self.content_region.width` or `self.size.width` on the WorktreePane to determine available width. Since WorktreePane has a border, `content_region.width` gives the correct inner width minus border characters. [VERIFIED: property docstrings confirmed]

However, at row-build time during `set_worktrees()`, the widget may not have been laid out yet (first call). A safe fallback: use a generous default width (e.g., 60) when `self.size.width == 0`. Phase 10's periodic rebuild will recompute with actual width. [ASSUMED: timing behavior]

### VerticalScroll Behavior
- `VerticalScroll` defaults to `can_focus=True` [VERIFIED: runtime check]
- It inherits from `ScrollableContainer` -> `Widget` [VERIFIED: MRO inspection]
- Does NOT override `mount()` or `remove_children()` [VERIFIED: `'mount' not in VerticalScroll.__dict__`]
- Scroll position resets when children are replaced (this is fine for Phase 9; Phase 10 will need cursor preservation) [ASSUMED: standard Textual behavior]

### Static.update() for Content Replacement
```python
# [VERIFIED: inspect.signature]
Static.update(content: VisualType = '', *, layout: bool = True) -> None
```
Used to replace the "Loading..." placeholder content, or for in-place row updates. The `layout=True` default triggers a layout recalculation.

## Path Abbreviation & Middle-Truncation

### Home Directory Abbreviation (D-13)
```python
# Pure function, no edge cases beyond D-13's spec:
from pathlib import Path

def abbreviate_home(path_str: str) -> str:
    """Replace leading home directory with ~."""
    home = str(Path.home())
    if path_str.startswith(home):
        return "~" + path_str[len(home):]
    return path_str
```
**Edge case:** `Path.home()` returns the home directory without trailing slash (e.g., `/Users/pieter`). If `path_str` is exactly the home directory, the result is `~` (no trailing slash). If the path is `/Users/pieterx`, it won't match because `startswith` checks the full prefix. This is correct behavior. [VERIFIED: `str(Path.home())` returns no trailing slash]

### Middle-Truncation (D-14)
D-14 specifies: preserve `~/first-segment/` and `/last-segment`, replace middle with `...`. Implementation:

```python
def middle_truncate(path: str, max_width: int) -> str:
    """Truncate path in the middle with ellipsis if wider than max_width."""
    if len(path) <= max_width:
        return path
    # Split into segments
    parts = path.split("/")
    if len(parts) <= 3:
        # Too few segments to middle-truncate meaningfully
        # Fall back to right-truncation
        return path[:max_width - 1] + "\u2026"
    # Keep first segment (~/prefix) and last segment
    head = parts[0] + "/" + parts[1]  # e.g., "~/Github"
    tail = parts[-1]                   # e.g., "feature-branch"
    ellipsis = "/\u2026/"
    if len(head) + len(ellipsis) + len(tail) > max_width:
        # Even head + ... + tail doesn't fit; right-truncate
        return path[:max_width - 1] + "\u2026"
    return head + ellipsis + tail
```
**Note:** The `\u2026` character (horizontal ellipsis) is 1 cell wide, matching D-14's description. Using a single Unicode ellipsis is preferable to three dots (`...`) for space efficiency. [ASSUMED: style choice for planner]

## Common Pitfalls

### Pitfall 1: VerticalScroll Stealing Focus
**What goes wrong:** If the inner `VerticalScroll` has `can_focus=True` (its default), Tab cycling may focus the scroll container instead of the `WorktreePane` parent, causing the border accent to not appear.
**Why it happens:** Textual's focus chain walks the DOM tree and stops at the first focusable widget. VerticalScroll defaults to focusable.
**How to avoid:** Subclass `VerticalScroll` with `can_focus=False`, exactly as `ProjectDetail` does with `_DetailScroll`. [VERIFIED: `_DetailScroll(VerticalScroll, can_focus=False)` in project_detail.py line 12-18]
**Warning signs:** Tab focuses the scroll area but the pane border doesn't turn accent color.

### Pitfall 2: call_from_thread with Async Callable
**What goes wrong:** If `set_worktrees` were an async method, `call_from_thread` would need to handle coroutine scheduling differently.
**Why it happens:** `call_from_thread` accepts both sync and async callables, but the existing pattern uses sync.
**How to avoid:** Keep `set_worktrees` synchronous (it only schedules DOM operations, no I/O). [VERIFIED: existing `_set_projects` is synchronous]
**Warning signs:** TypeError about coroutine, or `set_worktrees` silently not executing.

### Pitfall 3: Widget Size = 0 on First set_worktrees Call
**What goes wrong:** Middle-truncation reads `self.size.width` to determine available space, but on the first call (from `_set_projects` -> `_load_worktrees` -> `set_worktrees`), the widget may not have been laid out yet, yielding width=0.
**Why it happens:** The worker fires during `_set_projects`, which runs during `on_mount`. Layout hasn't happened yet.
**How to avoid:** Default to a generous max width (e.g., 80) when `self.size.width == 0`. Phase 10's refresh will recompute with real width.
**Warning signs:** All paths appear fully truncated or not truncated at all on first render.

### Pitfall 4: CSS Selector Specificity for WorktreeRow vs ObjectRow
**What goes wrong:** If `DEFAULT_CSS` selectors for `WorktreeRow` conflict with `ObjectRow` selectors (e.g., both inherit from `Static`), styling leaks between panes.
**Why it happens:** Textual CSS applies globally based on widget type names.
**How to avoid:** Use specific class names: `WorktreeRow { height: 2; }` not `Static { height: 2; }`. The existing `WorktreePane Static { ... }` selector in the stub is for the placeholder only -- it must be updated or scoped. [VERIFIED: current stub has `WorktreePane Static { ... }` which would apply to ALL Static children including rows]
**Warning signs:** Rows show centered text, or unexpected styling.

### Pitfall 5: Importing GroupHeader Creates Cross-Widget Dependency
**What goes wrong:** `from joy.widgets.project_detail import GroupHeader` in `worktree_pane.py` creates an import dependency between widget modules.
**Why it happens:** GroupHeader is defined in project_detail.py but needed by worktree_pane.py.
**How to avoid:** Either (a) duplicate GroupHeader in worktree_pane.py (simple, ~10 lines), or (b) extract GroupHeader to a shared module (e.g., `widgets/shared.py`), or (c) accept the cross-import. Option (a) is simplest for a 10-line class. [ASSUMED: architecture choice for planner]

### Pitfall 6: Placeholder Static Selector After Rebuild
**What goes wrong:** The Phase 8 stub CSS `WorktreePane Static { content-align: center middle; ... }` would apply to ALL Static widgets inside the pane, including WorktreeRow and GroupHeader after rebuild.
**Why it happens:** The CSS selector is too broad.
**How to avoid:** Replace the Phase 8 placeholder CSS with scoped selectors:
```css
WorktreePane .empty-state { content-align: center middle; color: $text-muted; text-style: dim; }
WorktreePane .worktree-row { height: 2; padding: 0 1; }
WorktreePane .group-header { ... }  /* or reuse GroupHeader class name */
```
[VERIFIED: current stub CSS targets `WorktreePane Static` broadly]

## Code Examples

### WorktreeRow: Two-Line Static with rich.Text
```python
# Source: Derived from ObjectRow pattern (src/joy/widgets/object_row.py)
# and D-07/D-08 specifications
from rich.text import Text
from textual.widgets import Static

ICON_BRANCH = "\ue0a0"     # nf-pl-branch
ICON_DIRTY = "\uf111"       # nf-fa-circle
ICON_NO_UPSTREAM = "\U000f0be1"  # nf-md-cloud_off

class WorktreeRow(Static):
    """Two-line row: branch + indicators on line 1, path on line 2."""
    DEFAULT_CSS = """
    WorktreeRow {
        width: 1fr;
        height: 2;
        padding: 0 1;
    }
    """
    
    @staticmethod
    def _render_text(branch: str, is_dirty: bool, has_upstream: bool, 
                     display_path: str) -> Text:
        t = Text(no_wrap=True, overflow="ellipsis")
        t.append(f" {ICON_BRANCH} ", style="bold")
        t.append(branch)
        if is_dirty:
            t.append(f" {ICON_DIRTY}", style="$warning")
        if not has_upstream:
            t.append(f" {ICON_NO_UPSTREAM}", style="dim")
        t.append("\n")
        t.append(f"  {display_path}", style="dim")
        return t
```

### set_worktrees Idempotent Rebuild
```python
# Source: Derived from ProjectDetail._render_project pattern
def set_worktrees(self, worktrees: list[WorktreeInfo]) -> None:
    scroll = self.query_one("#worktree-scroll")
    scroll.remove_children()
    
    if not worktrees:
        # Empty state (D-15 or D-16)
        scroll.mount(Static("message", classes="empty-state"))
        return
    
    # Group by repo_name, sorted alphabetically (D-11)
    grouped: dict[str, list[WorktreeInfo]] = {}
    for wt in worktrees:
        grouped.setdefault(wt.repo_name, []).append(wt)
    
    for repo_name in sorted(grouped, key=str.lower):
        scroll.mount(GroupHeader(repo_name))
        # Sort worktrees within group by branch (D-12)
        for wt in sorted(grouped[repo_name], key=lambda w: w.branch.lower()):
            path = abbreviate_home(wt.path)
            path = middle_truncate(path, self._get_available_width())
            scroll.mount(WorktreeRow(wt.branch, wt.is_dirty, wt.has_upstream, path))
```

### _load_worktrees Worker in JoyApp
```python
# Source: Mirrors existing _load_data pattern (src/joy/app.py:73-80)
@work(thread=True)
def _load_worktrees(self) -> None:
    from joy.store import load_repos
    from joy.worktrees import discover_worktrees
    repos = load_repos()
    worktrees = discover_worktrees(repos, self._config.branch_filter)
    self.app.call_from_thread(self._set_worktrees, worktrees)

def _set_worktrees(self, worktrees: list[WorktreeInfo]) -> None:
    self.query_one(WorktreePane).set_worktrees(worktrees)
```

### Test Pattern: Asserting on Static Content
```python
# Source: Existing test pattern from test_pane_layout.py:73-76
# For string content:
static = pane.query_one(Static)
assert "coming soon" in str(static.content).lower()

# For rich.Text content (Phase 9 rows):
row = pane.query(WorktreeRow)[0]
plain = str(row.content)  # rich.Text.__str__ returns .plain
assert "feature-branch" in plain
assert "\uf111" in plain  # dirty indicator present
```

### Test Pattern: Mocking Store for Worktree Tests
```python
# Source: Existing mock pattern from test_pane_layout.py:27-30
from unittest.mock import patch
from joy.models import Config, Repo, WorktreeInfo

@pytest.fixture
def mock_store_with_worktrees():
    worktrees = [
        WorktreeInfo(repo_name="joy", branch="feat-x", path="/Users/pieter/Github/joy/wt/feat-x",
                     is_dirty=True, has_upstream=True),
        WorktreeInfo(repo_name="joy", branch="feat-y", path="/Users/pieter/Github/joy/wt/feat-y",
                     is_dirty=False, has_upstream=False),
    ]
    with patch("joy.store.load_projects", return_value=[...]), \
         patch("joy.store.load_config", return_value=Config()), \
         patch("joy.store.load_repos", return_value=[Repo(name="joy", local_path="/Users/pieter/Github/joy")]), \
         patch("joy.worktrees.discover_worktrees", return_value=worktrees):
        yield
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `WorktreePane` shows "coming soon" | Fill with live worktree data | Phase 9 (this phase) | Pane becomes functional |
| No worktree data in UI | GroupHeaders + WorktreeRows | Phase 9 | WKTR-02, WKTR-03 satisfied |

**Deprecated/outdated:**
- The Phase 8 "coming soon" placeholder Static and its broad `WorktreePane Static { ... }` CSS selector must be replaced with scoped selectors.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Widget.size.width may be 0 on first set_worktrees call | Common Pitfalls #3 | Paths render without truncation on first paint; fixed on Phase 10 refresh |
| A2 | VerticalScroll scroll position resets when children are replaced | Textual API Details | Minor: scroll jumps to top on rebuild (acceptable for Phase 9; Phase 10 must handle) |
| A3 | Unicode ellipsis U+2026 preferred over "..." for truncation | Path Abbreviation | Purely aesthetic; either works |
| A4 | GroupHeader can be imported from project_detail.py or duplicated | Common Pitfalls #5 | No runtime risk; only architecture cleanliness concern |

## Open Questions

1. **GroupHeader sharing strategy**
   - What we know: GroupHeader is 10 lines, defined in project_detail.py, needed in worktree_pane.py
   - What's unclear: Whether to import cross-widget, duplicate, or extract to shared module
   - Recommendation: Duplicate in worktree_pane.py (simplest, avoids coupling, 10 lines is trivial)

2. **Exact empty-state detection for D-15 vs D-16**
   - What we know: D-15 = no repos registered (repos=[]), D-16 = repos exist but discover returns []
   - What's unclear: `set_worktrees` receives only the flat list, not the repos list. How to distinguish?
   - Recommendation: Pass an additional signal. Options: (a) add a `repos_count: int` parameter to `set_worktrees`, (b) check `load_repos()` length inside the pane (breaks presentational-only contract), or (c) have `_set_worktrees` in app.py pass the repos count alongside the worktree list. Option (c) is cleanest per D-01's "pane stays purely presentational" principle.

3. **Branch filter display in D-16 empty state**
   - What we know: D-16 says show `"(filtered: {branch_filter})"` with the comma-separated filter list
   - What's unclear: `set_worktrees` receives only the worktree list, not the filter config
   - Recommendation: Same solution as Q2 -- pass `branch_filter` from the app to the pane method, or extend the method signature.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 0.25 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_worktree_pane.py -x -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WKTR-02a | Worktrees grouped under repo section headers | unit | `uv run pytest tests/test_worktree_pane.py::test_grouping_by_repo -x` | Wave 0 |
| WKTR-02b | Repos with no active worktrees are hidden | unit | `uv run pytest tests/test_worktree_pane.py::test_empty_repos_hidden -x` | Wave 0 |
| WKTR-02c | Repo sections ordered alphabetically (D-11) | unit | `uv run pytest tests/test_worktree_pane.py::test_repo_order_alphabetical -x` | Wave 0 |
| WKTR-02d | Worktrees within repo ordered alphabetically (D-12) | unit | `uv run pytest tests/test_worktree_pane.py::test_worktree_order_alphabetical -x` | Wave 0 |
| WKTR-03a | Row line 1 shows branch name | integration | `uv run pytest tests/test_worktree_pane.py::test_row_shows_branch -x` | Wave 0 |
| WKTR-03b | Dirty indicator present when is_dirty=True | unit | `uv run pytest tests/test_worktree_pane.py::test_dirty_indicator_shown -x` | Wave 0 |
| WKTR-03c | No-upstream indicator present when has_upstream=False | unit | `uv run pytest tests/test_worktree_pane.py::test_no_upstream_indicator_shown -x` | Wave 0 |
| WKTR-03d | No indicators when clean + has upstream | unit | `uv run pytest tests/test_worktree_pane.py::test_clean_tracked_no_indicators -x` | Wave 0 |
| WKTR-03e | Row line 2 shows abbreviated path | unit | `uv run pytest tests/test_worktree_pane.py::test_row_shows_abbreviated_path -x` | Wave 0 |
| WKTR-10 | Pane is read-only (no cursor, no activation bindings) | integration | `uv run pytest tests/test_worktree_pane.py::test_pane_read_only -x` | Wave 0 |
| D-01 | App loads worktrees via threaded worker | integration | `uv run pytest tests/test_worktree_pane.py::test_app_loads_worktrees -x` | Wave 0 |
| D-05 | Loading... placeholder shown before data arrives | integration | `uv run pytest tests/test_worktree_pane.py::test_loading_placeholder -x` | Wave 0 |
| D-13 | Path abbreviation replaces home dir with ~ | unit | `uv run pytest tests/test_worktree_pane.py::test_path_abbreviation -x` | Wave 0 |
| D-14 | Middle-truncation for long paths | unit | `uv run pytest tests/test_worktree_pane.py::test_middle_truncation -x` | Wave 0 |
| D-15 | Empty state: no repos registered | integration | `uv run pytest tests/test_worktree_pane.py::test_empty_state_no_repos -x` | Wave 0 |
| D-16 | Empty state: repos exist but no worktrees | integration | `uv run pytest tests/test_worktree_pane.py::test_empty_state_no_worktrees -x` | Wave 0 |
| D-03 | set_worktrees is idempotent (call twice, same result) | unit | `uv run pytest tests/test_worktree_pane.py::test_set_worktrees_idempotent -x` | Wave 0 |
| REGRESSION | Existing 197 tests remain green | regression | `uv run pytest -q` | Existing |

### Test Strategy Notes

**Unit tests (pure function, no Textual app):**
- Path abbreviation (`abbreviate_home`)
- Middle-truncation (`middle_truncate`)
- Row text rendering (`WorktreeRow._render_text`) -- assert on `rich.Text.plain` content and span styles
- Grouping/ordering logic if extracted as a pure function

**Integration tests (Textual pilot, async):**
- App startup populates worktree pane (mock `discover_worktrees` + `load_repos`)
- Empty states render correct messages
- Loading placeholder visible before worker completes
- Row content visible in mounted pane
- Pane remains focusable via Tab (regression from Phase 8)

**Test assertion patterns for rich.Text content:**
```python
# Assert on plain text content (codepoints visible as characters)
row = pane.query(WorktreeRow)[0]
plain = str(row.content)  # calls Text.__str__() -> .plain
assert "feature-branch" in plain
assert "\uf111" in plain  # dirty icon present

# Assert on styled spans
text = row.content  # rich.Text object
spans = list(text._spans)
# Find span covering the dirty icon and check its style
```

**Mocking strategy for integration tests:**
```python
# Mock at the module level (joy.store, joy.worktrees) as done in existing tests
# Key mocks needed:
# - joy.store.load_projects -> list[Project]
# - joy.store.load_config -> Config
# - joy.store.load_repos -> list[Repo]
# - joy.worktrees.discover_worktrees -> list[WorktreeInfo]
```

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_worktree_pane.py -x -q`
- **Per wave merge:** `uv run pytest -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_worktree_pane.py` -- all Phase 9 unit and integration tests (new file)
- [ ] No new framework install needed (pytest + pytest-asyncio already configured)
- [ ] No new conftest fixtures needed beyond what each test file defines locally (following existing pattern)

## Sources

### Primary (HIGH confidence)
- Textual 8.2.3 installed version -- Widget.remove_children, Widget.mount, Static.update, Static.content, VerticalScroll.can_focus, @work decorator signatures all verified via `inspect.signature` and runtime tests
- `src/joy/widgets/project_detail.py` -- GroupHeader pattern (lines 50-61), _render_project rebuild pattern (lines 128-171), _DetailScroll non-focusable scroll pattern (lines 12-18)
- `src/joy/widgets/object_row.py` -- Nerd Font icon constants (lines 10-19), single-Static row pattern
- `src/joy/app.py` -- @work(thread=True) + call_from_thread pattern (lines 73-80), _set_projects call site (lines 82-89)
- `src/joy/models.py` -- WorktreeInfo dataclass (lines 136-144), Config.branch_filter (line 100-102)
- `rich.cells.cell_len` -- verified all icon codepoints are 1 cell wide
- [Nerd Fonts cheat sheet](https://www.nerdfonts.com/cheat-sheet) -- nf-fa-circle U+F111, nf-md-cloud_off U+F0BE1

### Secondary (MEDIUM confidence)
- Widget.content_region.width for inner width calculation -- docstring confirmed "minus padding and border"
- `Path.home()` returns no trailing slash -- standard Python behavior verified

### Tertiary (LOW confidence)
- None -- all claims verified against installed code or official APIs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all APIs verified against installed Textual 8.2.3
- Architecture: HIGH -- directly mirrors existing ProjectDetail pattern already in production
- Pitfalls: HIGH -- all derived from verified API behavior and existing code patterns
- Nerd Font codepoints: HIGH -- verified via runtime cell_len tests and Nerd Fonts cheat sheet

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable -- Textual 8.x API unlikely to break in patch releases)
