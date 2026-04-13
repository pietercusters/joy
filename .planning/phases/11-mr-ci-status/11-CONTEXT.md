# Phase 11: MR & CI Status - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the existing `WorktreePane` rows to display open MR/PR status and CI pipeline results per branch, fetched via `gh` (GitHub CLI) and `glab` (GitLab CLI). When a branch has an open MR, line 1 gains the MR number + open/draft icon + CI status badge; line 2 switches from the abbreviated path to MR author + last commit (short hash + message). When no MR exists for a branch, the row is unchanged from Phase 9 (path on line 2).

Out of scope: repo registry UI (Phase 13), iTerm2 terminal pane (Phase 12), surfacing per-repo git errors (Phase 7 D-02 contract unchanged), interactive row activation (read-only pane per Phase 9).

</domain>

<decisions>
## Implementation Decisions

### Row Layout
- **D-01:** Line 2 is context-sensitive: shows `@author  hash commit-msg` when MR data is available for that branch, and `  ~/abbreviated/path` (current behavior) when no MR exists. The path is not shown alongside MR info — MR context is more useful at a glance, and the branch name + MR number provides sufficient orientation.
- **D-02:** Line 1 layout (when MR): `  branch  !N  [open-icon | draft-icon]  [CI-icon]  [dirty]  [no-upstream]`. The MR number, MR state icon, and CI icon appear between the branch name and the existing dirty/upstream indicators. When no MR: existing Phase 9 layout unchanged.
- **D-03:** `WorktreeRow.build_content()` receives extended arguments (or a richer info object) — the row is responsible for rendering both the no-MR and MR variants based on what data is present. Keep single `Static` per row for rebuild-cheapness (Phase 9 D-07 contract).

### MR Status Vocabulary
- **D-04:** Open vs. Draft are visually distinct: open MRs use a colored icon (e.g., `nf-cod-git_pull_request` in green/accent); draft MRs use a dim icon (e.g., `nf-cod-git_pull_request_draft` in muted color). Draft communicates "not ready to merge" at a glance.
- **D-05:** CI status shows three terminal states: ✓ pass (green), ✗ fail (red), ● pending/running (yellow). When no CI data is available, the CI slot is blank — no placeholder icon. Nerd Font glyph constants follow the same pattern as `ICON_DIRTY` / `ICON_NO_UPSTREAM` in `worktree_pane.py`.

### Fetch Architecture
- **D-06:** MR/CI data is fetched in the same `_load_worktrees()` background thread, sequentially after `discover_worktrees()` completes. `fetch_mr_data(repos, worktrees)` runs in the same worker and returns a mapping of `(repo_name, branch) -> MRInfo | None`. The merged result is passed to `set_worktrees()`. No second worker, no timer.
- **D-07:** `fetch_mr_data()` lives in a new module `src/joy/mr_status.py`. It dispatches to `gh` for GitHub repos and `glab` for GitLab repos (using `Repo.forge` to route). Repos with `forge: unknown` are silently skipped — no MR fetch attempt.
- **D-08:** New `MRInfo` dataclass in `models.py` (alongside `WorktreeInfo`, per established pattern): `mr_number: int`, `is_draft: bool`, `ci_status: str | None` (values: `"pass"`, `"fail"`, `"pending"`, `None`), `author: str`, `last_commit_hash: str`, `last_commit_msg: str`. Optional MR enrichment on top of existing `WorktreeInfo` — not merged into `WorktreeInfo` itself.

