# Features Research: v1.1 Workspace Intelligence

**Domain:** Developer workspace dashboard (keyboard-driven TUI with live status)
**Researched:** 2026-04-13
**Confidence:** MEDIUM-HIGH (pattern research from existing tools, iTerm2 API verified against official docs)

---

## Worktree Pane

### Table Stakes — Essential Info Per Worktree Row

Every git worktree TUI (lazygit, lazyworktree, branchlet) shows these. Missing any makes the pane feel incomplete.

| Information | Why Essential | Complexity | Display Convention |
|-------------|--------------|------------|-------------------|
| Branch name | The primary identifier. Users think in branches, not paths. | Low | Bold or primary color. First thing in the row. |
| Dirty indicator | "Do I have uncommitted work here?" is the #1 question developers ask when switching context. | Low | Single char: `*` or `M` (modified). Lazygit uses a colored dot. Lazyworktree uses a dirty file count. A simple `*` is enough for a secondary pane — joy is not a git client. |
| Ahead/behind remote | "Has this been pushed?" and "Do I need to pull?" are immediate workflow questions. | Med | Arrows: `3` ahead, `1` behind. Lazygit uses exactly this convention. Omit if 0/0 (clean state = no noise). |
| Worktree path (abbreviated) | Disambiguates when multiple worktrees exist. Full path is too long; show just the directory name or relative path. | Low | Dimmed text on line 2. `~/Code/joy-worktrees/feature-xyz` becomes `feature-xyz` or `../feature-xyz`. |
| "No remote" indicator | Worktrees from local-only branches need a visual cue that there is nothing to push/pull against. | Low | Dim text like `(local)` or a distinct icon. Lazygit shows branches without remotes differently. |

### Differentiators — Nice-to-Have Info

| Information | Value | Complexity | Notes |
|-------------|-------|------------|-------|
| MR/PR status | "Is there an open MR for this branch?" — connects git state to code review workflow. | Med-High | Requires `gh pr list` / `glab mr list` CLI calls. Lazyworktree shows this with status icons. Only worth doing if joy already calls these CLIs for the existing `mr` object type. |
| CI status | Pass/fail/running indicator per branch. Lazyworktree shows: check=passed, X=failed, dot=pending, circle=skipped. | Med-High | Same CLI dependency as MR status. Cache aggressively (lazyworktree uses 30s cache). Only show for branches with associated PRs — no PR means no CI to show. |
| Last commit message (truncated) | Reminds user what they were working on. | Low | Truncate to ~40 chars. Dimmed. Only valuable if the branch name is cryptic (e.g., `fix/123`). |
| Last commit date/age | "How stale is this worktree?" | Low | Relative time: `2h ago`, `3d ago`. Helps identify abandoned worktrees. |
| Repo name | Which repo this worktree belongs to when displaying worktrees from multiple repos. | Low | Group header above worktrees from the same repo, similar to how joy v1.0 groups objects by kind. |

### Recommended Two-Line Row Format

Based on lazygit's branches panel and lazyworktree's display, the proven pattern for dense branch info in a terminal list is a two-line row:

```
  feature/workspace-intelligence  * 3 1  CI:passed
  ~/repos/joy  2h ago
```

Line 1: Icon + branch name (bold) + dirty marker + ahead/behind + optional CI badge
Line 2: Path (dimmed) + age (dimmed)

This matches the PROJECT.md spec for "two-line rows" and is the standard across git TUIs. Single-line rows force truncation that makes scanning harder.

### Branch Filter Pattern

Lazygit sorts branches by recency (most recently checked-out first). Lazyworktree shows all worktrees by default with optional filtering. The PROJECT.md mentions "configurable branch filter" — the most useful filter is hiding branches matching a pattern (e.g., `main`, `develop`) since those are always there and not interesting in a worktree overview.

**Recommendation:** Default to showing all worktrees sorted by last-modified time. Add a configurable `exclude_branches` list in settings (e.g., `["main", "master", "develop"]`). No interactive filter needed — the pane is small and the worktree count is typically under 10.

---

## Terminal Pane

