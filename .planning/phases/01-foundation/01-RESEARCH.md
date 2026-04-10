# Phase 1: Foundation - Research

**Researched:** 2026-04-10
**Domain:** Python headless library -- data model, TOML persistence, subprocess operations
**Confidence:** HIGH

## Summary

Phase 1 creates the complete headless foundation for joy: data model (dataclasses with enums), TOML persistence (atomic read/write to `~/.joy/`), and subprocess-based operations for all 7 object types. No TUI code exists in this phase. The codebase is empty -- this phase establishes every pattern future phases build on.

The core technical challenge is getting the two-level type system (PresetKind for users, ObjectType for operations) correct, implementing lossless TOML round-trips with the keyed `[projects.{name}]` schema, and ensuring all subprocess operations are correct and testable via mocked calls. The atomic write pattern (tempfile + `os.replace`) must be established from day one to prevent data loss.

Research verified that `tomli_w` handles `str` Enums and `date` objects natively, the keyed TOML schema round-trips correctly, and all macOS subprocess commands (`open`, `pbcopy`, `osascript`) are available on the target machine. Python 3.13.7 and uv 0.11.2 are installed.

**Primary recommendation:** Build three modules (`models.py`, `store.py`, `operations.py`) in strict dependency order with unit tests after each. Use the `@opener` decorator registry pattern for type dispatch. Use `tempfile.mkstemp` + `os.replace` for atomic writes. Mock all subprocess calls in tests.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Projects are identified by name-as-key in `projects.toml`. Schema: `[projects.{name}]` with a `name` field and `[[projects.{name}.objects]]` array for objects. Human-readable and hand-editable. Renaming requires updating the key, which is acceptable for this personal tool.
- **D-02:** Objects within a project use an `[[projects.{name}.objects]]` array-of-tables. Each object has `kind`, `value`, and `open_by_default` fields.
- **D-03:** Full pyproject.toml with hatchling build backend, `src/joy/` layout, and a `joy = "joy.app:main"` entry point that prints "Not yet implemented" (Phase 1 stub). Phase 1 creates the complete package scaffold so `uv sync` works and subsequent phases import `from joy.models import ...`.
- **D-04:** `src/` layout (src/joy/ package). Tests live in `tests/` at repo root.
- **D-05:** Python >=3.11 required (gets tomllib in stdlib, asyncio.TaskGroup, modern type hints).
- **D-06:** Use plain Python dataclasses (not Pydantic). Models are pure data -- no I/O, no side effects.
- **D-07:** `ObjectType` as `str` Enum for TOML serialization transparency: values are the literal strings written to disk (`"string"`, `"url"`, `"obsidian"`, `"file"`, `"worktree"`, `"iterm"`).
- **D-08:** `PresetKind` as `str` Enum for the 9 named presets (mr, branch, ticket, thread, file, note, worktree, agents, url). Each maps to an ObjectType + default label. The mapping lives in a `PRESET_MAP` dict in models.py.
- **D-09:** Three core modules: `models.py` (pure data), `store.py` (TOML I/O), `operations.py` (subprocess operations). Data flows one direction: Store -> Models -> Operations.
- **D-10:** Store reads/writes atomically: write to `~/.joy/projects.toml.tmp`, then `os.replace()`. Config at `~/.joy/config.toml`. Both files created with sane defaults on first run if missing.
- **D-11:** Operations accept a `Config` dataclass as a parameter rather than reading `~/.joy/config.toml` directly. This keeps operations.py testable in isolation.
- **D-12:** iTerm2 / AppleScript operation (agents type): implement fully in Phase 1 using `osascript`. Mark with a test tagged `@pytest.mark.macos_integration`.
- **D-13:** Unit tests mock subprocess calls (`unittest.mock.patch("subprocess.run")`). Test logic and dispatch -- not that macOS actually opens the app. Exception: tests tagged `@pytest.mark.macos_integration` test real subprocess behavior.
- **D-14:** Tests cover: model serialization round-trips, store read/write/atomic-write, all 7 operation types dispatch correctly, all 9 preset-to-type mappings resolve correctly.

