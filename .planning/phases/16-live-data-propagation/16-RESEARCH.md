# Phase 16: Live Data Propagation - Research

**Researched:** 2026-04-15
**Domain:** Background data mutation (MR auto-add, agent stale marking) in a Textual TUI with TOML persistence
**Confidence:** HIGH

## Summary

Phase 16 adds two propagation behaviors to the existing background refresh cycle: (1) auto-adding MR ObjectItems to projects when a worktree's MRInfo matches a project's BRANCH object, and (2) marking/unmarking AGENTS ObjectItems as stale based on iTerm2 session presence. PROP-01 and PROP-03 (worktree object management) are explicitly dropped per D-01 in CONTEXT.md.

The implementation is constrained to a narrow surface: a new `_propagate_changes()` method on `JoyApp` called from `_maybe_compute_relationships()` after the RelationshipIndex is computed. All data needed for propagation is already available on the main thread (`self._current_worktrees`, `self._current_sessions`, `self._projects`, `self._repos`, and the freshly-computed `self._rel_index`). The MR data dict `(repo_name, branch) -> MRInfo` is passed through `_set_worktrees()` and needs to be stored on the app instance for propagation to access.

**Primary recommendation:** Implement `_propagate_changes(mr_data)` as a synchronous method on JoyApp that runs after `_maybe_compute_relationships()` on the main thread. Collect all mutations, call `_save_projects_bg()` once if any project was modified, emit `self.notify()` per mutation, then rebuild the project list and detail pane. Add `stale: bool = False` to ObjectItem (runtime-only, excluded from `to_dict()`). Apply `--stale` CSS class on ObjectRow during ProjectDetail rendering.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** PROP-01 (auto-remove gone worktree TOML objects) and PROP-03 (move worktree objects between projects) are dropped entirely. Worktrees are dynamic live data -- the WorktreePane handles their display. No new WORKTREE ObjectItems will be auto-created by propagation. Existing WORKTREE ObjectItems in projects.toml are left in place.
- **D-02:** MR auto-add: When a worktree has MRInfo and the owning project has a BRANCH object matching the worktree's branch, check if the project already has an MR ObjectItem with the same URL. If not found, append a new ObjectItem: `kind=MR, value=mr_info.url, label="PR #{mr_info.mr_number}", open_by_default=False`.
- **D-03:** Duplicate check is by URL equality only -- same PR URL already existing as any MR ObjectItem skips. Different PRs (different URLs) are always appended.
- **D-04:** MR objects are auto-added but never auto-removed (PROP-07). Even if the PR closes, the MR object stays.
- **D-05:** Projects with no `repo` field are excluded from MR propagation (PROP-08).
- **D-06:** Agent stale marking: compare current iTerm2 sessions to AGENTS-kind ObjectItems across all projects. Absent session_name = stale. Reappeared = cleared. Stale state is in-memory only, never written to projects.toml.
- **D-07:** Stale state lives as a runtime flag on ObjectItem: `stale: bool = False` field (not serialized by `to_dict()`, not loaded from TOML).
- **D-08:** Stale visual: a CSS class `--stale` on ObjectRow dims the text color and italicizes the value column. Applied when `item.stale` is True, removed when False.
- **D-09:** "Workers discover, main thread mutates" -- propagation logic runs on the main thread, called from `_maybe_compute_relationships()` or a new `_propagate_changes()` method called immediately after.
- **D-10:** All mutations in a single refresh cycle are collected first, then `_save_projects_bg()` is called once per cycle.
- **D-11:** When propagation changes something, emit a brief status bar message. Silent when nothing changes.
- **D-12:** After propagation mutates `_projects`, call `project_list.set_projects(self._projects, self._repos)` then re-trigger detail view via existing `set_project()` path.

### Claude's Discretion
- Exact Python data structure for stale agent tracking (set of session names, dict keyed by project+value, etc.)
- Whether stale clearing is a separate method or folded into `_propagate_changes()`
- Whether `_propagate_changes()` is a new method or logic inlined into `_maybe_compute_relationships()`
- CSS specifics for `--stale` appearance (exact color values, which columns are affected)
- Whether auto-added MR objects get `open_by_default=True` or `False` (recommend False)

