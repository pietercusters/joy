# Phase 10: Background Refresh Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-13
**Phase:** 10-background-refresh-engine
**Areas discussed:** Timestamp display, Stale data signaling, Manual refresh feedback

---

## Timestamp Display

| Option | Description | Selected |
|--------|-------------|----------|
| border_title suffix | "Worktrees  2m ago" — always visible regardless of focus, zero extra DOM nodes | ✓ |
| Static at bottom of pane | A pinned row at the bottom of the scroll area — more prominent but consumes vertical space | |
| sub_title when focused | Shows in app header only when Worktrees pane has focus — invisible otherwise | |

**User's choice:** border_title suffix  
**Notes:** The preview sealed it — "Worktrees  2m ago" in the pane border fits the lazy-git/k9s aesthetic already established.

---

## Stale Data Signaling

| Option | Description | Selected |
|--------|-------------|----------|
| Timestamp color change | Timestamp turns yellow/orange when stale — "Worktrees  ⚠ 2m ago" | ✓ |
| STALE label | Adds "STALE" text prefix to timestamp when stale — more explicit | |
| No special indicator | Let the timestamp age naturally — growing number implies staleness | |

**User's choice:** Timestamp color change  
**Notes:** Warning icon + yellow color on border_title. Stale threshold: age > 2× refresh_interval or worker exception.

---

## Manual Refresh Feedback

| Option | Description | Selected |
|--------|-------------|----------|
| Silent | No toast — the timestamp updating is the only confirmation | ✓ |
| Brief toast notification | notify("Refreshing…") disappears automatically | |
| Border_title feedback | "Worktrees  Refreshing…" while worker runs, then restores with new timestamp | |

**User's choice:** Silent  
**Notes:** Explicit preference — no toast on `r` press. The timestamp update after completion is sufficient feedback.

---

## Claude's Discretion

- Timer mechanism (Textual `set_interval` vs. manual async loop)
- Whether timestamp is relative ("2m ago") or absolute ("14:32") and whether a 1-second heartbeat timer keeps it live
- Rich markup details for stale color (yellow vs. orange, exact Nerd Font warning glyph)
- Whether `WorktreePane` exposes a `set_refresh_label()` method or JoyApp writes `border_title` directly
- `r` binding label text in Footer

## Deferred Ideas

None raised during discussion.
