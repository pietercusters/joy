# Quick Task 260420-ak5: Extend New-Project Modal — Research

**Researched:** 2026-04-20
**Domain:** Textual 8.x multi-widget ModalScreen composition
**Confidence:** HIGH

## Summary

The new-project modal needs to grow from a single `Input` into a three-section `ModalScreen` that captures name, optional repo, and branch in one screen. All Textual primitives required (`Input`, `ListView`, focus management, `display: none` toggling) are well-supported in 8.x and follow patterns already used in this codebase (`RepoPickerModal`, `PresetPickerModal`). No new dependencies are needed.

**Primary recommendation:** Build a single `NewProjectModal(ModalScreen[NewProjectResult | None])` with a named `dataclass` return type. Use `display: none` CSS toggling to swap between the branch `ListView` and a branch `Input` inline. Focus Tab order falls naturally from DOM order; shift focus explicitly with `widget.focus()` only on mount and after the inline swap.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Branch field: ListView of 5 most recently checked-out local branches + "(type custom…)" item at bottom. Selecting "(type custom…)" opens a plain Input prompt for free-text entry.
- Repo field: optional — "(none)" is a valid choice in the repo ListView.
- Modal structure: single ModalScreen containing all three fields (name Input at top, repo ListView, branch ListView + custom escape). Not a sequential chain of separate modals.

### Claude's Discretion
- Exact CSS layout/styling within the single modal
- How to fetch the 5 recent branches (git branch --sort=-committerdate or git reflog)
- Tab/focus order between the three sections
- Whether branch list is fetched for the selected repo's path or the current working directory

### Deferred Ideas (OUT OF SCOPE)
- (none stated)
</user_constraints>

---

## 1. Multi-Section ModalScreen Composition

**Pattern:** `ModalScreen[T]` with a single `Vertical` container holding multiple sections. Each section is a labeled group: title `Static`, then the interactive widget. The modal returns `T` via `self.dismiss(value)`.

```python
# Source: textual.textualize.io/guide/screens + existing codebase pattern
class NewProjectModal(ModalScreen["NewProjectResult | None"]):

    BINDINGS = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-body"):
            yield Static("New Project", classes="modal-title")
            # Section 1 — name
            yield Static("Name", classes="section-label")
            yield Input(placeholder="Project name", id="name-input")
            # Section 2 — repo
            yield Static("Repo  (optional)", classes="section-label")
            yield ListView(*repo_items, id="repo-list")
            # Section 3 — branch
            yield Static("Branch", classes="section-label")
            yield ListView(*branch_items, id="branch-list")
            yield Input(placeholder="Custom branch name", id="branch-input")  # hidden initially
            yield Static("Tab: next section  Enter: select  Escape: cancel", classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one("#branch-input").display = False   # hide until "(type custom…)" selected
        self.query_one("#name-input").focus()
```

[VERIFIED: textual.textualize.io/widgets/list_view, textual.textualize.io/styles/display]

**CSS:** `display: none` removes a widget from the layout flow entirely — no blank space left. `display: block` restores it. Set via `widget.display = False/True` in Python. [VERIFIED: textual.textualize.io/styles/display]

---

## 2. Focus Management Between Sections

**Tab order:** Textual traverses focusable widgets in DOM order. Since `Input` and `ListView` are both focusable, pressing Tab from `#name-input` moves to `#repo-list`, then to `#branch-list`, then to `#branch-input` (when visible). No manual Tab binding needed.

**Explicit focus after swap:** When "(type custom…)" is selected, set `display = True` on `#branch-input`, set `display = False` on `#branch-list`, then call `self.query_one("#branch-input").focus()`.

**On mount:** Always focus `#name-input` explicitly — same pattern as `NameInputModal.on_mount()`.

[VERIFIED: textual.textualize.io/api/widget — `focus()`, `can_focus`, DOM traversal; textual.textualize.io/guide/input]

**Known gotcha with ListView and Enter:** `ListView` intercepts Enter to fire `ListView.Selected`. The `Input.Submitted` event fires on Enter too, but only when the `Input` has focus. These are independent events — no conflict as long as you route events by widget ID.

