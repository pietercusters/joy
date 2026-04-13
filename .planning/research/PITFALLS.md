# Pitfalls Research: joy v1.1 Workspace Intelligence

**Domain:** Adding background data fetching, iTerm2 Python API, and new panes to an existing Python TUI
**Researched:** 2026-04-13
**Focus:** Integration pitfalls for v1.1 features added to the existing v1.0 Textual app
**Overall confidence:** HIGH (most findings verified from primary sources)

NOTE: v1.0 pitfalls (CP-1 through CP-4, CM-1 through CM-6, IR-1 through IR-3, PD-1 through PD-3, UR-1, UR-2) are already addressed in the shipped codebase. This file documents NEW pitfalls specific to v1.1 features.

---

## iTerm2 Python API Pitfalls

### IT-1: Event Loop Conflict -- iterm2.run_until_complete() vs Textual's asyncio Loop (CRITICAL)

**What goes wrong:** Calling `iterm2.run_until_complete(main)` from inside a running Textual app raises `RuntimeError: This event loop is already running`. The iTerm2 library internally calls `asyncio.new_event_loop()` and `loop.run_until_complete()`, which conflicts with the already-running Textual event loop on the same thread.

**Why it happens:** Textual runs its own asyncio event loop. The iTerm2 Python API's `run_until_complete()` creates a NEW event loop and tries to run it. Python forbids running two event loops in the same thread. This is the single most dangerous integration pitfall for v1.1.

**Consequences:** App crash on first iTerm2 API call. Complete failure of terminal pane.

**Warning signs:** `RuntimeError: This event loop is already running` in logs. iTerm2 features silently do nothing.

**Prevention:**
- NEVER use `iterm2.run_until_complete()` inside the Textual app
- Use `iterm2.Connection.async_create()` instead -- this was designed for environments where an event loop already exists (REPL, embedded contexts). It returns a connection without creating a new event loop, using `asyncio.ensure_future()` to schedule its dispatch on the existing loop.
- Run all iTerm2 API calls as `await`-able coroutines within Textual's existing event loop
- Pattern:
  ```python
  async def _connect_iterm2(self) -> iterm2.Connection:
      return await iterm2.Connection.async_create()
  ```
- If `async_create()` proves insufficient, the fallback is to run iTerm2 API calls in a separate thread with its own event loop using `@work(thread=True)` and `asyncio.run()` inside that thread

**Detection:** Test iTerm2 connection during app startup. If `RuntimeError` occurs, the integration pattern is wrong.

**Phase:** Must be resolved in the very first phase that introduces iTerm2 Python API. Proof-of-concept before building features.

**Confidence:** HIGH -- verified by reading the iTerm2 connection.py source code: `run_until_complete` calls `loop = asyncio.new_event_loop()` then `loop.run_until_complete()`.

---

### IT-2: iTerm2 Not Running or Python API Disabled

**What goes wrong:** The iTerm2 Python API requires: (1) iTerm2 running, (2) "Enable Python API server" enabled in Preferences > General > Magic. If either is false, the connection fails. With `retry=True`, the connection retries forever, blocking the worker. With `retry=False`, it raises immediately but every 30-second refresh hits the same error.

**Why it happens:** The iTerm2 Python API communicates via a local websocket server that iTerm2 hosts. If iTerm2 is not running, there is no server. If the API is disabled, the server rejects connections (permission denied / 401).

**Consequences:** Terminal pane permanently blank. If retry=True, the worker is blocked forever -- consuming resources and never returning.

**Warning signs:** Terminal pane shows "Connecting..." forever. CPU creeps up from retry loops.

**Prevention:**
- Default to `retry=False`. Catch the connection error and set a "disconnected" state
- Show clear status: "iTerm2 not running" or "Enable Python API in iTerm2 Preferences > General > Magic"
- Implement exponential backoff for reconnection: 5s, 10s, 30s, then stop until manual refresh (`r`)
- Cache the connection object and reuse it. Only reconnect when the cached connection is dead
- On first failure, check if iTerm2 is running via `subprocess.run(["pgrep", "-x", "iTerm2"])` -- if not, skip API calls entirely
- Provide a green/red dot indicator in the terminal pane for connection status

**Detection:** Launch joy with iTerm2 not running. Launch with Python API disabled. Both must degrade gracefully.

**Phase:** Same phase as IT-1 -- connection lifecycle designed as a unit.

**Confidence:** HIGH -- verified from iTerm2 troubleshooting docs: connection errors produce specific codes (2 = connection error, not running or API not enabled).

---

### IT-3: GPLv2+ License of the iterm2 Package

**What goes wrong:** The `iterm2` package is GPLv2+ licensed (verified on PyPI, version 2.15 released 2026-04-12). If joy is MIT-licensed, adding `iterm2` as a hard dependency creates a license conflict.

