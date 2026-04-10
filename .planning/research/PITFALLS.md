# Pitfalls Research: joy

**Domain:** Python TUI project artifact manager (Textual, macOS-only, keyboard-driven)
**Researched:** 2026-04-10

---

## Critical Pitfalls

Mistakes that cause rewrites, broken UX, or unusable shipped product.

### CP-1: Blocking the Textual Event Loop

**What goes wrong:** Any synchronous/blocking call inside an event handler, `on_mount`, or message handler freezes the entire TUI. The screen goes unresponsive -- no key input, no rendering, no feedback. Even a 200ms file read or subprocess call is noticeable.

**Why it happens:** Textual runs on asyncio. Coroutines only yield at `await` points. If you call `subprocess.run()`, `open().read()`, or `time.sleep()` inside a handler, the event loop is blocked until it returns. This is the single most common Textual mistake.

**Consequences:** UI appears frozen or dead. Users think the app crashed. Especially bad for joy because `o` (activate object) launches subprocesses (`open`, `osascript`) and those calls MUST be non-blocking.

**Prevention:**
- Use `@work(thread=True)` decorator or `self.run_worker()` for any I/O or subprocess call
- Use `asyncio.create_subprocess_exec()` instead of `subprocess.run()` for launching URLs/apps
- Never use `time.sleep()` -- use `await asyncio.sleep()` or `self.set_timer()`
- Use `app.call_from_thread()` when a threaded worker needs to update the UI

**Detection:** App freezes momentarily when opening URLs, files, or iTerm2 windows. Profile with `python -X importtime` for import-time issues.

**Phase:** Phase 1 (core TUI) -- establish the pattern from day one. Every object activation handler must be async.

**Confidence:** HIGH -- documented in official Textual docs, confirmed by multiple sources.

---

### CP-2: Slow Startup from Eager Imports

**What goes wrong:** The TUI takes 500ms+ to show first paint. For a "snappy developer tool," anything over 300ms feels sluggish. Textual + Rich alone import in ~130-230ms. Add httpx, pydantic, or any heavy library and you easily hit 500ms+.

**Why it happens:** Python evaluates all top-level imports eagerly. Textual and Rich have substantial import trees. Any additional dependency (TOML writer, AppleScript helpers, etc.) compounds the problem.

**Consequences:** Users perceive the tool as slow. For a tool meant to be launched dozens of times daily, even 200ms extra startup is painful.

**Prevention:**
- Profile imports early: `python -X importtime -c "from joy.app import JoyApp" 2>&1 | head -30`
- Move non-essential imports inside functions (e.g., TOML writing only when saving, AppleScript only when activating agents)
- Use Textual's `Lazy` widget for the detail pane content -- only render visible content on startup
- Avoid libraries that auto-detect and import optional deps (httpx does this with click/rich)
- Keep `__init__.py` files minimal -- no imports that trigger dependency chains
- Target: first paint under 350ms

**Detection:** Run `time joy` from shell. If it's over 400ms to first paint, investigate.

**Phase:** Phase 1 -- measure from the very first prototype. Much harder to fix retroactively.

**Confidence:** HIGH -- Posting (a real Textual app) documented a 40% improvement (580ms to 360ms) using exactly these techniques. Source: https://darren.codes/posts/python-startup-time/

---

### CP-3: Fire-and-Forget Async Tasks (The Heisenbug)

**What goes wrong:** You create an asyncio task with `asyncio.create_task()` but don't store a reference. The garbage collector destroys the task before it completes. The operation silently fails -- no error, no warning, no traceback.

**Why it happens:** Unlike threads, asyncio tasks have no lifecycle protection. If no reference exists, GC collects them. This is intermittent and timing-dependent, making it extremely hard to debug.

**Consequences:** Object activations randomly fail to open. iTerm2 windows sometimes don't create. URLs sometimes don't open. The randomness makes it look like a system issue, not a code bug.