### Table Stakes — Essential Info Per Terminal Session

| Information | Why Essential | Complexity | Display Convention |
|-------------|--------------|------------|-------------------|
| Window/tab name | The session identity. iTerm2 windows created by joy's `agents` type already have meaningful names (the agent name). | Low | Primary text. Bold or highlighted. |
| Foreground process | "What is running in this session right now?" — the most glanceable piece of status. | Med | iTerm2 exposes `jobName` variable (e.g., `claude`, `vim`, `zsh`). Show after the session name, dimmed. |
| Working directory | "Which project is this session for?" — maps terminal sessions to repos/projects. | Med | iTerm2 exposes `path` variable. Abbreviate to directory name. Requires shell integration for reliable path tracking. |
| Focus action (Enter) | The whole point of the pane: see a session, press Enter, switch to it. | Med | `session.async_activate(select_tab=True, order_window_front=True)` via iTerm2 Python API. |

### Differentiators — Claude Agent Detection

This is joy's unique value proposition in the terminal pane. No other tool does this.

| Feature | Value | Complexity | Notes |
|---------|-------|------------|-------|
| Claude busy/waiting detection | When running Claude Code agents in iTerm2, knowing at a glance whether each agent is busy (processing) or waiting (needs input) is extremely valuable. Saves constant window-switching to check. | Med-High | Detection approach: check `jobName` — if it is `claude` the agent is active. Whether it is "busy" vs "waiting" likely requires heuristics: check if the process is consuming CPU, or read recent screen output for prompt indicators. This needs prototyping. |
| Session status indicator | Color or icon showing busy (spinning/active) vs idle (waiting for input). | Low (once detection works) | Nerd Font spinner or status dot: green=waiting (needs you), yellow=busy (working), gray=idle shell. |

### iTerm2 Python API Pattern

The API follows this iteration pattern (verified against official docs):

```python
app = await iterm2.async_get_app(connection)
for window in app.terminal_windows:
    for tab in window.tabs:
        for session in tab.sessions:
            name = await session.async_get_variable("name")
            job = await session.async_get_variable("jobName")
            path = await session.async_get_variable("path")
```

Key variables available per session:
- `jobName` — foreground process name (e.g., "claude", "vim", "zsh")
- `commandLine` — full command line of foreground job
- `path` — current working directory (requires shell integration)
- `name` — session name as shown in tab bar
- `pid` / `jobPid` — process IDs

**Important constraint:** The iTerm2 Python API requires a running connection to iTerm2. This is async (`asyncio`-based). Joy already uses Textual's async event loop, which is compatible. The `iterm2` package (PyPI) would be a new dependency.

### Anti-Pattern: Showing Too Many Sessions

A developer might have 20+ iTerm2 sessions open. Showing all of them defeats the purpose of quick scanning. Lazyworktree's approach: only show sessions related to known worktrees/repos.

**Recommendation:** Filter to only show sessions from windows whose names match joy's known agent names, or sessions whose working directory matches a registered repo path. An "all sessions" toggle could exist but default-off keeps the pane focused.

---

## Repo Registry

### Table Stakes

| Feature | Why Essential | Complexity | Notes |
|---------|--------------|------------|-------|
| Add/remove repos in settings | Users must be able to tell joy which repos to monitor. | Low | Extend the existing SettingsModal. Store as `[[repos]]` array-of-tables in config.toml. |
| Local path + remote URL per repo | Local path for git operations (worktree discovery, dirty checks). Remote URL for deducing GitHub/GitLab context. | Low | TOML schema: `path = "/Users/pieter/Github/joy"`, `remote = "https://github.com/pietercusters/joy"`. |
| Auto-deduce repo name | From the directory name or remote URL. Less typing for the user. | Low | `os.path.basename(path)` or parse last segment of remote URL. User can override. |
| Validate path exists | Immediate feedback if the path is wrong. | Low | Check on save. Show error in settings modal. |

### Differentiators