**Why it happens:** GPLv2+ is copyleft. A project that depends on GPLv2+ code must comply with GPL terms for distribution. MIT is compatible as input, but the distributed combination must honor GPL.

**Consequences:** License compliance issue for a public repo.

**Prevention:**
- Make `iterm2` an optional dependency: `[project.optional-dependencies] terminal = ["iterm2>=2.7"]`
- At runtime: `try: import iterm2` with fallback to AppleScript via `osascript`
- This also eliminates import time cost when the Python API is not needed
- The AppleScript fallback (already used in v1.0 for agents) provides basic session listing without the iterm2 package

**Detection:** Review `pyproject.toml` dependency list.

**Phase:** Architecture decision before any iTerm2 code is written.

**Confidence:** HIGH -- GPLv2+ verified on PyPI page.

---

### IT-4: Async Exception Swallowing in iTerm2 API Calls

**What goes wrong:** Exceptions in async tasks connected to the iTerm2 API are silently swallowed. Screen content reads fail, session lookups return None, RPCException is raised -- but no error surfaces. The terminal pane shows stale data.

**Why it happens:** Python asyncio discards exceptions in unawaited tasks. The iTerm2 troubleshooting docs explicitly warn: "Always catch exceptions in async tasks. They are silently swallowed." Combined with Textual workers using `exit_on_error=False`, errors vanish.

**Consequences:** Terminal pane shows stale data with no error indication. Debugging is blind.

**Prevention:**
- Wrap every iTerm2 API call in try/except and log or display the error
- Use a structured error state: `_last_error: str | None` on the terminal pane widget
- When `_last_error` is set, render it in the pane instead of stale data
- Log exceptions to `~/.joy/debug.log` when `--debug` flag is passed
- Pattern:
  ```python
  try:
      contents = await session.async_get_screen_contents()
  except iterm2.RPCException as e:
      self._last_error = f"iTerm2 error: {e}"
      return
  ```

**Detection:** Force an error (close target session while joy reads it) and verify the pane shows an error.

**Phase:** Every phase that adds iTerm2 API calls must include error handling.

**Confidence:** HIGH -- documented in iTerm2 Python API troubleshooting guide.

---

### IT-5: Session Enumeration Returns Stale Data

**What goes wrong:** The iTerm2 `App` object is a snapshot. Sessions created after the snapshot are invisible. Closed sessions may still appear.

**Why it happens:** `await iterm2.async_get_app(connection)` captures current state. It does not update automatically.

**Consequences:** Terminal pane lists closed sessions. New sessions don't appear until next full refresh.

**Prevention:**
- Re-fetch the app object before each enumeration: `app = await iterm2.async_get_app(connection)`
- Use `NewSessionMonitor` and `SessionTerminationMonitor` for real-time tracking instead of polling
- Catch `InvalidSessionId` when accessing a session that was closed between enumeration and use

**Detection:** Open/close iTerm2 tabs rapidly while terminal pane is updating.

**Phase:** Terminal pane implementation.

**Confidence:** MEDIUM -- inferred from API design (snapshot model) and lifecycle docs.

---

### IT-6: Startup Time Regression from iterm2 + protobuf Import

**What goes wrong:** Adding `iterm2` pulls in `protobuf` and `websockets`. Eager import at module level adds 100-250ms, pushing past the 350ms startup target.

**Why it happens:** `protobuf` compiles proto message classes on import. v1.0 has ~250ms startup. Adding 200ms pushes to 450ms.

**Consequences:** Joy feels sluggish on launch.

**Prevention:**
- NEVER import `iterm2` at module top-level
- Import inside terminal pane's `on_mount()` or refresh worker
- The terminal pane renders after the top row -- user sees projects first, so 200ms delay in terminal is invisible
- Measure: `python -X importtime -c "import iterm2" 2>&1 | head -20`

**Detection:** `time joy` shows >400ms to first paint.

**Phase:** First phase of v1.1.

**Confidence:** HIGH -- protobuf import cost is well-documented. v1.0 already uses lazy imports.

---

### IT-7: Shell Integration Required for Some Variables

**What goes wrong:** `session.async_get_variable("path")` returns None/empty without iTerm2 shell integration installed. Also affects `hostname`, `username`, `lastCommand`.

**Why it happens:** These variables rely on shell integration scripts being sourced in the user's shell profile. Without them, iTerm2 cannot track working directory.

**Prevention:**
- Handle None/empty for all session variables -- show "Unknown" for missing data
- `jobName` and `commandLine` work WITHOUT shell integration (from process table), so Claude detection is unaffected
- Show a one-time hint: "Install iTerm2 shell integration for directory tracking"

**Detection:** Test with a fresh iTerm2 profile that has no shell integration.

**Phase:** Terminal pane implementation.

**Confidence:** MEDIUM -- documented in iTerm2 variables reference, but exact fallback behavior needs testing.

---

## Background Polling Pitfalls