### Claude's Discretion
- Exact TOML schema for `config.toml` (fields for IDE path, vault path, editor, terminal tool)
- Default values for Config dataclass fields when `~/.joy/config.toml` is absent
- Internal structure of the PRESET_MAP dict and any helper methods on PresetKind
- pytest configuration (conftest.py, fixtures, custom markers)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within Phase 1 scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OBJ-01 | `string` type -- activating copies value to clipboard | Operations module: `_copy_string` opener using `subprocess.run(["pbcopy"], input=...)` |
| OBJ-02 | `url` type -- activating opens URL in default browser | Operations module: `_open_url` opener using `subprocess.run(["open", url])` |
| OBJ-03 | `url` type with Notion/Slack URL -- opens desktop app | Operations module: URL hostname detection (`notion.so` / `slack.com`) with scheme conversion at activation time |
| OBJ-04 | `obsidian` type -- opens file in Obsidian vault via URI | Operations module: `_open_obsidian` opener building `obsidian://open?vault=...&file=...` with proper URL encoding |
| OBJ-05 | `file` type -- opens file in configured editor | Operations module: `_open_file` opener using `subprocess.run(["open", "-a", config.editor, path])` |
| OBJ-06 | `git worktree` type -- opens path in configured IDE | Operations module: `_open_worktree` opener using `subprocess.run(["open", "-a", config.ide, path])` |
| OBJ-07 | `special string` type -- creates/focuses named iTerm2 window | Operations module: `_open_iterm` opener using `subprocess.run(["osascript", "-e", script])` |
| PRESET-01 | `mr` preset -- url type, opens in browser | PRESET_MAP: `PresetKind.MR -> ObjectType.URL` |
| PRESET-02 | `branch` preset -- string type, copies to clipboard | PRESET_MAP: `PresetKind.BRANCH -> ObjectType.STRING` |
| PRESET-03 | `ticket` preset -- url type, opens in Notion | PRESET_MAP: `PresetKind.TICKET -> ObjectType.URL` (Notion detection in URL opener) |
| PRESET-04 | `thread` preset -- url type, opens in Slack | PRESET_MAP: `PresetKind.THREAD -> ObjectType.URL` (Slack detection in URL opener) |
| PRESET-05 | `file` preset -- file type, opens in editor | PRESET_MAP: `PresetKind.FILE -> ObjectType.FILE` |
| PRESET-06 | `note` preset -- obsidian type, opens in Obsidian | PRESET_MAP: `PresetKind.NOTE -> ObjectType.OBSIDIAN` |
| PRESET-07 | `worktree` preset -- worktree type, opens in IDE | PRESET_MAP: `PresetKind.WORKTREE -> ObjectType.WORKTREE` |
| PRESET-08 | `agents` preset -- iterm type, creates/opens iTerm2 window | PRESET_MAP: `PresetKind.AGENTS -> ObjectType.ITERM` |
| PRESET-09 | `url` preset -- url type, opens in browser | PRESET_MAP: `PresetKind.URL -> ObjectType.URL` |
| DIST-02 | All user data and config live in `~/.joy/` | Store module: `JOY_DIR = Path.home() / ".joy"`, `config.toml` + `projects.toml` |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Tech stack:** Python only, managed with `uv` -- no other runtimes
- **Platform:** macOS only -- relies on OS-level URL handlers and AppleScript
- **Install target:** `uv tool install git+<repo>` -- must work as a globally installed tool
- **Config location:** `~/.joy/` -- projects data, global settings, all state lives here
- **Design:** Minimalistic, snappy -- no heavy dependencies that slow startup
- **Build backend:** hatchling (not uv_build, not setuptools)
- **Python version:** >=3.11 (gets tomllib in stdlib)
- **Dependencies:** Only two runtime deps: `textual` and `tomli_w`. Phase 1 does not need textual.
- **Function calls:** Always use keyword arguments like `arg=value`

## Standard Stack

