# Quick Task 260420-izh: pane-sync-dimmed-selection-and-scoped-open - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Task Boundary

Change the pane sync behavior in joy's 4-pane layout so that when any item is selected, all other panes sync according to a priority cascade:

1. **Exact item match** — select the item that represents that exact item (primarily: the Details pane)
2. **Project match** — select the item that represents the Project itself
3. **Project-scoped item** — select an item in that pane that belongs to the same Project

If none of rules 1–3 can be satisfied for a pane:
- That pane switches from the current yellow full-fill selection to a **dimmed border outline** selection (grey border, no fill)
- Keyboard shortcuts to open an object in that dimmed pane show a brief status message instead of opening (e.g., "No branch for this project")

</domain>

<decisions>
## Implementation Decisions

### Dimmed state visual treatment
- Use a **dimmed border outline only** (muted/grey border highlight, no fill color)
- The row remains visible but clearly not "active" — not selected in the project-matching sense

### Scoped-open behavior for dimmed panes
- When a shortcut to open an object is pressed in a dimmed pane: **show a brief status message** (e.g., "No branch for this project") instead of opening
- Silently ignoring was considered but user prefers visible feedback

### Multi-match rule (multiple items in pane belong to active project)
- Select the **first item in list** (topmost) that belongs to the project
- No per-project memory of last-visited item in each pane

### Claude's Discretion
- Exact mechanics of "which pane is the source of truth" — last-action-wins is the natural model (selecting in any pane re-drives all others)
- How to detect project membership for each item type (branch, worktree, ticket, note, etc.) — use existing project linkage data
- Implementation details of the dimmed border CSS/TCSS class in Textual
- Whether to refactor the sync logic into a centralized event/message vs. distributed watchers — choose whatever is cleanest

</decisions>

<specifics>
## Specific Ideas

- The status message for blocked opens should name the object type: "No branch for this project", "No worktree for this project", etc.
- If refactoring is needed to make the sync logic clean and simple, do it — the user explicitly asked for clean implementation over minimal diff

</specifics>
