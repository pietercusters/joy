# Stack Research: joy

**Project:** joy -- keyboard-driven Python TUI for managing coding project artifacts
**Researched:** 2026-04-10
**Overall confidence:** HIGH

---

## Recommended Stack

### TUI Library: Textual 8.x

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| textual | ^8.2 | TUI framework | Only serious option for Python TUI in 2025-2026. CSS-based layout, built-in widgets (ListView, DataTable), first-class keyboard binding system, async-native, active development (monthly releases through 2025-2026). MIT licensed. |
| rich | >=14.2 | Terminal rendering | Textual dependency -- also useful standalone for any non-TUI rich text output |

**Confidence:** HIGH -- Textual is the unchallenged standard for Python TUI applications. Version 8.2.3 released April 5, 2026. Active development with frequent releases. No credible alternative exists that matches its feature set.

**Key Textual features for joy:**

- **Keyboard bindings:** First-class `BINDINGS` class variable on any widget. Searches focus chain upward through DOM. Supports priority bindings, multiple keys per action, custom keymaps (vim-style hjkl trivial to add). Exactly what joy needs.
- **Two-pane layout:** Dock sidebar left with `dock: left` in CSS. ListView widget for project list, scrollable content pane for project detail. Built-in, no hacking required.
- **CSS styling:** Textual CSS (subset of web CSS) allows clean separation of layout/style from logic. External `.tcss` files supported. Enables the "minimalistic but pretty" goal.
- **ListView + ListItem:** Purpose-built widgets for the project list pane with keyboard navigation (up/down/enter) built in.
- **Lazy widget mounting:** Widgets can be lazily mounted after first refresh, reducing perceived startup time.
- **Startup time:** Textual itself renders fast (~12ms render cycles reported). The bottleneck is Python import time. With `uv tool install`, the virtual environment is pre-built, so import resolution is fast. Expect sub-500ms to first render for a lean app -- acceptable for a developer tool.

**Python version:** Require >=3.11. This gets us `tomllib` in stdlib (see Data Storage below) and all modern Python features. Textual supports 3.9+ but there is no reason to support older versions for a personal macOS-only tool.

**Textual dependencies pulled in automatically:** markdown-it-py, mdit-py-plugins, rich, typing-extensions, platformdirs, pygments. All lightweight.

### Data Storage: TOML (tomllib + tomli_w)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| tomllib | stdlib (3.11+) | Read TOML | Zero-dependency TOML parsing, in Python stdlib since 3.11 |
| tomli_w | ^1.0 | Write TOML | Lightweight TOML writer, counterpart to tomllib |

**Confidence:** HIGH

**Rationale -- TOML over JSON, YAML, or SQLite:**

| Format | Human-editable | Comments | Python stdlib | Schema simplicity | Verdict |
|--------|---------------|----------|--------------|-------------------|---------|
| TOML | Excellent | Yes | Read: 3.11+ | Great for flat/nested config | **Winner** |
| JSON | Decent | No | Yes (json) | Verbose for nested data | Runner-up |
| YAML | Good | Yes | No (PyYAML dep) | Indentation footguns | No |
| SQLite | No | N/A | Yes (sqlite3) | Overkill for this data | No |

