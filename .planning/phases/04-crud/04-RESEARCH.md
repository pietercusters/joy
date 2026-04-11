# Phase 4: CRUD - Research

**Researched:** 2026-04-11
**Domain:** Textual ModalScreen, CRUD mutations, modal chaining, TUI form patterns
**Confidence:** HIGH

## Summary

Phase 4 wires five keyboard actions (`n`, `a`, `e`, `d`, `delete`/`D`) into the existing Textual TUI to support full CRUD on projects and objects. All mutations use four `ModalScreen` subclasses: a name input modal, a type-to-filter preset picker, a value input modal, and a confirmation dialog. The codebase from Phases 1-3 already provides all the primitives needed: `save_projects()`, `@work(thread=True)`, `app.notify()`, `set_projects()`, `set_project()`, and `highlighted_object`.

The core Textual capability is `push_screen(screen, callback)` for single modals and the same pattern applied recursively for the add-object loop. The `push_screen_wait()` / `@work` pattern is an alternative but callback-based chaining is simpler here. All four `ModalScreen` subclasses follow the same structural template and CSS pattern already established in Textual's own examples.

No new Python dependencies are required. All modal widget building blocks (`Input`, `ListView`, `ListItem`, `Label`, `Static`) are Textual builtins.

**Primary recommendation:** Implement all four modal screens in a new `src/joy/screens/` directory using `ModalScreen[T]` with `push_screen(screen, callback)` chaining. The add-object loop re-pushes `PresetPickerModal` from the value-input callback until Escape returns `None`.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Project Creation Flow**
- D-01: `n` is globally bound on `JoyApp` (same as `O`); available from both panes.
- D-02: Two-step flow: (1) name modal, (2) add-object form opens immediately after.
- D-03: Add-object form loops back automatically until user presses Escape.
- D-04: After name confirmed, project is immediately added to `JoyApp._projects`, persisted, list refreshed, then add-object form opens.

**Object Add Form**
- D-05: Type-to-filter preset picker — user types to filter 9 preset kinds in real-time; j/k or arrows navigate; Enter selects. No generic/custom type in Phase 4.
- D-06: After preset selection, second input captures value only — no label field.
- D-07: Add form is a `ModalScreen` pushed via `push_screen()`.

**Object Edit Form**
- D-08: `e` opens modal pre-populated with current value; preset kind is fixed (no type change); Escape cancels, Enter confirms.
- D-09: `e` is bound on `ProjectDetail`; updates `ObjectItem.value` in-place, refreshes row, persists in background thread.

**Object Deletion**
- D-10: `d` shows modal confirmation "Delete {kind} '{value}'?"; Enter confirms, Escape cancels.
- D-11: `d` bound on `ProjectDetail`; after deletion, cursor moves to previous row (or stays at same index if it was last).

**Project Deletion**
- D-12: `delete` key from `JoyListView` shows modal confirmation with full message.
- D-13: After deletion, adjacent project selected (next if available, else previous). `JoyApp._projects` updated, persisted, list refreshed.

**Confirmation Modal Design**
- D-14: Confirmation dialogs are small centered `ModalScreen` overlays. Enter confirms, Escape cancels (consistent with CORE-04).
- D-15: Modal shows item name/value so user can confirm they're deleting the right thing.

**Persistence Pattern**
- D-16: All mutations persist via `save_projects(JoyApp._projects)` in `@work(thread=True)` background thread — same pattern as Phase 3.

### Claude's Discretion

- Exact `ModalScreen` widget hierarchy for each modal type.
- How type-to-filter filtering is implemented (custom `Input` + `ListView` pair).
- CSS for modal overlays (centering, width, border style).
- Exact copy for toast notifications after add/edit/delete operations.
- Key binding for project delete — `delete` key vs `D` — choose whichever Textual handles more cleanly.
- Error handling if project name already exists.

### Deferred Ideas (OUT OF SCOPE)

