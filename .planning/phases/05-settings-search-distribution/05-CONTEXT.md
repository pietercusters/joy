# Phase 5: Settings, Search & Distribution - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Dedicated settings screen (global config editing), real-time project filtering, and distribution packaging (`uv tool install`, `joy --version`, README). Object reordering (MGMT-04) is explicitly out of scope — deferred as needlessly complex for v1.

</domain>

<decisions>
## Implementation Decisions

### Settings Screen

- **D-01:** Settings screen is a **ModalScreen overlay** — `push_screen(SettingsModal())` sits on top of the main view (dimmed background). Consistent with Phase 4 modal patterns.
- **D-02:** The modal contains **5 editable fields** for the `Config` model: `ide`, `editor`, `obsidian_vault`, `terminal`, and `default_open_kinds`.
- **D-03:** `default_open_kinds` is edited via a **multi-select checklist** showing all 9 preset kinds with toggle checkboxes. The checklist section inside the modal is scrollable to handle the height.
- **D-04:** On **Escape**, the modal dismisses without saving. On **Save** (Enter or a Save button), the updated `Config` is persisted via `save_config()` in a `@work(thread=True)` background thread — same pattern as `_save_projects_bg()`.
- **D-05:** Settings is triggered by a global key binding on `JoyApp` (accessible from both panes). Key choice is Claude's discretion — `s` is natural and currently unbound.

### Project Filtering

- **D-06:** Pressing `/` enters filter mode. A **Textual `Input` widget mounts inline at the top of the project list pane** — not a modal.
- **D-07:** The project list filters **in real-time** as the user types: only projects whose names contain the substring (case-insensitive) are shown.
- **D-08:** **Escape exits filter mode**, unmounts the input, and restores the full unfiltered project list. Clearing the input text also restores the full list.
- **D-09:** Filtering operates on `ProjectList._projects` — the filtered view calls `set_projects()` with the subset. The canonical `JoyApp._projects` list is never mutated by filtering.
- **D-10:** `/` is bound on `JoyListView` (or `ProjectList`) — pane-scoped, same scope as `j`/`k`.

### Distribution & Packaging

- **D-11:** `joy --version` outputs the installed version before launching the TUI. Implementation: check `sys.argv` for `--version` at the top of `main()` and print the version from `importlib.metadata`, then exit. No `argparse` — keeps `main()` minimal.
- **D-12:** README covers: installation (`uv tool install git+<repo>`), first-run setup (config.toml location, required fields), and key usage (key bindings reference). Claude's discretion for exact structure and prose.

### Object Reordering

- **D-13 (DEFERRED):** MGMT-04 (`J`/`K` object reorder) is **explicitly out of scope for Phase 5** — deferred as needlessly complex. The `J`/`K` bindings are NOT added.

### Claude's Discretion

- Exact key for opening settings (`s` is the natural choice — unbound globally)
- SettingsModal CSS: centering, width, height, border style
- Tab/Shift+Tab navigation between the 5 fields inside the modal
- Whether Save is triggered by Enter on the last field, a dedicated Save button, or both
- Toast copy after saving settings ("Settings saved")
- README structure and prose
- `joy --version` version string format (e.g., `joy 0.1.0`)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements for this phase
- `.planning/REQUIREMENTS.md` — SETT-01 through SETT-06, PROJ-06, DIST-01, DIST-03, DIST-04 (the requirements Phase 5 must satisfy). Note: MGMT-04 is explicitly deferred.

### Foundation layer (data model, persistence)
- `src/joy/models.py` — `Config` dataclass with all 5 fields (`ide`, `editor`, `obsidian_vault`, `terminal`, `default_open_kinds`)
- `src/joy/store.py` — `load_config()` and `save_config()` already implemented with atomic write

### TUI Shell layer
- `.planning/phases/02-tui-shell/02-CONTEXT.md` — Pane navigation, footer key hints, focus patterns
- `src/joy/app.py` — `JoyApp`: `_config`, `BINDINGS`, `_load_data()` (already calls `load_config`) — Phase 5 adds settings binding here
- `src/joy/widgets/project_list.py` — `JoyListView`, `ProjectList`, `set_projects()` — Phase 5 adds `/` filter binding and inline input here

### CRUD layer (established modal patterns)
- `.planning/phases/04-crud/04-CONTEXT.md` — ModalScreen pattern (D-07), `@work(thread=True)` + `save_projects()`, toast notifications — all reused for SettingsModal and `save_config()`
- `src/joy/screens/` — Existing ModalScreen implementations as reference: `NameInputModal`, `PresetPickerModal`, `ValueInputModal`, `ConfirmationModal`

### Packaging
- `pyproject.toml` — entry point already defined (`joy = "joy.app:main"`), version is `0.1.0`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `store.save_config(config)` — atomic TOML write, fully implemented. Phase 5 calls this after settings save.
- `store.load_config()` — already called in `JoyApp._load_data()`; `JoyApp._config` is populated at startup.
- `@work(thread=True, exit_on_error=False)` + `call_from_thread()` — established pattern for non-blocking I/O. Use for `save_config()` call.
- `app.notify(message)` — toast notifications, already used throughout. Use for "Settings saved" feedback.
- `ProjectList.set_projects(projects)` — rebuilds the left pane list. Filtering calls this with a subset.
- `JoyApp._projects` — canonical list; never mutated by filter. Filter passes a filtered copy to `set_projects()`.
- `src/joy/screens/` — Four existing ModalScreen subclasses as implementation reference for SettingsModal.

### Established Patterns
- **ModalScreen**: `push_screen(Modal(), callback)` — established in Phase 4. SettingsModal follows the same push pattern; callback receives the updated Config (or None if cancelled).
- **Global vs pane-scoped bindings**: Settings key (`s`) goes on `JoyApp.BINDINGS` (global). `/` filter goes on `JoyListView.BINDINGS` (pane-scoped).
- **Background thread I/O**: All `save_config()` calls in `@work(thread=True)` methods.
- **Lazy imports inside workers**: `from joy.store import save_config` inside the worker function (CP-2 pattern).

### Integration Points
- `JoyApp` → add settings binding + `action_settings()` method; settings callback updates `self._config`
- `JoyListView` → add `/` binding + `action_filter()` method; inline `Input` widget mounted/unmounted on the `ProjectList`
- `ProjectList` → `set_projects()` called with filtered subset during active filter; full list restored on Escape
- New: `SettingsModal(ModalScreen)` with 4 `Input` fields + 1 checklist widget for `default_open_kinds`
- `main()` in `app.py` → add `sys.argv` check for `--version` before `app.run()`

</code_context>

<specifics>
## Specific Ideas

- Settings screen is a **ModalScreen overlay** (not a full Screen replacement) — user explicitly preferred overlay consistency with Phase 4 patterns, accepting the modal height tradeoff.
- `default_open_kinds` uses a **checklist** inside the modal with internal scrolling — user explicitly chose checklist over text input despite the modal height concern.
- Object reorder (`J`/`K`, MGMT-04) is **explicitly skipped** — user decision, not a planning oversight.

</specifics>

<deferred>
## Deferred Ideas

### Object Reordering (MGMT-04)
- `J`/`K` to move objects up/down in the detail pane — explicitly deferred by user as needlessly complex for v1. Can be added in a future phase if needed.

</deferred>

---

*Phase: 05-settings-search-distribution*
*Context gathered: 2026-04-11*
