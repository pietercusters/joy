# Quick Task 260416-m39: Projects Overview Icon Ribbon + MR Status - Research

**Researched:** 2026-04-16
**Domain:** Textual Static widget, Rich.Text layout, Project model extension, TOML persistence
**Confidence:** HIGH — all findings sourced directly from codebase inspection

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Icon row layout: Rich.Text with padding — name left-aligned, icons right-aligned, name truncates with "…" when narrow. Same pattern as WorktreeRow (single DOM node, no extra containers). Content width derived from widget's `content_region.width` at render time.
- MR data source: live API data only, `_current_mr_data` keyed by `(repo_name, branch)`. Active branch via `rel_index`. Fallback chain: worktree-linked branch MR → highest-numbered open MR for project's repo → latest closed MR.
- Project status persistence: add `status: str = "idle"` to `Project` dataclass. Three states: prio (green ●), hold (dim ●), idle (dim ○). Cycle order: idle → prio → hold → idle. Keyboard shortcut `g` in ProjectList.
- Spacer rows between repo sections (`.section-spacer` pattern from WorktreePane).

### Claude's Discretion
- Icon constants centralization (shared module vs. import from worktree_pane)
- Exact icon characters for ticket, thread, note, terminal, worktree
- MR closed/merged icon choice
- How MR data is passed from app to ProjectList

### Deferred Ideas (OUT OF SCOPE)
- None specified
</user_constraints>

---

## Finding 1: Rich.Text Right-Alignment in ProjectRow

**Pattern used in WorktreeRow:** `build_content()` is a `@staticmethod` that receives `display_path: str` as a parameter — width is computed by the *caller* (`WorktreePane.set_worktrees`) via `self._get_available_width()` which reads `self.content_region.width`. Width is not read inside the row itself.

**For ProjectRow:** The same approach should be used. `ProjectRow._build_content()` currently returns a plain `str`. It needs to:
1. Accept `avail_width: int` as a parameter (or let `ProjectList._rebuild()` compute it and pass it in)
2. Return `rich.Text` (not str — `Static.update()` accepts both, `Text` is needed for styled segments)
3. Compute padding: `pad = max(0, avail_width - len(status_dot) - 1 - len(name) - len(mr_strip) - len(icon_ribbon))`

**Width reading pattern from WorktreePane (VERIFIED: codebase):**
```python
def _get_available_width(self) -> int:
    width = self.content_region.width
    if width == 0:
        return 80  # safe default when widget not yet laid out
    return max(width - 2, 20)  # subtract 2 for border, floor at 20
```

**ProjectList** has `padding: 0 1` on ProjectRow (not a border), so subtract 2 for the left+right padding.

**Key point:** `content_region.width` is available on any mounted widget at render time. Reading it from `ProjectList` (the container, not the row) is correct — the row's own content_region may not yet be settled when `_build_content()` first runs. Pass width from `_rebuild()` to row constructor, and also into `set_counts()` / a new `refresh_content(avail_width)` method for badge updates.

**Row layout formula (left-to-right, Rich.Text segments):**
```
[status-dot] [space] [project-name] [padding spaces] [MR-strip (if any)] [space] [icon-ribbon]
```
Name truncates with "…" when `avail_width - fixed_right_width - 2 < len(name)`.

---

## Finding 2: Icon Constants — What Exists vs. What's Needed

### Already defined in `worktree_pane.py` [VERIFIED: codebase]
```python
ICON_BRANCH    = "\ue0a0"   # nf-pl-branch
ICON_DIRTY     = "\uf111"   # nf-fa-circle
ICON_NO_UPSTREAM = "\U000f0be1"
ICON_MR_OPEN   = "\uea64"   # nf-cod-git_pull_request
ICON_MR_DRAFT  = "\uebdb"   # nf-cod-git_pull_request_draft
ICON_CI_PASS   = "\uf00c"   # nf-fa-check
ICON_CI_FAIL   = "\uf00d"   # nf-fa-times
ICON_CI_PENDING = "\uf192"  # nf-fa-dot_circle_o
```

### Already defined in `object_row.py` as `PRESET_ICONS` [VERIFIED: codebase]
```python
PRESET_ICONS = {
    PresetKind.BRANCH:    "\ue0a0",   # nf-pl-branch (same as ICON_BRANCH)
    PresetKind.TICKET:    "\uf0ea",   # nf-fa-clipboard
    PresetKind.THREAD:    "\uf086",   # nf-fa-comment
    PresetKind.NOTE:      "\uf040",   # nf-fa-pencil
    PresetKind.WORKTREE:  "\uf07b",   # nf-fa-folder
    PresetKind.TERMINALS: "\uf120",   # nf-fa-terminal
    # ...others
}
```

### What's needed for icon ribbon
The 6-slot ribbon (branch, ticket, thread, note, terminal, worktree) uses:
- `PRESET_ICONS[PresetKind.BRANCH]` = "\ue0a0"
- `PRESET_ICONS[PresetKind.TICKET]` = "\uf0ea"
- `PRESET_ICONS[PresetKind.THREAD]` = "\uf086"
- `PRESET_ICONS[PresetKind.NOTE]` = "\uf040"
- `PRESET_ICONS[PresetKind.TERMINALS]` = "\uf120"
- `PRESET_ICONS[PresetKind.WORKTREE]` = "\uf07b"

