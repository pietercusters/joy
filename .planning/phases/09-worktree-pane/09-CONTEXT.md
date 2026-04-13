# Phase 9: Worktree Pane - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Render the output of `discover_worktrees()` (Phase 7) inside the existing `WorktreePane` stub (bottom-right of the 2x2 grid, Phase 8). The pane shows worktrees grouped under repo section headers with two-line rows (branch + indicators on line 1, abbreviated path on line 2). It is read-only: no selection cursor, no keyboard interaction beyond scrolling, no activation. Tab focus still lands on it per Phase 8 (D-10).

Out of scope: background refresh timer (Phase 10), MR/CI indicators on rows (Phase 11), surfacing per-repo git errors (requires changing Phase 7 D-02 silent-skip contract — not this phase), repo registry UI (Phase 13).

</domain>

<decisions>
## Implementation Decisions

### Data Flow & Pane API
- **D-01:** App-owned data load, push to pane. `JoyApp` gains a `@work(thread=True)` worker (`_load_worktrees`) that calls `discover_worktrees(repos, config.branch_filter)` and invokes `worktree_pane.set_worktrees(list)` via `call_from_thread`. Mirrors the existing `ProjectList.set_projects` pattern. The pane stays purely presentational.
- **D-02:** Initial load fires from `JoyApp._set_projects` (`src/joy/app.py:82`) — i.e., after projects + config have landed from `_load_data`. Rationale: we need `config.branch_filter` to pass to `discover_worktrees()`, and `_set_projects` is the existing synchronization point where config is guaranteed available. Pane shows "Loading…" placeholder until that fires.
- **D-03:** Public pane API is a single method: `WorktreePane.set_worktrees(worktrees: list[WorktreeInfo]) -> None`. Idempotent — clears existing row DOM and rebuilds from the new list. Phase 10's refresh timer will call the same method on each tick (no additional `refresh()` method, no message-based indirection).
- **D-04:** Repos list input: `WorktreePane.set_worktrees` receives only the flat `list[WorktreeInfo]` from `discover_worktrees()`. Grouping happens inside the pane (by `worktree.repo_name`). The pane does not need a separate `list[Repo]` argument — the phase goal says "repos with no active worktrees are hidden", which falls out naturally from grouping only over repos that appear in the flat list.
- **D-05:** Between first paint and the initial `set_worktrees` call, the pane displays a centered, muted "Loading…" Static — same styling as the Phase 8 "coming soon" placeholder. The placeholder widget is replaced (not just re-texted) on the first `set_worktrees` call; subsequent calls replace only row content.