### Core (Phase 1 only -- no Textual needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| tomllib | stdlib (3.11+) | Read TOML files | Zero-dependency TOML parsing in stdlib. [VERIFIED: Python 3.13.7 available on machine] |
| tomli_w | 1.2.0 | Write TOML files | Lightweight counterpart to tomllib. Handles str Enums and date objects natively. [VERIFIED: PyPI, round-trip tested] |
| dataclasses | stdlib | Data model definitions | Gives `__eq__`, `__repr__`, `field()` with zero import cost. [VERIFIED: stdlib] |

### Supporting (Dev dependencies)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | ~=9.0 | Test framework | All unit tests. [CITED: pypi.org/project/pytest] |
| hatchling | 1.29.0 | Build backend | In pyproject.toml build-system only. [CITED: pypi.org/project/hatchling] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| dataclasses | Pydantic | Adds ~50ms import time and validation overhead. Unnecessary for trusted data we write ourselves. |
| tomli_w | tomlkit | tomlkit preserves comments on round-trip. But joy owns its data files -- no user comments to preserve. |
| asdict() for serialization | Custom to_dict methods | asdict() doesn't convert str Enums to .value (verified). Custom serialization is required anyway. |

**Installation (Phase 1):**
```bash
uv init --lib --name joy
uv add tomli-w
uv add --dev pytest
```

**Version verification:**
- tomli_w: 1.2.0 (released 2025-01-15) [VERIFIED: pypi.org/project/tomli-w]
- hatchling: 1.29.0 (released 2026-02-23) [VERIFIED: WebSearch pypi.org/project/hatchling]
- pytest: ~9.0.3 (released 2026-04-07) [VERIFIED: WebSearch pypi.org/project/pytest]

## Architecture Patterns

### Recommended Project Structure
```
joy/
  pyproject.toml
  src/
    joy/
      __init__.py          # Version only
      app.py               # Entry point stub (prints "Not yet implemented")
      models.py            # Dataclasses: ObjectType, PresetKind, ObjectItem, Project, Config, PRESET_MAP
      store.py             # TOML read/write with atomic writes
      operations.py        # Type-dispatched subprocess operations
  tests/
    __init__.py
    conftest.py            # Shared fixtures, custom markers
    test_models.py         # Model creation, equality, properties, PRESET_MAP
    test_store.py          # TOML round-trip, atomic writes, missing file handling
    test_operations.py     # Subprocess mock tests for all 7 operation types
```

### Pattern 1: Two-Level Type System (PresetKind + ObjectType)

**What:** User-facing `PresetKind` enum (9 values) maps to operation-facing `ObjectType` enum (6 values) via a `PRESET_MAP` dict.

**When to use:** Always. This is the core dispatch architecture.

**Example:**
```python
# Source: .planning/research/ARCHITECTURE.md (verified and tested)
from enum import Enum
from dataclasses import dataclass, field
from datetime import date


class ObjectType(str, Enum):
    STRING = "string"
    URL = "url"
    OBSIDIAN = "obsidian"
    FILE = "file"
    WORKTREE = "worktree"
    ITERM = "iterm"


class PresetKind(str, Enum):
    MR = "mr"
    BRANCH = "branch"
    TICKET = "ticket"
    THREAD = "thread"
    FILE = "file"
    NOTE = "note"
    WORKTREE = "worktree"
    AGENTS = "agents"
    URL = "url"


PRESET_MAP: dict[PresetKind, ObjectType] = {
    PresetKind.MR: ObjectType.URL,
    PresetKind.BRANCH: ObjectType.STRING,
    PresetKind.TICKET: ObjectType.URL,
    PresetKind.THREAD: ObjectType.URL,
    PresetKind.FILE: ObjectType.FILE,
    PresetKind.NOTE: ObjectType.OBSIDIAN,
    PresetKind.WORKTREE: ObjectType.WORKTREE,
    PresetKind.AGENTS: ObjectType.ITERM,
    PresetKind.URL: ObjectType.URL,
}
```

### Pattern 2: Decorator-Based Operation Registry

**What:** Dict-based registry with `@opener(ObjectType.X)` decorator for registering type-specific handlers.

**When to use:** In operations.py for all object activations.