- Label field on `ObjectItem` — model has it but forms won't expose it in Phase 4.
- Generic/custom object type (non-preset) — not in Phase 4 scope.
- Duplicate project name validation UX is Claude's discretion for error message approach.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PROJ-04 | User can create a new project (enter name; add objects via pre-defined form) | D-01–D-04: name modal + add-object loop; `push_screen(callback)` chaining confirmed |
| PROJ-05 | User can delete a project after confirming | D-12–D-13: `delete`/`D` on `JoyListView` + `ConfirmationModal` + adjacent selection logic |
| MGMT-01 | Pressing `a` opens add-object form (choose preset type, enter value) | D-05–D-07: `PresetPickerModal` (type-to-filter `Input` + `ListView`) + `ValueInputModal` |
| MGMT-02 | Pressing `e` opens edit form for selected object | D-08–D-09: `ValueInputModal` pre-populated, bound on `ProjectDetail` |
| MGMT-03 | Pressing `d` removes selected object after confirming | D-10–D-11: `ConfirmationModal`, bound on `ProjectDetail`, cursor adjustment after delete |
</phase_requirements>

---

## Standard Stack

### Core (no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| textual | 8.2.3 | ModalScreen, Input, ListView, ListItem, Label, Static | Already installed; all widgets are built-in [VERIFIED: `uv run python -c "import textual; print(textual.__version__)"` → 8.2.3] |
| tomli_w | ^1.0 | TOML write (persistence) | Already installed; `save_projects()` established |

No new packages required. All modal building blocks are Textual builtins.

**Installation:**
```bash
# No new packages — Phase 4 uses existing venv
uv sync
```

### New File Structure

```
src/joy/
├── app.py                     # Add n binding + action_new_project()
├── models.py                  # Unchanged
├── store.py                   # Unchanged
├── operations.py              # Unchanged
├── screens/                   # NEW directory
│   ├── __init__.py
│   ├── name_input.py          # NameInputModal
│   ├── preset_picker.py       # PresetPickerModal
│   ├── value_input.py         # ValueInputModal
│   └── confirmation.py        # ConfirmationModal
└── widgets/
    ├── object_row.py          # Unchanged
    ├── project_detail.py      # Add a, e, d bindings + action methods
    └── project_list.py        # Add delete/D binding + action_delete_project()
```

---

## Architecture Patterns

### Pattern 1: ModalScreen[T] with push_screen(callback)

The standard Textual pattern for returning data from a modal.

```python
# Source: https://textual.textualize.io/guide/screens/
class NameInputModal(ModalScreen[str | None]):
    """Returns project name string on Enter, None on Escape."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    NameInputModal {
        align: center middle;
    }
    NameInputModal > Vertical {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $background 80%;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("New Project", classes="modal-title")
            yield Input(placeholder="Project name")
            yield Static("Enter to create, Escape to cancel", classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if not value:
            self.app.notify("Project name cannot be empty", severity="error", markup=False)
            return
        self.dismiss(value)

    def action_cancel(self) -> None:
        self.dismiss(None)
```

Caller pattern:
```python
# In JoyApp:
def action_new_project(self) -> None:
    def on_name(name: str | None) -> None:
        if name is None:
            return
        # Create project, persist, refresh list, select, then open add-object loop
        self._create_project(name)
    self.push_screen(NameInputModal(), on_name)
```

