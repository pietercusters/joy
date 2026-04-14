# Phase 15: Cross-Pane Selection Sync - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-04-14
**Phase:** 15-cross-pane-selection-sync
**Mode:** discuss
**Areas analyzed:** Sync trigger point, Toggle key + default state

## Gray Areas Presented

| Gray Area | Options Shown | User Decision |
|-----------|--------------|---------------|
| Sync trigger point | Every cursor move / Pane focus (Tab entry) / Debounced 150ms | Every cursor move |
| Toggle key + default state | x + ON / x + OFF / t + ON | x, default ON |

## Assumptions (Pre-discussion)

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| RelationshipIndex query methods ready to use | Confident | resolver.py present, Phase 14 complete |
| Sync loop prevention via `_is_syncing` guard (CP-1) | Confident | STATE.md Research CP-1 note |
| Sync trigger fires on cursor move (not Enter) | Likely | ProjectList uses ProjectHighlighted on move; Enter is already claimed in WorktreePane/TerminalPane |
| WorktreePane/TerminalPane need new message classes | Confident | Neither posts cursor messages currently |
| Focus stays on active pane (no `.focus()` call from sync) | Confident | SYNC-07 explicit; existing detail-pane pattern uses call_after_refresh + focus |
| Toggle ephemeral (no disk persistence) | Confident | REQUIREMENTS.md SYNC-10 explicitly deferred |

## Area 1: Sync Trigger Point

**Question presented:** When should cross-pane sync fire from WorktreePane and TerminalPane?

**Options:**
1. Every cursor move — j/k immediately triggers sync (same as ProjectList's ProjectHighlighted)
2. Pane focus (Tab entry) — sync fires once when Tab brings focus into pane
3. Debounced cursor move (150ms) — sync fires 150ms after cursor stops

**User choice:** Every cursor move

**Rationale:** Consistent with existing ProjectList behavior; feels live and reactive.

**Consequence:** WorktreePane and TerminalPane must add `WorktreeHighlighted` / `SessionHighlighted` message classes and post them from `action_cursor_up` / `action_cursor_down`.

## Area 2: Toggle Key + Default State

**Question presented:** Toggle key and default sync state?

**Options:**
1. `x`, default ON — feature immediately visible
2. `x`, default OFF — user opts in
3. `t`, default ON — "t for toggle"

**User choice:** `x`, default ON

**Rationale:** `x` is unused in current bindings, mnemonic for "cross-pane". Default ON means the feature is discoverable without any setup.

**Consequence:** BINDINGS gets `("x", "toggle_sync", "Sync: on")` with dynamic label update. `_sync_enabled = True` at startup.

## Corrections Made

No corrections — user confirmed both recommended defaults.

## Prior Decisions Applied (No Re-ask)

- Cursor pattern (`_cursor` + `_rows` + `_update_highlight()`) — established across all panes in v1.0/v1.1
- RelationshipIndex query API — locked by Phase 14 D-03
- No focus stealing — SYNC-07 explicit in requirements
- Toggle ephemeral — SYNC-10 explicitly deferred in REQUIREMENTS.md