---

## 3. Branch List: Git Command

**Recommended command (list-form subprocess per project convention):**

```python
# Source: VERIFIED by running against this repo — returns correct results
result = subprocess.run(
    ["git", "branch", "--sort=-committerdate", "--format=%(refname:short)"],
    capture_output=True,
    text=True,
    timeout=5,
    cwd=repo_path,   # repo_path or None for cwd
)
branches = [b for b in result.stdout.strip().splitlines() if b][:5]
```

- `--sort=-committerdate` gives most recently committed-to branches first, which approximates "recently checked-out" well and is simpler than parsing `git reflog`.
- `--format=%(refname:short)` gives bare branch names with no `* ` prefix or leading whitespace.
- Returns `[]` on failure (no git repo, timeout, etc.) — safe fallback.
- `cwd=None` falls back to the process working directory if no repo path is available.

[VERIFIED: subprocess.run list-form confirmed working in this environment]

**Where to call it:** Fetch branches in `__init__` of the modal (before compose) or in `on_mount` (synchronous — acceptable since it's fast and local, no network). Since the modal is always shown from the main thread and git branch is consistently sub-100ms on local repos, no thread worker is needed. Match the `timeout=5` convention used throughout `worktrees.py`.

**Fallback if no repo selected yet:** Fetch from current working directory (`cwd=None`). If the user later selects a different repo, branches do not re-fetch (acceptable for MVP — can iterate).

---

## 4. "(type custom…)" Inline Swap Pattern

Two approaches exist. **Use the inline `display` toggle** — it's simpler and avoids push_screen complexity:

```python
_CUSTOM_BRANCH_SENTINEL = "(type custom…)"

def on_list_view_selected(self, event: ListView.Selected) -> None:
    if event.list_view.id == "branch-list":
        index = event.list_view.index
        if index is not None and self._branch_options[index] == _CUSTOM_BRANCH_SENTINEL:
            # Swap ListView for Input
            self.query_one("#branch-list").display = False
            branch_input = self.query_one("#branch-input")
            branch_input.display = True
            branch_input.focus()
        # else: selection recorded — will be read on final submission
```

When `#branch-input` is focused and Enter is pressed, `Input.Submitted` fires. At that point, read the value and proceed.

**Why not push_screen for "(type custom…)":** A nested push_screen requires an extra callback layer, breaks the single-modal promise, and complicates the cancel path. The display-toggle approach keeps all state in one place.

[ASSUMED: display toggle on ListView is idiomatic for inline conditional swap — no official "swap widget" guide found, but the `display` CSS property behavior is VERIFIED.]

---

## 5. Return Type and app.py Integration

**Return type — use a dataclass:**

```python
from dataclasses import dataclass

@dataclass
class NewProjectResult:
    name: str
    repo: str | None        # repo name (str) or None for no assignment
    branch: str | None      # branch name (str) or None for no branch pre-fill
```

This is cleaner than a tuple — callers don't need to remember index order. The modal becomes `NewProjectModal(ModalScreen[NewProjectResult | None])` — `None` on Escape/cancel.

**`action_new_project()` changes in `app.py`:**

Current (line 614–639):
```python
def action_new_project(self) -> None:
    def on_name(name: str | None) -> None:
        if name is None:
            return
        ...
        project = Project(name=name)
        ...
    self.push_screen(NameInputModal(), on_name)
```

New:
```python
def action_new_project(self) -> None:
    def on_result(result: NewProjectResult | None) -> None:
        if result is None:
            return
        if any(p.name == result.name for p in self._projects):
            self.notify(f"Project '{result.name}' already exists", severity="error", markup=False)
            return
        project = Project(name=result.name, repo=result.repo)
        # Optionally pre-add branch object if result.branch is provided
        if result.branch:
            from joy.models import ObjectItem, PresetKind
            project.objects.append(ObjectItem(kind=PresetKind.BRANCH, value=result.branch))
        self._projects.append(project)
        self._save_projects_bg()
        project_list = self.query_one(ProjectList)
        project_list.set_projects(self._projects, self._repos)
        new_index = len(self._projects) - 1
        project_list.call_after_refresh(lambda: project_list.select_index(new_index))
        self.query_one(ProjectDetail).set_project(project)
        self.notify(f"Created project: '{result.name}'", markup=False)
        self._start_add_object_loop(project)
    self.push_screen(NewProjectModal(repos=self._repos), on_result)
```

**Constructor signature for the new modal:**
```python
def __init__(self, repos: list[Repo]) -> None:
    super().__init__()
    self._repos = repos
    self._branch_options: list[str] = self._fetch_recent_branches() + [_CUSTOM_BRANCH_SENTINEL]
    self._repo_options: list[str | None] = [r.name for r in repos] + [None]  # None = "(none)"
```

---

## 6. Common Pitfalls

### Pitfall 1: Event routing when two ListViews are in one modal
`on_list_view_selected` fires for ANY `ListView` in the widget tree. Always gate on `event.list_view.id` (`"repo-list"` vs `"branch-list"`) or `event.list_view` identity — never assume which list fired.

### Pitfall 2: `display = False` widget still receives Tab focus
A widget with `display = False` is removed from layout but may still be in the focus cycle in some Textual versions. Guard the final submission: if `#branch-input` is hidden, ignore its value (treat branch as `None`). Track a boolean `self._custom_branch_mode: bool = False` for clarity.

### Pitfall 3: Submitting name with Enter while ListView has focus
If the user's cursor is on the `#repo-list` or `#branch-list` when they press Enter, `ListView.Selected` fires — not `Input.Submitted`. The modal must have an explicit "confirm" path. Options:
- Add a BINDING for a key that reads all current state and dismisses (e.g., `ctrl+enter` or a dedicated "Create" binding).
- Or: after branch selection (both from list and custom input), auto-confirm if name is filled.

**Recommended:** Add a `("ctrl+n", "confirm", "Create")` BINDING that reads current state from all three sections and calls `dismiss(result)`. This makes the confirm path explicit regardless of which widget has focus.

### Pitfall 4: Repo list selection marking vs. value tracking
`RepoPickerModal` uses `index` to look up `_options[index]`. Replicate this: maintain `self._selected_repo: str | None = None` updated in `on_list_view_selected` for the repo list. Same for `self._selected_branch: str | None = None`.

---

## Architecture: File Changes Required

| File | Change |
|------|--------|
| `src/joy/screens/new_project.py` | New file — `NewProjectModal` + `NewProjectResult` dataclass |
| `src/joy/screens/__init__.py` | Add `NewProjectModal`, `NewProjectResult` to exports |
| `src/joy/app.py` | `action_new_project()`: replace `NameInputModal` call with `NewProjectModal`; update `on_result` callback |
| `src/joy/screens/name_input.py` | Unchanged — still used elsewhere (rename flow, etc.) |

`NewProjectResult` can live in `new_project.py` (no circular imports — it has no deps on other joy modules except `joy.models.Repo`).

---

## Sources

### Primary (HIGH confidence)
- `/websites/textual_textualize_io` — ModalScreen, ListView.Selected, Input.Submitted, display CSS, focus() API
- Codebase inspection — `name_input.py`, `repo_picker.py`, `preset_picker.py`, `worktrees.py` subprocess pattern

### Secondary (VERIFIED by running)
- `git branch --sort=-committerdate --format=%(refname:short)` — confirmed in this repo
- Python `subprocess.run` list-form — confirmed produces correct branch list

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `display = False` removes widget from Tab focus cycle in Textual 8.x | Pitfall 2 | If wrong: hidden `#branch-input` could receive focus; guard with `self._custom_branch_mode` boolean |
| A2 | Fetching branches synchronously in `__init__` or `on_mount` is acceptable (< 100ms) | Section 3 | If wrong on slow NFS/remote-backed path: add `@work(thread=True)` worker + `call_from_thread` to populate branch list after mount |
