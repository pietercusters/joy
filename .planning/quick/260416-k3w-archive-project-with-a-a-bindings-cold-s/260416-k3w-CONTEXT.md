# Quick Task 260416-k3w: Project Archive Feature — Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Task Boundary

Add project archiving to the joy TUI:

- `a` in ProjectList → confirmation modal → archive project to `~/.joy/archive.toml` (strips worktrees + terminals objects, optionally closes iTerm2 sessions)
- `A` in ProjectList → archive browser popup (two sections: branch-matched at top, rest below; `u` unarchives selected project and closes popup)
- Archived projects stored as cold storage in a separate TOML file; unarchiving restores them to `projects.toml` without worktree/terminal objects

</domain>

<decisions>
## Implementation Decisions

### Worktrees/Terminals pane impact
None. Archiving removes the project from `projects.toml` → `_rel_index` rebuild on the next refresh cycle drops it automatically → WorktreePane and TerminalPane auto-clean with zero code changes to those widgets. The only call into terminal code is `close_session()` (existing function in `terminal_sessions.py`) for the optional terminal close. No pane code changes needed.

### Archive confirmation modal
New dedicated `ArchiveModal` screen (not extending ConfirmationModal). Has three key bindings:
- `Enter` — Archive + close terminals (default)
- `a` — Archive only (skip terminal close)
- `Esc` — Cancel

Keeps ConfirmationModal clean. The new modal is specific to this one use case.

### Archived project data model
New `ArchivedProject` wrapper dataclass:
```python
@dataclass
class ArchivedProject:
    project: Project
    archived_at: datetime
```
Keeps `Project` model clean. `archive.toml` has its own schema independent of `projects.toml`.

### Archive popup / unarchive UX
`A` key opens a modal overlay listing archived projects in two sections:
- Top section: projects whose `BRANCH` object value matches a currently checked-out worktree branch
- Bottom section: remaining archived projects
Both sections sorted by `archived_at` descending (latest archived first). `u` unarchives the highlighted project (restores to `projects.toml` without worktree/terminal objects) and closes the popup.

### Branch matching logic
Match on the archived project's `BRANCH` object value (`PresetKind.BRANCH`) against the set of currently active worktree branch names from `_rel_index`. Simple string equality.

### Claude's Discretion
- TOML storage schema for `archive.toml` (follow the keyed schema pattern from `projects.toml`, with `archived_at` as an additional field per entry)
- Archive popup widget structure (a new `Screen` subclass with a scrollable list — follow TerminalPane/WorktreePane patterns)
- Whether to show section headers ("Active branch" / "Archived") in the popup

</decisions>

<specifics>
## Specific Requirements

- Strip `PresetKind.WORKTREE` and `PresetKind.TERMINALS` objects on archive; preserve all other objects (MR, BRANCH, TICKET, etc.)
- Closing terminal sessions: call `close_session()` for each terminal in the project before archiving
- Unarchive: append restored project to `projects.toml`, remove from `archive.toml`, no worktree/terminal objects
- Archive popup should be keyboard-navigable (up/down/j/k) with `u` to unarchive highlighted

</specifics>

<canonical_refs>
## Canonical References

- `src/joy/store.py` — existing TOML persistence patterns (atomic write, keyed schema)
- `src/joy/models.py` — Project, ObjectItem, PresetKind
- `src/joy/widgets/project_list.py` — existing BINDINGS, action handlers
- `src/joy/screens/confirmation.py` — ConfirmationModal as structural reference
- `src/joy/terminal_sessions.py` — close_session() for terminal cleanup

</canonical_refs>