### Deferred Ideas (OUT OF SCOPE)
- **PROP-01** (auto-remove gone worktree TOML objects) -- dropped
- **PROP-03** (move worktree objects between projects) -- dropped
- **PROP-09** (auto-remove MR when PR closes) -- deferred to v1.3+
- **PROP-10** (undo for auto-mutations) -- deferred to v1.3+
- **SYNC-10** (sync toggle persistence) -- deferred to v1.3+
- **PERF-01** (real-time file watching) -- 30s refresh sufficient for v1.2
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROP-01 | Auto-remove gone worktree objects after 2+ missing refreshes | DROPPED per D-01 -- WorktreePane handles display live |
| PROP-02 | Auto-add MR object when detected for project's branch | MR auto-add pattern: match via RelationshipIndex + mr_data dict; URL dedup; append ObjectItem |
| PROP-03 | Move worktree objects between projects when branch changes | DROPPED per D-01 -- WorktreePane handles display live |
| PROP-04 | Mark agent objects stale when session absent from iTerm2 | Stale flag on ObjectItem + CSS class on ObjectRow; session name set comparison |
| PROP-05 | Clear stale marker when agent session reappears | Same stale propagation pass clears stale when session found in current set |
| PROP-06 | Branch objects never modified by propagation | Propagation only touches MR-kind objects (append) and AGENTS-kind objects (stale flag); branches excluded by design |
| PROP-07 | MR objects auto-added but never auto-removed | Only append path; no deletion logic for MR objects |
| PROP-08 | Projects without repo excluded from all propagation | Guard check `project.repo is not None` before MR propagation |
</phase_requirements>

## Standard Stack

No new libraries needed. Phase 16 uses only the existing project stack.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| textual | ^8.2 | TUI framework (CSS classes, widgets, `notify()`) | Already installed; provides `add_class`/`remove_class` for stale styling |
| tomli_w | ^1.0 | TOML writing via `_save_projects_bg()` | Already installed; atomic write path established |

### Supporting
No additional dependencies. All propagation logic is pure Python operating on existing data structures.

## Architecture Patterns

### Recommended Changes Structure
```
src/joy/
  models.py          # Add stale: bool = False to ObjectItem (not serialized)
  app.py             # Add _propagate_changes() method, store mr_data, call from _maybe_compute_relationships
  widgets/
    object_row.py    # Apply --stale CSS class based on item.stale
    project_detail.py  # Apply --stale during row construction in _render_project
```

### Pattern 1: MR Auto-Add (PROP-02)
**What:** After RelationshipIndex is computed, scan worktrees that have MRInfo and check if their owning project already has an MR object with the same URL.
**When to use:** Every refresh cycle where `_worktrees_ready` and `_sessions_ready` are both True.
**How it works:**

```python
# Source: CONTEXT.md D-02, D-03, D-05 [VERIFIED: codebase analysis]
def _propagate_mr_auto_add(self, mr_data: dict) -> list[str]:
    """Auto-add MR objects for detected PRs. Returns list of notification messages."""
    messages = []
    if not mr_data or self._rel_index is None:
        return messages

    for (repo_name, branch), mr_info in mr_data.items():
        if not mr_info.url:
            continue
        # Find the project that owns this worktree via branch match
        # Need to find the project with a BRANCH object matching (repo_name, branch)
        for project in self._projects:
            if project.repo is None:
                continue  # D-05: skip projects without repo
            if project.repo != repo_name:
                continue
            # Check if project has a BRANCH object matching this branch
            has_branch = any(
                obj.kind == PresetKind.BRANCH and obj.value == branch
                for obj in project.objects
            )
            if not has_branch:
                continue
            # D-03: Duplicate check by URL
            already_has_mr = any(
                obj.kind == PresetKind.MR and obj.value == mr_info.url
                for obj in project.objects
            )
            if already_has_mr:
                continue
            # D-02: Append new MR object
            new_mr = ObjectItem(
                kind=PresetKind.MR,
                value=mr_info.url,
                label=f"PR #{mr_info.mr_number}",
                open_by_default=False,
            )
            project.objects.append(new_mr)
            messages.append(f"Added PR #{mr_info.mr_number} to {project.name}")
    return messages
```