| Feature | Value | Complexity | Notes |
|---------|-------|------------|-------|
| Auto-detect remote from local path | Run `git remote get-url origin` to fill in remote URL automatically. Saves user from looking it up. | Low | Single subprocess call. Only if path is a valid git repo. |
| Auto-detect forge type | Parse remote URL to determine GitHub vs GitLab. `github.com` in URL = GitHub, `gitlab` = GitLab. No user config needed. | Low | Simple string matching. Determines whether to use `gh` or `glab` CLI. |

### Anti-Features for Repo Registry

| Anti-Feature | Why Avoid |
|--------------|-----------|
| Auto-discover repos on disk | Scanning the filesystem is slow, unpredictable, and finds repos the user does not care about. User should explicitly register repos. |
| Repo health monitoring | Checking if repos are cloned correctly, have valid remotes, etc. is scope creep. Joy trusts the user's git setup. |

---

## Grouping and Refresh Patterns

### Project-to-Repo Grouping

**Pattern from ecosystem:** GitHub's repository dashboard groups repos by organization. LazyWorktree groups worktrees by repository. The universal pattern for grouping in developer tools is:

1. **Section headers** — non-interactive, visually distinct group labels
2. **Sorted groups** — alphabetical or by most-recently-used
3. **"Other" / "Ungrouped" bucket** — items that do not match any group go at the end, not hidden

Joy v1.0 already uses this exact pattern for objects grouped by PresetKind (GroupHeader + items). Applying it to projects grouped by repo is a natural extension.

**Recommendation:** Group header shows repo name (from registry). Projects associated with a repo appear under that header. Projects without a repo association go under "Other" at the bottom. Collapsible groups add complexity without clear value for a list that likely has <30 projects — skip it.

**How to associate projects with repos:** Match project worktree objects' paths against registered repo paths. If a project has a worktree whose path is inside a registered repo, it belongs to that repo group. This is implicit and requires zero user configuration beyond what already exists.

### Background Refresh Patterns

Research across developer TUI tools reveals three refresh architecture patterns:

| Pattern | Used By | Pros | Cons | Fit for Joy |
|---------|---------|------|------|------------|
| Fixed-interval polling | k9s (2s default), btop, pbs-tui | Simple to implement, predictable behavior, easy to configure | Wastes resources when nothing changes, can miss rapid changes between polls | Good fit. 30s is infrequent enough to be cheap. |
| Event/reactive push | Some Kubernetes dashboards via watch APIs | Zero waste, instant updates | Requires push infrastructure. Git has no push API. iTerm2 has VariableMonitor but adds complexity. | Overkill for v1.1. |
| Hybrid (poll + manual refresh) | Lazyworktree (30s cache + manual), lazygit (filesystem watcher + manual) | Best UX: auto-updates in background, `r` for immediate refresh when user knows state changed. | Slightly more complex than pure polling. | Best fit for joy. |

**Recommended approach for joy:**

1. `set_interval(30)` in Textual (configurable via `refresh_interval` in config.toml)
2. `r` keybinding for immediate manual refresh
3. Last-updated timestamp shown in pane header (e.g., "Worktrees (30s ago)")
4. During refresh: brief indicator (e.g., dim the timestamp or show a subtle loading dot)
5. On error: show error inline in the pane, not a modal. "Failed to read /path/to/repo" with dimmed text

**Error handling patterns from k9s and lazygit:**
- Never block the UI on a failed refresh
- Show stale data with a staleness indicator rather than clearing the pane
- Log errors but do not toast/notify on every failed poll (would spam every 30s)
- On persistent failure (3+ consecutive), show a persistent warning in the pane

**What k9s gets right:** Configurable refresh rate, `r` for manual refresh, stale data shown with age indicator.
**What k9s gets wrong:** Default 2s refresh is too aggressive for non-Kubernetes use cases. Joy's 30s default is sensible for git status (which changes on human timescales, not machine timescales).

### Refresh Scope

Not everything needs the same refresh cadence:

| Data Source | Refresh Cost | Staleness Tolerance | Recommendation |
|-------------|-------------|---------------------|----------------|
| Git worktree list | Low (subprocess) | 30s is fine | Include in standard 30s poll |
| Git dirty status per worktree | Medium (one `git status` per worktree) | 30s is fine | Include in standard 30s poll |
| Ahead/behind counts | Medium (requires remote refs) | 60s+ is fine | Include in 30s poll, skip if offline |
| CI/MR status | High (HTTP API via CLI) | 60-120s is fine | Separate cadence or lazy-load on demand. Lazyworktree caches for 30s. |
| iTerm2 sessions | Low (Python API call) | 10-15s would feel responsive | Could poll faster (15s) since the API call is cheap |

---

## UX Patterns for Dense Data Panes

### What Makes Dense Panes Readable

Based on analysis of lazygit, k9s, btop, and lazyworktree:

**1. Consistent column alignment.** Even in a list (not a table), aligning status indicators to the same column position across rows creates scannable vertical channels. Branch names left-aligned, status indicators right-aligned or at a fixed offset.

**2. Two-line rows with clear hierarchy.** Line 1 is the identity (branch name, session name) in primary/bold text. Line 2 is metadata (path, age) in dimmed text. This is how lazyworktree and modern email clients display dense list items. The eye reads line 1 for scanning, drops to line 2 only when needed.

**3. Color as semantic signal, not decoration.** Use color only for meaningful status: green=good/clean, yellow=warning/dirty, red=error/conflict. Gray/dim for secondary info. Never use color for purely aesthetic purposes in a dense pane — it becomes noise.

**4. Negative space between groups.** A blank line or distinct header between groups (repo sections in the project list, or a separator between worktrees and the refresh timestamp) prevents visual blending. Lazygit uses thin separator lines between panels.

**5. Progressive disclosure.** Show the minimum by default. Additional detail on hover/select or in a detail pane. The worktree pane shows branch + dirty status; selecting a worktree could show full path, last commit, MR link in a tooltip or status bar. btop and k9s both follow this pattern.

**6. Fixed pane positions.** Lazygit's genius is that panels never move. The user develops spatial memory: "branches are top-left, diff is right, files are bottom-left." Joy's 2x2 grid should be permanent — never rearrange panes based on state.

### What Makes Dense Panes Overwhelming

**1. Everything at maximum prominence.** When every piece of data is bold, colored, and icon-decorated, nothing stands out. The most common mistake in developer dashboards. Lazyworktree avoids this by using dim text for secondary info.

**2. Too many status indicators per row.** More than 3-4 inline status badges per row creates visual noise. If a worktree row shows: dirty indicator + ahead count + behind count + CI status + MR status + age — that is 6 indicators. Rule of thumb: 2-3 indicators on line 1, supporting info on line 2.

**3. Full paths instead of abbreviations.** `/Users/pieter/Github/joy-worktrees/feature-workspace-intelligence` is 70 characters. `feature-workspace-intelligence` is 35. Use the shortest unambiguous representation.

**4. No visual rest.** Wall-to-wall text with no spacing, no group separators, no dimming. The eye cannot find anchor points. Even 1 blank line between groups dramatically improves scannability.

**5. Updating data that shifts layout.** When a refresh changes the number of items and the list jumps/reflows, the user loses their place. Always preserve cursor position across refreshes. Lazygit and k9s both do this.

---

## Anti-Patterns to Avoid

### From Git TUI Tools

| Anti-Pattern | Seen In | Why It Fails | Prevention for Joy |
|--------------|---------|--------------|-------------------|
| Modal overload for status info | Early gitui versions | Requiring a modal to see branch status interrupts flow. Status should be visible at a glance. | Show status inline in the worktree row. Modals only for mutations (add, edit, delete). |
| Showing all branches, not just worktrees | N/A (hypothetical) | Users asked for worktree status, not a full branch list. Mixing branches-without-worktrees into the pane dilutes its purpose. | Only show branches that have active worktrees. Joy is not a git branch manager. |
| Blocking UI on git operations | Early lazygit versions | `git status` on a large repo can take seconds. If the UI freezes, users think the app crashed. | Run all git operations in background workers (`@work(thread=True)` in Textual). Show stale data while refreshing. |
| Auto-fetching from remote | Some git GUIs | Fetching can trigger auth prompts, take seconds on slow connections, and has side effects (updates remote refs). | Never auto-fetch. Only read local state. User runs `git fetch` themselves. Ahead/behind counts use local ref state. |

