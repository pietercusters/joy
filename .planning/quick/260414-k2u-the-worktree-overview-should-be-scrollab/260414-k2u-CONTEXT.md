# Quick Task 260414-k2u: Worktree Pane — Cursor Navigation + Enter to Open — Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Task Boundary

Add interactive cursor navigation to WorktreePane (currently read-only) so users can navigate worktree rows with j/k, activate them with Enter, and escape back to the projects pane. Pressing Enter opens the MR URL in the browser if MR data exists, or opens the worktree path in the configured IDE if no MR.

</domain>

<decisions>
## Implementation Decisions

### Navigation style
- Mirror TerminalPane exactly: j/k (and up/down arrows) move the cursor, Enter activates the selected row, Escape returns focus to the projects pane
- GroupHeader rows are skipped by the cursor — cursor only lands on WorktreeRow items (same as TerminalPane skipping GroupHeader)
- Cursor highlight uses the same `--highlight` CSS variable / CSS class pattern as TerminalPane and ProjectList

### Enter — MR open
- If the selected WorktreeRow has an associated MRInfo with a URL: `webbrowser.open(mr_info.url)`
- Same pattern as url-type objects in joy; works for both GitHub and GitLab MR URLs

### Enter — No-MR fallback
- If no MR: open the worktree path in the configured IDE via `subprocess.run(["open", "-a", config.ide, worktree.path], check=False)`
- Same pattern as the existing `git worktree` object type in operations.py

### Claude's Discretion
- Footer hint update: update context-sensitive footer to show j/k/Enter/Esc hints when WorktreePane is focused (follow the existing pattern in app.py where sub_title updates per focused pane)
- Test additions: add unit tests for cursor navigation and Enter action (mirror test_terminal_pane.py patterns)

</decisions>

<specifics>
## Specific References

- TerminalPane cursor pattern: `src/joy/widgets/terminal_pane.py` — exact model to replicate
- IDE open pattern: `src/joy/operations.py` `_open_worktree()` — `subprocess.run(["open", "-a", config.ide, path])`
- MR URL field: `MRInfo.url` in `src/joy/models.py`
- MR data access: `mr_data: dict[tuple[str, str], MRInfo]` passed to `set_worktrees()`; keyed by `(repo_name, branch)`
- WorktreeRow needs to expose `repo_name` and `branch` so the Enter handler can look up `mr_data`

</specifics>

<canonical_refs>
## Canonical References

No external specs — requirements fully captured in decisions above.
</canonical_refs>