### Graceful Degradation
- **D-09:** When MR fetch fails for any reason (CLI not installed, not authenticated, rate-limited, network error), the affected branches render without MR data: path stays on line 2, no MR badges on line 1. Consistent with Phase 7 D-02 silent-skip pattern.
- **D-10:** When **all** repos fail MR fetch (total failure, not partial), append a brief note to `WorktreePane.border_title` — e.g., `"Worktrees  ⚠ gh: not auth"`. Same mechanism as Phase 10 D-03 stale-warning. Partial failures (some repos get MR data, some don't) are silent — partial data is fine.
- **D-11:** MR fetch errors are detected at the `fetch_mr_data()` boundary — a try/except per repo, returning `None` for that repo's branches on any exception. The module never raises; callers get partial or empty results safely.

### Claude's Discretion
- Exact Nerd Font codepoints for open MR icon, draft MR icon, CI pass/fail/pending icons (suggest `\ue728` nf-dev-git_pull_request or `\ueaab` nf-cod-git_pull_request for open; check Nerd Font 3.x codepoints for draft variant).
- `fetch_mr_data()` internal implementation: `subprocess.run(["gh", "pr", "list", "--json", ...])` vs. `gh pr view` per branch — choose whatever yields the needed fields in one call per repo rather than one per branch.
- Whether `MRInfo` gets a convenience property `ci_icon` / `mr_icon` or the pane builds those strings inline.
- Author display format: `@handle` (from `gh pr list --json author`), or `Display Name` — prefer `@handle` for brevity.
- Commit message truncation: truncate `last_commit_msg` to fit available line width minus the hash prefix (e.g., `abc1234 fix: description` truncated to pane width).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope
- `.planning/ROADMAP.md` §"Phase 11: MR & CI Status" — Goal, requirements WKTR-07, WKTR-08, WKTR-09, success criteria (3 items)
- `.planning/PROJECT.md` — Core value, snappy/minimal constraint, macOS-only platform

### Prior phases this phase extends
- `.planning/phases/09-worktree-pane/09-CONTEXT.md` — D-07 (single Static per row, two-line rich.Text), D-08 (Nerd Font glyph vocabulary), D-03 (`set_worktrees()` is the sole public API between app and pane)
- `.planning/phases/10-background-refresh-engine/10-CONTEXT.md` — D-07 (`_load_worktrees()` is the sequential worker; Phase 11 extends it), D-03/D-04 (stale detection pattern; border_title note follows the same mechanism)
- `.planning/phases/07-git-worktree-discovery/07-CONTEXT.md` — D-02 (silent-skip on errors; MR fetch follows the same contract)

### Existing code this phase modifies
- `src/joy/app.py` — `JoyApp._load_worktrees()`: add `fetch_mr_data(repos, worktrees)` call after discover; `JoyApp._set_worktrees()`: pass MRInfo map to `set_worktrees()`; detect total MR failure for border_title note (D-10)
- `src/joy/widgets/worktree_pane.py` — `WorktreePane.set_worktrees()`: accept MRInfo map; pass to `WorktreeRow`; `WorktreeRow.build_content()`: extend for MR/no-MR variants (D-01–D-03); `set_refresh_label()`: extend to accept MR failure flag for border_title note (D-10)
- `src/joy/models.py` — add `MRInfo` dataclass (D-08)

### New module
- `src/joy/mr_status.py` — new module with `fetch_mr_data(repos: list[Repo], worktrees: list[WorktreeInfo]) -> dict[tuple[str, str], MRInfo]` (D-06, D-07, D-11). Uses `subprocess.run(["gh", ...])` / `subprocess.run(["glab", ...])` per repo.

### Testing baseline (regression)
- Full test suite must remain green
- `tests/test_worktrees.py` — 16 Phase 7 tests must stay green
- `tests/test_worktree_pane.py` — Phase 9 pane unit + integration tests must stay green

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `WorktreeRow.build_content(branch, is_dirty, has_upstream, display_path) -> Text` (`src/joy/widgets/worktree_pane.py`) — static method; extend signature to accept optional `MRInfo | None`. When `None`, existing two-line path render. When present, MR two-line render.
- `ICON_DIRTY`, `ICON_NO_UPSTREAM`, `ICON_BRANCH` constants in `worktree_pane.py` — add `ICON_MR_OPEN`, `ICON_MR_DRAFT`, `ICON_CI_PASS`, `ICON_CI_FAIL`, `ICON_CI_PENDING` following the same constant pattern.
- `JoyApp._load_worktrees()` worker (`src/joy/app.py:111-124`) — existing `@work(thread=True)` with try/except; MR fetch slots in after `discover_worktrees()` call, same thread.
- `JoyApp._set_worktrees()` (`src/joy/app.py`) — already dispatches to `WorktreePane.set_worktrees()`; extend to pass MRInfo map through.
- `WorktreePane.set_refresh_label(timestamp, stale)` — extend with `mr_error: bool` parameter to append the border_title note (D-10).
- `subprocess.run(["gh", ...], capture_output=True, text=True)` pattern — same as `store.py:get_remote_url` and `worktrees.py` git calls; no new subprocess pattern needed.
- `Repo.forge` field — already `"github"` / `"gitlab"` / `"unknown"` from Phase 6 `detect_forge()`. Routes `gh` vs `glab` CLI dispatch in D-07.

### Established Patterns
- Pure data in `models.py`, I/O in separate modules — `MRInfo` in models.py, fetch logic in `mr_status.py`.
- `subprocess.run(..., capture_output=True, text=True, check=False)` — inspect returncode, never raises.
- Try/except per-unit silent-skip — `worktrees.py:discover_worktrees` already does this per repo.
- `@work(thread=True)` + `call_from_thread` — no changes to threading model needed.
- Inline `DEFAULT_CSS` on widgets — no external `.tcss` files.

### Integration Points
- `JoyApp._load_worktrees()` at `app.py:111` — add `mr_data = fetch_mr_data(repos, worktrees)` inside the try block, after `worktrees = discover_worktrees(...)`. Catch exceptions from `fetch_mr_data` into `mr_failed: bool`.
- `JoyApp._set_worktrees(worktrees, repo_count, branch_filter)` — add `mr_data: dict` and `mr_failed: bool` parameters; forward to `set_worktrees()` and `set_refresh_label()`.
- `WorktreePane.set_worktrees(worktrees, *, repo_count, branch_filter)` — add `mr_data: dict[tuple[str,str], MRInfo] = {}` parameter; look up each worktree's MRInfo before constructing `WorktreeRow`.
- `WorktreeRow.__init__` and `build_content()` — accept `mr_info: MRInfo | None = None`.

</code_context>

<specifics>
## Specific Ideas

- Row preview confirmed by user:
  - With MR open:  `  branch  !42 • ✓  [dirty]` / `  @pieter  abc1234 fix: login redirect`
  - With MR draft: `  branch  !43 ○ –` / `  @pieter  def5678 wip: new auth flow`
  - No MR:         `  branch  [dirty]` / `  ~/Github/joy/wt/feature` (unchanged)
- Border_title failure note confirmed: `"Worktrees  ⚠ gh: not auth"` when all repos fail MR fetch.
- CI vocabulary confirmed: ✓ green (pass), ✗ red (fail), ● yellow (pending/running), blank when no CI data.
- Open vs draft distinction confirmed: different icons + color (open = accent/green, draft = muted/dim).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 11-mr-ci-status*
*Context gathered: 2026-04-13*