### From Terminal Dashboard Tools

| Anti-Pattern | Seen In | Why It Fails | Prevention for Joy |
|--------------|---------|--------------|-------------------|
| Aggressive refresh causing flicker | Early btop, some k9s versions | Redrawing the entire screen every 1-2 seconds causes visible flicker, especially over SSH. | Only update changed cells/rows, not the entire pane. Textual's reactive system handles this if used correctly. |
| Toast spam on every refresh error | Various monitoring TUIs | If a git repo is temporarily unavailable, toasting every 30 seconds is maddening. | Log errors silently. Show inline "error" state in the pane. Only toast on first occurrence. |
| Resetting scroll/cursor on refresh | Various | User scrolls to worktree #5, refresh fires, cursor jumps to #1. Infuriating. | Preserve cursor index across refreshes. Match by identity (branch name), not by position. |
| Showing raw error messages | Various CLI tools | "fatal: not a git repository" in a pane is unhelpful to glance at. | Translate to human-friendly messages: "Not a git repo" or "Path not found". Keep it short. |

### From Information Density Design

| Anti-Pattern | Description | Prevention for Joy |
|--------------|-------------|-------------------|
| Feature creep in panes | Starting with "just branch name" and gradually adding CI, MR, age, commit message, author, file count... until each row is 4 lines. | Hard limit: 2 lines per worktree row, 1 line per terminal session row. If it does not fit, it does not ship. |
| Inconsistent icon vocabulary | Using different icon styles (Nerd Font + Unicode + ASCII) in the same pane. | Pick one icon set (Nerd Font, matching v1.0) and use it exclusively. |
| Color overuse | Every status gets its own color, resulting in a rainbow pane that communicates nothing. | Maximum 4 colors with semantic meaning: default (white/fg), dimmed (gray), success (green), warning (yellow). Red reserved for errors only. |

---

## Feature Dependencies for v1.1

```
Repo Registry (settings) --> Project Grouping (needs repo list)
Repo Registry (settings) --> Worktree Discovery (needs repo paths)
Worktree Discovery --> Worktree Pane (needs worktree data)
Worktree Discovery --> New Project from Worktree (needs worktree list)
Background Refresh Engine --> Worktree Pane (refresh feeds data)
Background Refresh Engine --> Terminal Pane (refresh feeds data)
iTerm2 Python API integration --> Terminal Pane (needs session data)
4-Pane Layout (CSS) --> Worktree Pane + Terminal Pane (needs container)
```

Critical path: Repo Registry --> Worktree Discovery --> Background Refresh --> Worktree Pane
Parallel track: iTerm2 API integration --> Terminal Pane
Independent: 4-Pane Layout, Project Grouping

---

## MVP Recommendation for v1.1

### Phase 1: Foundation
1. **Repo registry in settings** — everything depends on this
2. **4-pane layout** — CSS-only change, enables all pane work
3. **Project grouping by repo** — uses repo registry, improves existing pane

### Phase 2: Worktree Intelligence
4. **Worktree discovery** (git worktree list --porcelain per registered repo)
5. **Worktree pane with basic display** (branch name, dirty indicator, path)
6. **Background refresh engine** (set_interval + manual `r`)

### Phase 3: Terminal Intelligence
7. **iTerm2 Python API integration** (session enumeration)
8. **Terminal pane with basic display** (session name, foreground process, working directory)
9. **Enter to focus session**

### Phase 4: Polish
10. **Ahead/behind counts** in worktree pane
11. **Claude agent detection** in terminal pane
12. **New project from worktree** modal enhancement
13. **CI/MR status** in worktree pane (if CLI integration is clean)

### Defer to v1.2+
- CI/MR status if it requires complex CLI orchestration
- Interactive worktree creation/deletion from joy
- Terminal session creation from joy
- Worktree-to-terminal-session linking

