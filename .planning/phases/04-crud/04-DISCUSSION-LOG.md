> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-11
**Phase:** 04-crud
**Mode:** discuss
**Areas discussed:** Project creation flow, Object form fields, New-project key + scope, Delete confirmation style

## Gray Areas Presented

### Project creation flow
- What happens after user enters the new project name?
- Success criteria says "with pre-defined object slots" — ambiguous

### Object form fields
- Add: preset list, preset + generic, or type-to-filter?
- Edit: value only, value + label, or value + label + kind?
- Label field: include or omit from add form?

### New-project key + scope
- Key: `n`, `N`, or other?
- Scope: global or project-list-only?

### Delete confirmation style
- Modal dialog, footer inline prompt, or type-to-confirm?

## Decisions Made

### Project creation flow
- After entering name → immediately open add-object form (**not** create-empty-then-done)
- After adding object → loop back to add-object form (press Escape to finish)

### Object form fields
- Add form type picker: **type-to-filter** (user types to filter the 9 preset kinds in real time)
- Edit form: **value only** — kind (preset type) is fixed, cannot change
- Label field: **omitted** — value only in both add and edit forms

### New-project key + scope
- Key: **`n`** (lowercase)
- Scope: **global** — available from both project list and detail pane (mirrors `O` global binding pattern)

### Delete confirmation style
- **Modal dialog overlay** — centered `ModalScreen`, shows item name, Enter confirms, Escape cancels

## Corrections / Overrides

- "Auto-populate preset stubs" rejected — too opinionated about project structure; user prefers explicit add via loop
- "Preset list (no filter)" rejected — user prefers type-to-filter for speed

## No Deferred Scope Creep

Discussion stayed within Phase 4 boundaries. No new capabilities surfaced.
