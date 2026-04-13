# Research Summary: joy

**Project:** joy
**Domain:** Developer project artifact manager (keyboard-driven Python TUI)
**Researched:** 2026-04-10
**Confidence:** HIGH

## Executive Summary

joy is a keyboard-driven Python TUI that gives developers a single interface to manage and instantly open all artifacts related to a coding project -- branches, MRs, tickets, worktrees, notes, agent windows, and more. The recommended approach is Textual 8.x for the TUI framework with TOML for data storage, yielding a total dependency footprint of just two packages (textual, tomli-w). All macOS integration (URL schemes, clipboard, iTerm2) runs through subprocess calls to OS-provided commands, requiring zero additional Python libraries.

The architecture is clean and well-bounded: five components (Data Model, Store, Operations, Widgets, App/Screens) with unidirectional data flow and strict separation between UI and business logic. Widgets post messages upward; Screens handle operations and persistence. The two-level type system (PresetKind for users, ObjectType for dispatch) is the critical design insight -- it means adding a new artifact kind (e.g., Figma links) requires one enum entry and one mapping, zero new operation code.

The primary risks are event loop blocking (every subprocess call must use Textual's `@work(thread=True)` decorator), slow startup from eager imports (target under 350ms to first paint), and non-atomic file writes that could destroy `~/.joy/projects.toml`. All three have well-documented prevention patterns. The iTerm2 AppleScript integration is in maintenance mode but sufficient for joy's simple needs (create/activate named windows).

## Stack

- **TUI framework:** Textual 8.x -- the unchallenged standard for Python TUI apps. CSS-based layout, built-in ListView, first-class keyboard bindings, async-native. No credible alternative.
- **Data storage:** TOML via stdlib `tomllib` (read) + `tomli_w` (write). Human-editable, comments supported, perfect fit for joy's data shape. Two files: `~/.joy/config.toml` and `~/.joy/projects.toml`.
- **macOS integration:** All through `subprocess` -- `open` command for URL schemes, `pbcopy` for clipboard, `osascript` for iTerm2 AppleScript. Zero Python library dependencies.
- **Packaging:** `uv tool install git+<repo>` with hatchling build backend. Entry point via `[project.scripts]`. Python >=3.11 required (gets `tomllib` in stdlib).

## Architecture at a Glance

**Components:** Data Model (dataclasses) -> Store (TOML read/write) -> Operations (dict-based type dispatch) -> Widgets (Textual custom widgets) -> App/Screens (wiring layer). Data flows in one direction; widgets never import store or operations directly.

**Data model:** `Project` has a list of `ObjectItem`s. Each `ObjectItem` has a `PresetKind` (user-facing: mr, branch, ticket, etc.) that maps to an `ObjectType` (operation-facing: URL, STRING, FILE, etc.). Six operation handlers cover all nine preset kinds.

**~/.joy/ layout:**
```
~/.joy/
  config.toml        # IDE, editor, vault, terminal preferences
  projects.toml      # All projects + their objects in one file
```

Single file, not directory-per-project. Data volume is tiny (<10KB for 50 projects). Atomic writes via temp-file + `os.replace()`.

## Table Stakes Features

- Instant startup (<350ms to first paint)
- Two-pane layout: project list (left) + project detail (right) with clear focus indicator
- vim-style navigation (j/k + arrow keys)
- Visible keyboard shortcuts in a context-sensitive footer bar
- Consistent key vocabulary (a=add, d=delete, e=edit, o=open, q=quit, /=filter, ?=help)
- Confirmation on destructive actions (delete project only, not single objects)
- Immediate visual feedback in status bar ("Opened in browser", "Copied to clipboard")
- Escape always goes back -- user should never feel trapped
- Persistent state across sessions (~/.joy/ data files)
- Search/filter on project list (/ to filter by name, real-time substring match)

## Differentiators

- **"Open All" with `O`**: One keystroke opens the entire project context -- IDE, browser tabs, iTerm2 window, everything marked as "open by default." This is joy's killer feature. No other TUI does this.
- **Spacebar toggle for the "open by default" set**: Visual indicator (filled/empty) next to each object. Immediately visible, immediately actionable.
- **Per-object type icons (Nerd Font)**: Visual scanning is 10x faster. Branch icon, MR icon, note icon -- the eye finds what it needs before reading text.
- **Object reordering (J/K)**: Controls activation sequence for `O`. Display order = open order.
- **Quick-add from clipboard**: Detect URL or branch name in clipboard and pre-fill type/value on add.
- **Project-as-context philosophy**: Not a bookmark manager. Each project is a complete developer context for resuming work on a codebase.

## Anti-Features to Avoid

- **Mouse interaction** -- keyboard-driven by design; two paradigms would dilute the identity
- **Plugin/extension system** -- massive complexity for a single-user tool; add types by editing code
- **Inline editing** -- known TUI anti-pattern; use separate edit overlay/modal
- **100+ keybindings** -- keep under 25 total; every key discoverable from footer or `?` help
- **Fancy animations** -- Textual's creator warns against decorative animation in terminals
- **Auto-sync/cloud features** -- adds network dependency, latency, auth flows; user can git-manage ~/.joy/
- **Multi-window/tabbed interface** -- stick to two-pane layout; overlays for forms
- **Configurable keybindings** -- premature complexity; ship opinionated defaults
- **Undo/redo system** -- confirmation dialogs suffice for the simple mutations joy performs

## Critical Pitfalls to Address

| # | Pitfall | Severity | Phase | Prevention |
|---|---------|----------|-------|------------|
| 1 | **Event loop blocking** -- any `subprocess.run()` in a handler freezes the entire TUI | CRITICAL | Phase 1 | Use `@work(thread=True)` for all I/O and subprocess calls from day one |
| 2 | **Slow startup from eager imports** -- Textual+Rich alone cost 130-230ms; additional imports push past 350ms | CRITICAL | Phase 1 | Profile with `python -X importtime`; lazy-import non-essential modules; use Textual's `Lazy` widget |
| 3 | **Non-atomic file writes** -- interrupted write to `projects.toml` destroys all data | CRITICAL | Phase 2 | Write to temp file + `os.replace()` pattern; keep `.bak` copy before writes |
| 4 | **Fire-and-forget async tasks** -- GC collects unref'd tasks silently | CRITICAL | Phase 1 | Always use `@work` decorator; never bare `asyncio.create_task()` |
| 5 | **Widget lifecycle confusion** -- querying children in `compose()` or `__init__()` crashes | HIGH | Phase 1 | Load data in `on_mount()` only; use `call_after_refresh()` for post-layout work |
| 6 | **Focus traps in keyboard-only nav** -- focus stuck in widget with no escape | HIGH | Phase 1 | Every modal/input must handle Escape; test complete focus cycle |
| 7 | **Obsidian URI path encoding** -- spaces and special chars in file paths break opens | HIGH | Phase 2 | Always `urllib.parse.quote()` vault name and file path |

## Open Questions / Risks

- **iTerm2 AppleScript longevity**: Officially deprecated (maintenance mode only). Works for joy's simple needs today. If iTerm2 drops AppleScript entirely, the Python API (`iterm2` package) is the fallback. Low risk for the foreseeable future.
- **Startup time budget**: Textual+Rich import alone is 130-230ms. Hitting the <350ms target requires discipline with lazy imports. Needs measurement from the very first prototype -- much harder to fix retroactively.
- **URL scheme stability**: Notion and Slack have changed URL scheme formats in the past. Mitigation: store original HTTPS URLs, convert to app-specific schemes at activation time (not at storage time). Needs real-world validation.
- **uv tool upgrade behavior**: `uv tool upgrade joy` may not pull latest git commits. Users must use `uv tool install --force git+<repo>` for updates. Needs clear documentation and a `joy --version` command.
- **AppleScript race conditions**: iTerm2 session targeting can hit the wrong window if sessions are created/closed rapidly. Mitigated by identifying windows by name with a `joy:` prefix convention, but needs testing under real conditions.

## Recommended Phase Sequence

### Phase 1: Foundation (No UI)

**Rationale:** The data model, persistence layer, and operations module have zero dependencies on Textual. Building and testing them first validates the core data design and type dispatch system before any TUI complexity enters the picture.

**Delivers:** `models.py`, `store.py`, `operations.py` with unit tests. Proven data round-trip through TOML. Verified subprocess calls for each object type.

**Features:** Persistent storage, all object type operations (URL open, clipboard copy, IDE launch, Obsidian URI, iTerm2 window)

**Avoids:** CP-4 (non-atomic writes -- implement temp+rename from the start), CM-5 (TOML library choice -- lock in tomllib + tomli_w), UR-1 (Obsidian encoding -- test edge cases in unit tests)

### Phase 2: Basic TUI Shell

**Rationale:** With the data layer proven, build the visual shell. This phase establishes the two-pane layout, keyboard navigation model, and focus management -- the patterns everything else depends on.

**Delivers:** `app.py`, `widgets/`, `screens/main.py`, CSS styles. Renders projects and objects. Navigation works. No mutations yet.

**Features:** Two-pane layout, project list navigation, project detail display, object rows with icons, footer key hints, focus indicators

**Avoids:** CP-1 (event loop blocking -- establish `@work` pattern), CP-2 (slow startup -- measure from first prototype), CM-1 (lifecycle -- data in `on_mount`), CM-2 (CSS layout -- use `fr` units, test with `--dev`), CM-3 (key conflicts -- simple letter keys), CM-6 (focus traps -- Escape always works)

### Phase 3: Operations Integration

**Rationale:** Wire the proven operations layer into the proven TUI shell. This delivers the core value proposition: see a project's artifacts and open them with one keystroke.

**Delivers:** `o` (open single object), `O` (open all defaults), `space` (toggle open-by-default), clipboard copy notification, status bar feedback.

**Features:** Single object activation, "Open All" killer feature, open-by-default toggle, ephemeral status messages

**Avoids:** CP-1 (all operations through `@work(thread=True)`), CP-3 (use `@work` not raw `create_task`), CM-4 (use `subprocess.run(["open", ...])` not `webbrowser.open()`)

### Phase 4: CRUD

**Rationale:** With read and activate working, add create/update/delete. These require modal screens (forms, confirmations) which are a distinct Textual pattern.

**Delivers:** Add/edit/delete objects and projects. Modal forms (ObjectFormModal, ProjectFormModal, ConfirmDeleteModal). Full data lifecycle.

**Features:** `a` add object, `e` edit object, `d` delete object, `n` new project, delete project with confirmation

**Avoids:** CM-6 (modals must handle Escape), UR-2 (store HTTPS URLs, convert at open time)

### Phase 5: Polish and Distribution

**Rationale:** Core functionality is complete. This phase adds quality-of-life features, error handling, settings screen, and distribution validation.

**Delivers:** Settings screen, search/filter, object reordering (J/K), error handling for missing config / invalid TOML / subprocess failures, `joy --version`, documented install/upgrade process.

**Features:** Settings screen, search/filter on project list, object reordering, Nerd Font icon fallback, error recovery, quick-add from clipboard

**Avoids:** PD-1 (validate `uv tool install .` in clean env), PD-2 (document reinstall-based upgrades), PD-3 (test all deps declared)

### Phase Ordering Rationale

- **Foundation first** because the data model and operations module are dependency-free and testable in isolation. Getting the type system and persistence right prevents rework in every later phase.
- **TUI shell before operations wiring** because layout and focus management are the hardest Textual patterns to get right and affect every subsequent feature. Changing layout later cascades through all widgets.
- **Operations before CRUD** because the read+activate loop is the core value proposition. A user can manually edit TOML to add projects and still get full value from the TUI. CRUD is convenience, not core.
- **Polish last** because settings, search, reordering, and error handling are independent features that don't affect each other. They can be added in any order without rework.

### Research Flags

**Needs deeper research during planning:**
- **Phase 3 (Operations Integration):** iTerm2 AppleScript reliability under real conditions. Test with iTerm2 not running, with multiple windows, with rapid open/close. The race condition (IR-2) and session naming (IR-3) pitfalls need hands-on validation.

**Standard patterns (skip research-phase):**
- **Phase 1 (Foundation):** Dataclasses, TOML read/write, subprocess calls -- all well-documented stdlib patterns.
- **Phase 2 (TUI Shell):** Textual two-pane layout, ListView, CSS styling -- heavily documented with official examples.
- **Phase 4 (CRUD):** Textual ModalScreen, form inputs -- standard Textual patterns with official guides.
- **Phase 5 (Polish):** Search/filter, settings forms, error handling -- no novel patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Textual is the unchallenged Python TUI standard. TOML has stdlib support. Two total dependencies. Verified via PyPI, official docs. |
| Features | HIGH | Feature set derived from established TUI patterns (lazygit, taskwarrior-tui, k9s). UX conventions well-documented by multiple practitioners. |
| Architecture | HIGH | Textual's compose/message-bubbling model maps directly to joy's needs. Five-component design with clear boundaries. Build order validated by dependency analysis. |
| Pitfalls | HIGH | Critical pitfalls (event loop blocking, startup time, atomic writes) are well-documented with proven prevention patterns. iTerm2 risks are MEDIUM confidence. |

**Overall confidence:** HIGH

### Gaps to Address

- **Startup time measurement:** Must be validated empirically from the first prototype. The 350ms target is achievable based on the Posting project's documented results, but joy's specific import chain needs profiling.
- **iTerm2 AppleScript edge cases:** Session race conditions and window naming behavior need hands-on testing. Documentation is sparse on multi-window scenarios.
- **URL scheme durability:** Notion and Slack scheme formats may change. The "store HTTPS, convert at open time" pattern mitigates this, but needs periodic validation.
- **uv tool install from git:** The upgrade path (`--force` reinstall vs. tagged releases) needs validation and documentation.

## Sources

### Primary (HIGH confidence)
- Textual official docs -- framework, layout, bindings, workers, widgets
- Python stdlib docs -- tomllib, subprocess, webbrowser, dataclasses
- uv docs -- tool install, build backends, project config
- Obsidian URI scheme docs

### Secondary (MEDIUM confidence)
- Posting (Textual app) startup optimization -- lazy import benchmarks
- Textual blog -- async heisenbug, TUI design lessons
- Jens Roemer TUI Design guide -- UX patterns and anti-patterns
- Lazygit UX analysis -- navigation conventions
- iTerm2 scripting docs -- AppleScript API (maintenance mode)

### Tertiary (LOW confidence)
- iTerm2 session race condition bug report (GitLab #5462) -- specific to multi-session scenarios
- Notion/Slack URL scheme stability -- based on community reports, not independently verified

---
*Research completed: 2026-04-10*
*Ready for roadmap: yes*
