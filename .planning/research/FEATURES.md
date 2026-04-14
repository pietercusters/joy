# Feature Landscape: Cross-Pane Intelligence (v1.2)

**Domain:** Developer project artifact manager -- cross-pane sync and live data propagation
**Researched:** 2026-04-14
**Confidence:** MEDIUM (patterns synthesized from multiple TUI tools; no single authoritative source for "cross-pane sync" as a pattern)

## Table Stakes

Features users expect from any multi-pane TUI that shows related data across panels. Missing these makes the cross-pane feature feel broken or half-baked.

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| **Selection in one pane updates context in another** | This is the lazygit/ranger fundamental: selecting a file shows its diff; selecting a branch shows its commits. Users with multi-pane TUI experience will immediately expect selection in Projects to filter/highlight Worktrees and Agents. | Med | Relationship resolver (new), all 4 pane widgets | lazygit: selecting a file updates the right-side diff panel. ranger: selecting a directory updates the preview column. k9s: selecting a resource shows its YAML/describe. This is the core of "linked panels." |
| **Sync is instant and non-blocking** | When cursor moves in any pane, related panes must update within the same render cycle (no visible lag, no spinner). The data is already in memory -- this is pure UI filtering, not I/O. | Low | In-memory relationship index | lazygit achieves this because the diff panel reads from already-loaded git state. joy's worktree and terminal data are already loaded from the last refresh cycle. |
| **Sync direction is "highlight moves, related items highlight"** | NOT "selection in pane A moves cursor in pane B." The pattern is: pane A cursor moves -> pane B visually marks related items (border, dim non-matching, badge). The user stays in control of each pane's cursor independently. | Low | CSS classes for "related" vs "unrelated" rows | k9s xray view does this: selecting a deployment shows its related pods inline. lazygit: selecting a branch does NOT move the file panel cursor, but the diff panel content updates. |
| **Graceful empty state when no match found** | If the selected project has no matching worktrees or agents, the related pane should show "No matching worktrees" -- not go blank or show stale data from the previous selection. | Low | Each pane's empty-state rendering (already exists) | k9s shows "No resources in this namespace" cleanly. lazygit shows empty diff panel with no content. |
| **Badge counts on parent rows** | When navigating a list of projects, seeing "(2 worktrees, 1 agent)" inline prevents the user from needing to check other panes. This is the k9s pattern: resource counts appear in the resource list itself. | Med | WorktreePane data + TerminalPane data available at ProjectList render time | k9s shows pod counts on deployments, container counts on pods. This is table stakes for any "overview" TUI that shows parent-child relationships. |
| **Sync toggle must be discoverable** | The keyboard shortcut to enable/disable sync must appear in the footer when relevant panes have focus. Undiscoverable toggles are invisible features. | Low | Footer binding system (already exists) | lazygit shows all available keys in the panel header. joy already has context-sensitive footer via Textual BINDINGS. |
| **Stale items are visually distinct, not hidden** | When an agent session disappears or a worktree is deleted, dim/strikethrough the row rather than silently removing it. Sudden disappearance is disorienting. Mark stale, let the user acknowledge or let next refresh clean up. | Med | Stale detection logic, CSS styling for stale state | VS Code marks deleted files with strikethrough in source control. k9s shows "Terminating" pods in a different color rather than hiding them. The pattern is: show the transition state, don't jump-cut. |
| **Live data changes surface as non-modal notifications** | When a worktree auto-adds to a project TOML or an MR is auto-detected, show a brief status bar message. Silent data mutations are confusing -- the user wonders "where did that come from?" | Low | Status bar notification (already exists via self.app.notify) | lazygit uses a brief status message when operations complete. joy already has this pattern. |

## Differentiators

