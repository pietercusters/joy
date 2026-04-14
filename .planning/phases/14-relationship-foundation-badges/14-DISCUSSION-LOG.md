# Phase 14: Relationship Foundation & Badges - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the Q&A.

**Date:** 2026-04-14
**Phase:** 14-relationship-foundation-badges
**Mode:** discuss

## Gray Areas Presented

| Area | Selected? |
|------|-----------|
| Resolver architecture | Yes |
| Badge appearance | Yes |
| Cursor restoration fallback | Yes |

## Resolver Architecture

| Question | Options | Answer |
|----------|---------|--------|
| Where should the resolver live? | Standalone module / Inline in app.py | Standalone module (src/joy/resolver.py) |
| What should the resolver return? | RelationshipIndex object / Just counts dict | RelationshipIndex object |
| When does the app compute the RelationshipIndex? | After both worktrees + sessions load / After worktrees load only | After both worktrees + sessions load |

## Badge Appearance

| Question | Options | Answer |
|----------|---------|--------|
| How should counts appear on project rows? | Icons + numbers / Just numbers | Icons + numbers (Nerd Font icons inline) |
| Should badges show when count is zero? | Always show both / Hide zeros | Always show both |

## Cursor Restoration Fallback

| Question | Options | Answer |
|----------|---------|--------|
| Where should cursor land when item disappears? | Clamp to last valid row / Reset to row 0 / Stay at nearest matching | Clamp to last valid row (same as ProjectList delete D-13) |

## Corrections Made

No corrections — all recommended options accepted.
