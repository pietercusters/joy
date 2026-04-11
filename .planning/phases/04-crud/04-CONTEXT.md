# Phase 4: CRUD - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Add, edit, and delete projects and objects through modal forms with keyboard navigation and confirmation dialogs. Wires `n` (new project), `a` (add object), `e` (edit object), `d` (delete object), and `delete`/`D` (delete project) into the existing TUI shell. No new display widgets beyond modal overlays — purely mutations plus the Textual ModalScreen infrastructure.

</domain>

<decisions>
## Implementation Decisions

### Project Creation Flow

- **D-01:** New project creation is triggered by `n` — bound **globally on `JoyApp`** (available from both project list and detail pane). Same global-binding pattern as `O`.
- **D-02:** Project creation is a **two-step flow**: (1) a modal prompts for the project name, (2) immediately after confirming the name, the add-object form opens.
- **D-03:** After the user adds one object, the add-object form **loops back** automatically so they can keep adding objects. The user presses Escape to finish and land in the detail pane of the new project.
- **D-04:** After the new project is created (name confirmed), it is immediately added to `JoyApp._projects`, persisted via `save_projects()`, and the project list is refreshed to show and select the new project before the add-object form opens.

### Object Add Form

- **D-05:** The add-object form uses a **type-to-filter preset picker**: the user types characters and the list of 9 preset kinds filters in real-time. j/k or arrow keys navigate the filtered list; Enter selects. No generic/custom type option in Phase 4.
- **D-06:** After selecting a preset type, a second input captures the **value only** — no label field. The `label` field on `ObjectItem` remains empty (the raw value is used for display, which is the current `ObjectRow` behavior).
- **D-07:** The add form is presented as a **Textual ModalScreen pushed via `push_screen()`**. The outer project-creation flow composes two sequential modal screens: name input → add-object loop.

### Object Edit Form

- **D-08:** Pressing `e` on a highlighted object opens a modal pre-populated with the current value. The user edits the value only — **the preset kind (type) is fixed and cannot be changed**. Escape cancels, Enter confirms.
- **D-09:** `e` is bound on `ProjectDetail` (detail pane only, same scope as `o` and `space`). Editing an object updates `ObjectItem.value` in-place, refreshes the `ObjectRow`, and persists via `save_projects()` in a background thread.

### Object Deletion

- **D-10:** Pressing `d` on a highlighted object shows a **modal confirmation dialog**: "Delete {kind} '{value}'? Press Enter to delete, Escape to cancel." Enter confirms and removes the object; Escape dismisses with no change.
- **D-11:** `d` is bound on `ProjectDetail`. After deletion, the cursor moves to the previous row (or stays at the same index if it was the last item). The object list is re-rendered and persisted atomically.

### Project Deletion

- **D-12:** Pressing `delete` (the delete key) from the **project list pane** (when focus is on `JoyListView`) shows a modal confirmation: "Delete project '{name}'? This will remove it and all its objects. Press Enter to delete, Escape to cancel."
- **D-13:** After project deletion, the adjacent project is selected (next project if available, else previous). `JoyApp._projects` is updated, persisted, and the project list refreshed.

### Confirmation Modal Design

- **D-14:** Confirmation dialogs are small centered **`ModalScreen`** overlays (not inline footer prompts). Enter confirms the destructive action; Escape always cancels — consistent with CORE-04 ("Escape always navigates back; no focus traps").
- **D-15:** Modal content shows the item name/value so users can confirm they're deleting the right thing.

### Persistence Pattern

- **D-16:** All mutations (add object, edit object, delete object, delete project, create project) persist via `save_projects(JoyApp._projects)` in a `@work(thread=True)` background thread — same pattern as Phase 3's toggle persistence.

### Claude's Discretion

- Exact `ModalScreen` widget hierarchy for name input vs preset picker vs confirmation dialog
- How the type-to-filter filtering is implemented in Textual (custom `Input` + `ListView` pair, or using `SelectionList`)
- CSS for modal overlays (centering, width, border style)
- Exact copy for toast notifications after add/edit/delete operations
- Key binding for project delete — `delete` key vs `D` (capital) — choose whichever Textual handles more cleanly
- Error handling if project name already exists (show error message in the modal)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements for this phase
- `.planning/REQUIREMENTS.md` — PROJ-04, PROJ-05, MGMT-01, MGMT-02, MGMT-03 (the 5 requirements Phase 4 must satisfy)

### Foundation layer (data model, persistence)
- `.planning/phases/01-foundation/01-CONTEXT.md` — Data model decisions (D-01–D-14): dataclasses, TOML schema, atomic write pattern
- `src/joy/models.py` — `Project`, `ObjectItem`, `Config`, `PresetKind`, `ObjectType`, `PRESET_MAP` — CRUD modifies these
- `src/joy/store.py` — `save_projects()`, `load_projects()` — atomic write already established; Phase 4 calls `save_projects()` after every mutation