### Pattern 2: Agent Stale Marking (PROP-04, PROP-05)
**What:** Compare current iTerm2 sessions against AGENTS ObjectItems across all projects. Set `stale=True` when session name is absent; clear when present.
**When to use:** Every refresh cycle, after sessions are loaded.

```python
# Source: CONTEXT.md D-06, D-07 [VERIFIED: codebase analysis]
def _propagate_agent_stale(self) -> list[str]:
    """Mark/unmark agent objects as stale. Returns notification messages."""
    messages = []
    # Build set of active session names
    active_sessions = {s.session_name for s in self._current_sessions}

    for project in self._projects:
        for obj in project.objects:
            if obj.kind != PresetKind.AGENTS:
                continue
            was_stale = getattr(obj, 'stale', False)
            is_now_absent = obj.value not in active_sessions
            obj.stale = is_now_absent
            if is_now_absent and not was_stale:
                messages.append(f"Agent '{obj.value}' offline in {project.name}")
            elif not is_now_absent and was_stale:
                messages.append(f"Agent '{obj.value}' back online in {project.name}")
    return messages
```

### Pattern 3: Store `mr_data` on App Instance
**What:** The `mr_data` dict is currently passed through `_set_worktrees()` to `WorktreePane.set_worktrees()` but not stored on the app. Propagation needs it.
**Implementation:**

```python
# In JoyApp.__init__:
self._current_mr_data: dict = {}

# In _set_worktrees:
self._current_mr_data = mr_data or {}
```

### Pattern 4: _is_syncing Guard During Propagation Pane Rebuilds
**What:** When propagation calls `project_list.set_projects()` and `detail.set_project()`, these trigger DOM rebuilds that may fire cursor messages. The `_is_syncing` guard must be active during these rebuilds to prevent spurious sync operations.
**Source:** Phase 15 CONTEXT.md established this pattern; already used in `_set_worktrees()` and `_set_terminal_sessions()`.

```python
# Source: Phase 15 D-03, already in app.py [VERIFIED: codebase]
self._is_syncing = True
try:
    project_list.set_projects(self._projects, self._repos)
    # Re-trigger detail for current project
    if project_list._cursor >= 0:
        current = project_list._rows[project_list._cursor].project
        self.query_one(ProjectDetail).set_project(current)
finally:
    self._is_syncing = False
```

### Pattern 5: ObjectItem.stale Field (Runtime-Only)
**What:** Add `stale: bool = False` to ObjectItem dataclass. Must NOT appear in `to_dict()`.

```python
# Source: CONTEXT.md D-07 [VERIFIED: models.py analysis]
@dataclass
class ObjectItem:
    kind: PresetKind
    value: str
    label: str = ""
    open_by_default: bool = False
    stale: bool = False  # Runtime-only; not serialized

    def to_dict(self) -> dict:
        # Existing code -- stale is intentionally excluded
        return {
            "kind": self.kind.value,
            "value": self.value,
            "label": self.label,
            "open_by_default": self.open_by_default,
        }
```

### Pattern 6: --stale CSS Class on ObjectRow
**What:** Apply CSS class to ObjectRow when `item.stale` is True. The CSS dims text and italicizes the value column.

```python
# In project_detail.py _render_project, after creating row:
if item.stale:
    row.add_class("--stale")
```

```css
/* In ObjectRow DEFAULT_CSS or ProjectDetail DEFAULT_CSS */
ObjectRow.--stale .col-value {
    text-style: italic;
    color: $text-muted;
}
ObjectRow.--stale .col-icon {
    color: $text-muted;
}
ObjectRow.--stale .col-kind {
    text-style: italic;
}
```