### BP-1: Subprocess Calls Blocking the Event Loop (CRITICAL)

**What goes wrong:** Running `subprocess.run(["gh", "pr", "list"])` on the main thread blocks Textual. With 10 repos at 30s intervals, the UI freezes for seconds every cycle.

**Why it happens:** `subprocess.run()` is synchronous. 10 repos x 500ms each = 5 seconds of blocking.

**Consequences:** UI freezes periodically. Keys queue up and fire in bursts.

**Prevention:**
- Use `@work(thread=True)` for all subprocess calls (v1.0 established this pattern)
- Run repos concurrently with `asyncio.create_subprocess_exec()` + `asyncio.gather()`
- Cap concurrency with `asyncio.Semaphore(4)` to avoid fork-bombing
- Always set `timeout=10` on subprocess calls
- Pattern:
  ```python
  async def refresh_all_repos(repos):
      sem = asyncio.Semaphore(4)
      async def refresh_one(repo):
          async with sem:
              proc = await asyncio.create_subprocess_exec(
                  "git", "worktree", "list", "--porcelain",
                  cwd=repo.path, stdout=PIPE, stderr=PIPE
              )
              stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
              return parse_worktrees(stdout.decode())
      return await asyncio.gather(*(refresh_one(r) for r in repos), return_exceptions=True)
  ```

**Detection:** Time refresh cycles. Log if any takes >2 seconds.

**Phase:** Background refresh engine -- first thing to get right.

**Confidence:** HIGH -- standard async subprocess pattern.

---

### BP-2: GitHub API Rate Limiting via gh CLI

**What goes wrong:** `gh` CLI uses GraphQL API. Authenticated users get 5,000 points/hour. At 30s intervals for 10 repos, that is 1,200 calls/hour. Each call costs 1-2 points. Approaching the limit, gh returns 403 errors.

**Consequences:** All GitHub data stops updating. Error messages flood the TUI.

**Warning signs:** "API rate limit exceeded" errors from gh. Data stops updating.

**Prevention:**
- Poll active project's repo at 30s, background repos at 5-minute intervals
- Check rate limit: `gh api rate_limit --jq '.resources.graphql.remaining'` -- if below 500, extend interval to 5 minutes
- Batch queries with `gh api graphql` instead of multiple `gh pr list` calls
- Show rate limit status in footer
- Design tiered refresh: active=30s, others=5m, low-rate=stop

**Detection:** Monitor remaining rate limit after each cycle.

**Phase:** Background refresh engine design.

**Confidence:** HIGH -- GitHub rate limits verified from official docs. gh CLI discussion #5381 confirms GraphQL usage.

---

### BP-3: gh/glab CLI Not Installed or Not Authenticated

**What goes wrong:** `gh` not installed gives `FileNotFoundError`. Installed but not authenticated gives auth errors on stderr. `glab` has similar failure modes plus known issues with token expiry (keyring tokens broken since glab 1.84.0).

**Consequences:** Every refresh produces errors. Error toast spam.

**Warning signs:** `FileNotFoundError`. Non-zero exit with "not logged in" on stderr.

**Prevention:**
- On startup, probe CLI availability: `shutil.which("gh")` and `shutil.which("glab")`. Cache result.
- If CLI not found, disable that provider and show "gh not installed" inline
- Detect auth errors: gh writes "not logged into any GitHub hosts" to stderr. Use `capture_output=True` or `stderr=subprocess.PIPE`
- IMPORTANT: gh writes some errors to stderr that `subprocess.run()` does NOT capture by default
- Check auth once on startup: `gh auth status` (exit 0 = authenticated, 1 = not)
- Check common PATH locations for macOS: `/usr/local/bin/gh`, `/opt/homebrew/bin/gh`
- Make MR/CI status purely additive: worktree pane works fine without it

**Detection:** Test with gh not installed. Test with gh installed but not authenticated.

**Phase:** First phase introducing gh/glab calls.

**Confidence:** HIGH -- verified from gh CLI issue discussions and glab GitLab issues.

---

### BP-4: Subprocess Timeout and Zombie Processes

**What goes wrong:** `subprocess.run()` with no timeout hangs when git commands encounter SSH key prompts, DNS failures, or network timeouts. With `shell=True`, only the shell is killed on timeout -- the actual command becomes an orphan.

**Why it happens:** `subprocess.run(timeout=N)` kills the child process, but with `shell=True` it kills the shell, not the grandchild. Git over SSH prompts for passphrase interactively, hanging forever.

**Consequences:** Zombie processes accumulate. One hung subprocess per refresh = 120 zombies/hour.