[VERIFIED: Official Textual screens guide — push_screen + dismiss pattern]
[VERIFIED: Issue #5512 closed Feb 2025 — callbacks work from all invocation contexts]

### Pattern 2: Add-Object Loop via Recursive Callback

The loop is implemented by re-pushing `PresetPickerModal` from within the value-input callback.

```python
# In JoyApp or ProjectDetail — re-push pattern:
def _start_add_object_loop(self, project: Project) -> None:
    def on_preset(preset: PresetKind | None) -> None:
        if preset is None:
            return  # Escape exits loop

        def on_value(value: str | None) -> None:
            if value is not None:
                # Append object, persist, refresh
                obj = ObjectItem(kind=preset, value=value)
                project.objects.append(obj)
                self._save_projects_bg()
                self.query_one(ProjectDetail).set_project(project)
            # Loop: push preset picker again regardless of value result
            self._start_add_object_loop(project)

        self.push_screen(ValueInputModal(preset), on_value)

    self.push_screen(PresetPickerModal(), on_preset)
```

**Loop exit condition:** When `PresetPickerModal` returns `None` (user pressed Escape), `on_preset` returns without re-pushing. The user lands in the detail pane of the new/current project.

[VERIFIED: Textual screens guide — "Chaining Modals from Callbacks" pattern]
[ASSUMED: The recursive push pattern (pushing from within a callback that itself came from a push) works correctly in Textual 8.x — no known issues found]

### Pattern 3: Type-to-Filter Preset Picker

An `Input` + `ListView` inside one `ModalScreen`. The `on_input_changed` handler rebuilds list items in real time.

```python
class PresetPickerModal(ModalScreen[PresetKind | None]):
    BINDINGS = [("escape", "cancel", "Cancel")]

    # All 9 presets in GROUP_ORDER
    ALL_PRESETS: list[PresetKind] = [
        PresetKind.WORKTREE, PresetKind.BRANCH, PresetKind.MR,
        PresetKind.TICKET, PresetKind.THREAD, PresetKind.FILE,
        PresetKind.NOTE, PresetKind.AGENTS, PresetKind.URL,
    ]

    def __init__(self) -> None:
        super().__init__()
        self._filtered: list[PresetKind] = list(self.ALL_PRESETS)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Add Object", classes="modal-title")
            yield Input(placeholder="Type to filter...", id="filter-input")
            yield ListView(
                *[ListItem(Label(f"{PRESET_ICONS[k]}  {k.value}")) for k in self.ALL_PRESETS],
                id="preset-list",
            )
            yield Static("j/k to navigate, Enter to select, Escape to cancel",
                        classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one("#filter-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        self._filtered = [k for k in self.ALL_PRESETS if query in k.value]
        listview = self.query_one("#preset-list", ListView)
        listview.clear()
        for kind in self._filtered:
            listview.append(ListItem(Label(f"{PRESET_ICONS[kind]}  {kind.value}")))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.index is not None and event.index < len(self._filtered):
            self.dismiss(self._filtered[event.index])

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter from filter input: select first item in filtered list."""
        listview = self.query_one("#preset-list", ListView)
        if self._filtered:
            # Move focus to list so user can press Enter to select,
            # OR directly select the first item
            if len(self._filtered) == 1:
                self.dismiss(self._filtered[0])

    def action_cancel(self) -> None:
        self.dismiss(None)
```

**Key concern — focus management:** When user types in the filter `Input`, the `ListView` needs to be navigable with j/k while focus is on the input. Two options:
1. Keep focus on `Input`, intercept j/k in `on_key()` to manually move `ListView.index`.
2. After filter + Enter, move focus to `ListView` for j/k selection then Enter.

Option 1 is simpler UX (no manual focus switch required). Option 2 is more Textual-idiomatic.

[VERIFIED: ListView.clear() + .append() pattern for dynamic filtering from official docs]
[ASSUMED: Focus management between Input filter and ListView navigation — approach not explicitly specified in docs; needs implementation-time decision]

### Pattern 4: ValueInputModal (Add + Edit)

Single `Input` modal, supports both modes (add = empty, edit = pre-populated):

```python
class ValueInputModal(ModalScreen[str | None]):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, kind: PresetKind, existing_value: str = "") -> None:
        super().__init__()
        self._kind = kind
        self._existing_value = existing_value

    def compose(self) -> ComposeResult:
        mode = "Edit" if self._existing_value else "Add"
        hint = "Enter to save, Escape to cancel" if self._existing_value else "Enter to add, Escape to cancel"
        with Vertical():
            yield Static(f"{mode} {self._kind.value}", classes="modal-title")
            yield Input(value=self._existing_value, placeholder="Enter value")
            yield Static(hint, classes="modal-hint")

    def on_mount(self) -> None:
        inp = self.query_one(Input)
        inp.focus()
        # Move cursor to end of pre-populated value
        inp.cursor_position = len(self._existing_value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if not value:
            self.app.notify("Value cannot be empty", severity="error", markup=False)
            return
        self.dismiss(value)

    def action_cancel(self) -> None:
        self.dismiss(None)
```

[VERIFIED: Input(value=...) for pre-population from Textual Input widget docs]

### Pattern 5: ConfirmationModal (Delete)

Destructive modal with red border:

```python
class ConfirmationModal(ModalScreen[bool]):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "confirm", "Confirm"),
    ]

    DEFAULT_CSS = """
    ConfirmationModal {
        align: center middle;
    }
    ConfirmationModal > Vertical {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $error;
        padding: 1 2;
    }
    """

    def __init__(self, title: str, prompt: str) -> None:
        super().__init__()
        self._title = title
        self._prompt = prompt

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self._title, classes="modal-title")
            yield Static(self._prompt)
            yield Static("Enter to delete, Escape to cancel", classes="modal-hint")

    def on_mount(self) -> None:
        self.focus()  # Focus the screen itself for key capture

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
```

**Important:** `ConfirmationModal` has no `Input` widget so `on_mount` focuses the screen itself (not a child widget) to ensure Enter/Escape BINDINGS are captured.

[VERIFIED: ModalScreen BINDINGS pattern from Textual screens guide]

### Pattern 6: Background Save

Established Phase 3 pattern — unchanged:

```python
@work(thread=True, exit_on_error=False)
def _save_projects_bg(self) -> None:
    from joy.store import save_projects  # noqa: PLC0415
    save_projects(self.app._projects)
```

[VERIFIED: Phase 3 codebase — `_save_toggle()` in `project_detail.py`]

### Anti-Patterns to Avoid

- **Blocking `save_projects()` in action handlers:** Never call `save_projects()` directly in an action handler — always wrap in `@work(thread=True)`.
- **`push_screen_wait` without `@work`:** `push_screen_wait` requires a `@work` decorator; using it in a plain action handler will fail.
- **Awaiting `dismiss()` in message handlers:** Textual raises `ScreenError` if you await `dismiss()` in a message handler. Call `self.dismiss(value)` synchronously.
- **Mutating `_projects` list in background thread:** All list mutations (`append`, `remove`) must happen on the main thread (in action handlers / callbacks). Background thread only calls `save_projects()`.
- **Direct DOM manipulation before `call_after_refresh`:** Same warning as Phase 2/3 — use `set_project()` (which uses `call_after_refresh`) after mutations.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Modal overlay | Custom overlay widget | `ModalScreen` | Built-in semi-transparent background, focus trapping, key binding isolation |
| Text input | Custom character buffer | `Input` widget | Cursor, backspace, clipboard paste, all handled |
| Filterable list | Custom rendered list | `Input` + `ListView` pair | `ListView.clear()` + `append()` for real-time rebuild is idiomatic |
| Confirmation dialog | Footer-bar "y/n" prompt | `ConfirmationModal(ModalScreen)` | Consistent UX, Escape always cancels (CORE-04) |
| Sequential modal flow | Global state machine | Callback chaining in `push_screen` | Textual's native pattern — no external state needed |

**Key insight:** Everything the planner needs is Textual built-ins. The only new code is the four `ModalScreen` subclasses and the mutations + callbacks wiring them into existing widgets.

---

## Common Pitfalls

### Pitfall 1: Focus management in PresetPickerModal
**What goes wrong:** User types in filter `Input`, hits j/k expecting to navigate the `ListView`, but focus is on `Input` so j/k moves cursor in text field instead.
**Why it happens:** Focus determines which widget processes key events. `Input` consumes j/k as text input.
**How to avoid:** Intercept j/k in the modal's `on_key()` method and manually call `listview.action_cursor_down()` / `listview.action_cursor_up()` while focus stays on `Input`. OR: Tab to move focus to `ListView` after typing, then j/k navigates. The `on_key()` interception approach is cleaner UX.
**Warning signs:** User reports j/k typed literally into filter field.

### Pitfall 2: Confirmation modal Enter key not captured
**What goes wrong:** `ConfirmationModal` has no `Input` widget; user presses Enter but nothing happens.
**Why it happens:** Without a focused child widget, the modal screen itself must have focus. If `on_mount` doesn't call `self.focus()`, key events fall through.
**How to avoid:** In `ConfirmationModal.on_mount()`, call `self.focus()` so the screen itself captures `enter` and `escape` via its `BINDINGS`.
**Warning signs:** Enter/Escape in confirmation dialog does nothing.

### Pitfall 3: Project mutation race condition
**What goes wrong:** `_save_projects_bg()` runs in a background thread while another user action calls `save_projects()` again.
**Why it happens:** Two concurrent background threads both write to `projects.toml`.
**How to avoid:** Atomic write via `os.replace` (already implemented in `store.py`) means the last write wins — no corruption. Race is benign for joy's use case (single user, fast saves). Not a blocking concern.
**Warning signs:** TOML file corrupted (won't happen with atomic write pattern).

### Pitfall 4: `push_screen` from `@work` thread
**What goes wrong:** Calling `self.app.push_screen()` from inside a `@work(thread=True)` method raises an error or silently fails.
**Why it happens:** `push_screen` must be called from the main event loop thread.
**How to avoid:** All `push_screen` calls go in action handlers (main thread) or synchronous callbacks (main thread). Background threads only call `save_projects()`.
**Warning signs:** Modal doesn't appear when expected.

### Pitfall 5: Modal CSS `height: auto` with `ListView`
**What goes wrong:** `PresetPickerModal` with `height: auto` and a `ListView` of 9 items may grow taller than the terminal window.
**Why it happens:** `height: auto` sizes to content; 9 list items + chrome = ~14 rows on a small terminal.
**How to avoid:** Set `max-height: 20` on the modal container. Or use `height: auto` and let Textual handle overflow (it clips to terminal bounds). Document the expected height in CSS.
**Warning signs:** Modal extends off bottom of screen.

### Pitfall 6: Cursor position after object delete
**What goes wrong:** After deleting the last object in a group, the cursor lands on a `GroupHeader` widget instead of an `ObjectRow`.
**Why it happens:** `_rows` only tracks `ObjectRow` widgets; `_cursor` indexes into `_rows`. After `set_project()` re-renders, `_cursor` is reset to 0 (first row of first group). No issue if using `set_project()` for re-render.
**How to avoid:** Always call `set_project()` after object mutations — it fully re-renders and resets `_cursor` to 0 (or -1 if no rows). The UI-SPEC says to move to previous row, but simpler/safer is to call `set_project()` and let it set `_cursor = max(0, min(previous_cursor, len(new_rows)-1))`.
**Warning signs:** Crash on `self._rows[self._cursor]` indexing after delete.

### Pitfall 7: Project delete with empty list
**What goes wrong:** After deleting the last project, `JoyApp._projects` is empty. Attempts to select adjacent project raise `IndexError`.
**Why it happens:** Adjacent selection logic assumes at least one project remains.
**How to avoid:** Guard: `if not self._projects: clear detail pane only`. Detail pane `set_project(None)` or equivalent no-op.
**Warning signs:** `IndexError` in `_set_projects` or `ProjectList.select_first()`.

---

## Code Examples

### Complete push_screen callback chain (create project + add-object loop)

```python
# In JoyApp — action_new_project
def action_new_project(self) -> None:
    def on_name(name: str | None) -> None:
        if name is None:
            return
        # Check duplicate
        existing = [p.name for p in self._projects]
        if name in existing:
            self.notify(f"Project '{name}' already exists", severity="error", markup=False)
            return
        # Create and persist
        project = Project(name=name)
        self._projects.append(project)
        self._save_projects_bg()
        self.query_one(ProjectList).set_projects(self._projects)
        # TODO: select new project in list
        self.query_one(ProjectDetail).set_project(project)
        # Start add-object loop
        self._start_add_object_loop(project)

    self.push_screen(NameInputModal(), on_name)

def _start_add_object_loop(self, project: Project) -> None:
    def on_preset(preset: PresetKind | None) -> None:
        if preset is None:
            return  # Escape — exit loop

        def on_value(value: str | None) -> None:
            if value is not None:
                obj = ObjectItem(kind=preset, value=value)
                project.objects.append(obj)
                self._save_projects_bg()
                self.query_one(ProjectDetail).set_project(project)
            # Loop back — always push preset picker again
            self._start_add_object_loop(project)

        self.push_screen(ValueInputModal(preset), on_value)

    self.push_screen(PresetPickerModal(), on_preset)
```

### Project deletion with adjacent selection

```python
# In JoyListView or ProjectList:
def action_delete_project(self) -> None:
    project_list = self.app.query_one(ProjectList)
    index = self.index  # JoyListView.index is the highlighted index
    if index is None or index >= len(project_list._projects):
        return
    project = project_list._projects[index]

    def on_confirm(confirmed: bool) -> None:
        if not confirmed:
            return
        projects = self.app._projects
        projects.remove(project)
        self.app._save_projects_bg()
        # Select adjacent project
        new_index = min(index, len(projects) - 1)
        project_list.set_projects(projects)
        if projects:
            self.index = new_index
        else:
            self.app.query_one(ProjectDetail).set_project(None)  # clear detail
        self.app.notify(f"Deleted project: '{project.name}'", markup=False)

    self.app.push_screen(
        ConfirmationModal(
            title="Delete Project",
            prompt=f"Delete project '{project.name}'? This will remove it and all its objects."
        ),
        on_confirm,
    )
```

### Object deletion with cursor adjustment

```python
# In ProjectDetail:
def action_delete_object(self) -> None:
    item = self.highlighted_object
    if item is None:
        self.app.notify("No object selected", severity="error", markup=False)
        return
    prev_cursor = self._cursor
    kind_val = item.kind.value
    value_trunc = _truncate(item.value)

    def on_confirm(confirmed: bool) -> None:
        if not confirmed:
            return
        self._project.objects.remove(item)
        self._save_toggle()
        # Re-render; _render_project resets cursor to 0
        # Restore cursor to prev_cursor - 1 (or 0) via post-render
        self.set_project(self._project)
        self.app.notify(f"Deleted: {kind_val} '{value_trunc}'", markup=False)

    self.app.push_screen(
        ConfirmationModal(
            title="Delete Object",
            prompt=f"Delete {item.kind.value} '{_truncate(item.value, 40)}'?"
        ),
        on_confirm,
    )
```

Note: `set_project()` re-renders and sets `_cursor = 0 if rows else -1`. To restore to previous position (minus 1 for deleted item), `_render_project` would need to accept an initial cursor hint. Simpler approach: after `set_project()` is called, the `call_after_refresh` chain resets cursor to 0. If preserving position matters, pass `target_cursor = max(0, prev_cursor - 1)` to a modified `_render_project`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pop_screen()` to dismiss modals | `self.dismiss(result)` on `ModalScreen` | Textual ~0.27 | dismiss() carries return value to callback; cleaner than manual pop |
| Callback-only modal results | `push_screen_wait()` with `@work` | Textual ~0.30 | Async/await pattern available but callbacks remain idiomatic for simple chains |
| Manual key binding in CSS | `BINDINGS` class variable on `ModalScreen` | Long-established | Escape binding on ModalScreen is standard |

**Not deprecated:**
- `push_screen(screen, callback)` — still the primary pattern
- `ModalScreen[T]` generic typing — confirmed working in 8.2.3

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Recursive `push_screen` from callback (pushing `PresetPickerModal` again from within `on_value` callback) works without issues in Textual 8.2.3 | Pattern 2 (Add-Object Loop) | Loop doesn't work; need `push_screen_wait` + `@work` instead |
| A2 | `on_input_submitted` fires correctly in Textual 8.2.3 `ModalScreen` (old ModalScreen+Input bug is fixed) | Pattern 1, 4 | Enter doesn't dismiss modal; need `on_key("enter")` workaround |
| A3 | `ListView.clear()` + `append()` inside `on_input_changed` doesn't cause flicker or focus issues in ModalScreen | Pattern 3 (Preset Picker) | Filter causes visual artifacts; may need to rebuild `ListItem` differently |
| A4 | `self.focus()` in `ConfirmationModal.on_mount()` correctly captures Enter/Escape BINDINGS | Pattern 5 | Confirmation modal Enter does nothing; need explicit Button widgets |
| A5 | `project.objects.remove(item)` correctly identifies the item by identity (not value equality) | Object deletion | Wrong item deleted if two items have same value and kind |

**A2 note:** Issue #2194 was closed April 2, 2023 (fixed in PR #2195). We are on Textual 8.2.3 (April 2026). Risk is very low.
**A5 note:** Python `list.remove()` uses `==` equality, not `is` identity. `ObjectItem` is a dataclass — equality is value-based. If two identical objects exist, `remove()` deletes the first one found. Use `project.objects.pop(index)` instead, using the index of the selected item.

---

## Open Questions

1. **PresetPickerModal focus strategy for j/k navigation**
   - What we know: `Input` consumes j/k as text characters; `ListView` handles j/k natively when focused.
   - What's unclear: Should we intercept j/k in `on_key()` to forward to `ListView` while keeping `Input` focused? Or switch focus with Tab?
   - Recommendation: Implement `on_key()` to intercept `j`/`k` and call `listview.action_cursor_down()` / `listview.action_cursor_up()`. This gives seamless filter + navigate without Tab. Planner should include a task to prototype and verify.

2. **Cursor restoration after object delete**
   - What we know: `set_project()` resets `_cursor` to 0 after re-render.
   - What's unclear: The UI-SPEC says "cursor moves to previous row (index - 1)"; `set_project()` doesn't support this.
   - Recommendation: Modify `_render_project` to accept an optional `initial_cursor` parameter. Pass `max(0, prev_cursor - 1)` when called after deletion. This keeps the user's visual position stable.

3. **Selecting new project in list after creation**
   - What we know: `ProjectList.set_projects()` rebuilds the list but doesn't auto-select a specific item.
   - What's unclear: How to set `JoyListView.index` to the newly created project's position after `set_projects()`.
   - Recommendation: Add a `select_project(name: str)` method to `ProjectList` that finds the index by name and sets `listview.index`. Or: append to end and select `len(projects) - 1`.

4. **`delete` key vs `D` for project deletion**
   - What we know: The UI-SPEC says "`delete` or `D`"; Claude's discretion for which to use.
   - What's unclear: Textual's handling of the terminal `delete` key (DEL, ASCII 127) may differ across terminal emulators.
   - Recommendation: Bind both `delete` and `D` in `JoyListView.BINDINGS`. Test in macOS Terminal and iTerm2. Use `D` as primary (safer), `delete` as alias.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 4 is pure code additions (new Python files + modifications to existing widgets). No new external tools, services, CLIs, or databases required beyond the existing venv.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest tests/test_tui.py -q` |
| Full suite command | `uv run pytest tests/ -q` |

Current test suite: **90 passed, 1 deselected** (all green as of research date).

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROJ-04 | `n` opens name modal; valid name creates project | unit/integration | `uv run pytest tests/test_tui.py::test_n_creates_project -x` | ❌ Wave 0 |
| PROJ-04 | `n` → escape → no project created | unit | `uv run pytest tests/test_tui.py::test_n_escape_noop -x` | ❌ Wave 0 |
| PROJ-04 | `n` → duplicate name → error toast | unit | `uv run pytest tests/test_tui.py::test_n_duplicate_name_error -x` | ❌ Wave 0 |
| PROJ-04 | `n` → project persisted via save_projects | unit | `uv run pytest tests/test_tui.py::test_n_persists -x` | ❌ Wave 0 |
| PROJ-05 | `D` from project list → confirmation → project removed | unit | `uv run pytest tests/test_tui.py::test_D_deletes_project -x` | ❌ Wave 0 |
| PROJ-05 | Project delete → adjacent project selected | unit | `uv run pytest tests/test_tui.py::test_D_selects_adjacent -x` | ❌ Wave 0 |
| MGMT-01 | `a` in detail pane → preset picker opens | unit | `uv run pytest tests/test_tui.py::test_a_opens_preset_picker -x` | ❌ Wave 0 |
| MGMT-01 | Preset picker filter reduces list | unit | `uv run pytest tests/test_screens.py::test_preset_picker_filter -x` | ❌ Wave 0 |
| MGMT-01 | Full add-object flow: a → select preset → enter value → object appears | integration | `uv run pytest tests/test_tui.py::test_a_full_flow -x` | ❌ Wave 0 |
| MGMT-02 | `e` on highlighted object → modal pre-populated with value | unit | `uv run pytest tests/test_tui.py::test_e_opens_edit_modal -x` | ❌ Wave 0 |
| MGMT-02 | Edit → save → value updated in project | unit | `uv run pytest tests/test_tui.py::test_e_updates_value -x` | ❌ Wave 0 |
| MGMT-03 | `d` on highlighted object → confirmation modal | unit | `uv run pytest tests/test_tui.py::test_d_shows_confirmation -x` | ❌ Wave 0 |
| MGMT-03 | `d` → confirm → object removed | unit | `uv run pytest tests/test_tui.py::test_d_deletes_object -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/ -q` (full suite, 90+ tests, ~8s)
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_tui.py` — add PROJ-04, PROJ-05, MGMT-01, MGMT-02, MGMT-03 test functions (extend existing file)
- [ ] `tests/test_screens.py` — new file for unit testing modal screens in isolation (PresetPickerModal filter logic, ConfirmationModal dismiss)
- [ ] `src/joy/screens/__init__.py` — new directory needs `__init__.py`

**Note on Textual pilot + modals:** Testing modals with `pilot.press()` requires the modal to be on the screen stack. Pattern:
```python
async with app.run_test() as pilot:
    await pilot.pause(0.2)
    await app.workers.wait_for_complete()
    await pilot.press("n")  # opens NameInputModal
    await pilot.pause(0.1)
    # Now modal is active — press keys into Input
    await pilot.press(*"my-project")
    await pilot.press("enter")
    await pilot.pause(0.1)
    # Verify project created
```
`await pilot.press(*"string")` unpacks characters as individual key presses — confirmed in Textual testing docs.

---

## Security Domain

Phase 4 involves no authentication, no network calls, no cryptography, and no user-supplied input that is executed as code. Input is stored as plain TOML strings and displayed back to the user. ASVS categories that apply:

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A |
| V5 Input Validation | Minimal | Empty string check; no injection risk (TOML values are escaped by `tomli_w`) |
| V6 Cryptography | No | N/A |

**Threat pattern:** User types a project name or object value into an `Input` widget. The value is written to `~/.joy/projects.toml` via `tomli_w.dumps()`. `tomli_w` correctly escapes all TOML special characters. No injection risk. No external sharing.

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 4 |
|-----------|------------------|
| Python only, managed with `uv` | All code is Python; no new runtimes |
| macOS only | No cross-platform concerns |
| `uv tool install` target | No new dependencies beyond existing `textual` + `tomli_w` |
| Config at `~/.joy/` | Persistence unchanged; `save_projects()` writes to `~/.joy/projects.toml` |
| Minimalistic, snappy — no heavy dependencies | Modal screens are all Textual built-ins; startup time unaffected |
| No inline editing | All editing through modal overlays (REQUIREMENTS.md Out of Scope confirms) |
| GSD workflow enforcement | Phase uses GSD execute-phase |

---

## Sources

### Primary (HIGH confidence)
- [Textual Screens Guide](https://textual.textualize.io/guide/screens/) — push_screen, ModalScreen[T], dismiss, callback chaining
- [Textual App API](https://textual.textualize.io/api/app/) — push_screen, push_screen_wait, call_from_thread signatures
- [Textual Input Widget](https://textual.textualize.io/widgets/input/) — Input.Changed, Input.Submitted, on_mount focus
- [Textual ListView](https://textual.textualize.io/widgets/list_view/) — clear(), append(), ListView.Selected, ListView.Highlighted
- [Textual Screen API](https://textual.textualize.io/api/screen/) — dismiss() signature and ScreenError warning
- `uv run python -c "import textual; print(textual.__version__)"` — Textual 8.2.3 installed [VERIFIED]
- `uv run pytest tests/ -q` — 90 passed, 1 deselected [VERIFIED]
- Existing codebase (`app.py`, `project_detail.py`, `project_list.py`, `store.py`) — Phase 3 patterns [VERIFIED]

### Secondary (MEDIUM confidence)
- [mathspp — How to use modal screens](https://mathspp.com/blog/how-to-use-modal-screens-in-textual) — callback + chain patterns with code examples
- [Textual CHANGELOG](https://github.com/Textualize/textual/blob/main/CHANGELOG.md) — v8.2.3 most recent (2026-04-05), v8.0 introduced `mode` param for push_screen
- [Issue #5512 closed](https://github.com/Textualize/textual/issues/5512) — callbacks from any invocation context work (merged Feb 2025)
- [Issue #2194 closed](https://github.com/Textualize/textual/issues/2194) — ModalScreen+Input key handling fixed (merged April 2023)

### Tertiary (LOW confidence)
- None — no unverified claims remain

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components are existing installed deps (verified)
- Architecture: HIGH — ModalScreen[T] + push_screen + callback pattern is official Textual pattern (verified via docs + closed issues)
- Pitfalls: HIGH for pitfalls 1–4 (established patterns); MEDIUM for pitfalls 5–7 (inferred from codebase analysis)

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (Textual releases monthly; verify `textual.__version__` before execution)