**Example:**
```python
# Source: .planning/research/ARCHITECTURE.md
from typing import Callable
from models import ObjectItem, ObjectType, Config

Opener = Callable[[ObjectItem, Config], None]
_OPENERS: dict[ObjectType, Opener] = {}


def opener(obj_type: ObjectType):
    def decorator(fn: Opener) -> Opener:
        _OPENERS[obj_type] = fn
        return fn
    return decorator


def open_object(item: ObjectItem, config: Config) -> None:
    handler = _OPENERS.get(item.object_type)
    if handler is None:
        raise ValueError(f"No opener registered for {item.object_type}")
    handler(item, config)
```

### Pattern 3: Atomic File Writes

**What:** Write to tempfile in same directory, then `os.replace()` for atomic swap.

**When to use:** Every write to `~/.joy/projects.toml` and `~/.joy/config.toml`.

**Example:**
```python
# Source: verified with local test
import os
import tempfile
from pathlib import Path

def atomic_write(path: Path, data: bytes) -> None:
    """Write data atomically using temp file + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp_path, path)
    except BaseException:
        # Clean up temp file on any failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
```

### Pattern 4: Custom Serialization (not asdict)

**What:** Custom `to_dict()` methods instead of `dataclasses.asdict()` for TOML serialization.

**Why:** `asdict()` does NOT convert `str` Enums to their `.value` -- it keeps them as Enum instances. While `tomli_w` happens to handle this correctly (it treats str Enums as strings), relying on this implicit behavior is fragile. Explicit `.value` conversion is safer and clearer.

**Example:**
```python
# Source: verified with local Python 3.13.7 test
from dataclasses import asdict

# BAD: asdict preserves Enum type, not string value
d = asdict(object_item)  # d["kind"] is PresetKind.MR, not "mr"

# GOOD: explicit serialization
def object_item_to_dict(item: ObjectItem) -> dict:
    return {
        "kind": item.kind.value,
        "value": item.value,
        "label": item.label,
        "open_by_default": item.open_by_default,
    }
```

[VERIFIED: tested locally -- `asdict()` preserves Enum type, `tomli_w` still serializes correctly because str Enum is a str subclass, but explicit is better than implicit]

### Pattern 5: URL Smart Dispatch (Notion/Slack detection)

**What:** The URL opener detects Notion and Slack URLs by hostname and routes them to the desktop app instead of the default browser.

**When to use:** In the `_open_url` handler to satisfy OBJ-03.

**Example:**
```python
# Source: verified with local urllib.parse test
from urllib.parse import urlparse

def _open_url(item: ObjectItem, config: Config) -> None:
    url = item.value
    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    if "notion.so" in hostname:
        # Convert https:// to notion:// for desktop app
        notion_uri = url.replace("https://", "notion://", 1)
        subprocess.run(["open", notion_uri], check=True)
    elif "slack.com" in hostname:
        # Open directly in Slack app via -a flag
        subprocess.run(["open", "-a", "Slack", url], check=True)
    else:
        # Default browser
        subprocess.run(["open", url], check=True)
```

### Anti-Patterns to Avoid

