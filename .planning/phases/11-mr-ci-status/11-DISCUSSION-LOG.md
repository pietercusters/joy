# Phase 11: MR & CI Status - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-13
**Phase:** 11-mr-ci-status
**Mode:** discuss
**Areas analyzed:** Row layout redesign, Fetch timing & worker, Graceful degradation, MR status vocabulary

## Assumptions Applied (from prior phases)

- CLI tool locked by ROADMAP: "GitHub/GitLab CLI integration" → `gh` + `glab`
- Silent-skip error pattern carried from Phase 7 D-02
- Single `Static` per row, two-line `rich.Text` (Phase 9 D-07) — must be preserved
- Nerd Font glyphs for all indicators (Phase 9 D-08)
- `_load_worktrees()` is the existing background worker (Phase 10 D-07)
- Border_title update mechanism already established (Phase 10 D-03)

## Assumptions Presented

### Row Layout
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Line 2 changes to MR author + commit when MR exists | Confident | Success criteria #3 literally states this |
| Path is dropped when MR data shows on line 2 | Likely | ROADMAP success criteria says "shown on second line" (implies replacement) |

### Fetch Architecture
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| gh/glab calls are slower than local git (network I/O) | Confident | Network call vs subprocess local call |
| Sequential in same worker is simplest correct approach | Likely | Matches existing _load_worktrees pattern; interval is 30s so latency acceptable |

### Graceful Degradation
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Silent skip on errors follows Phase 7 D-02 pattern | Confident | Established project pattern |
| Border_title note on total failure follows Phase 10 D-03 | Likely | Same mechanism already exists |

### MR Status Vocabulary
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Open + draft distinction is useful | Likely | Draft = not ready to merge; important signal |
| Three CI states (pass/fail/pending) vs two | Likely | Pending state gives useful "in progress" signal |

## Corrections Made

No corrections — all assumptions confirmed.

## Discussion Summary

### Row Layout
**Q:** When MR data is available, what shows on line 2?
**A:** Author · commit only (path disappears when MR exists)
**Rationale:** MR context more useful; branch + MR number provides sufficient orientation

### Fetch Timing
**Q:** How should MR/CI data be fetched?
**A:** Same worker, sequential — after `discover_worktrees()`, fetch MR data in same background thread
**Rationale:** Simple, always in sync; 30s interval tolerates the latency

### Graceful Degradation
**Q:** When gh/glab unavailable, what shows?
**A:** Border_title note — e.g., "Worktrees  ⚠ gh: not auth" on total failure; silent on partial
**Rationale:** Consistent with Phase 10 stale-warning mechanism; user sees something actionable

### MR Status Vocabulary
**Q:** Which MR states shown?
**A:** Open + Draft distinction — different icons/colors (open = accent, draft = muted)

**Q:** Which CI states shown?
**A:** Three states: ✓ pass (green), ✗ fail (red), ● pending (yellow); blank when no CI data
