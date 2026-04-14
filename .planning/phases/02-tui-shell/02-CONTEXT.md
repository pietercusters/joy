# Phase 2: TUI Shell - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Two-pane read-only Textual app: project list on the left, object detail on the right. Keyboard navigation throughout. No mutations (no creating/editing/deleting). Wires the `joy` entry point to actually launch the TUI. This phase delivers the visible shell that all subsequent phases (Activation, CRUD, Settings) build on.

</domain>

<decisions>
## Implementation Decisions

### Object Display Format

- **D-01:** Detail pane rows show: **icon + label + value (right-truncated to fit available width)**. Example: `  branch  main-feature  feature/auth-refactor`. Values are truncated with `…` so rows never wrap.
- **D-02:** Objects in the detail pane are **grouped by preset type** (e.g., all MRs together, all branches together, all tickets together). Groups use a subtle header row to separate them.
- **D-03:** Long values (especially URLs) are right-truncated to fit the available column width — no domain-only shortening. The full value is always in the data; display truncation is visual only.

### Pane Navigation Model

- **D-04:** **Enter** on a project in the left pane selects it AND shifts focus to the detail pane (right). Selecting a project already updates the detail pane immediately via selection event.
- **D-05:** In the detail pane, **j/k** (and up/down arrows) navigate the object list. User can move a cursor over objects — important for Phase 3 (pressing `o` activates selected object).
- **D-06:** **Escape** returns focus from detail pane to the project list. Matches CORE-04 ("Escape always navigates back; no focus traps").

### Footer Key Hints

- **D-07:** Footer shows **all available bindings** for the current pane context — comprehensive, not minimal.
- **D-08:** Footer starts with a **pane context label** on the left (e.g., `Projects |` or `Detail |`), followed by all valid key bindings for that pane. Updates when focus shifts between panes.

### Visual Style & Layout

- **D-09:** Left pane (project list) is **~33% of terminal width** — balanced, not narrow sidebar. Right pane (detail) takes the remaining ~67%.
- **D-10:** Selection highlighting uses **full-row background highlight** across the full pane width. High-contrast, immediately clear which item is selected.
- **D-11:** Use **Textual's built-in default dark theme**. No custom CSS in Phase 2. Clean professional look without CSS overhead.

### Claude's Discretion

- Exact Nerd Font icon per preset type (mr, branch, ticket, thread, file, note, worktree, agents, url) — Claude chooses sensible icons during planning
- Group header row style (bold text, separator line, indented label — Claude decides)
- Exact footer format / separator character between pane label and key hints
- TCSS file organization (inline styles vs external .tcss)
- App class name and widget hierarchy specifics
- How startup data loading is done (sync in on_mount vs async worker) — must hit 350ms budget

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements for this phase
- `.planning/REQUIREMENTS.md` — CORE-01, CORE-02, CORE-03, CORE-04, CORE-06, CORE-07, PROJ-01, PROJ-02, PROJ-03 (the 9 requirements Phase 2 must satisfy)

### Foundation layer (Phase 1 deliverables)
- `.planning/phases/01-foundation/01-CONTEXT.md` — Phase 1 decisions: data model (D-01–D-14), TOML schema, module layout, Store/Models/Operations architecture
- `src/joy/models.py` — Project, ObjectItem, Config, PresetKind, ObjectType, PRESET_MAP — Phase 2 imports these directly
- `src/joy/store.py` — TOML I/O; Phase 2 uses Store to load projects on startup
- `src/joy/app.py` — Current stub entry point; Phase 2 replaces this with the Textual App class

### Stack decisions
- `.planning/research/STACK.md` — Textual 8.x rationale, startup time guidance, TOML writer choice
- `.planning/research/ARCHITECTURE.md` — Component architecture, data flow, integration points

### Critical pitfalls
- `.planning/research/PITFALLS.md` — CP-1 (blocking event loop — don't call store.load() synchronously in main thread), CP-2 (slow startup/imports), CP-3 (fire-and-forget async)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/joy/models.py`: `Project`, `ObjectItem`, `Config`, `PresetKind`, `ObjectType`, `PRESET_MAP` — direct imports for the TUI widgets
- `src/joy/store.py`: `Store` class — used in app startup to load project list
- `src/joy/app.py`: stub `main()` — Phase 2 replaces the body with `JoyApp().run()`
- `pyproject.toml`: `joy = "joy.app:main"` entry point already wired; Phase 2 just needs to add `textual` as a dependency

### Established Patterns (from Phase 1)
- Module layout: `src/joy/` package, `tests/` at root
- Data flows: Store → Models → (Phase 3) Operations
- No side effects in models; operations accept Config as parameter
- Python >=3.11, `src/` layout, hatchling build backend

### Integration Points
- `app.py → Store.load()`: Phase 2 calls store to get list of Projects on startup
- `ObjectItem.object_type`: detail pane uses this to pick the right icon
- `PresetKind` enum values: group headers in detail pane use preset kind as group label
- `Config.default_open_kinds`: not used in Phase 2 (read-only), but loaded for Phase 3 readiness

</code_context>

<specifics>
## Specific Ideas

- Entry point stub in Phase 1 (`joy` prints "Not yet implemented") → Phase 2 replaces with `JoyApp().run()`
- Textual not yet in `pyproject.toml` — Phase 2 must add `textual>=8.2` as a dependency
- Startup time budget: 350ms to first paint (CORE-06). Store load should be async or deferred to avoid blocking the initial render.
- The `worktree` and `agents` presets are special (one per project); others can be multiple. Group headers make this distinction visible.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 2 scope.

</deferred>

---

*Phase: 02-tui-shell*
*Context gathered: 2026-04-10*
