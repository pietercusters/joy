---
name: 260415-mh6 Context
description: User decisions for worktree logic refactor quick task
type: project
---

# Quick Task 260415-mh6: Refactor Worktree Logic — Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Task Boundary

Refactor the app's worktree logic and Worktrees pane to be clean and correct:
1. Auto-detect all git worktrees per repo, check what branch is checked out there, and link the worktree to a Project via that branch.
2. Fix the 'i' key to open that specific worktree in the IDE (currently buggy).
3. In the Worktrees pane, Enter should open the IDE (replace whatever Enter currently does).
4. Investigate and fix any other smells or bugs in the worktree logic.

</domain>

<decisions>
## Implementation Decisions

### IDE Open Behavior
- Always open the specific worktree path in the IDE: `ide <worktree_path>`
- Do NOT use any "IDE path configured on linked project" concept — remove that if it exists
- Both 'i' and Enter trigger the same action: open the worktree directory in the IDE

### Unlinked Worktrees
- Show all auto-detected worktrees in the pane, including those with no matching project branch
- Unlinked worktrees get a visual indicator (e.g. "unlinked" label or dim styling)
- IDE open action still works on unlinked worktrees (just opens their path)

### Enter Key in Worktrees Pane
- Enter replaces the current action — it now opens the IDE on the highlighted worktree
- Same behavior as 'i' key

### Claude's Discretion
- Exact visual indicator for unlinked worktrees (label text, color, etc.)
- Whether to keep 'i' as a parallel binding alongside Enter, or just use Enter
- How to handle stale/missing worktree paths
- Any other bugs found during investigation

</decisions>

<specifics>
## Specific Ideas

- User explicitly said there should be NO "ide path configured on linked project" — remove any such concept
- The 'i' key is described as "buggy" — needs careful investigation before fixing
- Both 'i' and Enter should do the same thing: `ide <worktree_path>`

</specifics>

<canonical_refs>
## Canonical References

No external specs — requirements fully captured in decisions above.

</canonical_refs>