### Anti-Patterns to Avoid
- **Mutating `_projects` from a background thread:** All mutations must happen on the main thread (D-09). Background workers only discover data; main thread mutates. Violating this causes TOML corruption or race conditions with Textual's widget tree.
- **Calling `_save_projects_bg()` per mutation:** Batch all mutations in a cycle, then call once (D-10). Multiple atomic writes per cycle cause unnecessary I/O and potential partial-state serialization.
- **Auto-removing MR objects:** PROP-07 explicitly forbids this. Even if a PR closes, the MR object stays.
- **Touching branch objects:** PROP-06 -- branch objects are user-curated and sacred. Propagation must never modify, add, or remove branch objects.
- **Writing stale state to TOML:** D-07 -- stale is in-memory only. If `to_dict()` serializes it, every refresh cycle would dirty projects.toml unnecessarily.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic TOML writes | Custom file locking | `_save_projects_bg()` via `store._atomic_write()` | Already handles temp file + os.replace; battle-tested |
| Session set comparison | Custom tracking data structure | Simple `set()` of session names from `self._current_sessions` | O(1) lookup, trivial to build from existing data |
| CSS conditional styling | Inline rich.Text style manipulation | Textual CSS class `--stale` via `add_class()`/`remove_class()` | Follows established `--highlight` pattern exactly |
| Duplicate MR detection | Hash-based dedup tracker | Simple `any()` over project.objects checking URL equality | Small list (<20 objects per project); linear scan is fine |

## Common Pitfalls

### Pitfall 1: Stale Flag Lost on TOML Round-Trip
**What goes wrong:** ObjectItem is loaded from TOML, which doesn't have `stale`. If `__init__` requires it or if there's no default, loading fails.
**Why it happens:** `stale: bool = False` is a runtime field not persisted. But `_toml_to_projects()` in `store.py` constructs ObjectItem explicitly -- it won't pass `stale` because TOML doesn't have it.
**How to avoid:** Ensure `stale` has a default value (`False`) in the dataclass. The existing `_toml_to_projects` function constructs ObjectItem with keyword arguments it finds in the TOML; unrecognized fields are ignored; missing fields use defaults. This works because `stale=False` is the correct default.
**Warning signs:** KeyError or TypeError when loading projects after adding the stale field.

### Pitfall 2: Sync Loop During Propagation Pane Rebuild
**What goes wrong:** Propagation calls `set_projects()` and `set_project()`, which trigger DOM rebuilds, which fire cursor messages, which trigger sync handlers, which mutate other panes, creating a cascade.
**Why it happens:** The `_is_syncing` guard from Phase 15 prevents this -- but only if it's set before the rebuild calls.
**How to avoid:** Wrap all pane rebuild calls in `self._is_syncing = True / try / finally / self._is_syncing = False`. This is the established pattern from `_set_worktrees()` and `_set_terminal_sessions()`.
**Warning signs:** Infinite loop, stack overflow, or cursor jumping unexpectedly after a refresh cycle.

### Pitfall 3: MR Auto-Add Duplicates on Every Refresh
**What goes wrong:** If the duplicate check doesn't work correctly, a new MR object is appended on every refresh cycle, creating dozens of duplicate entries.
**Why it happens:** URL comparison is case-sensitive or the URL format changes between refreshes (e.g., trailing slash).
**How to avoid:** D-03 specifies URL equality check. The `mr_info.url` comes from `gh`/`glab` CLI which returns consistent URLs. Test with explicit duplicate scenarios.
**Warning signs:** projects.toml growing rapidly; multiple identical MR objects in project detail.

### Pitfall 4: _save_projects_bg() Race with Next Cycle
**What goes wrong:** The background save from cycle N hasn't finished when cycle N+1 starts another save, potentially writing stale data.
**Why it happens:** `@work(thread=True)` fires and forgets; Textual doesn't queue workers.
**How to avoid:** This is already mitigated by the atomic write pattern in `store.py` (temp file + `os.replace`). The last write wins, which is correct since each save serializes the full project list. No additional locking needed.
**Warning signs:** Lost mutations (an auto-added MR disappears after the next cycle). Unlikely in practice due to atomic writes.

### Pitfall 5: Notifying for Every Stale Toggle on Every Cycle
**What goes wrong:** If an agent session is absent for 10 consecutive cycles, the user gets 10 "offline" notifications.
**Why it happens:** Not checking whether stale state actually changed.
**How to avoid:** Compare `was_stale` with `is_now_absent` and only notify on transitions (False->True or True->False). The code pattern above already handles this.
**Warning signs:** Spam of identical notification messages on each refresh.

