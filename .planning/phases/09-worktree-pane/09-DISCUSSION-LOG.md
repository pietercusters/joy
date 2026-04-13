# Phase 9: Worktree Pane - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in 09-CONTEXT.md — this log preserves the Q&A.

**Date:** 2026-04-13
**Phase:** 09-worktree-pane
**Mode:** discuss (interactive)
**Areas discussed:** Data flow & pane API, Row visuals & grouping, Ordering & path abbreviation, Empty states

## Gray Areas Selected

All four offered areas were selected:
- Data flow & pane API
- Row visuals & grouping
- Ordering & path abbreviation
- Empty states

## Area 1: Data flow & pane API

| Question | Options Presented | User Answer |
|----------|-------------------|-------------|
| Who triggers the initial worktree load, and where does it run? | App-owned push (rec) / Pane self-loads / Reactive attribute | **App-owned push** |
| When should the initial discover_worktrees() run? | After projects/config load (rec) / Parallel in on_mount / Lazy on first focus | **After projects/config load** |
| What API method should the pane expose? | set_worktrees(list) (rec) / set + refresh() / Post message | **set_worktrees(list)** |
| What to show before first data lands? | "Loading…" placeholder (rec) / Empty / Skeleton rows | **"Loading…" placeholder** |

All recommended options accepted.

## Area 2: Row visuals & grouping

| Question | Options Presented | User Answer |
|----------|-------------------|-------------|
| Underlying widget for grouped list | VerticalScroll + custom rows (rec) / ListView w/ suppressed selection / DataTable | **VerticalScroll + custom rows** |
| Two-line row layout | Single Static + rich Text `\n` (rec) / Container + 2 Statics / Single line w/ hover-path | **Single Static + rich Text `\n`** (confirmed after user asked for DOM clarification) |
| Indicator style | Nerd Font icons (rec) / ASCII markers / Text labels | **Nerd Font icons** |
| Repo section header style | Reuse GroupHeader (rec) / Icon + name + count / Rule line + name | **Reuse GroupHeader** |

User asked what "DOM" meant mid-area. Claude explained DOM (widget tree), tradeoff (1 Static per row = ~20 nodes vs Container + 2 Statics = ~60 nodes on every Phase 10 refresh), and recommended the single-Static approach. User accepted recommendation and all three remaining options in the area.

## Area 3: Ordering & path abbreviation

| Question | Options Presented | User Answer |
|----------|-------------------|-------------|
| Order of repo sections | Alphabetical by repo name (rec) / repos.toml insertion order / Dirty-first | **Alphabetical by repo name** |
| Worktree order within a repo | Alphabetical by branch (rec) / Dirty-first then alpha / Default-branch-first then alpha | **Alphabetical by branch** |
| Path abbreviation algorithm | `~/` for home (rec) / `~/` + middle-collapse / Relative to repo | **`~/` for home, no other rewriting** |
| Overflow when path too wide | Right-truncate via overflow:hidden (rec) / Middle-truncate with ellipsis / Wrap to 3rd line | **Middle-truncate with ellipsis** (user corrected the recommendation) |

Three recommended; user corrected overflow to middle-truncate — they valued preserving both ends of the path (home-relative prefix + leaf segment) over zero-extra-code right-truncation.

## Area 4: Empty states

| Question | Options Presented | User Answer |
|----------|-------------------|-------------|
| No repos registered | "No repos registered. Add one via settings." (rec) / "No repos registered." (no hint) / Blank | **"No repos registered. Add one via settings."** |
| All worktrees filtered | "No active worktrees." (rec) / "No active worktrees. (filtered: main, testing)" / Show headers anyway | **"No active worktrees. (filtered: main, testing)"** (user corrected to show the active filter list) |
| All repos errored | Same as "all filtered" (rec) / Distinct error message / List each broken repo | **Same as "all filtered"** |
| Empty slot rendering | Centered muted Static (rec) / Top-left like a row / GroupHeader styling | **Centered muted Static** |

Three recommended; user corrected the "all filtered" copy to include the filter list for troubleshooting transparency.

## Wrap-up

- All four areas completed in a single pass.
- One tangent: user asked "What is DOM?" during Area 2 — answered, then they accepted the recommendation.
- Final confirmation: "I'm ready for context" → CONTEXT.md written.

## Deferred Ideas Captured

(Moved to 09-CONTEXT.md <deferred>)

- Background refresh timer, last-refresh timestamp, stale indicator — Phase 10
- MR/CI status badges + author/commit line — Phase 11
- Per-repo error surfacing — requires changing Phase 7 D-02 silent-skip contract
- Repo registry UI (settings) — Phase 13
- Row activation to open worktree in IDE — explicit non-goal (success criterion #3)
- Per-worktree Claude/terminal session indicator — Phase 12
- Projects-pane grouping by repo — Phase 13
- Resize-responsive truncation recompute — future consideration (Phase 10 refresh incidentally handles it)

---

*Discussion completed 2026-04-13.*
