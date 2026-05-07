# Quick Task 260428-qtn: auto-set open_by_default on new/linked objects - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Task Boundary

When new objects are created (manual add via `a` key) or auto-linked (MR auto-add propagation),
check if the object's kind is in `config.default_open_kinds` and set `open_by_default=True` if so.

</domain>

<decisions>
## Implementation Decisions

### Scope
- Only applies to two code paths: manual add (app.py:691) and MR auto-add (app.py:322-327)
- Does NOT retroactively update existing objects when settings change
- Does NOT apply to virtual rows (REPO, TERMINALS from resolver — these aren't stored ObjectItems)

### Claude's Discretion
- No additional gray areas — the change is a 2-line behavioral fix at two known locations

</decisions>

<specifics>
## Specific Ideas

- `app.py:691` — `ObjectItem(kind=preset, value=value)` → add `open_by_default=preset.value in self._config.default_open_kinds`
- `app.py:322-327` — `ObjectItem(..., open_by_default=False)` → change to `open_by_default=PresetKind.MR.value in self._config.default_open_kinds`

</specifics>
