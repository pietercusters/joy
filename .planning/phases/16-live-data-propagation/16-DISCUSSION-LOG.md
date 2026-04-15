# Phase 16: Live Data Propagation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-15
**Phase:** 16-live-data-propagation
**Mode:** discuss
**Areas discussed:** Worktree scope, Stale agent display, Miss counter, Mutation feedback, MR auto-add fields

## Gray Areas Presented

| Area | Description |
|------|-------------|
| Stale agent display | PROP-04/05: visual treatment for offline agent objects |
| Miss counter for PROP-01 | Tracking 2+ consecutive absent refreshes; in-memory vs persisted |
| Mutation feedback | Silent vs status bar messages when propagation changes something |
| MR auto-add fields | Label format for auto-generated MR ObjectItems |

## User Notes (unsolicited additions)

During gray area selection, the user provided two architectural clarifications that changed the scope:

1. **Worktrees are dynamic** — "On a project, the worktree is very dynamic, it can change all the time, so it should no longer be a object of the Project that we store in the toml. It also does not have to show in the Details pane at all." → PROP-01 and PROP-03 dropped entirely.

2. **MR append, not replace** — "when an MR gets detected, I want it to be added as an extra object to the Project, not replace the current value for the mr object." → append semantics, duplicate check by URL.

## Decisions Made

### Worktrees in TOML
- **Question:** Should existing WORKTREE ObjectItems be migrated out, hidden, or left unchanged?
- **Answer:** Leave entirely unchanged — backward-compatible; no migration; PROP-01 and PROP-03 dropped.

### Stale agent display
- **Question:** What does "visually dimmed" mean for agent objects?
- **Answer:** Muted color + italic — CSS class on ObjectRow.

### Miss counter
- **Question:** Should the 2+ refresh absence counter survive restarts?
- **Answer:** In-memory only — resets on restart. Simple for a personal tool. (Note: PROP-01 was subsequently dropped, making this moot — recorded for completeness.)

### Mutation feedback
- **Question:** Silent per requirements, or status bar messages?
- **Answer:** Status bar message — brief, specific. E.g. "⊕ Added PR #42 to joy".

### MR auto-add label
- **Question:** What label format for auto-generated MR ObjectItem?
- **Answer:** "PR #123" — short, readable, auto-generated from MRInfo.mr_number.

### PROP-01/PROP-03 scope
- **Question:** Implement worktree TOML cleanup, or drop since worktrees are live data?
- **Answer:** Drop PROP-01 and PROP-03 entirely.

## Corrections Applied

None — scope reduction (PROP-01/PROP-03 dropped) was driven by user clarification, not a correction to a prior assumption.

## Scope Deferred

- PROP-01: dropped — WorktreePane handles worktrees live
- PROP-03: dropped — same reason
- PROP-09, PROP-10: already in REQUIREMENTS.md Future section (v1.3+)
