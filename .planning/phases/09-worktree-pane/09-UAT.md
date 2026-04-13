---
status: complete
phase: 09-worktree-pane
source: 09-01-SUMMARY.md, 09-02-SUMMARY.md, 09-03-SUMMARY.md
started: 2026-04-13T00:00:00Z
updated: 2026-04-13T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Worktrees Pane Visible
expected: Launch joy (`uv run joy` or `joy`). The right pane should be labeled "Worktrees" and show worktree rows (or an empty/loading state). The pane should be present and visible in the layout.
result: pass

### 2. Worktrees Grouped by Repo
expected: When repos have worktrees, the pane shows a bold repo/section header (e.g., repo name) above each group of worktree rows. If you have multiple repos, each has its own header. Repos are sorted alphabetically.
result: pass

### 3. Worktree Row Contents
expected: Each worktree row shows two lines: line 1 has a branch icon followed by the branch name (and any indicators), line 2 shows the abbreviated path (starting with ~ instead of /Users/you/...).
result: pass

### 4. Dirty Indicator Shown
expected: For a worktree with uncommitted changes, a yellow filled-circle icon (●) appears on line 1 of the row. For a clean worktree, no yellow circle is shown.
result: pass

### 5. No-Upstream Indicator Shown
expected: For a worktree whose branch has no remote upstream, a cloud-off icon appears on line 1 of the row. For a branch with an upstream, no cloud-off icon is shown.
result: pass

### 6. Long Path Middle-Truncated
expected: For a worktree with a very long path, the displayed path is truncated in the middle (e.g., ~/first-segment/…/leaf-segment) rather than cut off at the end.
result: pass

### 7. Pane is Read-Only
expected: Press j, k, or Enter while the Worktrees pane is focused — nothing happens (no navigation, no action). The pane displays only, it has no keyboard actions of its own.
result: pass

### 8. Tab Focus Border
expected: Press Tab to cycle focus to the Worktrees pane. A highlighted border accent appears around the pane indicating focus. Pressing Tab again moves focus away.
result: pass

### 9. Empty State — No Repos Registered
expected: If you have no repos configured (e.g., empty ~/.joy/repos.toml), the Worktrees pane shows the message "No repos registered. Add one via settings." instead of a list.
result: pass

## Summary

total: 9
passed: 9
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