- **Using `dataclasses.asdict()` directly for TOML serialization:** Enums are not converted to values. Use explicit serialization. [VERIFIED: local test]
- **Using `webbrowser.open()` for URLs:** Does not handle custom URI schemes (notion://, obsidian://, slack://). Always use `subprocess.run(["open", ...])`. [CITED: .planning/research/PITFALLS.md CM-4]
- **Non-atomic file writes:** Never use `open(path, "w").write(data)` for `~/.joy/` files. Always tempfile + `os.replace`. [CITED: .planning/research/PITFALLS.md CP-4]
- **Importing Textual in Phase 1:** Phase 1 is headless. No Textual import. The only runtime dependency is `tomli_w`.
- **Hard-coding `~/.joy/` path at module level without configurability:** Store module should define `JOY_DIR = Path.home() / ".joy"` as a module constant but the store functions should accept path overrides for testing.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TOML parsing | Custom parser | `tomllib` (stdlib) | TOML spec is deceptively complex (datetime, nested tables, escape sequences) |
| TOML writing | Custom serializer | `tomli_w` | Inline table vs array-of-tables formatting, proper escaping |
| Atomic file writes | `open(path, 'w')` | `tempfile.mkstemp()` + `os.replace()` | Interrupted writes corrupt data; rename is atomic on POSIX |
| URL encoding for Obsidian | Manual string replacement | `urllib.parse.quote()` | Handles spaces, parens, apostrophes, unicode correctly |
| Enum value access for TOML | `str(enum_member)` | `enum_member.value` | `str(StrEnum)` returns member name (e.g., `"PresetKind.MR"`), not value (e.g., `"mr"`) in Python 3.11+ |

**Key insight:** The two biggest serialization traps in this phase are (1) `asdict()` not converting Enums and (2) `str()` on a `str` Enum returning the qualified name, not the value. Both were verified locally. [VERIFIED: local Python 3.13.7 tests]

## Common Pitfalls

### Pitfall 1: asdict() Does Not Convert str Enums to Values
**What goes wrong:** `dataclasses.asdict()` returns Enum instances, not string values. If passed to a serializer that doesn't handle Enums, it fails or produces wrong output.
**Why it happens:** `asdict()` only recursively converts dataclass instances, tuples, lists, and dicts. Enums pass through unchanged.
**How to avoid:** Write explicit `to_dict()` methods that call `.value` on Enum fields.
**Warning signs:** TOML output contains `"PresetKind.MR"` instead of `"mr"`.
[VERIFIED: local Python 3.13.7 test]

### Pitfall 2: tomli_w Formats Inconsistently for Single vs Multi-Item Arrays
**What goes wrong:** `tomli_w` uses inline table syntax `{ key = "val" }` for arrays with 2+ items but `[[...]]` array-of-tables syntax for single-item arrays. The output looks inconsistent.
**Why it happens:** `tomli_w` optimizes formatting based on content size.
**How to avoid:** Accept this behavior -- both formats are valid TOML and round-trip correctly. Don't try to force consistent formatting.
**Warning signs:** Visual inconsistency in `projects.toml` between projects with one object vs many.
[VERIFIED: local tomli_w test]

### Pitfall 3: Non-Atomic File Writes Cause Data Loss
**What goes wrong:** `open(path, "w").write(data)` truncates the file before writing. If interrupted, `projects.toml` is empty or half-written.
**Why it happens:** The OS truncates on open, then writes sequentially. Any interruption between truncate and write-complete corrupts the file.
**How to avoid:** Write to temp file in same directory, then `os.replace()`.
**Warning signs:** `projects.toml` is empty or contains partial TOML after a crash.
[CITED: .planning/research/PITFALLS.md CP-4]

### Pitfall 4: Obsidian URI Encoding Fails on Special Characters
**What goes wrong:** Obsidian files with spaces, parentheses, or apostrophes in the path fail to open.
**Why it happens:** The `obsidian://open?vault=...&file=...` URI requires proper percent-encoding.
**How to avoid:** Use `urllib.parse.quote(vault, safe="")` for vault name and `quote(file_path, safe="/")` for file path. Keep `/` unencoded in file paths.
**Warning signs:** Notes with spaces in the name don't open.
[VERIFIED: local urllib.parse test with edge cases]

### Pitfall 5: TOML Schema Mismatch Between CONTEXT.md and ARCHITECTURE.md
**What goes wrong:** CONTEXT.md (D-01) specifies `[projects.{name}]` keyed schema, but ARCHITECTURE.md shows `[[project]]` array-based schema. Using the wrong one breaks deserialization.
**Why it happens:** ARCHITECTURE.md was written before the discuss phase locked the keyed schema.
**How to avoid:** Follow CONTEXT.md decisions D-01 and D-02 -- they are locked. Use `projects` as a dict of project dicts, not an array of project dicts.
**Warning signs:** Store code iterates over `data.get("project", [])` instead of `data.get("projects", {}).values()`.
[VERIFIED: both schemas tested locally -- keyed schema from CONTEXT.md works correctly]

### Pitfall 6: Entry Point Module Path Must Match src Layout
**What goes wrong:** `uv tool install .` succeeds but `joy` command gives ModuleNotFoundError.
**Why it happens:** The entry point in pyproject.toml (`joy = "joy.app:main"`) assumes `src/joy/app.py` exists with a `main()` function, and `[tool.hatch.build.targets.wheel] packages = ["src/joy"]` is set correctly.
**How to avoid:** Verify the full chain: pyproject.toml entry point -> module path -> function existence. Test with `uv run joy` before pushing.
**Warning signs:** `ModuleNotFoundError: No module named 'joy'` when running the installed command.
[CITED: .planning/research/PITFALLS.md PD-1]

## Code Examples

Verified patterns from research and local testing:

### TOML Round-Trip with Keyed Schema (D-01/D-02)
```python
# Source: verified with local tomli_w + tomllib test
import tomllib
import tomli_w
from pathlib import Path

def projects_to_toml(projects: list[Project]) -> dict:
    """Convert project list to TOML-serializable dict using keyed schema."""
    result: dict = {"projects": {}}
    for project in projects:
        result["projects"][project.name] = {
            "name": project.name,
            "created": project.created,
            "objects": [
                {
                    "kind": obj.kind.value,
                    "value": obj.value,
                    "label": obj.label,
                    "open_by_default": obj.open_by_default,
                }
                for obj in project.objects
            ],
        }
    return result

def toml_to_projects(data: dict) -> list[Project]:
    """Convert parsed TOML dict to project list."""
    projects = []
    for name, proj_data in data.get("projects", {}).items():
        objects = [
            ObjectItem(
                kind=PresetKind(obj["kind"]),
                value=obj["value"],
                label=obj.get("label", ""),
                open_by_default=obj.get("open_by_default", False),
            )
            for obj in proj_data.get("objects", [])
        ]
        projects.append(Project(
            name=name,
            objects=objects,
            created=proj_data.get("created", date.today()),
        ))
    return projects
```

### Atomic Write Implementation
```python
# Source: verified with local test
import os
import tempfile
import tomli_w
from pathlib import Path

def save_projects(projects: list[Project], path: Path) -> None:
    """Atomically write projects to TOML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = projects_to_toml(projects)
    content = tomli_w.dumps(data).encode("utf-8")

    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
```

### iTerm2 AppleScript (OBJ-07)
```python
# Source: .planning/research/ARCHITECTURE.md + .planning/research/STACK.md
import subprocess

def _open_iterm(item: ObjectItem, config: Config) -> None:
    """Create or activate a named iTerm2 window."""
    # Escape single quotes in the window name to prevent AppleScript injection
    name = item.value.replace('"', '\\"')
    script = f'''
    tell application "iTerm2"
        activate
        set targetWindow to missing value
        repeat with w in windows
            if name of w is "{name}" then
                set targetWindow to w
                exit repeat
            end if
        end repeat
        if targetWindow is missing value then
            set targetWindow to (create window with default profile)
            tell current session of targetWindow
                set name to "{name}"
            end tell
        end if
        select targetWindow
    end tell
    '''
    subprocess.run(["osascript", "-e", script], check=True)
```

### Config Dataclass with Sensible Defaults
```python
# Source: Claude's discretion per CONTEXT.md
@dataclass
class Config:
    """Global configuration loaded from ~/.joy/config.toml."""
    ide: str = "PyCharm"
    editor: str = "Sublime Text"
    obsidian_vault: str = ""
    terminal: str = "iTerm2"
    default_open_kinds: list[str] = field(
        default_factory=lambda: ["worktree", "agents"]
    )
```

### Test Fixture Pattern (subprocess mocking)
```python
# Source: D-13 decision + standard pytest pattern
import pytest
from unittest.mock import patch, call

def test_open_url_in_browser():
    """URL type opens URL in default browser via macOS open command."""
    item = ObjectItem(kind=PresetKind.MR, value="https://gitlab.com/mr/1")
    config = Config()

    with patch("joy.operations.subprocess.run") as mock_run:
        open_object(item=item, config=config)
        mock_run.assert_called_once_with(
            ["open", "https://gitlab.com/mr/1"], check=True
        )

def test_copy_string_to_clipboard():
    """String type copies value to clipboard via pbcopy."""
    item = ObjectItem(kind=PresetKind.BRANCH, value="feature/test")
    config = Config()

    with patch("joy.operations.subprocess.run") as mock_run:
        open_object(item=item, config=config)
        mock_run.assert_called_once_with(
            ["pbcopy"], input=b"feature/test", check=True
        )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `str(StrEnum)` returns value | `str(StrEnum)` returns qualified name | Python 3.11 | Must use `.value` explicitly for serialization |
| `atomicwrites` library | Manual `tempfile` + `os.replace()` | 2023 (atomicwrites deprecated) | No library needed; stdlib pattern only |
| `tomli` (backport) for reading | `tomllib` (stdlib) | Python 3.11 | Zero-dependency TOML reading |
| `webbrowser.open()` for URLs | `subprocess.run(["open", url])` on macOS | Always (macOS) | Correct URI scheme handling |
| Class hierarchy for type dispatch | Dict registry with decorator | Current pattern | Simpler, fewer files, same extensibility |

**Deprecated/outdated:**
- `atomicwrites` library: deprecated, use manual tempfile + os.replace [CITED: .planning/research/PITFALLS.md]
- `tomli` (backport): unnecessary on Python 3.11+ -- use stdlib `tomllib` [VERIFIED: stdlib docs]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Config defaults (PyCharm, Sublime Text, iTerm2) match user's setup | Code Examples / Config | Low -- user can edit config.toml; defaults are just first-run experience |
| A2 | `default_open_kinds = ["worktree", "agents"]` is a reasonable default | Code Examples / Config | Low -- user toggles with spacebar in Phase 3 |
| A3 | `open -a "Slack"` works to route Slack URLs to desktop app | Architecture Patterns / Pattern 5 | Medium -- if Slack app name differs, URL routing fails. Test needed. |
| A4 | `notion://` scheme conversion works for current Notion desktop version | Architecture Patterns / Pattern 5 | Medium -- scheme may change. Store HTTPS, convert at activation time. [CITED: .planning/research/PITFALLS.md UR-2] |

**If this table is empty:** N/A -- 4 assumptions listed above.

## Open Questions

1. **Notion URL scheme reliability**
   - What we know: Replacing `https://` with `notion://` has worked historically. Pitfalls research flags possible scheme changes.
   - What's unclear: Whether the current Notion desktop version (2026) still uses `notion://` scheme.
   - Recommendation: Implement the scheme conversion, test against a live Notion install during Phase 1 integration tests.

2. **TOML schema: preserving project ordering**
   - What we know: The keyed schema `[projects.{name}]` uses a dict. Python 3.7+ dicts preserve insertion order. TOML spec preserves table order. `tomllib` returns an ordered dict.
   - What's unclear: Whether `tomli_w` preserves dict key order when writing.
   - Recommendation: Test ordering preservation in the round-trip test. If order is lost, add an explicit `order` field or switch to `[[project]]` array syntax (would require re-discussing D-01).

3. **AppleScript string injection in iTerm2 opener**
   - What we know: The window name is interpolated directly into AppleScript. A project name containing `"` characters could break the script.
   - What's unclear: Whether simple double-quote escaping is sufficient, or if more robust sanitization is needed.
   - Recommendation: Escape `"` to `\"` in the window name. Add a test case with special characters in the name.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All code | Yes | 3.13.7 | -- |
| uv | Package management | Yes | 0.11.2 | -- |
| osascript | iTerm2 operations | Yes | /usr/bin/osascript | -- |
| pbcopy | Clipboard operations | Yes | /usr/bin/pbcopy | -- |
| open | URL/app launching | Yes | /usr/bin/open | -- |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ~9.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (Wave 0 -- create from scratch) |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OBJ-01 | string copies to clipboard via pbcopy | unit | `uv run pytest tests/test_operations.py::test_copy_string -x` | Wave 0 |
| OBJ-02 | url opens in default browser | unit | `uv run pytest tests/test_operations.py::test_open_url_browser -x` | Wave 0 |
| OBJ-03 | Notion/Slack url opens desktop app | unit | `uv run pytest tests/test_operations.py::test_open_url_notion -x` | Wave 0 |
| OBJ-04 | obsidian opens via URI scheme | unit | `uv run pytest tests/test_operations.py::test_open_obsidian -x` | Wave 0 |
| OBJ-05 | file opens in configured editor | unit | `uv run pytest tests/test_operations.py::test_open_file -x` | Wave 0 |
| OBJ-06 | worktree opens in configured IDE | unit | `uv run pytest tests/test_operations.py::test_open_worktree -x` | Wave 0 |
| OBJ-07 | iterm creates/focuses named window | unit | `uv run pytest tests/test_operations.py::test_open_iterm -x` | Wave 0 |
| PRESET-01..09 | preset-to-type mapping correct | unit | `uv run pytest tests/test_models.py::test_preset_map -x` | Wave 0 |
| DIST-02 | data lives in ~/.joy/ | unit | `uv run pytest tests/test_store.py::test_joy_dir -x` | Wave 0 |
| -- | TOML round-trip (serialize + deserialize) | unit | `uv run pytest tests/test_store.py::test_round_trip -x` | Wave 0 |
| -- | Atomic write (temp + replace) | unit | `uv run pytest tests/test_store.py::test_atomic_write -x` | Wave 0 |
| -- | Model equality and properties | unit | `uv run pytest tests/test_models.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `pyproject.toml` -- needs `[tool.pytest.ini_options]` section with markers and testpaths
- [ ] `tests/conftest.py` -- shared fixtures: `tmp_joy_dir` (temp directory for store tests), `sample_project` factory, `sample_config`
- [ ] `tests/test_models.py` -- model creation, equality, PRESET_MAP completeness
- [ ] `tests/test_store.py` -- TOML round-trip, atomic write, missing file handling
- [ ] `tests/test_operations.py` -- subprocess mock tests for all 7 operation types
- [ ] Framework install: `uv add --dev pytest`

## Security Domain

> This is a personal macOS-only tool with no network access, no authentication, and no user input from untrusted sources. Security concerns are minimal but documented.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A -- personal tool, no auth |
| V3 Session Management | No | N/A -- no sessions |
| V4 Access Control | No | N/A -- single user |
| V5 Input Validation | Minimal | Validate PresetKind/ObjectType enum values on TOML deserialization |
| V6 Cryptography | No | N/A -- no secrets stored |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| AppleScript injection via project name | Tampering | Escape double quotes in iTerm2 AppleScript string interpolation |
| Path traversal in file/worktree values | Tampering | Values are user-provided paths -- no validation needed (user controls their own data) |
| Malformed TOML causing crash | Denial of Service | Wrap `tomllib.load()` in try/except, return empty project list on parse failure |

## Sources

### Primary (HIGH confidence)
- Python 3.13.7 stdlib docs: tomllib, dataclasses, enum, subprocess, os, tempfile [VERIFIED: local runtime]
- Local verification tests: asdict() behavior, tomli_w round-trip, atomic writes, URL encoding [VERIFIED: ran on machine]
- `.planning/research/ARCHITECTURE.md` -- data model, component design, TOML schema, operations pattern
- `.planning/research/STACK.md` -- library choices, macOS integration approach
- `.planning/research/PITFALLS.md` -- atomic writes, URL encoding, AppleScript risks

### Secondary (MEDIUM confidence)
- PyPI: tomli-w 1.2.0 (2025-01-15), hatchling 1.29.0 (2026-02-23), pytest ~9.0.3 (2026-04-07) [CITED: pypi.org via WebSearch]

### Tertiary (LOW confidence)
- Notion `notion://` scheme behavior in current version [ASSUMED: based on historical behavior]
- Slack `open -a "Slack"` routing behavior [ASSUMED: standard macOS app routing]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- stdlib + verified PyPI packages, all tested locally
- Architecture: HIGH -- patterns verified with runnable code, TOML round-trip confirmed
- Pitfalls: HIGH -- all critical pitfalls verified locally (asdict, atomicity, encoding)
- Testing: HIGH -- standard pytest patterns, no novel testing challenges

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (30 days -- all technologies are stable)
