# Phase 1: Foundation - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

A fully tested headless Python library (no TUI) that can load/save projects from TOML, define all object types and presets, and perform every type-specific operation (clipboard, browser, IDE, Obsidian, iTerm2) via subprocess. This phase delivers the foundation all later phases build on — no UI, no entry point behavior, pure data and operations.

</domain>

<decisions>
## Implementation Decisions

### Project Identity / TOML Schema

- **D-01:** Projects are identified by name-as-key in `projects.toml`. Schema: `[projects.{name}]` with a `name` field and `[[projects.{name}.objects]]` array for objects. Human-readable and hand-editable. Renaming requires updating the key, which is acceptable for this personal tool.
- **D-02:** Objects within a project use an `[[projects.{name}.objects]]` array-of-tables. Each object has `kind`, `value`, and `open_by_default` fields.

### Package Structure

- **D-03:** Full pyproject.toml with hatchling build backend, `src/joy/` layout, and a `joy = "joy.app:main"` entry point that prints "Not yet implemented" (Phase 1 stub). Phase 1 creates the complete package scaffold so `uv sync` works and subsequent phases import `from joy.models import ...`.
- **D-04:** `src/` layout (src/joy/ package). Tests live in `tests/` at repo root.
- **D-05:** Python >=3.11 required (gets tomllib in stdlib, asyncio.TaskGroup, modern type hints).

### Data Model

- **D-06:** Use plain Python dataclasses (not Pydantic). Models are pure data — no I/O, no side effects. Dataclasses give `__eq__`, `__repr__`, and `asdict()`-compatible fields for free with zero startup cost.
- **D-07:** `ObjectType` as `str` Enum for TOML serialization transparency: values are the literal strings written to disk (`"string"`, `"url"`, `"obsidian"`, `"file"`, `"worktree"`, `"iterm"`).
- **D-08:** `PresetKind` as `str` Enum for the 9 named presets (mr, branch, ticket, thread, file, note, worktree, agents, url). Each maps to an ObjectType + default label. The mapping lives in a `PRESET_MAP` dict in models.py.

### Architecture

- **D-09:** Three core modules: `models.py` (pure data), `store.py` (TOML I/O), `operations.py` (subprocess operations). Data flows one direction: Store → Models → Operations.
- **D-10:** Store reads/writes atomically: write to `~/.joy/projects.toml.tmp`, then `os.replace()`. Config at `~/.joy/config.toml`. Both files created with sane defaults on first run if missing.

### Operations

- **D-11:** Operations accept a `Config` dataclass as a parameter rather than reading `~/.joy/config.toml` directly. This keeps operations.py testable in isolation — callers pass in the config, operations.py does not perform file I/O.
- **D-12:** iTerm2 / AppleScript operation (agents type): implement fully in Phase 1 using `osascript`. Mark with a test that is tagged `@pytest.mark.macos_integration` and document that it requires manual validation against a live iTerm2 instance.

### Testing

- **D-13:** Unit tests mock subprocess calls (`unittest.mock.patch("subprocess.run")`). Test logic and dispatch — not that macOS actually opens the app. Exception: tests tagged `@pytest.mark.macos_integration` test real subprocess behavior and are skipped in CI.
- **D-14:** Tests cover: model serialization round-trips, store read/write/atomic-write, all 7 operation types dispatch correctly, all 9 preset-to-type mappings resolve correctly.

### Claude's Discretion

- Exact TOML schema for `config.toml` (fields for IDE path, vault path, editor, terminal tool)
- Default values for Config dataclass fields when `~/.joy/config.toml` is absent
- Internal structure of the PRESET_MAP dict and any helper methods on PresetKind
- pytest configuration (conftest.py, fixtures, custom markers)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture and stack decisions
- `.planning/research/ARCHITECTURE.md` — Full data model design, component architecture, Store/Models/Operations separation, TOML schema examples
- `.planning/research/STACK.md` — Technology choices (Textual, tomllib/tomli_w, dataclasses), Python version rationale, packaging with hatchling

### Critical pitfalls to avoid
- `.planning/research/PITFALLS.md` — CP-1 (blocking event loop), CP-2 (slow startup/imports), CP-3 (fire-and-forget async), CP-4 (non-atomic writes). Phase 1 must establish non-atomic-write protection from day one.

### Requirements
- `.planning/REQUIREMENTS.md` — OBJ-01 through OBJ-07, PRESET-01 through PRESET-09, DIST-02: the exact requirements Phase 1 must satisfy

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — this is the first phase. The codebase is empty.

### Established Patterns
- No existing patterns — Phase 1 establishes them. The research files define the target patterns.

### Integration Points
- `src/joy/models.py` — Phase 2 (TUI Shell) imports Project, ObjectItem, Config from here
- `src/joy/store.py` — Phase 2 uses Store to load projects on startup
- `src/joy/operations.py` — Phase 3 (Activation) calls these from Textual event handlers (must be async-safe)

</code_context>

<specifics>
## Specific Ideas

- TOML schema preview confirmed by user: `[projects.my-project]` with `[[projects.my-project.objects]]` entries
- Package layout confirmed: `src/joy/` with `tests/` at repo root, full `pyproject.toml` from Phase 1
- Entry point stub: `joy` command prints "Not yet implemented" in Phase 1, wired up in Phase 2

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 1 scope.

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-04-10*