**Prevention:**
- Always store task references: `self._tasks.add(task); task.add_done_callback(self._tasks.discard)`
- Use Textual's `@work` decorator instead of raw `create_task()` -- it manages task lifecycle
- Use `asyncio.TaskGroup` (Python 3.11+) for grouped operations
- Never use bare `asyncio.create_task()` without storing the result

**Detection:** Operations that "sometimes work" are the classic symptom. Add logging to task completion callbacks.

**Phase:** Phase 1 -- use `@work` from the start and never use raw `create_task`.

**Confidence:** HIGH -- documented by Textual's creator: https://textual.textualize.io/blog/2023/02/11/the-heisenbug-lurking-in-your-async-code/

---

### CP-4: Non-Atomic Config File Writes Causing Data Loss

**What goes wrong:** Power loss, crash, or keyboard interrupt during a TOML write leaves `~/.joy/projects.toml` as a zero-byte or half-written file. Next startup fails with a parse error or silently loads empty data. All project configurations lost.

**Why it happens:** Naive `open("file", "w").write(data)` truncates the file before writing. If the process dies between truncation and write completion, the file is corrupted.

**Consequences:** Total data loss for all project configurations. For a personal tool that stores workflow state, this is catastrophic.

**Prevention:**
- Write to a temp file in the same directory, then `os.replace()` (atomic on POSIX)
- Pattern: `write to ~/.joy/.projects.toml.tmp` then `os.replace(tmp, target)`
- Use the `safer` library if you want a drop-in replacement for `open()`
- Keep a `.bak` copy before writes: `shutil.copy2(target, target + ".bak")`
- On startup, if main file is corrupt/missing, check for `.bak` and recover

**Detection:** Corrupt config file on startup. Add a try/except around TOML parsing with recovery logic.

**Phase:** Phase 2 (data storage) -- implement atomic writes from the first file operation.

**Confidence:** HIGH -- well-established pattern. The `atomicwrites` library is deprecated; use `safer` or manual temp+rename.

---

## Common Mistakes

Frequently made errors in Textual TUI development that degrade quality.

### CM-1: Textual Widget Lifecycle Confusion (compose vs on_mount timing)

**What goes wrong:** Accessing child widgets or DOM in the wrong lifecycle phase. Trying to query children immediately after `mount()` -- they aren't ready yet. Trying to set reactive attributes in `__init__` before the widget is mounted -- watchers that query DOM crash.

**Why it happens:** Textual guarantees mount completion by the *next* message handler, not immediately. `compose()` yields widgets, but they're not in the DOM until after compose returns.

**Consequences:** AttributeError or NoMatches exceptions during initialization. Widgets appear blank or in wrong state.

**Prevention:**
- Data loading and widget population goes in `on_mount()`, not `__init__()` or `compose()`
- Use `self.call_after_refresh()` if you need to act after layout is complete
- For reactive attributes in `__init__`, use `self.set_reactive(MyWidget.my_attr, value)` instead of direct assignment
- Never query child widgets inside `compose()` -- they don't exist yet

**Detection:** Exceptions during app startup containing "NoMatches" or "not mounted."

**Phase:** Phase 1 -- understand the lifecycle before building any widgets.

**Confidence:** HIGH -- documented in Textual official docs and GitHub issues.

---

### CM-2: Textual CSS Sizing and Layout Traps

**What goes wrong:** Widgets render at wrong sizes, overflow their containers, or collapse to zero height. The two-pane layout (project list + detail) either doesn't split correctly or one pane dominates.

**Why it happens:** Textual CSS is inspired by web CSS but has significant differences. Common traps:
- Default `box-sizing` is `border-box` (border/padding reduces content area)
- `height: auto` auto-detects from content but can collapse to 0 if content is empty
- Forgetting to set explicit widths on the two panes (use `width: 1fr` and `width: 2fr` for a 1:2 split)
- Button/Input widgets have default padding/border that make them taller than expected

**Consequences:** Broken layout. Detail pane either takes all space or collapses. Scrolling doesn't work in panes.

