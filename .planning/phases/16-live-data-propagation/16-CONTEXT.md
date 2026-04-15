# Phase 16: Live Data Propagation - Context

**Gathered:** 2026-04-15 (discuss mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Background refresh automatically keeps project objects in sync with live MR and agent state — auto-adding detected MR objects and marking/unmarking agent objects stale — without user action. Changes are written back to `~/.joy/projects.toml` via the existing `_save_projects_bg()` path.

**Scope reduction from requirements:** PROP-01 (auto-remove gone worktree objects) and PROP-03 (move worktree objects between projects) are dropped. Worktrees are fully covered by the live WorktreePane; they should not be stored as TOML objects going forward and existing WORKTREE ObjectItems are left untouched (backward-compatible). Only MR and AGENTS objects are managed by propagation.

</domain>

<decisions>
## Implementation Decisions

### Worktree objects (PROP-01, PROP-03 — dropped)

- **D-01:** PROP-01 (auto-remove gone worktree TOML objects) and PROP-03 (move worktree objects between projects) are dropped entirely. Worktrees are dynamic live data — the WorktreePane handles their display. No new WORKTREE ObjectItems will be auto-created by propagation. Existing WORKTREE ObjectItems in projects.toml are left in place (backward-compatible; user will remove manually if needed).

### MR auto-add (PROP-02)

- **D-02:** When a worktree has MRInfo (detected MR/PR) and the owning project has a BRANCH object matching the worktree's branch, check if the project already has an MR ObjectItem with the same URL. If not found → append a new ObjectItem: `kind=MR, value=mr_info.url, label="PR #{mr_info.mr_number}", open_by_default=False`.
- **D-03:** Duplicate check is by URL equality only — if the same PR URL already exists as any MR ObjectItem in the project, skip. Different PRs (different URLs) are always appended as separate objects.
- **D-04:** MR objects are auto-added but never auto-removed (PROP-07). Even if the PR closes, the MR object stays until the user removes it manually.
- **D-05:** Projects with no `repo` field are excluded from MR propagation (PROP-08) — cannot match a worktree to a project without a repo anchor.

### Agent stale marking (PROP-04, PROP-05)

- **D-06:** After each terminal session refresh, compare current iTerm2 sessions to AGENTS-kind ObjectItems across all projects. Any AGENTS object whose `value` (session name) is absent from the current sessions set is marked stale. When the session reappears (value back in sessions set), the stale marker clears. Stale state is in-memory only — never written to `projects.toml`.
- **D-07:** Stale state lives as a runtime flag on ObjectItem: `stale: bool = False` field (not serialized by `to_dict()`, not loaded from TOML). The app populates this after each terminal refresh cycle.
- **D-08:** Stale visual: a CSS class `--stale` on ObjectRow dims the text color and italicizes the value column. Applied when `item.stale` is True, removed when False. Uses the existing CSS/Textual pattern for conditional row styling.

### Propagation trigger point (CP-2)

- **D-09:** "Workers discover, main thread mutates" — propagation logic runs on the main thread, called from `_maybe_compute_relationships()` (after both worktree and session workers complete) or a new `_propagate_changes()` method called immediately after. No background thread touches `_projects` or `projects.toml`.

### Batched TOML writes

- **D-10:** All mutations in a single refresh cycle are collected first, then `_save_projects_bg()` is called once per cycle (not once per mutation). This avoids multiple atomic writes per refresh and reduces I/O.

### Mutation feedback

- **D-11:** When propagation actually changes something, emit a brief status bar message. Format examples:
  - `⊕ Added PR #42 to joy`
  - `● Agent 'claude-code' offline in joy`
  - `● Agent 'claude-code' back online in joy`
  Silent when nothing changes (normal case). Use the existing `self.notify()` or status bar update path already in app.py.

### ProjectDetail refresh after mutation

- **D-12:** After propagation mutates `_projects`, call `project_list.set_projects(self._projects, self._repos)` to update the project list, then re-trigger the active project's detail view via the existing `set_project()` path. Cursor preservation (D-12/D-13 from Phase 14) handles the rebuild.

### Claude's Discretion

- Exact Python data structure for stale agent tracking (set of session names, dict keyed by project+value, etc.)
- Whether stale clearing is a separate method or folded into `_propagate_changes()`
- Whether `_propagate_changes()` is a new method or logic inlined into `_maybe_compute_relationships()`
- CSS specifics for `--stale` appearance (exact color values, which columns are affected)
- Whether auto-added MR objects get `open_by_default=True` or `False` (recommend False — don't auto-open browser tabs)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Propagation — PROP-01 through PROP-08: full propagation spec (note: PROP-01 and PROP-03 dropped per D-01)

### Roadmap
- `.planning/ROADMAP.md` §Phase 16 — Phase goal, success criteria

### Prior phase context
- `.planning/phases/14-relationship-foundation-badges/14-CONTEXT.md` — RelationshipIndex API, refresh coordination pattern (D-07/D-08), _save_projects_bg() pattern
- `.planning/phases/15-cross-pane-selection-sync/15-CONTEXT.md` — _is_syncing guard (suppress cross-pane sync during pane rebuilds triggered by propagation)

### No external specs
No external ADRs or design docs — requirements fully captured in decisions above and REQUIREMENTS.md.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/joy/app.py` `_maybe_compute_relationships()` — natural injection point for propagation logic; both-flags gate ensures both workers have completed
- `src/joy/app.py` `_save_projects_bg()` — established atomic TOML write path via `store.save_projects()`
- `src/joy/app.py` `self._current_worktrees` / `self._current_sessions` — live data already stored after each worker cycle (available for propagation without re-fetching)
- `src/joy/app.py` `self._rel_index` — RelationshipIndex with `worktrees_for()` / `agents_for()` / `project_for_worktree()` / `project_for_agent()` query methods
- `src/joy/app.py` `_set_worktrees()` receives `mr_data: dict | None` — dict keyed by `(repo_name, branch) -> MRInfo`; MRInfo has `.url` and `.mr_number`
- `src/joy/widgets/object_row.py` `ObjectRow` — renders each ObjectItem; accepts `item: ObjectItem`; CSS customizable via class/pseudo-class
- `src/joy/models.py` `ObjectItem` — `kind: PresetKind`, `value: str`, `label: str`, `open_by_default: bool`; `to_dict()` method controls TOML serialization

### Established Patterns
- `cursor/_rows/_update_highlight()` — cursor pattern in all panes
- `@work(thread=True)` + `call_from_thread()` — background workers; main thread mutates
- `_is_syncing` guard — suppress cross-pane sync during rebuilds (must also suppress during propagation pane rebuilds)
- `set_counts()` method on ProjectRow — precedent for pushing computed data from app to widget rows

### Integration Points
- `src/joy/models.py` `ObjectItem` — add `stale: bool = False` field (runtime only; `to_dict()` must NOT serialize it)
- `src/joy/widgets/object_row.py` `ObjectRow` — apply `--stale` CSS class when `item.stale` is True; remove when False
- `src/joy/app.py` — add `_propagate_changes(mr_data)` method, call from `_maybe_compute_relationships()`; mutates `self._projects` in-place; calls `_save_projects_bg()` once if any changes; calls `self.notify(...)` per change
- `src/joy/widgets/project_detail.py` `ProjectDetail.set_project()` — already handles full re-render; call after propagation mutations to reflect stale agent state and new MR objects

</code_context>

<specifics>
## Specific Ideas

- "Worktree is very dynamic — should no longer be an object in toml or shown in Details" — user explicitly scoped out worktree object management from propagation
- "When an MR is detected, add it as an extra object to the project, not replace the current value" — append semantics, not replace
- Status bar messages on actual mutations — brief, specific (project name + what changed)

</specifics>

<deferred>
## Deferred Ideas

- **PROP-01** (auto-remove gone worktree TOML objects) — dropped; WorktreePane handles worktree display live
- **PROP-03** (move worktree objects between projects) — dropped; same reason
- **PROP-09** (auto-remove MR when PR closes) — explicitly deferred to v1.3+ (ambiguous semantics)
- **PROP-10** (undo for auto-mutations) — deferred to v1.3+
- **SYNC-10** (sync toggle persistence) — deferred to v1.3+
- **PERF-01** (real-time file watching) — 30s refresh sufficient for v1.2

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 16-live-data-propagation*
*Context gathered: 2026-04-15*