**Prevention:**
- NEVER use `shell=True`. Always pass command as a list: `["gh", "pr", "list"]`
- Always set `timeout=10` on every subprocess call
- Use `start_new_session=True` so the subprocess gets its own process group. On timeout, the entire group is killed
- Set `GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=5"` in subprocess environment to prevent SSH prompts
- Pattern:
  ```python
  result = subprocess.run(
      ["git", "worktree", "list", "--porcelain"],
      cwd=repo_path, capture_output=True, text=True, timeout=10,
      env={**os.environ, "GIT_SSH_COMMAND": "ssh -o BatchMode=yes -o ConnectTimeout=5"}
  )
  ```

**Detection:** Monitor process count. Test with a repo whose remote is unreachable.

**Phase:** Background refresh engine -- from the first subprocess call.

**Confidence:** HIGH -- verified via Python subprocess docs and CPython issues (30154, 37424).

---

### BP-5: Refresh Timer Stacking

**What goes wrong:** `set_interval(30)` fires regardless of how long the previous refresh took. If a refresh takes 35 seconds, two cycles overlap, doubling subprocess load and causing race conditions with out-of-order completion.

**Why it happens:** `set_interval` fires on a fixed schedule, not relative to completion.

**Consequences:** Concurrent refreshes compete. Older data overwrites newer data.

**Prevention:**
- Use `@work(thread=True, exclusive=True)` -- cancels previous worker when new one starts
- Better: use `set_timer(30)` (single-fire) at the END of each refresh cycle instead of `set_interval(30)`. Next refresh starts 30s after completion, not 30s after start.
- Track `_refresh_in_progress` flag. Skip if already running.
- Use a generation counter (like existing `_render_generation` in ProjectDetail) to discard stale results
- Pattern:
  ```python
  def _schedule_next_refresh(self):
      self.set_timer(30, self._do_refresh)

  @work(thread=True, exclusive=True)
  def _do_refresh(self):
      # ... work ...
      self.call_from_thread(self._schedule_next_refresh)
  ```

**Detection:** Timestamps in refresh logs. Check for overlapping cycles.

**Phase:** Background refresh engine design.

**Confidence:** HIGH -- standard timer pattern. Textual timer docs confirm set_interval vs set_timer behavior.

---

### BP-6: UI Flicker and Cursor Jump on Background Refresh

**What goes wrong:** Every 30 seconds the panes refresh. If refresh replaces the entire widget tree (recompose), cursor position resets, scroll is lost, visible flicker occurs.

**Why it happens:** Using `reactive(..., recompose=True)` destroys and recreates all children, losing all widget state.

**Consequences:** User is viewing worktree #5, refresh happens, they are back at #1.

**Prevention:**
- Do NOT use `recompose=True` for periodically-refreshed data
- Use update-in-place: compare old and new data, update existing widgets, add/remove only what changed
- Preserve highlighted index: save before refresh, restore after, matching by identity (branch name, session ID) not position
- Pattern: `self._highlighted_branch = current_branch_name` before refresh, find in new data after
- v1.0's `_render_generation` pattern is a good foundation -- extend it with cursor preservation

**Detection:** Select worktree #3, wait for refresh, verify cursor stays on worktree #3.

**Phase:** Background refresh engine -- build cursor preservation from day one.

**Confidence:** HIGH -- well-known reactive UI issue. k9s and lazygit both solve it by preserving cursor by identity.

---

### BP-7: Stale Data After Repo Path Changes

**What goes wrong:** A repo is moved or deleted. Background refresh tries the old path, gets errors, but the pane shows last successful data.

**Prevention:**
- On subprocess error for a repo, clear its pane data and show "Repo not found: /path"
- Validate paths on startup: `os.path.isdir(repo.path)` and check for `.git`
- Mark unreachable repos with a visual indicator
- Always show "last updated" timestamps

**Detection:** Delete a repo directory while joy is running.

**Phase:** Repo registry implementation.

**Confidence:** MEDIUM -- standard pattern.

---

## Textual Layout Pitfalls

### TL-1: 4-Pane Layout Breaking Existing 2-Pane (CRITICAL)

**What goes wrong:** Adding two panes to the existing `Horizontal(ProjectList, ProjectDetail)` breaks CSS sizing. `width: 1fr / 2fr` rules produce unexpected results. Panes collapse to zero height.

**Why it happens:** The current layout is a flat Horizontal with two children. A 2x2 grid requires restructuring to nested containers (`Vertical > two Horizontals`). This changes the DOM structure, breaking CSS selectors and widget queries.

**Consequences:** Complete layout breakage. All existing CSS invalid.

**Prevention:**
- Do this as a single atomic change. Do not add panes incrementally.
- Recommended structure:
  ```python
  def compose(self):
      yield Header()
      with Vertical(id="main-content"):
          with Horizontal(id="top-row"):
              yield ProjectList(id="project-list")
              yield ProjectDetail(id="project-detail")
          with Horizontal(id="bottom-row"):
              yield TerminalPane(id="terminal-pane")
              yield WorktreePane(id="worktree-pane")
      yield Footer()
  ```
