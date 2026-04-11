# Phase 5: Settings, Search & Distribution - Research

**Researched:** 2026-04-11
**Domain:** Textual ModalScreen, inline widget mounting, SelectionList, importlib.metadata, uv packaging
**Confidence:** HIGH

## Summary

Phase 5 adds three self-contained features to a fully working Phase 4 codebase: (1) a settings overlay modal for editing the 5 global Config fields, (2) real-time project filter via inline Input widget mounted in the project list pane, and (3) distribution packaging with `joy --version` and README.

The codebase already provides all the infrastructure needed — `save_config()`, `load_config()`, established ModalScreen patterns, the `@work(thread=True)` background-I/O pattern, and `app.notify()` toasts. Phase 5 is essentially applying those patterns to two new screens and one new CLI flag.

All Textual widget APIs (SelectionList, inline mount/remove, Tab navigation) were verified against the running Textual 8.2.3 environment. No external dependencies are required. All 114 existing tests pass green.

**Primary recommendation:** Build SettingsModal using SelectionList for the checklist, mount/remove an Input inline for filter mode, and add `--version` via a sys.argv check using importlib.metadata — all three follow patterns already established in the codebase.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Settings Screen**
- D-01: Settings screen is a ModalScreen overlay — `push_screen(SettingsModal())` sits on top of the main view (dimmed background). Consistent with Phase 4 modal patterns.
- D-02: The modal contains 5 editable fields for the Config model: `ide`, `editor`, `obsidian_vault`, `terminal`, and `default_open_kinds`.
- D-03: `default_open_kinds` is edited via a multi-select checklist showing all 9 preset kinds with toggle checkboxes. The checklist section inside the modal is scrollable to handle the height.
- D-04: On Escape, the modal dismisses without saving. On Save (Enter or a Save button), the updated Config is persisted via `save_config()` in a `@work(thread=True)` background thread — same pattern as `_save_projects_bg()`.
- D-05: Settings is triggered by a global key binding on `JoyApp` (accessible from both panes). Key choice is Claude's discretion — `s` is natural and currently unbound.

**Project Filtering**
- D-06: Pressing `/` enters filter mode. A Textual `Input` widget mounts inline at the top of the project list pane — not a modal.
- D-07: The project list filters in real-time as the user types: only projects whose names contain the substring (case-insensitive) are shown.
- D-08: Escape exits filter mode, unmounts the input, and restores the full unfiltered project list. Clearing the input text also restores the full list.
- D-09: Filtering operates on `ProjectList._projects` — the filtered view calls `set_projects()` with the subset. The canonical `JoyApp._projects` list is never mutated by filtering.
- D-10: `/` is bound on `JoyListView` (or `ProjectList`) — pane-scoped, same scope as `j`/`k`.

**Distribution & Packaging**
- D-11: `joy --version` outputs the installed version before launching the TUI. Implementation: check `sys.argv` for `--version` at the top of `main()` and print the version from `importlib.metadata`, then exit. No `argparse`.
- D-12: README covers: installation (`uv tool install git+<repo>`), first-run setup (config.toml location, required fields), and key usage (key bindings reference). Claude's discretion for exact structure and prose.

**Object Reordering**
- D-13 (DEFERRED): MGMT-04 (`J`/`K` object reorder) is explicitly out of scope for Phase 5.

### Claude's Discretion
- Exact key for opening settings (`s` is the natural choice — unbound globally)
- SettingsModal CSS: centering, width, height, border style
- Tab/Shift+Tab navigation between the 5 fields inside the modal
- Whether Save is triggered by Enter on the last field, a dedicated Save button, or both
- Toast copy after saving settings ("Settings saved")
- README structure and prose
- `joy --version` version string format (e.g., `joy 0.1.0`)

