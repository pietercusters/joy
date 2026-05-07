# Quick Task 260506-rc1: Add MR pane + placeholder pane - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning

<domain>
## Task Boundary

Add two new panes to the joy TUI: an MR status pane (top-right in a 3x2 grid) showing authored and reviewing MRs with pipeline/approval status, and an empty placeholder pane (bottom-right). Refactor MR fetching to use efficient batch calls with per-branch fallback.

</domain>

<decisions>
## Implementation Decisions

### Grid Layout
- Expand from 2x2 to 3x2 grid (3 columns, 2 rows)
- Top row: Project List | Project Detail | MR Pane
- Bottom row: Terminals | Worktrees | Placeholder
- Existing 4 panes keep their relative positions (just shift from 2-col to 3-col)

### MR Data Fetching Strategy
- Single batch call per repo: `gh pr list --author=@me` + `glab mr list --author=@me`, plus one reviewer query per repo
- Batch results feed BOTH the MR pane AND the worktree pane (shared data)
- Fallback: for active project branches that have no matching MR in the batch result, do a per-branch query for the leftovers
- All fetching runs in the existing background worker thread
- Parallel fetching across repos for efficiency

### Reviewer Status
- Summary status only (overall approval state per MR): approved, changes requested, commented, pending
- No per-reviewer breakdown — keeps API calls minimal and display simple
- Same approach for both GitHub and GitLab

### Claude's Discretion
- Internal data model structure for the new MR pane data
- Placeholder pane implementation details (minimal static widget)
- Exact CLI flags for GitHub/GitLab reviewer status queries

</decisions>

<specifics>
## Specific Ideas

- MR pane has two sections: "My MRs" (authored, open or draft) and "Review Requests" (requested reviewer, open, not draft)
- Each MR row shows: MR number, title, pipeline status icon, approval/review status
- Reuse existing icon constants from icons.py (ICON_MR_OPEN, ICON_MR_DRAFT, ICON_CI_PASS, etc.)
- Follow existing pane patterns: non-focusable scroll container, row widgets, cursor management

</specifics>