**Prevention:**
- Use `fr` units for the two-pane split: left pane `width: 1fr`, right pane `width: 2fr`
- Set `height: 1fr` on containers that should fill available space
- Use Textual's DevTools (`textual run --dev`) to inspect widget dimensions live
- Set `overflow-y: auto` on the detail pane for scrolling
- Remove default widget border/padding when building compact layouts: `border: none; padding: 0;`

**Detection:** Visual inspection. Run with `textual run --dev` for live CSS debugging.

**Phase:** Phase 1 -- get the two-pane layout right in the first milestone.

**Confidence:** HIGH -- documented in Textual layout guide and confirmed by GitHub issues.

---

### CM-3: Key Binding Conflicts with Terminal Emulators

**What goes wrong:** Keyboard shortcuts that work in one terminal don't work in another. Ctrl+key combinations are intercepted by the terminal, tmux, or iTerm2 before reaching the Textual app. Arrow keys stop working in certain contexts.

**Why it happens:** Textual can only receive keys that the terminal emulator forwards. iTerm2, Terminal.app, and tmux all intercept certain key combinations. Ctrl+C, Ctrl+Z, and many Ctrl+letter combos are claimed by the terminal. Even Escape can have timing issues (terminal escape sequences).

**Consequences:** Core navigation breaks for users with different terminal configurations.

**Prevention:**
- Stick to simple, safe bindings: single letters (`o`, `a`, `e`, `d`), Enter, Escape, Tab, arrow keys
- Avoid Ctrl+key for primary operations (fine for secondary shortcuts)
- Test in both iTerm2 and Terminal.app
- Use Textual's binding priority system for critical bindings: `Binding("o", "activate", priority=True)`
- Document that joy is designed for iTerm2 but should work in most terminals

**Detection:** Test all keybindings in iTerm2 specifically, since that's the target terminal.

**Phase:** Phase 1 -- design the keymap once and test early.

**Confidence:** HIGH -- confirmed by Textual FAQ, Posting project docs, and GitHub issues.

---

### CM-4: Using `webbrowser.open()` Instead of `subprocess.run(["open", ...])`

**What goes wrong:** `webbrowser.open()` doesn't reliably handle custom URL schemes (`notion://`, `obsidian://`, `slack://`). It may open in the wrong app, fail silently, or not handle `file://` paths.

**Why it happens:** `webbrowser.open()` is designed for HTTP URLs and browser control. Custom URL schemes require macOS's `open` command which delegates to the OS URL handler.

**Consequences:** Notion links open in browser instead of Notion app. Obsidian URIs fail. Slack deep links don't work.

**Prevention:**
- Always use `subprocess.run(["open", url])` or `asyncio.create_subprocess_exec("open", url)` on macOS
- For app-specific URLs: `subprocess.run(["open", "-a", "Notion", url])` to force the correct app
- For Obsidian: `subprocess.run(["open", f"obsidian://open?vault={vault}&file={file}"])`
- URL-encode paths properly: use `urllib.parse.quote()` for file paths with spaces/special chars

**Detection:** URLs opening in browser instead of the native app.

**Phase:** Phase 2 (object operations) -- this is the core of joy's activate functionality.

**Confidence:** HIGH -- macOS `open` command behavior is well-documented. `webbrowser` limitations confirmed by Python docs.

---

### CM-5: TOML Read/Write Library Mismatch

**What goes wrong:** Using `tomllib` (stdlib, read-only) for reading but a different library for writing, leading to subtle formatting differences, lost comments, or round-trip corruption.

**Why it happens:** Python's stdlib `tomllib` (3.11+) only reads TOML. For writing, you need a separate library. `tomli-w` is minimal and doesn't preserve style. `tomlkit` preserves style but is heavier.

**Consequences:** Config files lose comments or formatting on save. Users who manually edit `~/.joy/config.toml` find their formatting destroyed.

**Prevention:**
- Use `tomlkit` for both reading and writing -- it preserves comments and formatting during round-trips
- If startup time matters (it does for joy), lazy-import tomlkit: import inside the save function, not at module level
- Alternative: use `tomllib` for reading (fast, stdlib) and `tomli-w` for writing (fast), but accept that manual formatting will be lost on save
- Recommendation for joy: `tomllib` for reading (already in stdlib, zero import cost), `tomli-w` for writing (lightweight). Accept lost formatting since users rarely hand-edit these files.