- Use explicit heights: `#top-row { height: 1fr; } #bottom-row { height: 1fr; }` for 50/50
- Preserve existing width ratios within each row
- CRITICAL: Update ALL `query_one()` calls in app.py -- DOM path may change
- Test with `textual run --dev` to inspect computed sizes

**Detection:** Visual inspection. All four panes visible with correct proportions.

**Phase:** THE FIRST THING to implement in v1.1. Everything depends on layout.

**Confidence:** HIGH -- standard CSS layout restructuring.

---

### TL-2: Focus Management with Non-Interactive Panes

**What goes wrong:** Worktree and terminal panes are primarily display-only. If `can_focus=True`, Tab navigation includes them (4 panes to tab through). If `can_focus=False`, their keybindings (Enter, r) don't work.

**Consequences:** Either: Tab cycling is tedious (4 panes), or new panes can't respond to keys.

**Prevention:**
- Make new panes `can_focus=True` with specific BINDINGS (Enter, r)
- Use dedicated keys to jump to panes: `1`=project list, `2`=detail, `3`=terminal, `4`=worktree
- OR: Keep Tab cycling top row only, use dedicated keys for bottom panes
- Escape from bottom panes returns to top row
- `r` (refresh) should be a priority binding on App level, working regardless of focus

**Detection:** Tab through all panes. Count keystrokes to reach each. Escape from each.

**Phase:** Layout phase -- design focus model before content.

**Confidence:** HIGH -- based on existing joy patterns and Textual focus docs.

---

### TL-3: Widget Count Performance Degradation

**What goes wrong:** Two new panes with many child widgets (40+ worktree rows) plus existing detail pane rows. Textual recalculates layout for all visible widgets on every update.

**Consequences:** Perceptible lag when switching projects. Flicker during updates.

**Prevention:**
- Use batched DOM updates: remove all children then mount all new ones
- Use `widget.update(content)` to update existing widgets instead of remounting
- Consider a single `Static` widget rendering all worktree data as Rich text
- Profile with `textual run --dev`

**Detection:** Measure render time with varying widget counts.

**Phase:** After basic pane content works -- optimize if needed.

**Confidence:** MEDIUM -- depends on actual widget counts.

---

### TL-4: Key Binding Conflicts in 4-Pane Layout

**What goes wrong:** `j`/`k` defined on existing panes (JoyListView, ProjectDetail) may conflict with navigation in new panes. App-level bindings (q, n, s, O) may shadow pane bindings.

**Why it happens:** Textual walks from focused widget up to app. Pane bindings take priority unless app uses `priority=True`. With four panes, conflicts multiply.

**Prevention:**
- Document binding ownership:
  - App level (priority=True): `q`, `n`, `s`, `r`, `O`
  - Each pane: `j`/`k` for navigation, pane-specific actions
- `j`/`k` defined per pane, only active when that pane has focus
- App-level must-always-work bindings use `priority=True`
- Create a test matrix: (key x focused_pane) -- verify each cell

**Detection:** Test every binding in every focus state.

**Phase:** Layout and focus model phase.

**Confidence:** HIGH -- verified against Textual input documentation and existing joy code.

---

## Claude Detection Pitfalls

### CD-1: Process-Name Detection Unreliable

**What goes wrong:** Detecting "Claude is busy" via iTerm2's `jobName` variable fails because Claude Code runs as `node` (or full path like `/Users/pieter/.nvm/versions/node/v22.17.1/bin/node`). When Claude spawns subprocesses (git, npm), the foreground job changes temporarily.

**Consequences:** False negatives (Claude running but shows "idle" because jobName is "node"). False positives (other Node.js process). Flicker (Claude alternates with its subprocess tools).

**Prevention:**
- Use `commandLine` not `jobName`: `"claude" in (await session.async_get_variable("commandLine") or "").lower()`
- Handle flicker: maintain a 5-second sticky state. If Claude was foreground within last 5 seconds, still show "busy"
- Combine signals: commandLine contains "claude" AND (optionally) screen content matches Claude's UI
- Accept detection will never be 100%. Show "likely busy" / "likely idle" not definitive states

**Detection:** Run Claude Code, trigger tool use, verify detection doesn't flicker.

**Phase:** Terminal pane implementation.

**Confidence:** MEDIUM -- inferred from iTerm2 variable docs and Claude Code's Node.js architecture. The exact commandLine format needs empirical verification.

---

### CD-2: Screen Content Reading is Expensive and Racy

**What goes wrong:** `session.async_get_screen_contents()` for every terminal session every 30 seconds is expensive. Each call is a websocket round-trip. With 5+ sessions, adds significant latency.

**Prevention:**
- Only read screen contents for the selected/visible session
- For non-selected sessions, use lightweight variables only: `jobName`, `commandLine`, `path`
- Use `ScreenStreamer` (push-based) instead of polling for screen changes
- Rate limit screen reads to once per 5 seconds per session
- Cache content, only re-render if changed (compare hashes)