All of these already exist in `PRESET_ICONS`. No new icon codepoints needed for the ribbon.

### Recommendation: create `src/joy/widgets/icons.py`
[ASSUMED] that a shared module is cleaner than cross-importing between widget files. The duplication of `ICON_BRANCH` between `worktree_pane.py` and `object_row.py` (same codepoint) confirms the need.

**Proposed `icons.py`:**
```python
# MR/CI status icons (from worktree_pane)
ICON_MR_OPEN    = "\uea64"
ICON_MR_DRAFT   = "\uebdb"
ICON_MR_CLOSED  = "\uea65"  # nf-cod-git_pull_request_closed — for merged/closed state
ICON_CI_PASS    = "\uf00c"
ICON_CI_FAIL    = "\uf00d"
ICON_CI_PENDING = "\uf192"
# Branch/status icons (from worktree_pane)
ICON_BRANCH     = "\ue0a0"
ICON_DIRTY      = "\uf111"
ICON_NO_UPSTREAM = "\U000f0be1"
# Presence icons (from PRESET_ICONS in object_row)
ICON_TICKET     = "\uf0ea"
ICON_THREAD     = "\uf086"
ICON_NOTE       = "\uf040"
ICON_WORKTREE   = "\uf07b"
ICON_TERMINAL   = "\uf120"
```

Then both `worktree_pane.py` and `object_row.py` import from `icons.py`, eliminating the duplication.

---

## Finding 3: MR Selection Logic for Project Rows

**How `_current_mr_data` is structured [VERIFIED: codebase]:**
```python
self._current_mr_data: dict  # keyed by (repo_name, branch) -> MRInfo
```

**How rel_index links projects to worktrees [VERIFIED: codebase]:**
```python
rel_index.worktrees_for(project)  # returns list[WorktreeInfo]
# Each WorktreeInfo has: .repo_name, .branch, .path
```

**Recommended pure function for MR selection:**
```python
def pick_best_mr(
    project: Project,
    mr_data: dict[tuple[str, str], MRInfo],
    rel_index: RelationshipIndex,
) -> MRInfo | None:
    """Select the most relevant MR for a project row.

    Priority:
    1. Active branch MR: from linked worktrees via rel_index
    2. Highest-numbered open MR for project's repo
    3. Highest-numbered closed/merged MR for project's repo
    Returns None if no MR found or project has no repo.
    """
    if project.repo is None:
        return None

    # Priority 1: MR for any linked worktree's branch
    for wt in rel_index.worktrees_for(project):
        mr = mr_data.get((wt.repo_name, wt.branch))
        if mr is not None:
            return mr

    # Priority 2 & 3: scan all MRs for this repo
    repo_mrs = [
        mr for (repo, branch), mr in mr_data.items()
        if repo == project.repo
    ]
    if not repo_mrs:
        return None

    open_mrs = [mr for mr in repo_mrs if not mr.is_draft]
    if open_mrs:
        return max(open_mrs, key=lambda m: m.mr_number)
    # fallback: any MR (draft or otherwise) by highest number
    return max(repo_mrs, key=lambda m: m.mr_number)
```

This function is pure (no side effects), easily unit-testable, and belongs in `project_list.py` or a small `_mr_utils.py`. No `MRInfo` state field indicates open vs closed — `is_draft` is the only state flag. The fallback to "highest-numbered" is a reasonable proxy for "most recent."

---

## Finding 4: Data Flow — Passing MR Data to ProjectList

**Current flow [VERIFIED: codebase]:**
1. `_set_worktrees()` stores `_current_mr_data` and calls `_maybe_compute_relationships()`
2. `_maybe_compute_relationships()` calls `_update_badges()` (pushes rel_index to ProjectList)
3. `ProjectList.update_badges(index)` updates wt_count + agent_count per row

**Recommended approach: extend `update_badges()` to also accept `mr_data`.**

```python
# In ProjectList:
def update_badges(
    self,
    index: object,
    mr_data: dict[tuple[str, str], MRInfo] | None = None,
) -> None:
    ...
    for row in self._rows:
        wt_count = len(index.worktrees_for(row.project))
        agent_count = len(index.terminals_for(row.project))
        mr_info = pick_best_mr(row.project, mr_data or {}, index)
        row.set_counts(wt_count, agent_count, mr_info=mr_info)
```

```python
# In JoyApp._update_badges():
self.query_one(ProjectList).update_badges(self._rel_index, mr_data=self._current_mr_data)
```

**Why this over a new `update_mr_data()` method:** `update_badges` is already called from the exact right place (`_maybe_compute_relationships`), after both rel_index and `_current_mr_data` are available. Adding mr_data as an optional parameter adds zero new call sites and keeps the timing correct.