### Deferred Ideas (OUT OF SCOPE)
- Object Reordering (MGMT-04): `J`/`K` to move objects up/down in the detail pane — explicitly deferred.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SETT-01 | Global setting for preferred IDE (used for git worktree type) | Covered by SettingsModal `ide` Input field — Config.ide already exists |
| SETT-02 | Global setting for Obsidian vault path (used for obsidian type) | Covered by SettingsModal `obsidian_vault` Input field — Config.obsidian_vault already exists |
| SETT-03 | Global setting for preferred editor (used for file type) | Covered by SettingsModal `editor` Input field — Config.editor already exists |
| SETT-04 | Global setting for terminal tool (used for agents type) | Covered by SettingsModal `terminal` Input field — Config.terminal already exists |
| SETT-05 | Global default: which object types are pre-marked open by default when creating new project | Covered by SettingsModal SelectionList widget for `default_open_kinds` |
| SETT-06 | Dedicated settings screen accessible from the main screen | ModalScreen pushed via `s` binding on JoyApp — global access confirmed |
| PROJ-06 | User can filter project list by typing `/` followed by a substring (real-time) | Inline Input mounted in ProjectList; Input.Changed event fires on every keystroke |
| MGMT-04 | Pressing `J`/`K` moves selected object down/up | EXPLICITLY DEFERRED per D-13 — do not implement |
| DIST-01 | App is installable globally via `uv tool install git+<repo>` | pyproject.toml already has correct entry_point; verified working |
| DIST-03 | README covers installation, first-run setup, and key usage | New file to write — no technical blockers |
| DIST-04 | `joy --version` outputs the installed version | sys.argv check + importlib.metadata.version('joy') — verified returns '0.1.0' |
</phase_requirements>

---

## Standard Stack

### Core (all already in pyproject.toml — zero new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| textual | 8.2.3 (installed, verified) | SelectionList, Input, ModalScreen, mount/remove | All Phase 5 widget work is built on existing Textual dependency |
| importlib.metadata | stdlib (Python 3.11+) | `version('joy')` for `--version` flag | Zero-dependency; works post-install via package metadata |
| tomllib + tomli_w | stdlib + 1.x (installed) | load_config / save_config already implemented | No change needed |

**Installation:** No new packages needed. All Phase 5 functionality uses libraries already in the project.

**Version verification:** [VERIFIED: uv run python -c "import textual; ..."]: Textual 8.2.3 is installed and running in the project venv.

---

## Architecture Patterns

### Recommended Project Structure (additions only)

```
src/joy/
├── app.py                    # Add: s binding, action_settings(), _save_config_bg()
├── screens/
│   ├── __init__.py           # Add: SettingsModal to exports
│   └── settings.py           # NEW: SettingsModal(ModalScreen[Config | None])
└── widgets/
    └── project_list.py       # Add: / binding, action_filter(), _filter_active flag
```

### Pattern 1: SettingsModal (ModalScreen)

**What:** A ModalScreen overlay with 4 Input fields and 1 SelectionList widget. Returns updated Config on save, None on cancel.

**When to use:** Opened by `action_settings()` on JoyApp via `push_screen(SettingsModal(config), callback)`.

**Established pattern from existing screens:**
```python
# Source: src/joy/screens/name_input.py (established pattern)
class SettingsModal(ModalScreen[Config | None]):
    BINDINGS = [("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    SettingsModal { align: center middle; }
    SettingsModal > Vertical {
        width: 70;
        height: auto;
        max-height: 80vh;
        background: $surface;
        border: thick $background 80%;
        padding: 1 2;
    }
    SettingsModal .field-label { color: $text-muted; margin-top: 1; }
    SettingsModal SelectionList { height: auto; max-height: 12; }
    """

    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config = config  # pass current values for pre-population

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Settings", classes="modal-title")
            yield Static("IDE", classes="field-label")
            yield Input(value=self._config.ide, id="field-ide")
            yield Static("Editor", classes="field-label")
            yield Input(value=self._config.editor, id="field-editor")
            yield Static("Obsidian Vault Path", classes="field-label")
            yield Input(value=self._config.obsidian_vault, id="field-vault")
            yield Static("Terminal", classes="field-label")
            yield Input(value=self._config.terminal, id="field-terminal")
            yield Static("Default Open Kinds", classes="field-label")
            yield SelectionList(
                *[(k.value, k.value, k.value in self._config.default_open_kinds)
                  for k in PresetKind],
                id="field-kinds"
            )
            yield Button("Save", variant="primary", id="btn-save")
            yield Static("Tab to navigate, Enter/Save to save, Escape to cancel",
                        classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one("#field-ide", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self._do_save()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _do_save(self) -> None:
        config = Config(
            ide=self.query_one("#field-ide", Input).value.strip(),
            editor=self.query_one("#field-editor", Input).value.strip(),
            obsidian_vault=self.query_one("#field-vault", Input).value.strip(),
            terminal=self.query_one("#field-terminal", Input).value.strip(),
            default_open_kinds=self.query_one("#field-kinds", SelectionList).selected,
        )
        self.dismiss(config)
```