joy's data model is small: a list of projects, each with a list of typed objects plus metadata. This maps perfectly to TOML's table-of-tables syntax. Users can hand-edit `~/.joy/projects.toml` in emergencies. Comments survive round-trips if we use `tomlkit` instead of `tomli_w` (but `tomli_w` is simpler and we don't need comment preservation since joy owns the file).

**File structure in ~/.joy/:**

```
~/.joy/
  config.toml        # Global settings (IDE, vault path, editor, etc.)
  projects.toml      # All project data
```

Two files, not a directory-per-project. The data volume is tiny (dozens of projects, each with ~10 objects). Single-file is simpler to back up, simpler to implement, and TOML handles it cleanly.

**Example projects.toml:**

```toml
[[project]]
name = "joy"
created = 2026-04-10

[[project.object]]
type = "mr"
value = "https://gitlab.com/..."
label = "Main MR"
open_by_default = true

[[project.object]]
type = "branch"
value = "feature/tui-layout"
open_by_default = true
```

### macOS Integration

| Technology | Purpose | Approach |
|------------|---------|----------|
| subprocess + `open` | URL schemes | `subprocess.run(["open", "notion://..."])` -- macOS `open` command handles all registered URI schemes |
| subprocess + `pbcopy` | Clipboard | `subprocess.run(["pbcopy"], input=text.encode(), check=True)` -- zero dependencies, macOS built-in |
| subprocess + `osascript` | iTerm2/AppleScript | `subprocess.run(["osascript", "-e", script])` -- direct AppleScript execution |
| webbrowser (stdlib) | HTTP URLs | `webbrowser.open(url)` -- for regular web URLs, simpler than subprocess |

**Confidence:** HIGH -- these are stable macOS system interfaces, not library-dependent.

#### URL Scheme Opening (notion://, slack://, obsidian://)

Use `subprocess.run(["open", url])` for all URL types. The macOS `open` command dispatches to the registered handler for any URI scheme:

```python
import subprocess

def open_url(url: str) -> None:
    """Open any URL/URI scheme using macOS open command."""
    subprocess.run(["open", url], check=True)

# Works for all of these:
open_url("https://gitlab.com/...")           # Browser
open_url("notion://www.notion.so/...")       # Notion desktop
open_url("slack://channel?team=T0&id=C0")   # Slack desktop
open_url("obsidian://open?vault=wiki&file=Home")  # Obsidian
```

For Obsidian specifically, the URI format is: `obsidian://open?vault={vault_name}&file={file_path}` where file_path is URL-encoded and relative to the vault root. The vault name comes from joy's global config.

#### Clipboard (for `string` type objects like branch names)

No library needed. macOS provides `pbcopy`:

```python
import subprocess

def copy_to_clipboard(text: str) -> None:
    """Copy text to macOS clipboard."""
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
```

Do NOT add `pyperclip` as a dependency. It's a cross-platform abstraction layer that adds nothing on macOS-only.

#### AppleScript / iTerm2 Integration

Use `subprocess.run(["osascript", "-e", script])` to execute AppleScript. No Python wrapper library needed.

**Creating/activating a named iTerm2 window:**

```python
import subprocess

def open_iterm_window(name: str) -> None:
    """Create or activate a named iTerm2 window."""
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

**Important note:** iTerm2's AppleScript support is officially deprecated in favor of their Python API, but it will continue receiving bug fixes. For joy's use case (create/activate named windows), AppleScript is simpler, has zero dependencies, and the needed functionality is stable. The iTerm2 Python API requires installing `iterm2` package and running an async connection -- overkill for what is essentially "find or create a named window."

#### Opening files in editors/IDEs

```python
subprocess.run(["open", "-a", "Sublime Text", filepath])  # Sublime
subprocess.run(["open", "-a", "PyCharm", dirpath])          # PyCharm
```

The `-a` flag to `open` specifies the application. The app name comes from joy's global config.

### Packaging: uv with hatchling backend

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| uv | latest | Package manager, tool installer | Project requirement. Rust-based, fast, handles everything. |
| hatchling | ^1.25 | Build backend | Mature, well-documented, supports entry points cleanly. uv_build is newer but hatchling is battle-tested and uv works perfectly with it. |

**Confidence:** HIGH

**pyproject.toml structure for `uv tool install git+...`:**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "joy"
version = "0.1.0"
description = "Keyboard-driven TUI for managing coding project artifacts"
requires-python = ">=3.11"
license = "MIT"
dependencies = [
    "textual>=8.2,<9",
    "tomli_w>=1.0,<2",
]

[project.scripts]
joy = "joy.app:main"

[tool.hatch.build.targets.wheel]
packages = ["src/joy"]
```

**Why hatchling over uv_build:** uv_build is newer (default since July 2025) and works well for simple cases. However, hatchling has years of ecosystem validation, better documentation, and more configuration options. For a project that will be installed via `uv tool install git+...`, hatchling is the safer choice. Both work identically from the user's perspective.

**Project structure:**

```
joy/
  pyproject.toml
  src/
    joy/
      __init__.py
      app.py          # Entry point, main() function
      ...
```

**Installation command:**

```bash
uv tool install git+https://github.com/user/joy
```

This creates an isolated virtual environment, installs joy + dependencies, and symlinks `joy` onto PATH.

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tomli_w | ^1.0 | TOML writing | Always -- only non-stdlib dependency besides Textual |

That's it. Two dependencies total: `textual` and `tomli_w`. Everything else is stdlib or macOS system tools.

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| TUI framework | Textual | urwid | Ancient API, no CSS, no built-in widgets, poor keyboard binding system. Still works but feels like 2010. |
| TUI framework | Textual | prompt_toolkit | Designed for prompts/REPLs, not full-screen TUIs. Powers ipython but not suitable for a two-pane app. |
| TUI framework | Textual | curses (stdlib) | Extremely low-level. Would require building everything from scratch. No one should do this in 2026. |
| TUI framework | Textual | pytermgui | Small community, fewer widgets, less documentation. Textual is strictly better for this use case. |
| Data format | TOML | JSON | No comments, verbose syntax, not human-friendly for config-like data. Would work but TOML is better for this shape of data. |
| Data format | TOML | YAML | Adds PyYAML dependency, indentation-sensitive (footgun), security concerns with unsafe loading. No benefit over TOML here. |
| Data format | TOML | SQLite | Overkill for <100 records. Not human-editable. Adds complexity without benefit. Would make sense at 10K+ records. |
| Clipboard | pbcopy (subprocess) | pyperclip | Unnecessary dependency for macOS-only app. pyperclip just wraps pbcopy on macOS anyway. |
| AppleScript | subprocess + osascript | py-applescript | Extra dependency for what amounts to `subprocess.run(["osascript", ...])`. Not worth it. |
| AppleScript | subprocess + osascript | iTerm2 Python API | Requires `iterm2` package, async connection, more complex setup. Overkill for "create/activate named window." |
| Build backend | hatchling | uv_build | uv_build is newer and slightly faster to resolve, but hatchling has more documentation and community knowledge. Low-stakes decision -- either works fine. |
| Build backend | hatchling | setuptools | Legacy. Works but hatchling is the modern standard and simpler to configure. |
| Build backend | hatchling | poetry-core | Tied to Poetry ecosystem. Since we use uv, no reason to pull in poetry-core. |
| TOML writer | tomli_w | tomlkit | tomlkit preserves comments and style on round-trip, which is valuable if humans edit the file and joy modifies it. But tomli_w is simpler and joy owns its data files (no user comments to preserve). If comment preservation becomes needed later, swap to tomlkit -- the API is similar. |

## Confidence Levels

| Decision | Confidence | Reasoning |
|----------|------------|-----------|
| Textual as TUI framework | HIGH | Unchallenged standard. v8.2.3 released April 2026. Active monthly releases. No credible alternative. Verified via PyPI and official docs. |
| TOML for data storage | HIGH | Python stdlib support (tomllib), human-editable, perfect data shape fit. Well-established in Python ecosystem (pyproject.toml itself is TOML). |
| tomli_w for TOML writing | HIGH | Official counterpart to stdlib tomllib. Lightweight, maintained, simple API. Verified on PyPI. |
| subprocess for macOS integration | HIGH | Using OS-provided tools (open, pbcopy, osascript). Zero dependencies, maximally stable. Standard practice. |
| AppleScript for iTerm2 | MEDIUM | AppleScript is officially deprecated by iTerm2 (bug fixes only, no new features). But the needed features (create/select window, set name) are stable and simple. Risk: if iTerm2 drops AppleScript entirely in a future version. Mitigation: the Python API exists as a fallback. For a personal tool, this risk is acceptable. |
| hatchling as build backend | HIGH | Battle-tested, well-documented, works perfectly with uv. Verified via official uv and hatchling docs. |
| Python >=3.11 requirement | HIGH | Gets us tomllib in stdlib. macOS ships Python 3.12+ via Xcode CLT. uv manages Python versions anyway. No reason to support older versions for personal macOS-only tooling. |

## Key Findings

- **Textual 8.x is the clear winner for Python TUI.** No other library comes close for building a two-pane, keyboard-driven, visually polished terminal app. It has built-in ListView, CSS-based styling, first-class key bindings, and lazy widget mounting. Active development with monthly releases.

- **The entire dependency footprint is two packages: textual and tomli_w.** Everything else is either Python stdlib (tomllib, subprocess, webbrowser) or macOS system tools (open, pbcopy, osascript). This minimalism supports the "snappy startup" goal.

- **macOS integration requires zero Python libraries.** All URL scheme handling (notion://, slack://, obsidian://), clipboard operations, and iTerm2 automation work through subprocess calls to OS-provided commands. This is the correct approach for a macOS-only tool.

- **TOML is the right data format for joy.** Human-editable, comments supported, Python stdlib reading (3.11+), lightweight writer available. The data shape (list of projects with nested typed objects) maps naturally to TOML tables.

- **uv tool install with hatchling backend is straightforward.** A `[project.scripts]` entry point in pyproject.toml is all that's needed. Users run `uv tool install git+<repo>` and get `joy` on their PATH in an isolated environment.

## Sources

- Textual official site: https://textual.textualize.io/
- Textual PyPI: https://pypi.org/project/textual/
- Textual GitHub: https://github.com/Textualize/textual
- Textual keyboard bindings: https://textual.textualize.io/guide/input/
- Textual layout guide: https://textual.textualize.io/guide/layout/
- Textual lazy loading: https://textual.textualize.io/api/lazy/
- uv tool docs: https://docs.astral.sh/uv/guides/tools/
- uv build backend: https://docs.astral.sh/uv/concepts/build-backend/
- uv project config: https://docs.astral.sh/uv/concepts/projects/config/
- Python tomllib docs: https://docs.python.org/3/library/tomllib.html
- tomli_w PyPI: https://pypi.org/project/tomli-w/
- Obsidian URI scheme: https://help.obsidian.md/Extending+Obsidian/Obsidian+URI
- iTerm2 scripting docs: https://iterm2.com/3.4/documentation-scripting.html
- Python packaging guide: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