**Detection:** Time terminal pane refresh with varying session counts.

**Phase:** Terminal pane -- after basic connection works.

**Confidence:** MEDIUM -- based on API design. Needs benchmarking.

---

### CD-3: False Positives from Screen Content Matching

**What goes wrong:** Searching terminal content for "claude" produces false matches. `git log` showing a commit by "Claude" triggers false busy detection. Any script printing "claude" looks like Claude running.

**Prevention:**
- Prefer process-based detection (commandLine) over screen content
- If using screen content, match Claude Code's specific TUI patterns (status bar, spinner characters, specific layout at terminal bottom)
- Combine signals: commandLine AND screen pattern must both agree for "busy"
- Allow manual session marking in settings as a reliable override
- Never match on just the word "claude" in screen content

**Detection:** Run `echo "claude is great"` in a terminal and verify no false trigger.

**Phase:** Terminal pane -- after basic detection works.

**Confidence:** MEDIUM -- screen content matching is inherently heuristic.

---

## Worktree Discovery Pitfalls

### WD-1: Bare Repositories in Porcelain Output

**What goes wrong:** `git worktree list --porcelain` includes the bare repo as the first entry when the repo was cloned with `--bare`. Output has `bare` flag but no `HEAD` or `branch` line. Parsing code expecting `branch` crashes.

**Porcelain output for bare repo:**
```
worktree /path/to/bare-repo
bare

```

**Prevention:**
- Check for `bare` flag when parsing. Skip bare entries entirely.
- Parse each block as a dict of attributes. Only create worktree rows when `bare` is NOT present.

**Detection:** Test with a bare-cloned repository.

**Phase:** Worktree discovery implementation.

**Confidence:** HIGH -- verified from official `git worktree list --porcelain` documentation.

---

### WD-2: Detached HEAD Worktrees Have No Branch

**What goes wrong:** Detached HEAD worktrees show `detached` instead of `branch`. Code extracting branch name gets None.

**Porcelain output for detached:**
```
worktree /path/to/worktree
HEAD abc123def456
detached

```

**Prevention:**
- If `branch` absent, check for `detached`. Display as "detached @ abc1234" (first 7 of HEAD)
- Pattern: `branch = attrs.get("branch", "").removeprefix("refs/heads/") or f"detached @ {attrs.get('HEAD', '?')[:7]}"`

**Detection:** Create detached worktree: `git worktree add --detach /tmp/test HEAD~2`.

**Phase:** Worktree discovery.

**Confidence:** HIGH -- verified from official git docs.

---

### WD-3: Locked and Prunable Worktrees

**What goes wrong:** `locked` appears as `locked` (no reason) or `locked some reason text` (with reason). `prunable` similarly. Variable-format breaks naive parsing.

**Prevention:**
- Parse `locked` and `prunable` as optional attributes with optional values
- Show lock icon for locked worktrees, warning icon for prunable
- Use `--porcelain -z` (NUL-terminated) for robust parsing of reasons with unusual characters
- Skip or dim prunable worktrees (gitdir points to non-existent location)

**Detection:** Lock a worktree: `git worktree lock /path --reason "testing"`.

**Phase:** Worktree discovery.

**Confidence:** HIGH -- verified from official git docs.

---

### WD-4: Repo vs Worktree vs Submodule Confusion

**What goes wrong:** Running `git worktree list` from a worktree checkout (not main repo) still lists all worktrees -- but if both the main repo AND a worktree checkout are in the registry, worktrees appear twice. Submodule directories produce unexpected results.

**Why it happens:** Git worktrees have a `.git` file (not directory) pointing to the main repo. `git worktree list` always operates relative to the main repository. Submodules similarly redirect.

**Prevention:**
- Resolve the real repo root: `git rev-parse --git-common-dir` to find shared git dir, then deduplicate
- When adding repos to registry, normalize to main worktree: parse first entry of `git worktree list --porcelain`
- Skip submodule directories: `.git` is a file containing `gitdir: ...modules/...` path
- Deduplicate: if two registry entries share the same git-common-dir, merge them

**Detection:** Add both a main repo and one of its worktrees to the registry. Verify no duplication.

**Phase:** Repo registry implementation.

**Confidence:** MEDIUM -- depends on user's repo setup.

---

### WD-5: Worktree List Hangs on Unreachable Paths

**What goes wrong:** If a repo path points to a network filesystem that is unreachable or an unmounted external drive, `git worktree list` hangs waiting for the filesystem.

**Prevention:**
- Always use `timeout=10` on subprocess calls (covered in BP-4)
- Pre-check with `os.path.exists(repo.path)` -- fast, fails on unreachable mounts
- Run repo refreshes concurrently so one hung repo doesn't block others
- Show per-repo refresh status: "refreshing...", "timed out", "complete"

**Detection:** Add a repo path pointing to non-existent or unmounted path.

