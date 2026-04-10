<!-- GSD:project-start source:PROJECT.md -->
## Project

**joy**

`joy` is a keyboard-driven Python TUI for managing coding project artifacts. It gives developers an instant overview of all objects related to a project — branches, MRs, tickets, worktrees, notes, agents, and more — and lets them open any or all of them with a single keystroke. Installable globally via `uv`, configured per-machine in `~/.joy`.

**Core Value:** Every artifact for the active project, openable instantly from one interface — no hunting through tabs, terminals, or bookmarks.

### Constraints

- **Tech stack**: Python, managed with `uv` — no other runtimes
- **Platform**: macOS only — relies on OS-level URL handlers and AppleScript
- **Install target**: `uv tool install git+<repo>` — must work as a globally installed tool
- **Config location**: `~/.joy/` — projects data, global settings, all state lives here
- **Design**: Minimalistic, snappy — no heavy dependencies that slow startup
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### TUI Library: Textual 8.x
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| textual | ^8.2 | TUI framework | Only serious option for Python TUI in 2025-2026. CSS-based layout, built-in widgets (ListView, DataTable), first-class keyboard binding system, async-native, active development (monthly releases through 2025-2026). MIT licensed. |
| rich | >=14.2 | Terminal rendering | Textual dependency -- also useful standalone for any non-TUI rich text output |
- **Keyboard bindings:** First-class `BINDINGS` class variable on any widget. Searches focus chain upward through DOM. Supports priority bindings, multiple keys per action, custom keymaps (vim-style hjkl trivial to add). Exactly what joy needs.
- **Two-pane layout:** Dock sidebar left with `dock: left` in CSS. ListView widget for project list, scrollable content pane for project detail. Built-in, no hacking required.
- **CSS styling:** Textual CSS (subset of web CSS) allows clean separation of layout/style from logic. External `.tcss` files supported. Enables the "minimalistic but pretty" goal.
- **ListView + ListItem:** Purpose-built widgets for the project list pane with keyboard navigation (up/down/enter) built in.
- **Lazy widget mounting:** Widgets can be lazily mounted after first refresh, reducing perceived startup time.
- **Startup time:** Textual itself renders fast (~12ms render cycles reported). The bottleneck is Python import time. With `uv tool install`, the virtual environment is pre-built, so import resolution is fast. Expect sub-500ms to first render for a lean app -- acceptable for a developer tool.
### Data Storage: TOML (tomllib + tomli_w)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| tomllib | stdlib (3.11+) | Read TOML | Zero-dependency TOML parsing, in Python stdlib since 3.11 |
| tomli_w | ^1.0 | Write TOML | Lightweight TOML writer, counterpart to tomllib |
| Format | Human-editable | Comments | Python stdlib | Schema simplicity | Verdict |
|--------|---------------|----------|--------------|-------------------|---------|
| TOML | Excellent | Yes | Read: 3.11+ | Great for flat/nested config | **Winner** |
| JSON | Decent | No | Yes (json) | Verbose for nested data | Runner-up |
| YAML | Good | Yes | No (PyYAML dep) | Indentation footguns | No |
| SQLite | No | N/A | Yes (sqlite3) | Overkill for this data | No |
### macOS Integration
| Technology | Purpose | Approach |
|------------|---------|----------|
| subprocess + `open` | URL schemes | `subprocess.run(["open", "notion://..."])` -- macOS `open` command handles all registered URI schemes |
| subprocess + `pbcopy` | Clipboard | `subprocess.run(["pbcopy"], input=text.encode(), check=True)` -- zero dependencies, macOS built-in |
| subprocess + `osascript` | iTerm2/AppleScript | `subprocess.run(["osascript", "-e", script])` -- direct AppleScript execution |
| webbrowser (stdlib) | HTTP URLs | `webbrowser.open(url)` -- for regular web URLs, simpler than subprocess |
#### URL Scheme Opening (notion://, slack://, obsidian://)
# Works for all of these:
#### Clipboard (for `string` type objects like branch names)
#### AppleScript / iTerm2 Integration
#### Opening files in editors/IDEs
### Packaging: uv with hatchling backend
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| uv | latest | Package manager, tool installer | Project requirement. Rust-based, fast, handles everything. |
| hatchling | ^1.25 | Build backend | Mature, well-documented, supports entry points cleanly. uv_build is newer but hatchling is battle-tested and uv works perfectly with it. |
### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tomli_w | ^1.0 | TOML writing | Always -- only non-stdlib dependency besides Textual |
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