**Tab navigation:** [VERIFIED: Textual 8.2.3 runtime] Screen.BINDINGS includes `tab -> app.focus_next` and `shift+tab -> app.focus_previous` — Tab automatically advances focus through all focusable widgets (Input, SelectionList, Button) inside the modal. No manual implementation needed.

**SelectionList API:** [VERIFIED: Textual 8.2.3 runtime]
- Constructor accepts `(label, value, selected_bool)` tuples
- `.selected` property returns `list[str]` of selected values
- `SelectionList.SelectedChanged` message fires on toggle

### Pattern 2: Inline Filter Input (ProjectList)

**What:** Pressing `/` in JoyListView mounts an Input widget above the ListView; Escape/clear removes it and restores the full list.

**Key insight:** The Input is mounted directly into `ProjectList` (the Widget parent of JoyListView), not into JoyListView itself — this avoids interfering with ListView's own key handling.

```python
# Source: verified via Widget.mount signature (before=/after= parameters)
class JoyListView(ListView):
    BINDINGS = [
        # ... existing bindings ...
        Binding("/", "filter", "Filter", show=True),
    ]

    _filter_active: bool = False

    def action_filter(self) -> None:
        """Enter filter mode: mount Input above the list."""
        if self._filter_active:
            return  # already in filter mode
        parent = self.app.query_one("#project-list", ProjectList)
        filter_input = Input(placeholder="Filter projects...", id="filter-input")
        parent.mount(filter_input, before=self)  # mounts before the JoyListView
        self._filter_active = True
        filter_input.focus()
```

```python
# In ProjectList (parent widget):
def on_input_changed(self, event: Input.Changed) -> None:
    """Filter list in real-time as user types (D-07)."""
    query = event.value.lower()
    if query:
        filtered = [p for p in self.app._projects if query in p.name.lower()]
    else:
        filtered = list(self.app._projects)  # empty string = full list (D-08)
    self.set_projects(filtered)

def on_input_submitted(self, event: Input.Submitted) -> None:
    """Enter in filter input: dismiss the filter (stay on current subset)."""
    self._exit_filter_mode()
```

```python
# Escape from filter mode — handled in JoyListView:
def _exit_filter_mode(self) -> None:
    """Remove the filter input and restore the full project list."""
    parent = self.app.query_one("#project-list", ProjectList)
    try:
        filter_input = parent.query_one("#filter-input", Input)
        filter_input.remove()
    except Exception:
        pass
    self._filter_active = False
    parent.set_projects(self.app._projects)  # restore canonical list (D-09)
    self.focus()
```