### TUI Shell layer
- `.planning/phases/02-tui-shell/02-CONTEXT.md` — Display decisions: object row format, pane navigation, footer key hints
- `src/joy/app.py` — `JoyApp`: `_projects`, `_config`, `BINDINGS` — Phase 4 adds `n` binding and `action_new_project()` here
- `src/joy/widgets/project_detail.py` — `ProjectDetail`: `BINDINGS`, `_cursor`, `_rows`, `highlighted_object` — Phase 4 adds `a`, `e`, `d` bindings here
- `src/joy/widgets/project_list.py` — `ProjectList`, `JoyListView`: Phase 4 adds project-delete binding here; `set_projects()` used to refresh after create/delete
- `src/joy/widgets/object_row.py` — `ObjectRow`: may need updates if row needs to refresh after edit

### Activation layer (established patterns)
- `.planning/phases/03-activation/03-CONTEXT.md` — Key binding scope decisions (D-09, D-10): `o`/`space` on `ProjectDetail`, `O` globally on `JoyApp`; `@work(thread=True)` + `call_from_thread()` pattern; `app.notify()` toast pattern
- `src/joy/app.py` — `_open_defaults()` and `_save_toggle()` — reference implementations for background-thread persistence pattern

### Critical pitfalls
- `.planning/research/PITFALLS.md` — CP-1 (blocking event loop), CP-2 (slow startup/imports), CP-3 (fire-and-forget async): all apply to modal forms and persistence

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `store.save_projects(projects)` — atomic TOML write, fully established. Phase 4 calls this after every mutation.
- `@work(thread=True, exit_on_error=False)` + `self.app.call_from_thread()` — established pattern for non-blocking I/O (Phase 3). Use for all save operations in Phase 4.
- `app.notify(message, severity="error")` — toast notifications, already used in Phases 2-3. Use for success/error feedback after CRUD operations.
- `ProjectList.set_projects(projects)` — rebuilds and refreshes the left pane. Call after project create/delete.
- `ProjectDetail._render_project()` / `set_project(project)` — rebuilds detail pane rows. Call after object add/edit/delete.
- `ProjectDetail.highlighted_object` — property returning selected `ObjectItem | None`. Gate for `e` and `d` actions.
- `JoyApp._projects` — single source of truth for the project list. All mutations must update this list.

### Established Patterns
- **Global vs pane-scoped bindings**: `O` on `JoyApp` is the pattern for global keys; `o`/`space`/`escape` on `ProjectDetail` for pane-scoped. Phase 4: `n` global, `a`/`e`/`d` on `ProjectDetail`, `delete` on `JoyListView` or `ProjectList`.
- **Background thread I/O**: All `save_projects()` calls go in `@work(thread=True)` methods. Never call blocking I/O in action handlers.
- **Deferred render**: `set_project()` uses `call_after_refresh()` to avoid DOM manipulation before widgets are fully mounted. Modal dismiss + project list update may need the same care.
- **No inline editing**: Out of scope per REQUIREMENTS.md — all editing uses modal overlays.

### Integration Points
- `JoyApp` → needs `n` binding + `action_new_project()` method (mirrors `action_open_all_defaults()` structure)
- `ProjectDetail` → needs `a`, `e`, `d` BINDINGS + corresponding action methods
- `JoyListView` (or `ProjectList`) → needs `delete` binding for project deletion
- New: `ModalScreen` subclasses for name input, preset picker (with filter), value input, confirmation dialog
- `ProjectList.set_projects()` must be called after project create/delete to refresh left pane
- `ProjectDetail.set_project()` must be called after object add/edit/delete to refresh right pane

</code_context>

<specifics>
## Specific Ideas

- `n` is global — user can create a new project from the project list or detail pane without switching focus first.
- Project creation is a sequential flow: name modal → add-object loop modal (escape to finish).
- Add-object form loops until Escape — consistent with adding multiple objects without re-pressing `a`.
- Type-to-filter in add form: user types (e.g., "br") and the list filters to "branch". j/k or arrow navigates. Enter selects.
- Delete confirmation always shows the item name so users know exactly what they're deleting.

</specifics>

<deferred>
## Deferred Ideas

- Label field on ObjectItem — the model has it but forms won't expose it in Phase 4. Phase 5 or later.
- Generic/custom object type (non-preset) — not in Phase 4 scope.
- Duplicate project name validation UX — Claude's discretion for error message approach.

None — discussion stayed within Phase 4 scope.

</deferred>

---

*Phase: 04-crud*
*Context gathered: 2026-04-11*