### Row Visuals & Grouping
- **D-06:** Row container widget: `VerticalScroll` holding `GroupHeader(Static)` + `WorktreeRow(Static)` children. Same pattern as `ProjectDetail`. Scrolling is inherited from `VerticalScroll`; read-only (no selection cursor) is the default — no suppression logic needed.
- **D-07:** Each worktree row is a single `Static` containing a `rich.Text` with an embedded `\n`. Line 1: ` branch  [indicators]`. Line 2: `  ~/abbreviated/path`. Row `height: 2`. Single-node-per-row keeps refresh cheap for Phase 10's periodic rebuilds.
- **D-08:** Status indicators use Nerd Font glyphs (consistent with CORE-07). Dirty: ` ` (nf-fa-circle) colored to signal attention (suggest `$warning` or an orange). No-upstream: ` ` (nf-fa-cloud_off) in a dim/muted color. Clean + tracked worktrees render no indicator at all. A branch icon ` ` (nf-pl-branch, already used for the preset) optionally prefixes the branch name — align with the existing branch preset icon for consistency.
- **D-09:** Group headers reuse the `GroupHeader(Static)` pattern from `ProjectDetail` (`src/joy/widgets/project_detail.py:50-61`): bold, `$text-muted`, `padding: 0 1`, `height: 1`. Header text is the bare repo name (e.g., `joy`). No count suffix, no rule line. Consistent with the app's existing group-header vocabulary.
- **D-10:** Hide repos with zero worktrees (per phase success criterion #1). Implementation falls out of grouping over the flat `list[WorktreeInfo]` — a repo with no surviving entries after filtering contributes no `GroupHeader`.

### Ordering & Path Abbreviation
- **D-11:** Repo sections are ordered alphabetically by `Repo.name` (case-insensitive sort). Stable across sessions, independent of insertion order in `repos.toml`.
- **D-12:** Worktrees within a repo section are ordered alphabetically by `branch` name (case-insensitive). No dirty-first or default-branch-first grouping — stable positions protect muscle memory and scanning.
- **D-13:** Path abbreviation: replace a leading home-directory prefix (`Path.home()` string) with `~`. No other transformations. E.g., `/Users/pieter/Github/joy/wt/feat-x` → `~/Github/joy/wt/feat-x`. Paths outside the home directory render verbatim.
- **D-14:** When the abbreviated path is still wider than the pane, truncate in the middle with an ellipsis (e.g., `~/Github/…/long-branch-name`). Preserves both the home-relative prefix and the leaf segment, which together tell the user "which area of disk + which specific worktree." Implementation runs at row-build time against the pane's current inner width; on resize, a rebuild happens (the pane already rebuilds on every `set_worktrees` tick from Phase 10, so resize-responsiveness is a Phase 10 concern if needed).

### Empty States
- **D-15:** When `repos.toml` is empty / no repos registered (caller passes `repos=[]` to discover), pane shows a single centered muted Static: `"No repos registered. Add one via settings."`. The "via settings" hint anticipates the Phase 13 repo registry UI but remains accurate today because `DIST-02` puts all user data in `~/.joy/` where users can edit `repos.toml` directly.
- **D-16:** When repos exist but `discover_worktrees()` returns `[]` (all branches filtered out, or all repos errored and silently skipped per Phase 7 D-02), pane shows a single centered muted Static: `"No active worktrees. (filtered: {branch_filter})"` — where `{branch_filter}` is the comma-separated active filter list (e.g., `"main, testing"`). Makes the filter visible so users understand why the pane looks empty without needing to open settings.
- **D-17:** The "all repos errored" case is collapsed into D-16 — Phase 7 D-02 makes these indistinguishable at the `discover_worktrees` API boundary, and surfacing errors is Phase 10's job (last-refresh timestamp + stale-data indicators) rather than Phase 9's.
- **D-18:** Empty-state slot styling matches the Phase 8 `WorktreePane` "coming soon" stub: centered muted Static (`content-align: center middle; color: $text-muted; text-style: dim;`). The pane never looks broken — the border is always present, the message always reads as intentional.

### Claude's Discretion
- Exact hex/themed color for the dirty indicator (pick something visible on both the dark and light Textual palettes; `$warning` is a reasonable starting point).
- Whether the branch-icon prefix on line 1 is included or omitted — prefer consistency with the existing `PresetKind.BRANCH` icon (` `) to reinforce the app's visual vocabulary, but drop it if rows feel too busy.
- Middle-truncation algorithm (where to cut, how many segments to preserve on each side). Simple rule: keep the `~/<first-segment>/…/<last-segment>` shape when possible.
- Module layout — rows can live inline in `worktree_pane.py` or be extracted to a `worktree_row.py` sibling. Prefer inline unless the file grows past ~150 lines.
- Internal CSS ids / class names for row styling (suggest `.worktree-row`, `.group-header`, `.empty-state`).
- Whether to keep or reshuffle the `WorktreePane.BINDINGS = []` line (currently empty — leave as-is; the pane remains focusable per Phase 8 D-10 but has no keybindings).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope
- `.planning/ROADMAP.md` §"Phase 9: Worktree Pane" (lines 81-88) — Goal, requirements WKTR-02/WKTR-03/WKTR-10, success criteria (grouping + hidden empty repos + two-line rows + read-only), UI hint
- `.planning/PROJECT.md` — Core value (instant artifact view), v1.1 status, snappy/minimal constraint, macOS-only platform

### Prior phases this phase builds on
- `.planning/phases/07-git-worktree-discovery/07-CONTEXT.md` — D-01 (exact-match branch filter), D-02 (silent skip on errors — governs the "all errored" empty state collapse)
- `.planning/phases/08-4-pane-layout/08-CONTEXT.md` — D-08/D-09/D-10 (WorktreePane stub as focusable bordered container with `border_title = "Worktrees"`), D-11/D-12 (focus-border styling)

### Existing code this phase extends
- `src/joy/widgets/worktree_pane.py` — Current stub `WorktreePane(Widget, can_focus=True)` with border CSS. Replace the "coming soon" body while keeping the outer class shape, id (`worktrees-pane`), focus rules, and `border_title`.
- `src/joy/widgets/project_detail.py` §`GroupHeader` (lines 50-61) — The bold/muted/height:1 header pattern to reuse for repo section headers.
- `src/joy/widgets/object_row.py` — Nerd Font icon vocabulary (`PRESET_ICONS`), single-Static-with-`rich.Text` row pattern.
- `src/joy/app.py` §`JoyApp._load_data` + `_set_projects` (lines 69-90) — The worker + `call_from_thread` pattern to mirror for `_load_worktrees`, and the call site (`_set_projects`) where the new worker fires.
- `src/joy/worktrees.py` — `discover_worktrees(repos, branch_filter) -> list[WorktreeInfo]` — the data source this phase consumes.
- `src/joy/models.py` — `WorktreeInfo(repo_name, branch, path, is_dirty, has_upstream)` dataclass, `Config.branch_filter` default `["main", "testing"]`, `Repo` list.
- `src/joy/store.py` — `load_repos(path=REPOS_PATH) -> list[Repo]`, `load_config()` — how the app already gets the inputs this phase needs.

### Testing baseline (regression)
- `tests/test_worktrees.py` — 16 tests from Phase 7. Must remain green.
- `tests/test_app.py` (if present) — app-level tests must keep passing.
- Full suite (188+ tests at end of Phase 8) must remain green.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `WorktreePane` stub (`src/joy/widgets/worktree_pane.py`) — bordered focusable container with `border_title = "Worktrees"` and accent-on-focus border already in place; this phase fills the body.
- `GroupHeader(Static)` from `ProjectDetail` — drop-in repo section header widget (bold, `$text-muted`, `padding: 0 1`).
- `discover_worktrees()` (`src/joy/worktrees.py`) — pure-logic data source; takes `list[Repo]` + `branch_filter`, returns `list[WorktreeInfo]` with silent-skip on errors.
- `WorktreeInfo` dataclass (`src/joy/models.py:136`) — has everything the pane needs: `repo_name`, `branch`, `path`, `is_dirty`, `has_upstream`.
- Nerd Font icon constants in `object_row.py:PRESET_ICONS` — includes branch icon (` `) and folder icon (` `); new icons needed (dirty-circle, cloud-off) follow the same constant-definition pattern.
- `@work(thread=True)` + `call_from_thread` pattern (`app.py:_load_data` + `_set_projects`) — exact template for `_load_worktrees` + `set_worktrees`.

### Established Patterns
- Inline CSS on widget class via `DEFAULT_CSS = """..."""` — no external `.tcss` files (per Phase 8 convention).
- One widget class per file in `src/joy/widgets/`.
- Pure data in `models.py`, I/O in other modules — this phase adds no new models; it consumes `WorktreeInfo` only.
- Background thread for data load via `@work(thread=True)` + `call_from_thread` — keeps TUI responsive during git subprocess calls.
- `set_X(list)` idempotent methods for pane population (`ProjectList.set_projects`, now `WorktreePane.set_worktrees`).
- Rows as single `Static` with `rich.Text` (`ObjectRow`) — extend to two lines via `\n` in the rich text.
- Phase 7 silent-skip contract (D-02) — discover_worktrees never raises; all error handling happens at the caller layer (this phase does not change that).

### Integration Points
- `JoyApp.compose()` at `app.py:58-67` — no changes; `WorktreePane(id="worktrees-pane")` is already mounted.
- `JoyApp._set_projects` at `app.py:82-89` — extension point: after setting projects, also kick off `self._load_worktrees()` worker. Config is guaranteed loaded here.
- New `JoyApp._load_worktrees` (new method, thread worker) — calls `load_repos()` + `discover_worktrees(repos, self._config.branch_filter)`, then `call_from_thread(self._set_worktrees, list)`.
- New `JoyApp._set_worktrees(list[WorktreeInfo])` — thin dispatcher that calls `self.query_one(WorktreePane).set_worktrees(list)`.
- `WorktreePane.set_worktrees(list[WorktreeInfo])` — new public method; the sole contract between the app and the pane. Phase 10's refresh timer will call this too.
- `src/joy/widgets/worktree_pane.py` — body fill-in (rows, headers, empty states); keep the outer class shape from Phase 8.
- `src/joy/widgets/__init__.py` — `WorktreePane` already exported; no import changes needed.

</code_context>

<specifics>
## Specific Ideas

- Visual language should feel like lazygit / k9s panes the user already praised in Phase 8 — bordered pane, accent border on focus, clear section breaks, dense-but-not-cluttered rows.
- Two-line row should read as "branch is the headline, path is the address" — line 1 is the identity you scan for, line 2 is the navigation info.
- Nerd Font icons are a load-bearing part of the app's look (CORE-07) — reuse the existing icon vocabulary rather than inventing ASCII markers.
- "Empty" should always look intentional, never broken — matches the Phase 8 "coming soon" precedent.
- Refresh-cheapness matters: Phase 10 will rebuild this pane on a timer. Keep per-row DOM small (single Static per worktree row) so polling stays snappy.

</specifics>

<deferred>
## Deferred Ideas

- Background refresh timer + last-refresh timestamp + stale-age indicator — Phase 10.
- MR/CI status badges on rows + author/last-commit on the second line — Phase 11.
- Surfacing per-repo git errors (which repo failed, why) — requires changing Phase 7 D-02's silent-skip contract; out of scope here.
- Repo registry UI (add/edit/remove repos from settings) — Phase 13 (FLOW-03 territory).
- Selection cursor / activating a worktree row with Enter to open it in the IDE — explicitly non-goal per success criterion #3 (read-only pane). The existing `PresetKind.WORKTREE` preset on projects covers per-project worktree opening.
- Per-worktree Claude/terminal session indicator — Phase 12 (TERM territory).
- Groupable-by-repo projects pane counterpart — Phase 13 (FLOW-01).
- Resize-responsive middle-truncation recomputation — Phase 10 reruns `set_worktrees` on its timer, which handles this incidentally; a dedicated resize handler is future work if needed.

</deferred>

---

*Phase: 09-worktree-pane*
*Context gathered: 2026-04-13*
