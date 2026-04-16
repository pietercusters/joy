# Quick Task 260415-qqx: Build full iTerm2 terminal session control in TUI - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Task Boundary

Build full iTerm2 terminal session management in the joy TUI. Rename all "Agent" references to "Terminal". Add `n` (add named session), `e` (rename session), `d/D` (close/force-close with confirmation) key bindings to TerminalPane. Auto-create iTerm2 session when a Terminal object is added to a project. Auto-remove Terminal object from project (with popup) when its iTerm2 session disappears. Show a project-link flag icon on linked sessions in the Terminals overview.

</domain>

<decisions>
## Implementation Decisions

### iTerm2 API approach
Use the Python iterm2 API for all mutations (create, rename, close). Replace the existing AppleScript `_open_iterm()` opener in `operations.py` with Python API for consistency. New sessions created as tabs (not new windows).

### Input UX for n/e
Modal dialog (re-use existing `NameInputModal` pattern). `n` uses `NameInputModal(title="New Terminal Session")`. `e` uses `NameInputModal(title="Rename Session", initial_value=current_name)`.

### Auto-removal scope
Auto-remove ALL linked Terminal objects when their session disappears — regardless of how they were created. Written to TOML (permanent). Show informative notify popup. Guard: only remove when the fetched session list is non-empty (empty list = likely iTerm2 hiccup; skip removal that cycle).

### Conflict #1 — TOML backward compatibility
Rename TOML value from `"agents"` to `"terminals"`. Add alias in `_toml_to_projects()` that transparently reads old `"agents"` entries as `PresetKind.TERMINALS`. No manual migration needed.

### Conflict #2 — Auto-remove timing guard (simplest option)
Only trigger auto-remove when `fetch_sessions()` returned a non-empty list. If iTerm2 returns an empty list or None, skip the removal pass entirely that cycle. This is the safest guard without added complexity.

### Conflict #3 — Stale CSS/field becomes dead code
Remove `stale: bool` field from `ObjectItem`. Remove `--stale` CSS rules from `ObjectRow`. Remove stale-related logic from `_render_project()`. Remove all `_propagate_agent_stale()` logic.

### Conflict #4 — AppleScript vs Python API
Replace `_open_iterm()` in `operations.py` with a Python API implementation. The `o` key on a Terminal object in ProjectDetail will use the same Python API path (activate if exists, create if not). New sessions always created as tabs in the current iTerm2 window.

### Conflict #5 — Rename propagates to obj.value in TOML
When renaming a session via `e`, check if it is linked to a project via `_rel_index`. If linked, update `obj.value` in the project's object list and save TOML. Then rebuild `_rel_index` (trigger full refresh cycle) to keep cross-pane sync in sync.

### Conflict #6 — ConfirmationModal hint text
Parameterize `ConfirmationModal.hint` to accept a custom string. Default stays "Enter to confirm, Escape to cancel". Close-session dialogs pass their own phrasing.

### Conflict #7 — Stale rel_index after rename
After a rename, trigger the full terminal refresh cycle (`_load_terminal()`) so `_rel_index` is rebuilt with the new session name. Cross-pane sync resumes correctly on the next cycle.

### Conflict #8 — Flag display in TerminalPane
Add `linked_names: set[str]` parameter to `set_sessions()`. Called from app.py after `_rel_index` is available. `SessionRow` shows a project-link icon (e.g. `\uf07c` folder-open or `\uf0e8` sitemap) for linked sessions.

### Conflict #9 — SEMANTIC_GROUPS label
Rename `("Agents", [PresetKind.AGENTS])` to `("Terminals", [PresetKind.TERMINALS])`.

### Conflict #10 — Config.default_open_kinds
Update `models.py` default from `["worktree", "agents"]` to `["worktree", "terminals"]`. Also update `_toml_to_projects()` alias so existing `config.toml` files with `"agents"` continue to work.

### Conflict #11 — _PANE_HINTS update
Update `"terminal-pane"` hint to: `"o: Open  n: Add  e: Rename  d: Close  D: Force close"`.

### Conflict #12 — Tests
Update all test fixtures and assertions from `PresetKind.AGENTS` / `kind = "agents"` to `PresetKind.TERMINALS` / `kind = "terminals"`.

### Conflict #13 — Auto-create hook in _start_add_object_loop
After saving a `PresetKind.TERMINALS` object, immediately call `create_session(value)` in a background worker. This covers the "project adds terminal" flow from the ProjectDetail pane.

### Conflict #14 — Resolver naming
Rename `agents_for()` → `terminals_for()`, `project_for_agent()` → `project_for_terminal()`, `_ag_for_project` → `_term_for_project`, `_project_for_agent` → `_project_for_terminal`, `agent_to_project` → `terminal_to_project` throughout `resolver.py` and all callers in `app.py`.

### Close session flow (d/D keys)
- `d`: Push `ConfirmationModal("Close session?", "...", hint="Enter to close, Escape to cancel")` → on confirm → background worker calls `close_session(session_id, force=False)` → on failure → push second `ConfirmationModal("Force close?", ...)` → on confirm → `close_session(session_id, force=True)`.
- `D`: Push single `ConfirmationModal` for force-close directly, no retry needed.

### Claude's Discretion
- Icon for project-linked sessions: use `\uf444` (nf-md-link) or similar — executor picks the best available Nerd Font icon.
- Exact iTerm2 Python API calls for create/rename/close: executor to verify against installed iterm2 package API.

</decisions>

<specifics>
## Specific Ideas

- `TerminalPane` key bindings to add: `n` (add), `e` (rename), `d` (close with retry), `D` (force close).
- `create_session(name)` in `terminal_sessions.py`: Python API creates a new tab in the front window, sets session name.
- `rename_session(session_id, new_name)` in `terminal_sessions.py`: Python API sets session name variable.
- `close_session(session_id, force=False)` in `terminal_sessions.py`: Python API close (graceful or forced).
- Auto-remove logic: extracted from old `_propagate_agent_stale()` into new `_propagate_terminal_auto_remove()` that mutates `project.objects` and saves TOML when sessions disappear.
- Auto-create: triggered from `_start_add_object_loop()` when `preset == PresetKind.TERMINALS`.
- Flag icon in `SessionRow._build_content()`: extra append when `session_name in linked_names`.

</specifics>

<canonical_refs>
## Canonical References

- `src/joy/terminal_sessions.py` — existing fetch/activate; new create/rename/close go here
- `src/joy/models.py` — PresetKind, ObjectItem (stale field removal, TERMINALS rename)
- `src/joy/app.py` — _propagate_agent_stale replacement, _start_add_object_loop hook, _PANE_HINTS
- `src/joy/widgets/terminal_pane.py` — new bindings, set_sessions() signature, SessionRow flag
- `src/joy/widgets/project_detail.py` — SEMANTIC_GROUPS rename
- `src/joy/widgets/object_row.py` — stale CSS removal, KIND_SHORTCUT rename
- `src/joy/operations.py` — _open_iterm() replacement with Python API
- `src/joy/resolver.py` — naming rename (agents→terminals)
- `src/joy/screens/confirmation.py` — parameterize hint text
- `src/joy/store.py` — _toml_to_projects() backward compat alias

</canonical_refs>