---

## Complexity Assessment

| Feature | Complexity | Rationale |
|---------|------------|-----------|
| Repo registry in settings | Low | Extend existing SettingsModal + config.toml schema. Same pattern as existing settings. |
| 4-pane layout | Low-Med | CSS change from `Horizontal(left, right)` to a 2x2 grid. Textual CSS supports grid layout. Need to handle focus cycling across 4 panes. |
| Project grouping by repo | Med | Change project list rendering to include GroupHeaders. Match projects to repos by worktree path. |
| Worktree discovery | Med | `git worktree list --porcelain` per repo + `git status --porcelain` per worktree. Subprocess calls in background thread. Parsing is straightforward. |
| Worktree pane display | Med | New widget with two-line ListItem pattern. Custom rendering with status indicators. |
| Background refresh engine | Med | `set_interval` + `@work(thread=True)` for data fetching. Must preserve cursor position. Must handle errors gracefully. Must not flicker. |
| iTerm2 Python API integration | Med-High | New dependency (`iterm2` package). Async API that needs to coexist with Textual's event loop. Connection management. Must handle iTerm2 not running. |
| Terminal pane display | Med | Similar to worktree pane but simpler (one-line rows). Enter-to-focus via API. |
| Claude agent detection | High | No established pattern for this. Likely requires heuristics: check `jobName` for "claude", possibly check screen contents or CPU usage. Needs prototyping and iteration. |
| CI/MR status | Med-High | Requires `gh pr list` / `glab mr list` CLI calls. Parsing JSON output. Caching. Handling auth failures. Different behavior for GitHub vs GitLab. |
| New project from worktree | Low-Med | Extend existing NewProject modal with a "from worktree" option. Pre-fill name from branch, add worktree object automatically. |

---

## Sources

### Git TUI Tools
- Lazygit worktree UX discussion: https://github.com/jesseduffield/lazygit/discussions/2803
- Lazygit worktree view issue: https://github.com/jesseduffield/lazygit/issues/1801
- Lazygit branches panel deep dive: https://stuart.mchattie.net/posts/2025/06/21/lazygit-branches-panel/
- Lazygit status panel deep dive: https://oliverguenther.de/2021/04/lazygit-status-panel-deep-dive/
- LazyWorktree (dedicated worktree TUI): https://github.com/chmouel/lazyworktree
- LazyWorktree TUI interface guide: https://www.mintlify.com/chmouel/lazyworktree/guides/tui-interface
- LazyWorktree official site: https://chmouel.github.io/lazyworktree/
- GitUI: https://github.com/gitui-org/gitui
- Branchlet (worktree management): https://terminaltrove.com/branchlet/

### iTerm2 API
- iTerm2 Python API session docs: https://iterm2.com/python-api/session.html
- iTerm2 Python API app docs: https://iterm2.com/python-api/app.html
- iTerm2 variables reference: https://iterm2.com/documentation-variables.html
- iTerm2 Python API examples: https://iterm2.com/python-api/examples/index.html
- it2 CLI tool (wraps iTerm2 API): https://github.com/mkusaka/it2

### Dashboard and Refresh Patterns
- k9s configuration (refresh rate): https://k9scli.io/topics/config/
- k9s auto-refresh toggle request: https://github.com/derailed/k9s/issues/2256
- pbs-tui (auto-refresh terminal dashboard): https://samforeman.me/posts/2025/09/17/
- Textual set_interval/timer API: https://textual.textualize.io/api/timer/
- Textual workers guide: https://textual.textualize.io/guide/workers/

### UX and Information Density
- Designing for information density: https://uxdesign.cc/designing-for-information-density-69775165a18e
- UI density analysis: https://mattstromawn.com/writing/ui-density/
- Dashboard design patterns: https://dashboarddesignpatterns.github.io/patterns.html
- GitHub repository dashboard: https://github.com/orgs/community/discussions/181683

### Git Internals
- git-worktree documentation (--porcelain format): https://git-scm.com/docs/git-worktree
- git-status documentation (--porcelain format): https://git-scm.com/docs/git-status