Features that set joy's cross-pane intelligence apart from what lazygit/k9s/gitui offer. These create the "this tool understands my workflow" feeling.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| **Bidirectional sync: any pane can drive** | lazygit is unidirectional: left panels drive right panels. In joy, selecting a worktree should highlight the matching project AND agent, selecting an agent should highlight the matching project AND worktree. This makes the four-pane grid feel like one unified view, not a master-detail hierarchy. | High | Relationship resolver must handle all 3 match directions (project->worktree, worktree->project, terminal->project) | No mainstream TUI does true bidirectional sync across 4 panes. Most are master-detail (one drives many). This is a genuine differentiator. |
| **"Branch is king" ownership model** | When a worktree's branch matches a project, the project owns that worktree -- even if the worktree was physically created under a different repo path. This lets objects auto-migrate between projects when branches move. | Med | Branch-to-project mapping, TOML auto-update logic | No equivalent in other TUIs because they don't manage project-artifact relationships. This is domain-specific intelligence. |
| **Auto-add MR when detected for project's branch** | During refresh, if `gh`/`glab` returns an MR for a branch that matches a project, silently add it as an MR object. The user never has to manually add MR URLs. | Med | MR data from v1.1 refresh, project branch matching, TOML mutation | This is joy-specific workflow intelligence. No other TUI auto-populates project metadata from external tool output. |
| **Auto-remove worktree objects when worktree deleted** | If `git worktree list` no longer shows a worktree that's in a project's objects, remove the stale object from TOML. No manual cleanup needed. | Med | Worktree discovery diffing between refresh cycles, TOML mutation | Prevents the common annoyance of dead links accumulating in project configs. |
| **Sync on/off as a first-class toggle** | A single keypress toggles between "synced navigation" and "independent panes." When you want to explore worktrees freely without the project pane jumping around, turn sync off. When you want the unified view, turn it on. | Low | Boolean state in app, respected by all highlight handlers | Some IDEs have "link editor to navigator" toggles (Eclipse, IntelliJ). This brings that pattern to a TUI. Familiar to IDE users. |

## Anti-Features

