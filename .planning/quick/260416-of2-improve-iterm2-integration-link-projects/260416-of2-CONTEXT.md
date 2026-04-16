# Quick Task 260416-of2: Improve iTerm2 Integration — Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Task Boundary

Improve the iTerm2 integration in joy to:
1. Link each Project to a specific iTerm2 tab (not by name — by stable unique ID)
2. Auto-create an iTerm2 tab when a project is created
3. Refactor the Terminals/Sessions pane to group by tab (drop Agents/Others grouping)
4. Mark sessions with a Claude agent with a dot (existing behavior, keep)
5. Sessions not in any project-linked tab appear under "Other"
6. Remove the obsolete link-icon from sessions
7. Investigate whether iTerm2 tabs/windows have a stable persistent ID across restarts

</domain>

<decisions>
## Implementation Decisions

### Tab closed / missing
- Auto-recreate: when joy detects the stored tab ID is no longer valid, silently create a new tab for that project and update the stored ID. Seamless — no user-visible errors or prompts.

### Tab creation during project creation
- Best-effort, silent: attempt to create the tab; if iTerm2 is not running or the call fails, skip silently and continue with project creation. No blocking error shown.

### "Other" group content
- All sessions whose tab is not linked to any joy project, regardless of window or tab they're in.

### Claude's Discretion
- Whether to use iTerm2 window IDs or tab IDs as the link (investigate stability — prefer the most persistent option)
- How to detect a "stale" tab ID (e.g. check via AppleScript if ID still exists)
- Exact layout changes in the Terminals pane (while grouping by tab and keeping dot marker)
- Whether to store the tab ID in the project config (TOML) or in a separate state file
- Refactoring scope: keep it clean, remove obsolete link-icon code paths

</decisions>

<specifics>
## Specific Ideas

- The user wants tab-level grouping, not per-session. Each group header = one iTerm2 tab (named after the project).
- Sessions within a tab that have a Claude agent get a dot marker.
- The link-icon that previously indicated "session belongs to a project" is obsolete after this change — remove it.
- "Other" is the fallback group for any session not belonging to a project tab.

</specifics>

<canonical_refs>
## Canonical References

- iTerm2 AppleScript API: https://iterm2.com/3.4/documentation-scripting.html
- iTerm2 scripting reference for persistent IDs (uniqueIdentifier / window IDs)
- Existing joy iTerm2 integration code (investigate current state before planning)

</canonical_refs>