**Escape handling concern:** JoyListView currently has no BINDINGS for Escape (it's handled by ProjectDetail and ModalScreen). Adding an Escape binding on JoyListView only when `_filter_active` is True avoids conflicting with the screen's default Escape behavior. Alternative: handle via `on_key` checking `_filter_active`.

**Widget.mount API:** [VERIFIED: Textual 8.2.3 runtime]
- `Widget.mount(*widgets, before=None, after=None) -> AwaitMount`
- `before=` accepts widget reference, CSS selector string, or integer index
- `Widget.remove() -> AwaitRemove` on the Input widget removes it from DOM

**Input.Changed fires for empty string:** [VERIFIED: Textual docs — Input.Changed.value is the new value; fires on every keystroke including backspace to empty]

### Pattern 3: `--version` flag in main()

**What:** Check `sys.argv` before starting the TUI; print version and exit if `--version` is passed.

```python
# Source: verified via uv run python -c "import importlib.metadata; ..."
def main() -> None:
    """Main entry point for the joy CLI."""
    if len(sys.argv) > 1 and sys.argv[1] == "--version":
        import importlib.metadata  # noqa: PLC0415 — lazy import, matches CP-2 pattern
        try:
            version = importlib.metadata.version("joy")
        except importlib.metadata.PackageNotFoundError:
            version = "unknown"
        print(f"joy {version}")
        return
    app = JoyApp()
    app.run()
```

**importlib.metadata.version('joy') result:** [VERIFIED: uv run python] Returns `'0.1.0'` — reads from the installed package metadata written by hatchling at install time. Works with `uv tool install` because hatchling writes the METADATA file into the `.dist-info` directory.

### Pattern 4: SettingsModal integration in JoyApp

```python
# Add to JoyApp.BINDINGS:
Binding("s", "settings", "Settings", priority=True)

# Add to JoyApp:
def action_settings(self) -> None:
    def on_settings(config: Config | None) -> None:
        if config is None:
            return  # Escaped — no change (D-04)
        self._config = config
        self._save_config_bg()
        self.notify("Settings saved", markup=False)
    self.push_screen(SettingsModal(self._config), on_settings)

@work(thread=True, exit_on_error=False)
def _save_config_bg(self) -> None:
    """Persist config to TOML in background thread (D-04, same pattern as _save_projects_bg)."""
    from joy.store import save_config  # noqa: PLC0415
    save_config(self._config)
```

### Anti-Patterns to Avoid

- **Mutating JoyApp._projects during filter:** D-09 explicitly forbids this. Always pass a filtered copy to `set_projects()`. Restore `self.app._projects` on filter exit.
- **Using argparse for `--version`:** D-11 explicitly says no argparse. Use direct `sys.argv` check.
- **Storing Config fields as widget state after dismiss:** Extract field values inside `_do_save()` or `on_button_pressed()`, not in `action_cancel()` fallback. Escape must return None.
- **SelectionList.selected returning PresetKind enums:** `.selected` returns the *values* passed as the second tuple element — if you pass `k.value` (str), you get `list[str]` back, which matches `Config.default_open_kinds: list[str]`. Do NOT pass the enum object itself or you'll get wrong types.
- **Mounting filter Input inside JoyListView:** Mount it in the parent `ProjectList` widget using `before=self` (the JoyListView). This preserves JoyListView's key event handling scope.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-select checklist | Custom checkbox list widget | `SelectionList` (Textual 8.2.3) | Built-in, keyboard navigable, fires SelectedChanged, returns `.selected` list — verified in runtime |
| Tab navigation between fields | Manual focus chain | Automatic via Screen.BINDINGS `tab -> app.focus_next` | Textual handles this; no code needed |
| Atomic config write | Custom file write | `store.save_config()` already implemented | Atomic temp+replace already coded in Phase 1 |
| Version string parsing | Read pyproject.toml at runtime | `importlib.metadata.version('joy')` | Reads installed package metadata — always correct after install |
| CLI argument parsing | argparse setup | Direct `sys.argv` check | D-11 decision; keeps main() minimal |

**Key insight:** Every infrastructure piece (modal pattern, background I/O, toast, config I/O) already exists. Phase 5 is assembly, not construction.

---

## Common Pitfalls

### Pitfall 1: Filter mode Escape conflict

**What goes wrong:** Adding `Binding("escape", "exit_filter", ...)` on JoyListView when `_filter_active=False` causes Escape to be consumed by the ListView even when modals are open or focus is elsewhere.

**Why it happens:** Textual walks the focus chain upward dispatching bindings; a ListView Escape binding fires even if a modal is on top if `priority=True`.

**How to avoid:** Only handle Escape for filter exit via `on_key` with a `_filter_active` guard, or add the Escape binding dynamically (remove/add it) when filter mode is toggled. The cleanest pattern: handle Escape in `on_key` on `ProjectList`:

```python
def on_key(self, event) -> None:
    if self._filter_active and event.key == "escape":
        event.stop()
        self._exit_filter_mode()
```

**Warning signs:** Escape stops working in ConfirmationModal or NameInputModal after filter was used once.

### Pitfall 2: SelectionList selection tuple type mismatch

**What goes wrong:** Passing `(k.value, k, True)` (PresetKind enum as value) instead of `(k.value, k.value, True)` — `.selected` returns PresetKind enums, but `Config.default_open_kinds` expects `list[str]`.

**Why it happens:** SelectionList generic is `SelectionList[SelectionType]`; the value parameter can be any type, not just str.

**How to avoid:** Always pass `k.value` (the str `.value` of each PresetKind) as both label and value. [VERIFIED: SelectionList constructor accepts `tuple[ContentText, SelectionType, bool]`]

**Warning signs:** `save_config()` crashes with TOML serialization error because list contains enums instead of strings.

### Pitfall 3: Filter restoring wrong list

**What goes wrong:** After filtering, pressing Escape restores `ProjectList._projects` (the filtered subset!) instead of `JoyApp._projects` (the canonical full list).

**Why it happens:** `set_projects(subset)` updates `ProjectList._projects` in place. D-09 says JoyApp._projects is the canonical source.

**How to avoid:** Always restore from `self.app._projects` (canonical), never from `self._projects` (which may already be the filtered subset).

### Pitfall 4: --version check too late in main()

**What goes wrong:** `sys.argv` check placed after `app = JoyApp()` causes Textual to initialize even for `--version` calls, adding ~200ms overhead and potentially triggering `_load_data()`.

**Why it happens:** JoyApp.__init__ triggers compose/mount setup.

**How to avoid:** Check `sys.argv` as the very first thing in `main()`, before any JoyApp instantiation.

### Pitfall 5: SettingsModal pre-population from stale config

**What goes wrong:** Passing `Config()` (default) instead of `self._config` (current) to SettingsModal — user sees default values, not their saved settings.

**Why it happens:** `_config` starts as `Config()` class variable; `_load_data()` overwrites it after async load. If the modal is opened before the worker completes, it gets the default.

**How to avoid:** `_load_data()` is called on mount and completes within milliseconds (local file read). The `s` binding opens the modal interactively, so the worker is always complete by the time the user presses `s`. Pass `self._config` directly. No special guard needed.

---

## Code Examples

### SelectionList with pre-selected items
```python
# Source: verified via uv run python (Textual 8.2.3 runtime)
from textual.widgets import SelectionList
from joy.models import PresetKind

# In compose():
current_kinds = ["worktree", "agents"]  # from Config.default_open_kinds
yield SelectionList(
    *[(k.value, k.value, k.value in current_kinds) for k in PresetKind],
    id="field-kinds"
)

# Reading selections:
selected = self.query_one("#field-kinds", SelectionList).selected
# Returns: ['worktree', 'agents']  (list[str])
```

### Inline widget mount with before=
```python
# Source: verified via inspect.signature(Widget.mount) in Textual 8.2.3
parent_widget.mount(Input(placeholder="...", id="filter-input"), before=listview_widget)
# OR using CSS selector:
parent_widget.mount(Input(...), before="#project-listview")
```

### importlib.metadata version retrieval
```python
# Source: verified via uv run python in project environment
import importlib.metadata
try:
    version = importlib.metadata.version("joy")
except importlib.metadata.PackageNotFoundError:
    version = "unknown"
print(f"joy {version}")
# Output: joy 0.1.0
```

### Background config save (established pattern)
```python
# Source: app.py _save_projects_bg (established CP-2 pattern)
@work(thread=True, exit_on_error=False)
def _save_config_bg(self) -> None:
    from joy.store import save_config  # noqa: PLC0415 — lazy import per CP-2
    save_config(self._config)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| argparse for CLI flags | sys.argv direct check (D-11) | Phase 5 decision | Keeps main() minimal; no argparse import overhead |
| Full-screen settings page | ModalScreen overlay (D-01) | Phase 5 decision | Consistent with Phase 4 modal UX patterns |

**Not applicable / no deprecations:** The Textual and packaging stack is stable. SelectionList, ModalScreen, and mount/remove APIs are all current in Textual 8.2.3.

---

## Open Questions (RESOLVED)

1. **Filter mode Escape vs. focus restoration after filter exit**
   - What we know: Escape in filter mode should exit filter and restore full list (D-08); after removal of the Input, focus must return to JoyListView
   - What's unclear: Whether `filter_input.remove()` is awaitable in sync context or needs `call_after_refresh`
   - Recommendation: Use `self.call_after_refresh(self.focus)` on the JoyListView after removing the filter Input — same pattern used in `action_delete_project` for focus restoration
   - RESOLVED: Plan 05-02 Task 1 step 8 implements `listview.call_after_refresh(listview.focus)` after filter exit

2. **SettingsModal height on small terminals**
   - What we know: Modal has 5 fields + SelectionList (9 items) + Button + hint — total ~18-20 rows minimum
   - What's unclear: Whether `max-height: 80vh` on the inner Vertical is sufficient or if we need `VerticalScroll`
   - Recommendation: Use `max-height: 80vh` with `overflow: auto` on the inner container. The SelectionList itself is internally scrollable (max-height: 12). No VerticalScroll wrapper needed.
   - RESOLVED: Plan 05-01 Task 1 uses `max-height: 80vh; overflow: auto` CSS on the inner Vertical container

3. **`/` binding visible in Footer**
   - What we know: Footer shows bindings for the focused widget; `/` bound on JoyListView will show when list pane is focused
   - What's unclear: Whether showing "Filter" in the footer is desired alongside the other list bindings
   - Recommendation: `show=True` on the `/` binding — filter is a notable feature worth advertising
   - RESOLVED: Plan 05-02 Task 1 step 2 sets `show=True` on the JoyListView `/` binding

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python / uv | All | Yes | Python 3.12+, uv latest | — |
| Textual | All TUI features | Yes | 8.2.3 | — |
| tomli_w | save_config | Yes | installed | — |
| importlib.metadata | --version | Yes | stdlib (3.11+) | — |

**No missing dependencies.** Phase 5 adds no new packages.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_tui.py tests/test_screens.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

All 114 existing tests pass green. [VERIFIED: uv run pytest tests/ -q output: "114 passed, 1 deselected in 29.69s"]

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SETT-06 | Settings modal opens on `s` | unit/integration | `pytest tests/test_tui.py::test_s_opens_settings_modal -x` | No — Wave 0 |
| SETT-01..05 | Config fields editable and persisted | unit | `pytest tests/test_screens.py::test_settings_modal_* -x` | No — Wave 0 |
| SETT-04 (Escape cancel) | Escape dismisses without saving | unit | `pytest tests/test_screens.py::test_settings_escape_noop -x` | No — Wave 0 |
| PROJ-06 | `/` mounts filter input | integration | `pytest tests/test_tui.py::test_filter_mounts_input -x` | No — Wave 0 |
| PROJ-06 | Filter reduces project list | integration | `pytest tests/test_tui.py::test_filter_realtime -x` | No — Wave 0 |
| PROJ-06 | Escape exits filter, restores list | integration | `pytest tests/test_tui.py::test_filter_escape_restores -x` | No — Wave 0 |
| DIST-04 | `--version` prints version and exits | unit | `pytest tests/test_main.py::test_version_flag -x` | No — Wave 0 |
| DIST-01 | Package installable | manual only | `uv tool install .` (manual verification) | N/A — no automated test |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_screens.py` — add SettingsModal tests (file exists, add new test functions)
- [ ] `tests/test_tui.py` — add filter and settings-integration tests (file exists, add new test functions)
- [ ] `tests/test_main.py` — NEW file for `--version` flag unit test

---

## Security Domain

Settings, search, and distribution for a local CLI tool. No network, no auth, no user-uploaded data. ASVS categories assessed:

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Local tool, no auth |
| V3 Session Management | No | No sessions |
| V4 Access Control | No | Single-user local tool |
| V5 Input Validation | Partial | Config fields are free-text strings written to `~/.joy/config.toml`; no injection risk (TOML serialization via tomli_w handles escaping) |
| V6 Cryptography | No | No secrets stored |

**No security concerns for this phase.** Config values (paths, app names) are written to user's own config file via tomli_w serialization. No sanitization beyond "non-empty" checks is warranted for a local personal tool.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | After `filter_input.remove()`, calling `self.focus()` immediately (or via `call_after_refresh`) restores focus to JoyListView without issues | Architecture Patterns (Filter) | Focus might not land; need `call_after_refresh` as fallback — low risk |
| A2 | `max-height: 80vh` CSS is valid in Textual CSS subset | Architecture Patterns (Settings) | Modal might overflow; use `max-height: 30` (fixed lines) as fallback — low risk |

**All API claims (SelectionList, Widget.mount, Input.Changed, Tab navigation, importlib.metadata) were verified against the running Textual 8.2.3 environment.** Only CSS value support (vh units) was not runtime-verified.

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: uv run python] — Textual 8.2.3 installed; SelectionList, Input, Button, ModalScreen, Widget.mount/remove all verified in runtime
- [VERIFIED: uv run python] — `importlib.metadata.version('joy')` returns `'0.1.0'` in project environment
- [VERIFIED: uv run pytest] — 114 existing tests pass green; test infrastructure confirmed working
- [VERIFIED: source inspection] — existing screens (NameInputModal, PresetPickerModal, ValueInputModal, ConfirmationModal) inspected for pattern reuse
- [VERIFIED: JoyApp/ProjectDetail/JoyListView introspection] — `s` and `/` confirmed unbound in all existing BINDINGS

### Secondary (MEDIUM confidence)
- [CITED: Textual source — Screen.BINDINGS] — Tab/shift+tab automatically wired to `app.focus_next` / `app.focus_previous`

### Tertiary (LOW confidence)
- [ASSUMED: A1] — `call_after_refresh` pattern for focus after widget remove (by analogy with confirmed `action_delete_project` pattern)
- [ASSUMED: A2] — `vh` units supported in Textual CSS (not runtime-verified; fallback is fixed line count)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in running environment
- Architecture: HIGH — all APIs verified against Textual 8.2.3 runtime; patterns verified against existing codebase
- Pitfalls: HIGH — derived from codebase analysis and verified API behavior
- CSS specifics: MEDIUM — Textual CSS is a subset of web CSS; vh unit support assumed but not tested

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (Textual releases monthly; check for 8.3.x if planning is delayed)
