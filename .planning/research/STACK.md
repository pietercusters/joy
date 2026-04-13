# Stack Research: joy v1.1 Workspace Intelligence

**Project:** joy -- keyboard-driven Python TUI for managing coding project artifacts
**Milestone:** v1.1 Workspace Intelligence
**Researched:** 2026-04-13
**Overall confidence:** HIGH

---

## Context

v1.0 shipped with two runtime dependencies: `textual>=8.2` and `tomli-w>=1.0`. v1.1 adds real-time workspace state: iTerm2 session monitoring, git worktree discovery with dirty/remote status, MR/CI status via gh/glab CLIs, and a background refresh engine. This research covers ONLY the stack additions needed for v1.1.

---

## New Dependencies

### 1. iterm2 Python Package

| Property | Value |
|----------|-------|
| Package | `iterm2` |
| Version | 2.15 (released 2026-04-12) |
| License | GPLv2+ (acceptable for personal tool) |
| Transitive deps | `protobuf`, `websockets` |
| PyPI | https://pypi.org/project/iterm2/ |

**What it provides:** Full async Python API to iTerm2 -- list windows/tabs/sessions, read screen content, get session variables (working directory, foreground process, job name), focus/activate sessions.

**Why needed:** v1.0 uses AppleScript via `osascript` for creating/activating named windows. v1.1 needs deeper introspection: listing all sessions, reading `jobName` (to detect Claude), getting `path` (working directory), getting `commandLine` (foreground process). AppleScript cannot do this -- it has no equivalent to `async_get_variable()` or `async_get_contents()`.

**Key session variables available via `session.async_get_variable()`:**

| Variable | Description | Use in joy |
|----------|-------------|------------|
| `path` | Current working directory | Show cwd per terminal session |
| `jobName` | Foreground process name (e.g., "vim", "node") | Show what is running |
| `commandLine` | Full command line of foreground job | Detect Claude (`claude` in command) |
| `jobPid` | PID of foreground process | Health check |
| `name` | Session name as shown in tab bar | Display name |
| `columns` / `rows` | Terminal dimensions | Not needed |
| `hostname` / `username` | SSH detection (requires shell integration) | Not needed for v1.1 |

**Confidence:** HIGH -- verified via official iTerm2 Python API docs (v0.26) and PyPI page.

**Startup impact:** The `iterm2` package and its deps (protobuf, websockets) add import time. MUST lazy-import -- only import when the terminal pane is first rendered. Never at module top-level. Estimated import cost: 100-200ms for protobuf alone.

**Prerequisite:** User must enable "Python API server" in iTerm2 Preferences > General > Magic. Joy should detect connection failure and show a clear message in the terminal pane ("Enable iTerm2 Python API in Preferences > General > Magic").

### 2. No New Dependencies for CLI Integration

`gh` and `glab` are system-installed CLIs called via `subprocess` (or `asyncio.create_subprocess_exec`). No Python packages needed.

### 3. No New Dependencies for Git Operations

Use `subprocess` calls to `git` directly. Do NOT add GitPython. See "What NOT to Add" below.

---

## Updated pyproject.toml Dependencies

```toml
[project]
dependencies = [
    "tomli-w>=1.0",
    "textual>=8.2",
    "iterm2>=2.7",
]
```

Total runtime dependencies: 3 packages (was 2). Transitive deps added: `protobuf`, `websockets`. Acceptable trade-off for the terminal pane feature which is core to v1.1.

---

## Integration Patterns

### Pattern 1: iTerm2 Python API with Textual's Event Loop

**The problem:** `iterm2.run_until_complete()` creates its own asyncio event loop. Textual already runs its own event loop. You cannot have two event loops in the same thread.

**The solution:** Use `iterm2.Connection.async_create()` instead. This static async method creates a connection without creating a new event loop -- it uses the existing running loop. It was designed for REPL use but works perfectly for integration into any app that already has an event loop.

```python
# Inside a Textual async method (e.g., on_mount or a worker)
import iterm2

connection = await iterm2.Connection.async_create()
app = await iterm2.async_get_app(connection)

for window in app.terminal_windows:
    for tab in window.tabs:
        for session in tab.sessions:
            path = await session.async_get_variable("path")
            job = await session.async_get_variable("jobName")
            cmd = await session.async_get_variable("commandLine")
```

**Key insight:** `async_create()` calls `asyncio.ensure_future()` to run the dispatch loop as a background task on the current event loop. This means the iTerm2 websocket connection coexists with Textual's event loop naturally -- no threads, no second loop.