**Phase:** Background refresh engine.

**Confidence:** HIGH -- standard filesystem timeout issue.

---

### WD-6: Dirty Detection Overhead

**What goes wrong:** Detecting dirty status requires `git status` for each worktree. With 20 worktrees, that is 20 subprocess calls, each 200-500ms for large repos.

**Prevention:**
- Run dirty checks concurrently with semaphore pattern from BP-1
- Use `git diff --quiet HEAD` -- exits 0 if clean, 1 if dirty, no output parsing. Fastest option.
- Show dirty status only for active project's worktrees. Others on 5-minute interval.
- Alternative: `git status --porcelain --untracked-files=no` for minimal output

**Detection:** Measure refresh time with 20 worktrees.

**Phase:** Worktree pane implementation.

**Confidence:** MEDIUM -- performance depends on repo size.

---

## Mixed Platform (GitHub/GitLab) Pitfalls

### MP-1: Remote URL Detection Fails for Non-Standard Hosts

**What goes wrong:** Detecting GitHub vs GitLab by checking for "github.com" or "gitlab.com" in the remote URL fails for: self-hosted GitLab, GitHub Enterprise, SSH config aliases.

**Prevention:**
- Use CLIs for detection: `gh repo view --json name 2>/dev/null` succeeds for GitHub-compatible remotes. `glab repo view 2>/dev/null` for GitLab.
- Allow manual override per repo in settings
- Fall back to URL pattern matching as a heuristic, not primary method
- For SSH aliases, use `git remote get-url origin` (returns configured URL)

**Detection:** Test with SSH alias repo. Test with self-hosted GitLab.

**Phase:** Mixed platform support.

**Confidence:** MEDIUM -- detection heuristics have edge cases.

---

### MP-2: Different CLI Output Formats

**What goes wrong:** `gh pr list --json` and `glab mr list --json` return different JSON schemas. Field names differ: `headRefName` vs `source_branch`, `url` vs `web_url`, `state` values differ in case.

**Prevention:**
- Create a unified internal model (dataclass) for MR/PR data
- Write separate parser functions per CLI, each mapping to the unified model
- Key mappings:
  - gh `headRefName` = glab `source_branch`
  - gh `url` = glab `web_url`
  - gh `state` (OPEN/CLOSED/MERGED) = glab `state` (opened/closed/merged) -- case differs
  - gh `author.login` = glab `author.username`
- Test both parsers with real CLI output

**Detection:** Run both CLIs on real repos and compare output.

**Phase:** Mixed platform support.

**Confidence:** HIGH -- different schemas are verifiable.

---

### MP-3: Auth Credentials Independent Between Platforms

**What goes wrong:** User authenticated with `gh` but not `glab` (or vice versa). `glab` commands fail with "401 Unauthorized" or "token was revoked" -- looks like a network error, not an auth error.

**Prevention:**
- Check auth per platform on startup: `gh auth status` and `glab auth status`
- Store auth status per platform. If not authenticated, show "Run `glab auth login`" inline
- Do not attempt API calls for unauthenticated platforms
- Handle token expiry: if 401 after previously successful calls, re-check auth

**Detection:** Test with gh authenticated but glab not.

**Phase:** Mixed platform support.

**Confidence:** HIGH -- standard multi-platform auth issue.

---

## Phase-Specific Warnings Summary

| Phase Topic | Pitfall ID | Severity | Mitigation |
|-------------|------------|----------|------------|
| Layout restructure | TL-1 | CRITICAL | Atomic layout change, update all queries |
| Layout restructure | TL-2 | HIGH | Design focus model before content |
| Layout restructure | TL-4 | HIGH | Document binding ownership matrix |
| iTerm2 connection | IT-1 | CRITICAL | async_create(), never run_until_complete() |
| iTerm2 connection | IT-2 | HIGH | Graceful degradation, exponential backoff |
| iTerm2 dependency | IT-3 | HIGH | Optional dependency with AppleScript fallback |
| iTerm2 errors | IT-4 | HIGH | try/except every API call |
| Startup time | IT-6 | HIGH | Lazy import iterm2 in terminal pane only |
| Background refresh | BP-1 | CRITICAL | Thread workers + semaphore concurrency |
| Background refresh | BP-2 | HIGH | Tiered polling, rate limit monitoring |
| Background refresh | BP-4 | HIGH | Timeouts, no shell=True, BatchMode SSH |
| Background refresh | BP-5 | HIGH | Exclusive workers, set_timer not set_interval |
| Background refresh | BP-6 | HIGH | Update-in-place, preserve cursor by identity |
| CLI availability | BP-3 | HIGH | Probe with shutil.which, cache result |
| Worktree discovery | WD-1 | HIGH | Skip bare repo entries |
| Worktree discovery | WD-2 | HIGH | Handle detached HEAD display |
| Worktree discovery | WD-4 | MEDIUM | Deduplicate via git-common-dir |
| Worktree discovery | WD-6 | MEDIUM | Concurrent dirty checks, limit scope |
| Claude detection | CD-1 | MEDIUM | commandLine not jobName, sticky state |
| Claude detection | CD-3 | MEDIUM | Combine signals, avoid screen content alone |
| Terminal pane | IT-5 | MEDIUM | Re-fetch app object before enumeration |
| Terminal pane | IT-7 | MEDIUM | Handle None for shell integration vars |
| Terminal pane | CD-2 | MEDIUM | Read screen only for selected session |
| Platform detection | MP-1 | MEDIUM | CLI probing, manual override |
| Platform detection | MP-2 | HIGH | Unified data model, separate parsers |
| Platform auth | MP-3 | HIGH | Check auth on startup per platform |
| Performance | TL-3 | MEDIUM | Profile widget count, batch updates |
| Filesystem | WD-5 | MEDIUM | Timeouts + concurrent refreshes |
| Stale data | BP-7 | MEDIUM | Validate paths, staleness indicators |