### Pitfall 6: Stale Marking Persists Across Project Detail Navigations
**What goes wrong:** User navigates to a different project, then back -- stale state is lost because `set_project()` rebuilds rows from scratch.
**Why it happens:** The stale flag lives on the ObjectItem instance in `self._projects`. As long as the same ObjectItem instances are reused (not recreated), stale state persists. ProjectDetail.set_project() iterates project.objects directly, so the same ObjectItem instances (with their stale flags) are used.
**How to avoid:** This is naturally correct because `_projects` holds the canonical ObjectItem instances. The stale flag is set on these instances, and `_render_project()` reads from the same instances. No extra work needed.
**Warning signs:** Stale visual disappearing when switching projects and returning.

## Code Examples

### Complete _propagate_changes() Method

```python
# Source: synthesis of D-02, D-06, D-09, D-10, D-11, D-12 [VERIFIED: codebase analysis]
def _propagate_changes(self, mr_data: dict) -> None:
    """Run propagation logic after RelationshipIndex is computed (D-09).

    Main-thread only. Collects all mutations, saves once, notifies per change.
    """
    messages: list[str] = []

    # 1. MR auto-add (PROP-02)
    messages.extend(self._propagate_mr_auto_add(mr_data))

    # 2. Agent stale marking (PROP-04, PROP-05)
    messages.extend(self._propagate_agent_stale())

    # 3. Batch save if any TOML-persistent mutations occurred (D-10)
    mr_added = any("Added PR" in m for m in messages)
    if mr_added:
        self._save_projects_bg()

    # 4. Notify per mutation (D-11)
    for msg in messages:
        self.notify(msg, markup=False)

    # 5. Rebuild panes if anything changed (D-12)
    if messages:
        self._is_syncing = True
        try:
            project_list = self.query_one(ProjectList)
            project_list.set_projects(self._projects, self._repos)
            # Re-render active project detail to reflect stale or new MR objects
            if project_list._cursor >= 0 and project_list._cursor < len(project_list._rows):
                current = project_list._rows[project_list._cursor].project
                self.query_one(ProjectDetail).set_project(current)
        finally:
            self._is_syncing = False
```

### Integration Point in _maybe_compute_relationships()

```python
# Source: existing app.py line 218-237 + D-09 [VERIFIED: codebase]
def _maybe_compute_relationships(self) -> None:
    if not (self._worktrees_ready and self._sessions_ready):
        return
    self._worktrees_ready = False
    self._sessions_ready = False
    from joy.resolver import compute_relationships
    self._rel_index = compute_relationships(
        self._projects,
        self._current_worktrees,
        self._current_sessions,
        self._repos,
    )
    self._update_badges()
    # Phase 16: propagate MR auto-add and agent stale marking
    self._propagate_changes(self._current_mr_data)
```

### ObjectRow Stale Styling in ProjectDetail._render_project()

```python
# Source: D-08 [VERIFIED: project_detail.py analysis]
# In the row creation loop of _render_project():
for item in group_items:
    row = ObjectRow(item, index=row_index)
    if getattr(item, 'stale', False):
        row.add_class("--stale")
    scroll.mount(row)
    new_rows.append(row)
    row_index += 1
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual MR object creation | Auto-add MR when detected via gh/glab CLI | Phase 16 (this phase) | Users no longer need to manually add PR links |
| No stale indication for agents | Visual dimming when iTerm2 session absent | Phase 16 (this phase) | Immediate visibility of which agent sessions are still alive |

**Nothing deprecated:** This phase only adds new behavior; existing patterns are preserved.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `mr_info.url` from gh/glab CLI returns consistent, stable URLs (no trailing slash variation) | Common Pitfalls / Pitfall 3 | Duplicate MR objects on each refresh if URL format changes between calls |
| A2 | Textual CSS `text-style: italic` works on Static widgets containing Text objects | Pattern 6 | Stale visual would not render correctly; fallback: use dim color only |

All other claims are verified from codebase analysis or are direct copies of locked decisions from CONTEXT.md.

## Open Questions

1. **Should stale agent notifications use a specific icon prefix?**
   - What we know: D-11 shows format examples with bullet icons (e.g., `Agent 'claude-code' offline in joy`)
   - What's unclear: The exact Unicode symbol. The examples use `\u25cf` (BLACK CIRCLE) prefix.
   - Recommendation: Use the same format as shown in D-11. This is a cosmetic detail within Claude's discretion.

2. **Should `_propagate_changes()` rebuild panes even when only stale state changed?**
   - What we know: Stale state is runtime-only (no TOML write needed). But the visual (CSS class) requires ObjectRow to have `--stale` class.
   - What's unclear: Whether existing rows in ProjectDetail automatically reflect stale changes, or if a re-render is needed.
   - Recommendation: Re-render the detail pane on any change (stale or MR add). The `set_project()` call is cheap (< 10 rows typically) and guarantees correctness. Only skip if messages list is empty (nothing changed).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio 0.25 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_propagation.py -x` |