**Connection lifecycle:**
- Create the connection once in `on_mount()` of the terminal pane widget
- Store it as `self._iterm_connection`
- Reuse for all subsequent queries (the connection is persistent)
- Handle `ConnectionError` / `websockets` exceptions gracefully -- iTerm2 might not be running or API not enabled
- On error, show a status message in the terminal pane and skip iTerm2 data

**Confidence:** HIGH -- verified from iTerm2 connection.py source code on GitHub. `async_create()` explicitly does NOT create a new event loop.

### Pattern 2: Background Refresh with set_interval + Workers

**The pattern:** Use `set_interval()` to trigger periodic data fetches, and `@work` decorated async methods to do the actual fetching without blocking the UI.

```python
class WorktreePane(Widget):
    _refresh_timer: Timer | None = None

    def on_mount(self) -> None:
        # Start 30-second background refresh
        self._refresh_timer = self.set_interval(30, self._refresh_data)
        # Also fetch immediately on mount
        self._refresh_data()

    @work(exclusive=True)
    async def _refresh_data(self) -> None:
        """Fetch worktree data without blocking UI."""
        # Run git commands via asyncio subprocess
        proc = await asyncio.create_subprocess_exec(
            "git", "worktree", "list", "--porcelain",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=repo_path,
        )
        stdout, _ = await proc.communicate()
        # Parse and update reactive attribute
        self.worktrees = parse_worktree_output(stdout.decode())

    def action_manual_refresh(self) -> None:
        """Handle 'r' keybinding for manual refresh."""
        self._refresh_data()
```

**Why `set_interval` + `@work(exclusive=True)`:**
- `set_interval(30, callback)` fires the callback every 30 seconds, managed by Textual's timer system
- `@work(exclusive=True)` ensures only one fetch runs at a time -- if a previous fetch is still running, it gets cancelled
- The worker runs as an asyncio task on Textual's event loop, so `await` works naturally
- No thread needed because we use `asyncio.create_subprocess_exec` (non-blocking) instead of `subprocess.run` (blocking)

**Timer control:**
- `self._refresh_timer.pause()` -- pause when app is in background or modal is open
- `self._refresh_timer.resume()` -- resume when returning to main view
- `self._refresh_timer.reset()` -- restart countdown after manual refresh

**Last-updated indicator:**
- Store `self._last_refresh = datetime.now()` after each successful fetch
- Display as "Updated 15s ago" in the pane header, updating via a separate 1-second display timer

**Configurable interval:** Store `refresh_interval` in config.toml (default 30). Read on mount. The timer interval is set once; changing it requires restart (acceptable for a settings value).

**Confidence:** HIGH -- `set_interval`, `@work`, and `Timer.pause()`/`resume()` are all documented in official Textual API docs.

### Pattern 3: Async Subprocess for CLI Calls (gh, glab, git)

**The pattern:** Use `asyncio.create_subprocess_exec()` instead of `subprocess.run()` for all CLI calls in v1.1. This is a departure from v1.0's threaded worker pattern but is cleaner for the background refresh engine where multiple CLI calls happen concurrently.

```python
import asyncio

async def get_gh_pr_status(repo_path: str) -> dict:
    """Get PR status for current branch from GitHub."""
    proc = await asyncio.create_subprocess_exec(
        "gh", "pr", "list",
        "--json", "headRefName,state,statusCheckRollup,title,number,url",
        "--limit", "50",
        "-R", repo_remote,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        return {}
    return json.loads(stdout.decode())
```

**Why async subprocess over threaded subprocess.run:**
- Multiple repos can be queried concurrently with `asyncio.gather()`
- Stays on Textual's event loop -- no thread safety concerns, no `call_from_thread` needed
- `communicate()` prevents deadlocks with pipe buffers
- Natural cancellation via `@work(exclusive=True)` when new refresh starts

**Confidence:** HIGH -- `asyncio.create_subprocess_exec` is Python stdlib, well-documented.

### Pattern 4: Reactive Attributes for Data Flow

**The pattern:** Background workers update reactive attributes, which automatically trigger widget re-renders.