**Why not pre-compute `dict[str, MRInfo | None]` in app:** It would require either running `pick_best_mr` in app.py (wrong layer) or importing resolver types into app just to iterate, which is already done.

---

## Finding 5: Project.status Field — TOML Round-Trip

**Current `Project.to_dict()` [VERIFIED: codebase]:**
```python
def to_dict(self) -> dict:
    d = {
        "name": self.name,
        "created": self.created,
        "objects": [obj.to_dict() for obj in self.objects],
    }
    if self.repo is not None:
        d["repo"] = self.repo
    return d
```

**Current `_toml_to_projects()` [VERIFIED: codebase]:**
```python
repo = proj_data.get("repo")  # None if absent (backward compat)
projects.append(Project(name=name, objects=objects, created=created, repo=repo))
```

**Pattern for adding `status`:**

1. Add to `Project` dataclass:
   ```python
   status: str = "idle"
   ```

2. In `to_dict()` — only write when non-default (matches `repo` pattern):
   ```python
   if self.status != "idle":
       d["status"] = self.status
   ```
   Or always write it — either works; always-write is simpler and avoids edge cases on cycle-back to idle.

3. In `_toml_to_projects()` — read with default:
   ```python
   status = proj_data.get("status", "idle")
   projects.append(Project(..., status=status))
   ```

**Backward compat: fully safe.** Existing TOML files without `status` will default to `"idle"` via `.get("status", "idle")`. No migration needed.

**Also update `ArchivedProject` serialization:** `_archived_to_toml` calls `ap.project.to_dict()`, so archive round-trip is automatic if `to_dict()` includes status.

---

## Finding 6: `g` Keybinding Conflict Check

**Current ProjectList BINDINGS [VERIFIED: codebase]:**
```python
BINDINGS = [
    Binding("up", ...),
    Binding("down", ...),
    Binding("j", "cursor_down", ...),
    Binding("k", "cursor_up", ...),
    Binding("enter", ...),
    Binding("n", "new_project", ...),
    Binding("e", "rename_project", ...),
    Binding("D", "delete_project", ...),
    Binding("delete", ...),
    Binding("/", "filter", ...),
    Binding("R", "assign_repo", ...),
    Binding("a", "archive_project", ...),
    Binding("A", "open_archive_browser", ...),
]
```

`g` is **not used**. [VERIFIED: codebase]

**Global app-level check needed:** Grep confirms no `g` binding in BINDINGS elsewhere in the codebase.
<br>`g` is safe to add to ProjectList.

---

## Finding 7: Section Spacer Pattern

**WorktreePane uses [VERIFIED: codebase]:**
```python
# In CSS:
WorktreePane .section-spacer {
    height: 1;
}

# In set_worktrees():
if not first_group:
    await scroll.mount(Static("", classes="section-spacer"))
first_group = False
```

**ProjectList `_rebuild()` should use the same pattern.** The `.section-spacer` class can be defined in `ProjectList.DEFAULT_CSS` independently (no coupling to WorktreePane). The spacer goes *before* each group header except the first, including between the last repo group and "Other".

---

## Implementation Summary

### Files to touch
| File | Change |
|------|--------|
| `src/joy/widgets/icons.py` | NEW — centralized icon constants |
| `src/joy/models.py` | Add `status: str = "idle"` to `Project`; update `to_dict()` |
| `src/joy/store.py` | Read `status` with default in `_toml_to_projects()` |
| `src/joy/widgets/project_list.py` | Rewrite `ProjectRow._build_content()` → Rich.Text; add `g` binding; add spacers; update `update_badges()` signature |
| `src/joy/app.py` | Pass `mr_data` to `update_badges()` call in `_update_badges()` |
| `src/joy/widgets/worktree_pane.py` | Import ICON_* from `icons.py` instead of defining locally |
| `src/joy/widgets/object_row.py` | Optionally import ICON_BRANCH from `icons.py` |

### Row rendering architecture
`ProjectRow` becomes a `@staticmethod build_content(project, avail_width, mr_info, rel_index)` pattern matching `WorktreeRow.build_content()`. The row stores the project and current state; `_rebuild()` passes the width; `update_badges()` / new `refresh(avail_width, mr_info)` redraws.

---

## Sources

- `src/joy/widgets/project_list.py` — current ProjectRow, BINDINGS, update_badges [VERIFIED]
- `src/joy/widgets/worktree_pane.py` — ICON_* constants, build_content(), _get_available_width(), section-spacer [VERIFIED]
- `src/joy/widgets/object_row.py` — PRESET_ICONS dict [VERIFIED]
- `src/joy/models.py` — Project.to_dict(), Project fields [VERIFIED]
- `src/joy/store.py` — _toml_to_projects(), backward compat pattern [VERIFIED]
- `src/joy/resolver.py` — RelationshipIndex.worktrees_for() [VERIFIED]
- `src/joy/app.py` — _current_mr_data structure, _update_badges(), _maybe_compute_relationships() call site [VERIFIED]

**Research date:** 2026-04-16
**Confidence:** HIGH — all findings verified from codebase, no assumptions on critical paths
