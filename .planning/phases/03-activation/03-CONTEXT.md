# Phase 3: Activation - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire `o`/`O`/`space` into the existing TUI to deliver the core value: instant artifact access. Users can open any selected object (`o`), open all "open by default" objects for the current project (`O`), and toggle an object's default-open status (`space`). Each object displays a visual indicator of its status. Status feedback shown after every activation. No new widgets, no CRUD — purely wiring operations into the existing shell.

</domain>

<decisions>
## Implementation Decisions

### Open-by-default Indicator (ACT-04)

- **D-01:** Each `ObjectRow` displays a filled/empty dot (`●`/`○`) to the **left of the icon**. Row format becomes: `● {icon}  {label}  {value}` (filled = in default set, empty = not). This updates immediately when `space` is pressed.
- **D-02:** The dot character uses the same muted color as the row text when empty, and an accent color (or white) when filled — subtle contrast without a dedicated column.

### Status Bar Feedback (CORE-05)

- **D-03:** Use Textual's `app.notify()` toast for all activation feedback — floating, brief, doesn't disrupt layout.
- **D-04:** Message format includes the object value (short with value): `"Copied: feature/auth-refactor"`, `"Opened: notion.so/..."`, `"Opened in iTerm2: joy-agents"`. Trim long values with `…` if needed.
- **D-05:** Errors (subprocess failures) also use `app.notify()` with severity `"error"`.

### Bulk Open — O (ACT-02)

- **D-06:** `O` opens default objects **sequentially** in display order (matching `GROUP_ORDER` from `project_detail.py`). Each open fires in a background thread loop, not concurrent threads.
- **D-07:** On failure, **continue** — skip the failed object, proceed with remaining, then show one error toast per failure at the end.
- **D-08:** Feedback: **one toast per object** opened, same format as single `o`. Consistent UX regardless of how many objects open.

### Key Binding Scope

- **D-09:** `o` and `space` are bound **on `ProjectDetail`** (detail pane only). They fire only when the detail pane has focus. Standard Textual BINDINGS scoping handles this naturally.
- **D-10:** `O` is bound **globally on `JoyApp`** — fires from any pane (project list or detail). Uses the currently highlighted project's objects, regardless of which pane has focus. User can "launch everything" without navigating to the detail pane.
- **D-11:** If `o` is pressed with no highlighted object (empty project), show an error toast: `"No object selected"`. Silent no-op for `O` when no default objects exist.

### Persistence — space toggle (ACT-03)

- **D-12:** Toggle writes immediately to TOML via `store.save_projects()` in a background thread (`@work(thread=True)`). No batch-on-exit — same atomic-write pattern already established in `store.py`.

### Claude's Discretion

- Exact dot character encoding and Rich color for filled/empty state
- Whether `O` from the project list requires Enter first or reads the highlighted project directly
- Delay (if any) between sequential opens in `O` — start with 0ms, adjust if needed
- BINDINGS placement for `O` on `JoyApp` vs a priority binding

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements for this phase
- `.planning/REQUIREMENTS.md` — ACT-01, ACT-02, ACT-03, ACT-04, CORE-05 (the 5 requirements Phase 3 must satisfy)

### Foundation layer
- `.planning/phases/01-foundation/01-CONTEXT.md` — Data model decisions (D-06–D-12), operations architecture, iTerm2 AppleScript approach
- `src/joy/operations.py` — `open_object()` dispatcher + all 6 openers (string, url, obsidian, file, worktree, iterm) — Phase 3 calls this directly
- `src/joy/store.py` — `save_projects()` for persisting toggle changes; atomic write already established

### TUI Shell layer
- `.planning/phases/02-tui-shell/02-CONTEXT.md` — Display decisions (D-01–D-11), pane navigation model, focus/escape behavior
- `src/joy/widgets/project_detail.py` — `highlighted_object` property, `_rows` list, `GROUP_ORDER` for display order; Phase 3 adds `o`/`space` bindings here
- `src/joy/widgets/object_row.py` — Current row rendering; Phase 3 adds the `●`/`○` indicator column
- `src/joy/app.py` — `JoyApp`; Phase 3 adds `O` binding here, plus `Config` loading for passing to `open_object()`

### Models
- `src/joy/models.py` — `ObjectItem.open_by_default` field, `ObjectItem.object_type` property, `Config` dataclass (needed by `open_object()`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `operations.open_object(item=..., config=...)` — fully implemented, all 7 object types covered. Phase 3 just calls this.
- `ProjectDetail.highlighted_object` — property returning the selected `ObjectItem` or `None`. Ready for Phase 3.
- `store.save_projects(projects)` — atomic TOML write, already established pattern.
- `@work(thread=True)` decorator — used in Phase 2 for async store loading. Same pattern for activation to avoid blocking TUI.
- `app.notify()` — built into Textual App. No additional widget needed for feedback.

### Established Patterns
- Background thread via `@work(thread=True)` + `call_from_thread()` for all I/O (CP-1 compliance).
- `BINDINGS` class variable on widgets for scoped key bindings — `ProjectDetail` already has `escape`, `j/k`, `up/down`.
- `ObjectRow` is a `Static` widget; updating its rendered text requires remounting or `update()` call.
- `Config` is loaded in Phase 2 startup but stored on `JoyApp._config` (or needs to be — currently it's only passed to store, not cached). Phase 3 needs `Config` accessible from the app to pass to `open_object()`.

### Integration Points
- `ProjectDetail` → needs `o` and `space` BINDINGS + `action_open_object()` and `action_toggle_default()` methods
- `JoyApp` → needs `O` binding + `action_open_all_defaults()` method; needs `Config` stored as `self._config`
- `ObjectRow` → needs `●`/`○` prepended to rendered text; must be updatable in-place when `space` toggles
- `store.py` → `save_projects()` called after toggle; needs access to full project list (stored on `JoyApp._projects`)

</code_context>

<specifics>
## Specific Ideas

- `O` is global — user can hit `O` from the project list without pressing Enter first. `JoyApp` reads the highlighted project directly.
- Error toast for "No object selected" when `o` pressed with empty detail pane.
- Sequential opens for `O` with continue-on-error — user gets as many artifacts open as possible even if one fails.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 3 scope.

</deferred>

---

*Phase: 03-activation*
*Context gathered: 2026-04-11*