```python
class WorktreePane(Widget):
    worktrees: reactive[list[WorktreeInfo]] = reactive(list, recompose=True)
    last_updated: reactive[datetime | None] = reactive(None)

    def watch_worktrees(self, new_value: list[WorktreeInfo]) -> None:
        """Called automatically when worktrees changes."""
        # Recompose handles the UI update via recompose=True
        pass

    def watch_last_updated(self, new_value: datetime | None) -> None:
        """Update the timestamp display."""
        if new_value:
            self.query_one("#last-updated", Label).update(
                f"Updated {format_relative_time(new_value)}"
            )
```

**Confidence:** HIGH -- reactive attributes with `recompose=True` are core Textual pattern, documented in reactivity guide.

---

## CLI Commands Reference

### GitHub CLI (gh)

**PR status per branch:**
```bash
gh pr list --json headRefName,state,statusCheckRollup,title,number,url --limit 50 -R OWNER/REPO
```

Available JSON fields: `additions`, `assignees`, `author`, `baseRefName`, `headRefName`, `state`, `statusCheckRollup`, `title`, `number`, `url`, `isDraft`, `reviewDecision`, `mergedAt`, `closedAt`, and many more.

`statusCheckRollup` contains an array of check objects. The rollup state can be derived from individual check states.

**CI checks for specific PR:**
```bash
gh pr checks <PR-number> --json bucket,name,state,workflow,link -R OWNER/REPO
```

The `bucket` field normalizes states to: `pass`, `fail`, `pending`, `skipping`, `cancel`.