**Detection:** Save a config, inspect the file, check if comments/formatting survived.

**Phase:** Phase 2 (data storage) -- decide the library pair before writing any persistence code.

**Confidence:** HIGH -- confirmed by Real Python TOML guide and library comparisons.

---

### CM-6: Focus Traps in Keyboard-Only Navigation

**What goes wrong:** Focus gets stuck in a widget (e.g., an input field, a modal, or a sub-list) with no obvious way to escape. The user presses Escape or Tab and nothing happens. They're trapped.

**Why it happens:** Textual's focus chain follows DOM order. If a widget consumes Escape or Tab without propagating, focus is trapped. Modals that don't handle dismiss properly are the most common cause.

**Consequences:** User has to Ctrl+C to quit. For a keyboard-only tool, this is a critical UX failure.

**Prevention:**
- Always handle Escape to dismiss/unfocus: every modal, input, and dialog must respond to Escape
- Test the complete focus cycle: Tab through all widgets, Escape from every state
- Use `self.app.pop_screen()` for screen-based navigation -- built-in Escape handling
- Implement `action_focus_next` and `action_focus_previous` for Tab/Shift+Tab navigation
- The project list and detail pane should be the only two focusable regions in the main view

**Detection:** Manual testing: try to Tab/Escape from every interactive element.

**Phase:** Phase 1 -- design focus management into the navigation model.

**Confidence:** MEDIUM -- based on general TUI UX patterns and Textual focus documentation.

---

## iTerm2 Integration Risks

Specific risks for the `agents` object type that creates/activates named iTerm2 windows.

### IR-1: AppleScript Is Deprecated, but Python API Has Higher Complexity

**What goes wrong:** AppleScript for iTerm2 is in "maintenance mode" and no longer receiving improvements. The official recommendation is to use the iTerm2 Python API. However, the Python API requires iTerm2 to be running and has its own complexity.