---

## Key Findings

1. **The iTerm2 event loop conflict (IT-1) is the single most dangerous pitfall.** `iterm2.run_until_complete()` MUST NOT be used inside a Textual app. Use `iterm2.Connection.async_create()`. This must be validated in a proof-of-concept before building any features on top. Verified from source code.

2. **The iterm2 package is GPLv2+ licensed (IT-3).** Make it an optional dependency with an AppleScript fallback. This also eliminates import-time cost and avoids license complications for a public repo.

3. **Background subprocess polling needs three safety measures:** thread workers (BP-1), timeouts on every call (BP-4), and exclusive workers to prevent stacking (BP-5). Together these prevent the most common failure modes. The concurrent semaphore pattern caps system load.

4. **The 4-pane layout (TL-1) must be done as a single atomic restructure.** The current `Horizontal(ProjectList, ProjectDetail)` becomes `Vertical(Horizontal(top), Horizontal(bottom))`. All CSS and query_one() calls must be updated simultaneously. This is the first thing to implement.

5. **Claude detection (CD-1) will never be 100% reliable.** Use `commandLine` (not `jobName`) as primary signal with 5-second sticky decay. Design for "likely busy" / "likely idle" rather than definitive states.

6. **GitHub rate limiting (BP-2) is real at 30s polling.** Implement tiered refresh: active project at 30s, background repos at 5m, back off when rate limit is low. The 5,000 points/hour limit is consumed faster than intuition suggests.

7. **Refresh must preserve cursor position (BP-6).** Recompose-on-data-change is an anti-pattern for periodic refresh. Update widgets in-place, match items by identity (branch name / session ID), and restore cursor after data changes.

---

## Sources

- iTerm2 connection.py source: https://github.com/gnachman/iTerm2/blob/master/api/library/python/iterm2/iterm2/connection.py
- iTerm2 Python API Connection docs: https://iterm2.com/python-api/connection.html
- iTerm2 Python API Session docs: https://iterm2.com/python-api/session.html
- iTerm2 Python API Screen docs: https://iterm2.com/python-api/screen.html
- iTerm2 Python API Troubleshooting: https://iterm2.com/python-api/tutorial/troubleshooting.html
- iTerm2 Python API Lifecycle: https://iterm2.com/python-api/lifecycle.html
- iTerm2 Variables reference: https://iterm2.com/documentation-variables.html
- iTerm2 Python API auth: https://iterm2.com/python-api-auth.html
- iTerm2 package on PyPI (GPLv2+): https://pypi.org/project/iterm2/
- Textual Workers guide: https://textual.textualize.io/guide/workers/
- Textual Input/Bindings guide: https://textual.textualize.io/guide/input/
- Textual Timer API: https://textual.textualize.io/api/timer/
- GitHub CLI rate limits discussion: https://github.com/cli/cli/discussions/5381
- GitHub REST API rate limits: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- GitHub CLI subprocess stderr issue: https://discuss.python.org/t/gh-pr-list-stderr-is-not-captured-by-subprocess/29300
- GitLab CLI docs: https://docs.gitlab.com/cli/
- GitLab rate limits: https://docs.gitlab.com/security/rate_limits/
- glab keyring token issues: https://gitlab.com/gitlab-org/cli/-/work_items/8168
- Git worktree documentation: https://git-scm.com/docs/git-worktree
- Git worktrees with submodules: https://gist.github.com/ashwch/946ad983977c9107db7ee9abafeb95bd
- Python subprocess timeout issues: https://bugs.python.org/issue30154
- Python subprocess zombie fix: https://github.com/python/cpython/issues/81605
- Claude Code process issues: https://github.com/anthropics/claude-code/issues/11122
- asyncio RuntimeError workaround: https://medium.com/@vyshali.enukonda/how-to-get-around-runtimeerror-this-event-loop-is-already-running-3f26f67e762e