**Rate limits:** 5,000 requests/hour for authenticated users (gh uses the user's token). At 30-second refresh with ~5 repos, that is ~600 requests/hour. Well within limits.

**Auth requirement:** `gh auth login` must be done once. gh stores the token at `~/.config/gh/hosts.yml`. If not authenticated, gh commands fail with a clear error message -- handle this gracefully.

### GitLab CLI (glab)

**MR status per branch:**
```bash
glab mr list --source-branch BRANCH --output json -R OWNER/REPO
```

Returns JSON array of MR objects with state, title, web_url, etc.

**CI pipeline status:**
```bash
glab ci status --branch BRANCH --output json -R OWNER/REPO
```

Or for listing pipelines:
```bash
glab ci list --ref BRANCH --output json -R OWNER/REPO
```

**Auth requirement:** `glab auth login` must be done once. Similar to gh.

**Note:** glab uses `--output json` (not `--json fields`). The field set is fixed by the command, not selectable like gh.

### Git (direct subprocess)

**Worktree list:**
```bash
git worktree list --porcelain
```

Porcelain format is stable and machine-parseable. Each worktree is a block:
```
worktree /path/to/worktree
HEAD abc123def456
branch refs/heads/feature-branch
```

**Dirty check:**
```bash
git -C /path/to/worktree status --porcelain
```

Empty output = clean. Any output = dirty. The `--porcelain` flag ensures stable, parseable output.

**Remote check (has upstream):**
```bash
git -C /path/to/worktree rev-parse --abbrev-ref @{upstream} 2>/dev/null
```

Exit code 0 = has remote tracking. Non-zero = no remote.

**Remote URL (for GitHub vs GitLab detection):**
```bash
git -C /path/to/repo remote get-url origin
```

Parse the URL to determine if it is GitHub (use `gh`) or GitLab (use `glab`).

**Confidence:** HIGH -- all git porcelain commands are stable interfaces.

---

## What NOT to Add

### GitPython -- DO NOT ADD

| Reason | Detail |
|--------|--------|
| **Worktree support is broken** | GitPython throws `WorkTreeRepositoryUnsupported` when it encounters linked worktrees. Since joy v1.1 is fundamentally about worktrees, this is a dealbreaker. GitHub issue #719 (open since 2017), issue #344, issue #2022. |
| **Unnecessary abstraction** | Joy needs exactly 4 git commands: `worktree list --porcelain`, `status --porcelain`, `rev-parse --abbrev-ref @{upstream}`, `remote get-url origin`. Raw subprocess is simpler, faster, and zero-dependency. |
| **Heavy import** | GitPython imports ~50 modules. Unacceptable for a snappy TUI. |
| **Risk of weird edge cases** | GitPython uses persistent `git-cat-file` processes. Additional processes lingering is undesirable for a lightweight tool. |

**Use instead:** `asyncio.create_subprocess_exec("git", ...)` with porcelain flags. Four simple async helper functions, total ~60 lines of code.

### pyperclip -- DO NOT ADD

Already rejected in v1.0. macOS `pbcopy` via subprocess is simpler and zero-dependency.

### httpx / requests -- DO NOT ADD

Not needed. All API access goes through `gh` and `glab` CLIs, which handle authentication, pagination, and rate limiting. Adding an HTTP library would mean reimplementing auth (tokens, OAuth) for zero benefit.

### trio / anyio -- DO NOT ADD

No need for multiple event loops or structured concurrency abstractions. Textual's worker system + asyncio stdlib are sufficient. Adding trio would conflict with Textual's asyncio-based architecture.

---

## Startup Time Impact Assessment

v1.0 has two runtime deps. v1.1 adds `iterm2` which pulls in `protobuf` and `websockets`.

| Package | Estimated import time | Mitigation |
|---------|----------------------|------------|
| protobuf | 100-200ms | Lazy import -- only when terminal pane renders |
| websockets | 20-40ms | Lazy import -- only when terminal pane renders |
| iterm2 | 10-20ms (thin wrapper) | Lazy import -- only when terminal pane renders |

**Strategy:** Import `iterm2` inside the terminal pane's `on_mount()` method, not at module top-level. The terminal pane is in the bottom-left of the 2x2 grid -- it renders after the top row. By the time the user sees the terminal pane, the import will have happened during initial render.

Worktree and CLI data fetching use `asyncio.create_subprocess_exec` (stdlib) and `json.loads` (stdlib) -- zero additional import cost.

**Confidence:** MEDIUM -- import times are estimates based on similar protobuf-using packages. Must be measured empirically.

---

## Confidence Levels

| Decision | Confidence | Reasoning |
|----------|------------|-----------|
| iterm2 package for terminal introspection | HIGH | Only way to get session variables (path, jobName, commandLine). AppleScript cannot do this. Verified via official iTerm2 Python API docs. |
| Connection.async_create() for event loop integration | HIGH | Verified from iTerm2 source code. Explicitly designed for existing event loops. Does not create a new loop. |
| asyncio.create_subprocess_exec for CLI calls | HIGH | Python stdlib. Well-documented. Non-blocking. Natural fit for Textual's asyncio-based architecture. |
| set_interval + @work for background refresh | HIGH | Both are documented Textual APIs. set_interval returns Timer with pause/resume. @work(exclusive=True) handles cancellation. |
| Subprocess git over GitPython | HIGH | GitPython's worktree support is broken (multiple open issues since 2017). subprocess + porcelain flags is simpler and more reliable. |
| gh/glab CLI over direct API calls | HIGH | CLIs handle auth, pagination, rate limiting. Joy only needs to parse JSON output. Zero additional Python dependencies. |
| Lazy import for iterm2 | HIGH | Established pattern from v1.0 (lazy imports for store/operations). protobuf import cost would be unacceptable at startup. |

---

## Sources

### Primary (HIGH confidence)
- iTerm2 Python API v0.26 docs: https://iterm2.com/python-api/
- iTerm2 Session API: https://iterm2.com/python-api/session.html
- iTerm2 App API: https://iterm2.com/python-api/app.html
- iTerm2 Connection API: https://iterm2.com/python-api/connection.html
- iTerm2 Variables Reference: https://iterm2.com/documentation-variables.html
- iTerm2 connection.py source: https://github.com/gnachman/iTerm2/blob/master/api/library/python/iterm2/iterm2/connection.py
- iTerm2 PyPI: https://pypi.org/project/iterm2/
- iTerm2 Python API Security: https://iterm2.com/python-api-auth.html
- Textual Workers guide: https://textual.textualize.io/guide/workers/
- Textual Timer API: https://textual.textualize.io/api/timer/
- Textual Reactivity guide: https://textual.textualize.io/guide/reactivity/
- gh pr list docs: https://cli.github.com/manual/gh_pr_list
- gh pr checks docs: https://cli.github.com/manual/gh_pr_checks
- glab mr list docs: https://docs.gitlab.com/cli/mr/list/
- glab ci status docs: https://docs.gitlab.com/cli/ci/status/
- glab ci list docs: https://docs.gitlab.com/cli/ci/list/
- GitHub rate limits: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- Python asyncio subprocess: https://docs.python.org/3/library/asyncio-subprocess.html

### Secondary (MEDIUM confidence)
- GitPython worktree issue #719: https://github.com/gitpython-developers/GitPython/issues/719
- GitPython worktree issue #344: https://github.com/gitpython-developers/GitPython/issues/344
- GitPython worktree issue #2022: https://github.com/gitpython-developers/gitpython/issues/2022
- gh CLI rate limiting discussion: https://github.com/cli/cli/discussions/5381
