# Quick Task 260420-ak5: Extend new-project modal — Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Task Boundary

Replace the current single-Input NameInputModal used for new-project creation with a new multi-field single modal that collects: project name (Input), repo (optional ListView), and branch (ListView of 5 recent branches + "type custom" escape).

</domain>

<decisions>
## Implementation Decisions

### Branch field design
- Option B: ListView showing 5 most recently checked-out local branches + a "(type custom…)" item at the bottom
- Selecting "(type custom…)" opens a plain Input prompt for free-text entry
- User can pick from the list OR type a custom branch name

### Repo field optionality
- Optional — "(none)" remains a valid choice in the repo ListView
- User can skip repo assignment and assign later via the R key

### Modal structure
- Single modal — one ModalScreen containing all three fields: name (Input at top), repo section (ListView), branch section (ListView + custom escape)
- Not a sequential chain of separate modals

### Claude's Discretion
- Exact CSS layout/styling within the single modal
- How to fetch the 5 recent branches (git branch --sort=-committerdate or git reflog)
- Tab/focus order between the three sections
- Whether branch list is fetched for the selected repo's path or the current working directory

</decisions>

<specifics>
## Specific Ideas

- Existing RepoPickerModal (src/joy/screens/repo_picker.py) can be referenced for the repo ListView pattern but should NOT be reused directly — it's a full modal; here it's a section within a larger modal
- Existing NameInputModal (src/joy/screens/name_input.py) is the current entry point; the new modal replaces its use in action_new_project() in app.py
- The "(type custom…)" branch item should be visually distinct (e.g., italicized or prefixed with an icon)

</specifics>

<canonical_refs>
## Canonical References

- src/joy/screens/name_input.py — current modal being replaced for new-project flow
- src/joy/screens/repo_picker.py — existing repo ListView pattern to reference
- src/joy/app.py line ~614 — action_new_project() and on_name() callback
</canonical_refs>