**Why it happens:** iTerm2's Python API is more powerful but requires:
- iTerm2 must be running (can't launch it via the API)
- Scripts must connect to a running iTerm2 instance via its IPC mechanism
- The API is async-only with `async_`-prefixed methods
- Installing the `iterm2` Python package adds a dependency

**Consequences:** Extra complexity. If iTerm2 isn't running, the API can't connect. The `iterm2` package adds import time even when not used.

**Prevention:**
- Use AppleScript via `osascript` for joy's simple use case (create window, set name, activate). It's simpler and sufficient.
- AppleScript being in "maintenance mode" doesn't mean it's broken -- it just won't get new features. joy's needs are basic.
- Fall back gracefully: if `osascript` fails, show an error in the TUI rather than crashing
- Lazy-import the iTerm2 helper module -- never import at top level
- Launch iTerm2 first if not running: `subprocess.run(["open", "-a", "iTerm"])` then wait briefly before AppleScript

**Detection:** Test with iTerm2 not running. Test with multiple iTerm2 windows already open.

**Phase:** Phase 3 (agents object type) -- this is a later feature, not critical path.

**Confidence:** MEDIUM -- AppleScript still works, but the iTerm2 team explicitly recommends the Python API. For joy's simple needs, AppleScript is pragmatic.

---

### IR-2: Race Condition in AppleScript Session Targeting

**What goes wrong:** AppleScript sends text or commands to the wrong iTerm2 session/window if the target session was closed or if another session was activated between the "find window" and "write to session" steps.

**Why it happens:** There's a documented iTerm2 bug (GitLab issue #5462): if an initial session gets killed and another session is already open, AppleScript writes text to the wrong session. AppleScript commands are not atomic.

**Consequences:** Commands intended for one project's agent window end up in another window. Data leaks between projects.

**Prevention:**
- Always identify windows by name, not by index or "current window"
- After creating/finding a window, immediately set and verify its name property
- Use a unique naming convention: `joy: <project-name>` to minimize collision risk
- Add a brief delay (200-500ms) between creating a window and sending commands to it
- If the target window can't be found by name, create a new one rather than falling back to "current"

**Detection:** Test rapid open/close of iTerm2 windows while joy is activating agents.

**Phase:** Phase 3 (agents) -- build and test carefully with race conditions in mind.

**Confidence:** MEDIUM -- the specific bug is documented, but joy's use case (create/activate by name) is simpler than the documented failure mode (write to session).

---

### IR-3: iTerm2 Window Naming is Session-Level, Not Window-Level

**What goes wrong:** iTerm2's AppleScript API sets names on sessions, not windows. A window's "title" is derived from its active session's name. If the window has multiple tabs, the name may not display as expected.

**Why it happens:** iTerm2's hierarchy is: Application > Window > Tab > Session. The "name" property exists on sessions. Window titles are computed from the active tab's active session name, plus iTerm2's title bar configuration.

**Consequences:** Finding a window "by name" requires iterating windows, checking their sessions' names. If the user creates additional tabs in a joy-managed window, the naming may break.

**Prevention:**
- Set the session name immediately after creation
- When searching for existing windows, iterate all windows and check their first session's name
- Use a prefix pattern (`joy:projectname`) that's unlikely to collide with user-set session names
- Accept that if a user renames the session manually, joy won't find it -- document this behavior

**Detection:** Create a joy agent window, manually add tabs to it, then try to reactivate from joy.

**Phase:** Phase 3 (agents).

**Confidence:** MEDIUM -- based on iTerm2 API documentation for Window and Session objects.

---

## Packaging and Distribution Risks

Edge cases with `uv tool install git+...` distribution model.

### PD-1: Entry Point Not Found After Install

**What goes wrong:** `uv tool install git+https://github.com/user/joy` succeeds but running `joy` gives "command not found."

**Why it happens:** The `[project.scripts]` section in `pyproject.toml` is misconfigured or the entry point function doesn't exist. Common mistakes:
- Typo in the module path: `joy = "joy.app:main"` where `main` doesn't exist in `joy/app.py`
- Missing `__init__.py` in the package directory
- The `[build-system]` section is missing or misconfigured

**Consequences:** Users install but can't run the tool. First impression is "broken."

**Prevention:**
- Test `uv tool install .` locally before pushing
- Verify the entry point: `[project.scripts]\njoy = "joy.__main__:main"` and ensure that function exists
- Include `[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"` (or setuptools equivalent)
- Test in a clean environment: `uv tool install --force git+file:///path/to/local/repo`

**Detection:** `which joy` returns nothing after install.

**Phase:** Phase 1 -- validate the installation path on day one.

**Confidence:** HIGH -- standard Python packaging issue, well-documented.

---

### PD-2: Upgrade Doesn't Pull Latest Git Commit

**What goes wrong:** Running `uv tool upgrade joy` doesn't fetch new commits from the git repo. The user is stuck on an old version.

**Why it happens:** `uv tool upgrade` respects the originally installed version constraints. For git sources, it may not re-resolve to the latest commit on the branch. The lockfile pins a specific commit hash.

**Consequences:** Users don't get updates. They think they've upgraded but are running old code.

**Prevention:**
- Document the upgrade process: `uv tool install --force git+https://github.com/user/joy` (reinstall, not upgrade)
- Consider using `uv tool install --reinstall` for updates
- Pin a version in pyproject.toml and tag releases -- then `uv tool upgrade` works as expected
- Add a `joy --version` command so users can verify their installed version

**Detection:** `joy --version` shows wrong version after "upgrade."

**Phase:** Phase 1 -- document the install/upgrade process in README.

**Confidence:** HIGH -- confirmed by uv docs and GitHub issues about git dependency locking.

---

### PD-3: Missing Implicit Dependencies

**What goes wrong:** The tool installs fine in the development environment but fails for users because a dependency that's globally available in dev isn't declared in `pyproject.toml`.

**Why it happens:** `uv tool install` creates an isolated virtual environment. Any package not listed in `[project.dependencies]` won't be available. Common culprits:
- `tomlkit` or `tomli-w` (not stdlib)
- `iterm2` Python package (if using the Python API instead of AppleScript)
- Forgetting to declare `textual` itself

**Consequences:** ImportError on first run. Terrible first experience.

**Prevention:**
- Test installation in a completely clean environment (new user account or container)
- Run `uv tool install .` in a fresh directory without a virtualenv active
- List ALL runtime dependencies in `[project.dependencies]`
- Use `uv tool install --python 3.12` to test with a specific Python version

**Detection:** ImportError on first run after clean install.

**Phase:** Phase 1 -- CI should test `uv tool install` in a clean environment.

**Confidence:** HIGH -- standard packaging pitfall.

---

## Obsidian and URL Scheme Risks

### UR-1: Obsidian URI Path Encoding Breaks on Spaces and Special Characters

**What goes wrong:** Opening `obsidian://open?vault=My Vault&file=My Note` fails because the spaces and special characters aren't properly URL-encoded.

**Why it happens:** The Obsidian URI scheme requires proper percent-encoding for spaces, slashes, and special characters in vault names and file paths. The `open` command on macOS passes the URI as-is to the handler, but shell escaping and URL encoding are separate concerns.

**Consequences:** Notes with spaces in filenames (extremely common) fail to open. Users think Obsidian integration is broken.

**Prevention:**
- Always URL-encode the vault name and file path: `urllib.parse.quote(vault_name, safe="")` and `urllib.parse.quote(file_path, safe="/")`
- Build the URI carefully: `f"obsidian://open?vault={quote(vault)}&file={quote(file)}"`
- Test with file paths containing: spaces, parentheses, apostrophes, unicode characters, and nested directories
- Shell-escape the full URI when passing to subprocess: use list form `["open", uri]` not string form

**Detection:** Test with a note file named "My Project (2024) Notes/Daily Log.md".

**Phase:** Phase 2 (object operations) -- test encoding edge cases for every URL scheme.

**Confidence:** HIGH -- documented in Obsidian help docs, confirmed by forum posts about encoding issues.

---

### UR-2: Notion/Slack URL Scheme Changes Break Deep Links

**What goes wrong:** `notion://` or `slack://` URL schemes change format between app versions, breaking previously-stored deep links.

**Why it happens:** URL schemes for desktop apps are not standardized. Notion has changed its URL scheme format in the past. Slack's deep link format differs between the web and desktop app.

**Consequences:** Stored project URLs stop working after an app update.

**Prevention:**
- Store the original HTTPS URL, not the scheme-rewritten URL
- Convert `https://` to `notion://` (or equivalent) at activation time, not at storage time
- This way, if the scheme changes, you only need to update the conversion logic, not all stored data
- For Notion: replace `https://www.notion.so/` with `notion://www.notion.so/` at open time
- For Slack: consider using `open -a Slack <https-url>` instead of scheme rewriting

**Detection:** Stored URLs fail to open in the desktop app after an app update.

**Phase:** Phase 2 (object operations) -- design the storage format to store raw URLs.

**Confidence:** MEDIUM -- based on community reports of scheme changes; not independently verified for current versions.

---

## Per-Phase Warnings Summary

| Phase | Pitfall | Severity | Mitigation |
|-------|---------|----------|------------|
| Phase 1 (Core TUI) | CP-1: Event loop blocking | CRITICAL | Use @work decorator for all I/O |
| Phase 1 (Core TUI) | CP-2: Slow startup imports | CRITICAL | Profile imports, lazy-load non-essential |
| Phase 1 (Core TUI) | CP-3: Task GC heisenbug | CRITICAL | Always use @work, never bare create_task |
| Phase 1 (Core TUI) | CM-1: Widget lifecycle | HIGH | Load data in on_mount, not compose/init |
| Phase 1 (Core TUI) | CM-2: CSS layout traps | HIGH | Use fr units, test with --dev |
| Phase 1 (Core TUI) | CM-3: Key binding conflicts | HIGH | Stick to simple letter keys, test in iTerm2 |
| Phase 1 (Core TUI) | CM-6: Focus traps | HIGH | Escape always unfocuses/dismisses |
| Phase 1 (Core TUI) | PD-1: Entry point config | HIGH | Test uv tool install . on day one |
| Phase 2 (Data/Ops) | CP-4: Non-atomic writes | CRITICAL | Write temp + os.replace pattern |
| Phase 2 (Data/Ops) | CM-4: webbrowser.open | HIGH | Use subprocess open command |
| Phase 2 (Data/Ops) | CM-5: TOML library choice | MEDIUM | tomllib read + tomli-w write |
| Phase 2 (Data/Ops) | UR-1: Obsidian URI encoding | HIGH | URL-encode all path components |
| Phase 2 (Data/Ops) | UR-2: URL scheme fragility | MEDIUM | Store HTTPS, convert at open time |
| Phase 3 (Agents) | IR-1: AppleScript deprecation | MEDIUM | Use AppleScript for simplicity, accept risk |
| Phase 3 (Agents) | IR-2: Session race condition | MEDIUM | Identify by name, add delays |
| Phase 3 (Agents) | IR-3: Window vs session naming | MEDIUM | Use session name with prefix convention |
| Distribution | PD-2: Git upgrade behavior | HIGH | Document reinstall-based updates |
| Distribution | PD-3: Missing dependencies | HIGH | Test clean install in isolation |

---

## Key Findings

1. **Event loop blocking is the #1 Textual pitfall.** Every `subprocess.run()`, file read, or external tool invocation must go through `@work(thread=True)` or `asyncio.create_subprocess_exec()`. This must be the default pattern from line one of code, not retrofitted.

2. **Startup time will be a fight.** Textual + Rich alone cost 130-230ms. The Posting project (a real Textual app) documented a 40% reduction by lazy-importing non-essential modules. Joy should measure startup on every PR and target under 350ms to first paint.

3. **Atomic file writes are non-negotiable for `~/.joy/` data.** A single interrupted write can destroy all project configurations. The temp-file-then-rename pattern costs nothing and prevents catastrophic data loss.

4. **AppleScript is simpler than iTerm2's Python API for joy's needs.** The Python API is more powerful but requires iTerm2 to be running and adds dependency complexity. For "create named window + activate by name," AppleScript via `osascript` is the pragmatic choice despite being in maintenance mode.

5. **Store original URLs, not scheme-rewritten URLs.** Converting `https://` to `notion://` at storage time is a data design mistake. Convert at activation time so the storage format remains resilient to URL scheme changes across app versions.

---

## Sources

- Posting startup optimization: https://darren.codes/posts/python-startup-time/
- Textual async heisenbug: https://textual.textualize.io/blog/2023/02/11/the-heisenbug-lurking-in-your-async-code/
- Textual workers guide: https://textual.textualize.io/guide/workers/
- Textual layout guide: https://textual.textualize.io/guide/layout/
- Textual CSS guide: https://textual.textualize.io/guide/CSS/
- Textual input/bindings: https://textual.textualize.io/guide/input/
- 7 Lessons from Textual: https://www.textualize.io/blog/7-things-ive-learned-building-a-modern-tui-framework/
- iTerm2 Python API: https://iterm2.com/python-api/window.html
- iTerm2 AppleScript docs: https://iterm2.com/documentation-scripting.html
- iTerm2 session race condition bug: https://gitlab.com/gnachman/iterm2/-/work_items/5462
- Obsidian URI scheme: https://help.obsidian.md/Extending+Obsidian/Obsidian+URI
- Python TOML guide: https://realpython.com/python-toml/
- Atomic writes (safer vs atomicwrites): https://docs.bswen.com/blog/2026-04-04-safer-vs-atomicwrites-python/
- PEP 810 lazy imports: https://peps.python.org/pep-0810/
- uv tools guide: https://docs.astral.sh/uv/concepts/tools/
- uv git dependency updates: https://iifx.dev/en/articles/457001353/updating-git-dependencies-with-uv-the-upgrade-solution