| Full suite command | `uv run pytest -m "not slow and not macos_integration"` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROP-02 | MR auto-added when detected for project's branch | unit | `uv run pytest tests/test_propagation.py::test_mr_auto_add -x` | Wave 0 |
| PROP-02 | MR not added when URL already exists (dedup) | unit | `uv run pytest tests/test_propagation.py::test_mr_dedup -x` | Wave 0 |
| PROP-04 | Agent marked stale when session absent | unit | `uv run pytest tests/test_propagation.py::test_agent_stale_mark -x` | Wave 0 |
| PROP-05 | Agent stale cleared when session reappears | unit | `uv run pytest tests/test_propagation.py::test_agent_stale_clear -x` | Wave 0 |
| PROP-06 | Branch objects never modified by propagation | unit | `uv run pytest tests/test_propagation.py::test_branch_never_modified -x` | Wave 0 |
| PROP-07 | MR objects never auto-removed | unit | `uv run pytest tests/test_propagation.py::test_mr_never_removed -x` | Wave 0 |
| PROP-08 | Projects without repo excluded | unit | `uv run pytest tests/test_propagation.py::test_no_repo_excluded -x` | Wave 0 |
| PROP-04 | Stale state not serialized to TOML | unit | `uv run pytest tests/test_propagation.py::test_stale_not_in_toml -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_propagation.py -x`
- **Per wave merge:** `uv run pytest -m "not slow and not macos_integration"`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_propagation.py` -- covers PROP-02, PROP-04, PROP-05, PROP-06, PROP-07, PROP-08
- No framework install needed (pytest already configured)
- Conftest fixtures reusable; may need new helper fixtures for MRInfo and session sets

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `src/joy/app.py` -- refresh coordination, `_maybe_compute_relationships()`, `_save_projects_bg()`, `_is_syncing` guard
- Codebase analysis: `src/joy/models.py` -- ObjectItem dataclass, `to_dict()` serialization
- Codebase analysis: `src/joy/resolver.py` -- RelationshipIndex API, `compute_relationships()` function
- Codebase analysis: `src/joy/widgets/object_row.py` -- ObjectRow widget, CSS class pattern
- Codebase analysis: `src/joy/widgets/project_detail.py` -- `_render_project()` row construction
- Codebase analysis: `src/joy/store.py` -- `_atomic_write()`, `_projects_to_toml()`, `save_projects()`
- Codebase analysis: `src/joy/mr_status.py` -- `fetch_mr_data()` returns `dict[tuple[str, str], MRInfo]`
- Phase 14 CONTEXT.md -- D-07/D-08: refresh coordination pattern
- Phase 15 CONTEXT.md -- D-03: `_is_syncing` guard pattern
- Phase 16 CONTEXT.md -- D-01 through D-12: all locked decisions

### Secondary (MEDIUM confidence)
- Textual CSS class system: `add_class()`/`remove_class()` pattern verified from 6+ call sites in codebase [VERIFIED: codebase grep]
- Textual `text-style: italic` CSS property [ASSUMED: based on Textual CSS documentation knowledge]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries; all existing
- Architecture: HIGH -- all integration points verified in codebase; data flow fully mapped
- Pitfalls: HIGH -- identified from codebase analysis of existing refresh/sync patterns
- Stale CSS: MEDIUM -- `text-style: italic` assumed from Textual CSS knowledge; may need verification

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (stable codebase; no external dependency changes expected)