Things to explicitly NOT build for v1.2. Each would add complexity without proportional value or would actively harm UX.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Auto-move cursor in synced panes** | If selecting project A moves the cursor in WorktreePane to worktree X, the user loses their place. This is the single most common complaint about "linked views" in IDEs (Eclipse's "Link with Editor" was hated for this exact reason). | Highlight/dim related items but leave cursor position unchanged. The user decides when to navigate. |
| **Deep filtering (hide non-matching rows)** | Hiding rows in WorktreePane when a project is selected would break spatial memory. The user memorizes "my worktree is the 3rd row" -- if rows disappear and reappear, that mental model breaks. | Dim non-matching rows to 30% opacity. All rows stay visible. The eye naturally focuses on the bright ones. |
| **Sync between project list and project detail** | These two panes already have a master-detail relationship (selecting a project shows its objects). Adding sync logic here is redundant and would fight the existing on_project_list_project_highlighted handler. | Keep existing master-detail. Sync only applies to the cross-axis: Project <-> Worktree and Project <-> Terminal. |
| **Automatic project creation from discovered worktrees** | Dropped in v1.1 (FLOW-03, D-03). Still a bad idea: auto-creating projects pollutes the project list with noise. The user should decide what constitutes a "project." | Show unmatched worktrees normally in WorktreePane. If the user wants a project for it, they create one manually. |
| **Undo for auto-mutations (auto-add MR, auto-remove worktree)** | Undo for automated TOML changes adds significant complexity (change log, reverse operations). The mutations are small and recoverable (re-add manually, or the MR will re-detect on next refresh). | Show a notification when auto-mutations happen. If the user disagrees, they can manually adjust. |
| **Real-time file watching on ~/.joy/ TOML files** | Watching for external edits to TOML adds an inotify/kqueue dependency and edge cases (partial writes, encoding issues). The existing 30s refresh cycle is sufficient. | Rely on periodic refresh + manual `r` key. External TOML edits take effect on next refresh. |
| **Complex relationship graph visualization** | k9s xray-style tree views of project-worktree-agent relationships would be impressive but disproportionate engineering effort for a personal tool with <100 items. | Use badge counts on project rows and dim/highlight patterns. The four-pane grid IS the visualization. |
| **Persistent sync state across sessions** | Remembering whether sync was on/off last time adds config complexity. This is a session-level preference. | Default sync ON at startup. User toggles off if needed. State resets on quit. |

## UX Patterns from Comparable Tools

### Cross-Pane Sync Patterns (Ecosystem Analysis)

**lazygit: Unidirectional master-detail**
- LEFT panels (status, files, branches, commits, stash) drive the RIGHT panel (diff/log view)
- Selecting a file -> right panel shows its diff
- Selecting a commit -> right panel shows its changes
- Selecting a branch -> right panel shows its commit log
- LEFT panels are INDEPENDENT of each other: selecting a branch does NOT move the files cursor
- There is NO reverse direction: changing the diff view does NOT move the branch cursor
- Confidence: HIGH (verified via freeCodeCamp guide and oliverguenther deep-dive series)

**k9s: Drill-down stack with breadcrumbs**
- Single main view, but each selection pushes a new view onto a stack
- Deployments -> select -> Pods for that deployment -> select -> Container -> select -> Logs
- Breadcrumb trail at top shows navigation path
- NOT simultaneous multi-pane; sequential drill-down
- XRay view shows tree of resource relationships (deployment -> pod -> container -> secret)
- Namespace "breadcrumbs" via keys 1-9 for recently visited namespaces
- Confidence: HIGH (verified via k9scli.io, DeepWiki, Baeldung)

**ranger: Miller columns with automatic preview**
- Three columns: parent / current / preview
- Moving cursor in center column instantly updates right (preview) column
- Moving into a directory shifts all three columns left
- Purely hierarchical; no cross-cutting relationships
- Confidence: HIGH (well-documented, verified via ArchWiki and official user guide)

**gitui: Panel-local with shared context**
- Multi-panel layout similar to lazygit
- Selecting a file in the status panel shows its diff in an adjacent area
- Hunk-level staging directly in the diff view
- Panels update based on the focused panel's selection
- Confidence: MEDIUM (verified via DEV community article and GitHub README)

### Stale Object UX Patterns

**k9s: Terminating state shown inline**
- Pods being deleted show "Terminating" status in the list, not hidden
- Different color/style distinguishes terminating from running
- Confidence: MEDIUM (based on general k9s documentation; specific visual treatment not deeply documented)

**VS Code: Strikethrough for deleted files**
- In source control, deleted files appear with strikethrough text
- Files are visible but clearly marked as "going away"
- Confidence: HIGH (verified via VS Code issue tracker, standard behavior)

**General TUI pattern: Dim + icon for unavailable items**
- Wez's Terminal dims inactive panes using HSB multipliers
- Carbon Design System uses reduced opacity for disabled states
- Terminal convention: dim (ANSI style "dim") for less important/inactive items
- Confidence: MEDIUM (synthesized from multiple sources; no single TUI standard document)

### Badge Count Patterns

**k9s: Resource counts on parent resources**
- Deployment rows show replica counts (e.g., "3/3")
- Namespace view shows resource counts
- Counts update in real-time as resources change
- Confidence: HIGH (verified via k9scli.io and multiple tutorials)

**lazygit: Status panel shows branch behind/ahead counts**
- Status panel shows "X behind, Y ahead" for current branch
- This is a form of badge count (relationship data shown inline)
- Confidence: HIGH (verified via status panel deep-dive)

**General pattern: Parenthesized counts after labels**
- `my-project (2 wt, 1 ag)` or `my-project [2][1]`
- Numbered badges vs dot badges: use numbered when exact count matters, dot when just "has any"
- Confidence: MEDIUM (synthesized from Carbon Design System badge patterns)

## Feature Dependencies

```
Relationship Resolver (new)
  |-> Cross-pane selection sync
  |     |-> Sync toggle (on/off)
  |     |-> Visual dimming of non-matching rows
  |-> Badge counts on project rows
  |
  Uses: Project.repo field + branch matching
  Uses: WorktreeInfo.repo_name + WorktreeInfo.branch
  Uses: TerminalSession.session_name + TerminalSession.cwd

Worktree discovery (existing v1.1)
  |-> Auto-remove stale worktree objects from TOML
  |-> Auto-move worktree objects when branch changes project

MR data fetch (existing v1.1)
  |-> Auto-add MR objects to project TOML

Terminal session fetch (existing v1.1)
  |-> Agent stale detection (session gone -> mark stale)
  |-> Agent recovery (session reappears -> clear stale)

Badge counts
  |-> Requires: relationship resolver output
  |-> Requires: worktree + terminal data already loaded
  |-> Display: ProjectRow render must include count data
```

## Complexity Assessment

| Feature | Complexity | Rationale |
|---------|-----------|-----------|
| Relationship resolver | Med | Pure function: given projects, worktrees, terminals -> compute matches. No I/O. Main challenge is defining match criteria (repo name + branch for worktrees, session name/cwd for terminals). |
| Cross-pane highlight sync | Med | Each pane's _update_highlight must check resolver output and apply CSS classes. Risk: render performance if resolver runs on every cursor move. Mitigation: resolver output is a cached dict, lookup is O(1). |
| Sync toggle | Low | Single boolean on JoyApp. All panes check `self.app._sync_enabled` before applying sync highlighting. Footer shows current state. |
| Badge counts | Med | ProjectRow must accept count data. ProjectList._rebuild must have access to worktree/terminal data (currently it doesn't -- needs plumbing from JoyApp). Challenge: counts must update after each refresh, not just on initial load. |
| Auto-remove stale worktree objects | Med | Compare worktree discovery results with project objects. Remove objects whose worktree path no longer exists. Risk: false positives if a worktree is temporarily unavailable. Mitigation: require 2 consecutive missing refreshes before removal (debounce). |
| Auto-add MR objects | Med | Check MR data for branches matching project. Risk: duplicate MR objects if added manually AND auto-detected. Mitigation: check for existing MR object with same URL before adding. |
| Auto-move worktree objects | High | When branch X moves from project A to project B (because worktree branch changed), update both projects' TOML. Risk: data loss if the move logic is wrong. Needs careful testing. |
| Agent stale detection | Med | Compare terminal sessions with project agent objects. Mark agents whose iTerm2 session no longer exists. Recovery: clear stale flag when session reappears. Visual: dim + ghost icon for stale agents. |

## Phase Ordering Recommendation

Based on dependency analysis:

1. **Relationship resolver first** -- everything else depends on it
2. **Cross-pane sync + toggle** -- the headline feature; visible immediately
3. **Badge counts** -- uses resolver output, enhances project list pane
4. **Agent stale detection** -- independent from TOML mutations, visual-only
5. **Auto-remove/add/move TOML objects** -- data mutations are riskier; ship after the visual features are stable

Rationale: Visual features (sync, badges, stale indicators) are safe to ship -- they don't modify data. TOML mutations (auto-add MR, auto-remove worktree, auto-move) modify user data and need more defensive coding + testing.

## Sources

- lazygit panel architecture: [freeCodeCamp guide](https://www.freecodecamp.org/news/how-to-use-lazygit-to-improve-your-git-workflow/)
- lazygit files panel deep-dive: [oliverguenther.de](https://www.oliverguenther.de/2021/04/lazygit-the-files-panel/)
- lazygit commits panel: [oliverguenther.de](https://www.oliverguenther.de/2021/12/lazygit-the-commits-panel/)
- k9s xray resource relationships: [DeepWiki](https://deepwiki.com/derailed/k9s/5.3-pod-management)
- k9s navigation and breadcrumbs: [k9scli.io](https://k9scli.io/)
- k9s cheatsheet: [ahmedjama.com](https://ahmedjama.com/blog/2025/09/the-complete-k9s-cheatsheet/)
- TUI layout patterns (7 archetypes): [The Terminal Renaissance](https://dev.to/hyperb1iss/the-terminal-renaissance-designing-beautiful-tuis-in-the-age-of-ai-24do)
- TUI contextual hotkeys: [jensroemer.com](https://jensroemer.com/writing/tui-design/)
- ranger Miller columns: [ArchWiki](https://wiki.archlinux.org/title/Ranger)
- gitui architecture: [DEV community](https://dev.to/waylonwalker/gitui-is-a-blazing-fast-terminal-git-interface-32nd)
- Badge design patterns: [Carbon Design System](https://carbondesignsystem.com/patterns/status-indicator-pattern/)
- Disabled/stale state patterns: [Carbon Design System](https://carbondesignsystem.com/patterns/disabled-states/)
- VS Code strikethrough for deleted files: [VS Code issue #134116](https://github.com/microsoft/vscode/issues/134116)
- k9s stale context display: [k9s issue #3678](https://github.com/derailed/k9s/issues/3678)
