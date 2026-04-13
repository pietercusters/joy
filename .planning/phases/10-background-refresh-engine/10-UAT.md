---
status: complete
phase: 10-background-refresh-engine
source: 10-01-SUMMARY.md, 10-02-SUMMARY.md
started: 2026-04-13T00:00:00Z
updated: 2026-04-13T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Timestamp in Border Title on Startup
expected: Launch joy. The Worktrees pane border should show a timestamp after "Worktrees" — e.g., "Worktrees  just now" (two spaces between label and timestamp). This appears immediately after startup once the initial load completes.
result: pass

### 2. Manual Refresh with r Key
expected: With joy running, press `r` from any focused pane. The Worktrees pane border timestamp updates to "just now" (or a fresh value). No toast notification appears — the timestamp update is the only feedback.
result: pass

### 3. r Key Works from Any Pane
expected: Tab focus to the Projects pane (left side). Press `r`. The Worktrees pane timestamp still updates — the binding fires regardless of which pane has focus.
result: pass

### 4. Relative Timestamp Format
expected: After pressing `r`, the timestamp shows "just now". Wait about 20 seconds without refreshing — the timestamp should change from "just now" → "20s ago". After a minute it should show "Xm ago".
result: pass
note: "Fixed in 5f55323 — 5s label-update ticker added; re-verified by user"

### 5. Background Auto-Refresh
expected: Launch joy and leave it running without pressing anything. After ~30 seconds the Worktrees pane border timestamp should update automatically (without any keypress). The timestamp resets toward "just now".
result: pass
note: "Fixed in 5f55323 — same root cause as test 4; re-verified by user"

### 6. Scroll Position Preserved on Refresh
expected: If the Worktrees pane has enough worktrees to scroll, scroll down. Press `r` to refresh. After refresh completes, the scroll position should be preserved — not snapped back to the top.
result: blocked
blocked_by: other
reason: "cannot test it"

### 7. Stale Warning Glyph
expected: When data is stale (refresh failed or no successful refresh for > 60s), a ⚠ warning glyph should appear before the timestamp in the border title.
result: skipped

## Summary

total: 7
passed: 5
issues: 0
pending: 0
skipped: 1
blocked: 1

## Gaps

- truth: "Timestamp in border title changes over time (e.g., 'just now' → '20s ago' → '2m ago')"
  status: failed
  reason: "User reported: just now is always displayed, never changes"
  severity: major
  test: 4
  root_cause: "_update_refresh_label() is only called on refresh events (mark_refresh_success/failure). There is no periodic display-update timer. The label is computed once per data refresh (age ≈ 0 → 'just now') and then frozen. Between refreshes the displayed age never ages."
  artifacts:
    - path: "src/joy/app.py"
      issue: "_update_refresh_label only called from _mark_refresh_success/_mark_refresh_failure — no separate periodic label-update timer"
  missing:
    - "Add a second set_interval timer (every 5s) in _set_projects that calls _update_refresh_label() without triggering a data refresh"
  debug_session: ""

- truth: "Background auto-refresh fires every ~30s and updates the timestamp in the border title"
  status: failed
  reason: "User reported: just now is always displayed, never changes"
  severity: major
  test: 5
  root_cause: "Same root cause as test 4: auto-refresh timer fires correctly every 30s but each fire resets the label to 'just now' (age=0). Without a display-update ticker, the label never shows elapsed age between fires — it always reads 'just now' right after each data refresh."
  artifacts:
    - path: "src/joy/app.py"
      issue: "No display-update ticker; label frozen at 'just now' between 30s data-refresh cycles"
  missing:
    - "Same fix as test 4: periodic _update_refresh_label() call independent of data refresh"
  debug_session: ""
