# Quick Task 260506-rc1: Add MR Pane + Placeholder Pane - Research

**Researched:** 2026-05-06
**Domain:** GitHub/GitLab CLI batch MR fetching, Textual CSS grid expansion
**Confidence:** HIGH

## Summary

The task requires expanding the joy TUI from a 2x2 to a 3x2 grid, adding an MR status pane (top-right) and a placeholder pane (bottom-right). The critical path is refactoring MR fetching to use batch `--author=@me` calls that feed both the existing worktree pane badges AND the new MR pane, plus adding `reviewDecision` / `detailed_merge_status` fields for review status.

All needed CLI fields are available. GitHub `gh pr list --json` supports `reviewDecision` natively. GitLab `glab mr list --output json` includes `detailed_merge_status` which covers approval state. Textual CSS grid expansion from 2x2 to 3x2 is straightforward -- `grid-size: 3 2` with `grid-columns` for proportional sizing.

**Primary recommendation:** Refactor `mr_status.py` to return a richer result keyed by `(repo_name, branch)` that includes `reviewDecision`/approval status, then add a second fetch pass per repo for `--reviewer=@me` / `--search "review-requested:@me"` MRs. Share the batch result dict between worktree pane and MR pane via `app._current_mr_data`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Expand from 2x2 to 3x2 grid (3 columns, 2 rows)
- Top row: Project List | Project Detail | MR Pane
- Bottom row: Terminals | Worktrees | Placeholder
- Single batch call per repo: `gh pr list --author=@me` + `glab mr list --author=@me`, plus one reviewer query per repo
- Batch results feed BOTH the MR pane AND the worktree pane (shared data)
- Fallback: for active project branches with no MR in batch result, do per-branch query for leftovers
- All fetching in existing background worker thread
- Parallel fetching across repos
- Summary status only (overall approval state per MR): approved, changes requested, commented, pending
- No per-reviewer breakdown

### Claude's Discretion
- Internal data model structure for the new MR pane data
- Placeholder pane implementation details (minimal static widget)
- Exact CLI flags for GitHub/GitLab reviewer status queries
</user_constraints>

## GitHub CLI: `gh pr list` Batch Fetching

### Author's Open PRs (batch)

```bash
gh pr list -R OWNER/REPO --author @me --state open \
  --json number,headRefName,isDraft,statusCheckRollup,url,reviewDecision,title \
  --limit 100
```

**Available fields verified on live repo:** [VERIFIED: gh pr list --json output on pietercusters/joy]

Key fields for the MR pane:
| Field | Type | Values | Purpose |
|-------|------|--------|---------|
| `reviewDecision` | string | `APPROVED`, `CHANGES_REQUESTED`, `REVIEW_REQUIRED`, `""` (empty) | Review status summary |
| `title` | string | PR title text | Display in MR pane |
| `number` | int | PR number | Display + URL construction |
| `isDraft` | bool | true/false | Draft badge |
| `statusCheckRollup` | array | Check objects with `status`/`conclusion` | CI status (existing mapping works) |
| `headRefName` | string | Branch name | Matching to worktrees |
| `url` | string | Full PR URL | Opening in browser |

[VERIFIED: GitHub GraphQL API] `reviewDecision` enum has exactly 3 values:
- `APPROVED` -- PR has received an approving review
- `CHANGES_REQUESTED` -- Changes have been requested
- `REVIEW_REQUIRED` -- Review required before merge (no reviews yet, or not enough)
- Empty string `""` -- No review requirement configured

### Review-Requested PRs (separate query)

```bash
gh pr list -R OWNER/REPO --state open \
  --search "review-requested:@me" \
  --json number,headRefName,isDraft,statusCheckRollup,url,reviewDecision,title \
  --limit 100
```

[VERIFIED: gh pr list --search on pietercusters/joy] The `--search` flag with `review-requested:@me` returns PRs where the current user is a requested reviewer. Cannot combine `--author` with `--search` in the same call, so this needs a second call per repo.

**Alternative:** `--search "user-review-requested:@me"` also works (documented in GitHub search syntax). Both produce the same result.

## GitLab CLI: `glab mr list` Batch Fetching

### Author's Open MRs (batch)

```bash
glab mr list -R REMOTE_URL --author @me --output json --per-page 100
```

**Key fields from JSON output:** [VERIFIED: glab mr list on gitlab.com/gitlab-org/gitlab]

| Field | Type | Values | Purpose |
|-------|------|--------|---------|
| `detailed_merge_status` | string | See below | Approval/merge readiness |
| `title` | string | MR title | Display |
| `iid` | int | MR number | Display |
| `draft` | bool | true/false | Draft badge |
| `source_branch` | string | Branch name | Matching to worktrees |
| `web_url` | string | Full MR URL | Opening in browser |

**`detailed_merge_status` values relevant to approval:** [CITED: docs.gitlab.com/api/merge_requests/]
- `not_approved` -- Approvals still needed
- `ci_must_pass` -- Waiting on CI
- `ci_still_running` -- CI in progress
- `mergeable` -- Ready to merge (implies approved if approval required)
- `conflict` -- Merge conflicts exist
- `discussions_not_resolved` -- Open discussions block merge
- `checking` -- Git testing merge possibility

**CI status**: NOT included in `glab mr list` JSON. The existing `_fetch_glab_ci_status()` per-branch call via `glab ci get` remains necessary. For the new MR pane, we can map `detailed_merge_status` to a simpler status:
- `ci_still_running` -> CI pending
- `ci_must_pass` -> CI required (treat as pending)
- Other values don't directly indicate CI pass/fail

### Reviewer-Requested MRs (separate query)

```bash
glab mr list -R REMOTE_URL --reviewer @me --output json --per-page 100
```

[VERIFIED: glab mr list --help] The `--reviewer` flag is a first-class option (not a search string). Returns MRs where current user is an assigned reviewer.

## Batch vs Per-Branch Efficiency

### Current Approach (per-branch)
The existing `mr_status.py` already does batch calls per repo (one `gh pr list` or `glab mr list` per repo, not per branch). It filters results in Python by checking `branch in active_branches`. The only per-branch call is `glab ci get` for GitLab CI status.

### Proposed Refactoring
The refactoring is minimal because the current code is already batch-oriented:

1. **Add `--author @me` to GitHub calls** -- Currently fetches ALL open PRs and filters by branch. Adding `--author @me` would reduce results but miss PRs authored by others on the same branches. Decision: keep fetching all open PRs for worktree badges, but mark authored ones for the MR pane.

2. **Add `reviewDecision` and `title` to `--json` fields** -- Just extend the field list in the existing call.

3. **Add a second call per repo for reviewer MRs** -- `--search "review-requested:@me"` (GitHub) / `--reviewer @me` (GitLab). These are the user's review queue, not their authored MRs.

4. **Return structure**: Instead of just `dict[(repo_name, branch) -> MRInfo]`, return a richer structure that also includes all authored MRs and review-requested MRs regardless of whether they match a worktree branch.

### Recommended Data Model

```python
@dataclass
class MRDetail:
    """Extended MR info for the MR pane."""
    mr_number: int
    title: str
    is_draft: bool
    ci_status: str | None  # "pass" | "fail" | "pending" | None
    review_status: str | None  # "approved" | "changes_requested" | "review_required" | None
    url: str = ""
    repo_name: str = ""
    branch: str = ""
    is_review_request: bool = False  # True if this MR is in user's review queue

@dataclass
class BatchMRResult:
    """Complete MR fetch result for all repos."""
    by_branch: dict[tuple[str, str], MRInfo]  # existing format for worktree pane
    authored: list[MRDetail]  # all authored MRs for MR pane
    review_requests: list[MRDetail]  # MRs where user is reviewer
```

This preserves backward compatibility -- `by_branch` is the same dict the worktree pane already consumes.

## Textual Grid: 2x2 to 3x2 Expansion

[VERIFIED: Context7 Textual docs + existing app.py CSS]

### Current CSS
```css
#pane-grid {
    grid-size: 2 2;
    grid-rows: 1fr 1fr;
    grid-columns: 1fr 1fr;
}
```

### Proposed CSS
```css
#pane-grid {
    grid-size: 3 2;
    grid-rows: 1fr 1fr;
    grid-columns: 1fr 1fr 1fr;
}
```

Children are placed left-to-right, top-to-bottom in source order. With 6 children in a 3x2 grid:
- Position 1 (top-left): ProjectList
- Position 2 (top-center): ProjectDetail
- Position 3 (top-right): MRPane
- Position 4 (bottom-left): TerminalPane
- Position 5 (bottom-center): WorktreePane
- Position 6 (bottom-right): PlaceholderPane

### Gotchas and Considerations

1. **Minimum width**: With 3 columns in an 80-char terminal, each column gets ~26 chars. This is tight. Consider using `grid-columns: 1fr 2fr 1fr` to give project detail more space, or accept that users need >= 120-width terminals for comfortable use. [ASSUMED]

2. **Tab order**: Textual's Tab/Shift+Tab cycles through focusable widgets in DOM order. Adding two new widgets after the Grid's existing 4 means Tab order becomes: ProjectList -> ProjectDetail -> MRPane -> TerminalPane -> WorktreePane -> PlaceholderPane. The placeholder should likely NOT be focusable (`can_focus=False`). [VERIFIED: existing pane pattern uses `can_focus=True` on Widget subclass]

3. **Border styling**: Each existing pane has `border: solid $surface-lighten-2` and `:focus-within { border: solid $accent }`. New panes should replicate this pattern.

4. **`on_descendant_focus` in app.py**: Needs updating to handle the new pane IDs for subtitle and hint bar updates.

## Integration Pattern: Shared MR Data

The cleanest pattern (matching existing codebase conventions):

1. `_load_worktrees()` already fetches MR data and stores it in `app._current_mr_data`
2. Extend `_current_mr_data` to include the full `BatchMRResult` (or just add `_current_authored_mrs` and `_current_review_requests` as separate lists)
3. After `_set_worktrees()` completes, call `mr_pane.set_mr_data(authored, review_requests)`
4. The MR pane is a pure display widget -- no coupling to worktree pane

**Key principle**: The app.py background worker is the single data owner. Both panes receive their data via `set_*()` push methods, exactly like `WorktreePane.set_worktrees()` and `TerminalPane.set_sessions()`.

## Mapping Review Status to Display

### GitHub
| `reviewDecision` | Display | Icon suggestion |
|-------------------|---------|-----------------|
| `APPROVED` | "Approved" | green check or similar |
| `CHANGES_REQUESTED` | "Changes" | red/yellow indicator |
| `REVIEW_REQUIRED` | "Pending" | dim/neutral indicator |
| `""` (empty) | None | no indicator |

### GitLab
| `detailed_merge_status` | Maps to | Rationale |
|--------------------------|---------|-----------|
| `not_approved` | "Pending" | Needs approval |
| `mergeable` | "Approved" | All checks passed |
| `ci_still_running` | "Pending" | CI not done yet |
| `discussions_not_resolved` | "Changes" | Treat like changes requested |
| Others | None | Don't show review status |

## Common Pitfalls

### Pitfall 1: `gh pr list --author @me` misses PRs on worktree branches authored by others
**What goes wrong:** If the batch call uses `--author @me`, worktree badges for PRs authored by collaborators disappear.
**How to avoid:** Keep the existing "all open PRs" fetch for worktree badges. The `--author @me` is only for the MR pane's "My MRs" section. This means the GitHub call should NOT add `--author @me` -- instead filter in Python.

### Pitfall 2: `glab mr list` doesn't include CI pipeline status
**What goes wrong:** Assuming `glab mr list` JSON has pipeline data like GitHub's `statusCheckRollup`.
**How to avoid:** Keep the existing `_fetch_glab_ci_status()` per-branch call. For MRs not matching a worktree branch, use `detailed_merge_status` as a rough CI proxy (ci_still_running = pending).

### Pitfall 3: Terminal width with 3 columns
**What goes wrong:** 80-char terminals make each pane ~26 chars wide -- too narrow for meaningful MR titles.
**How to avoid:** Either set minimum width expectations (120 chars) or use `min-width` CSS. Truncate MR titles aggressively in the MR pane.

### Pitfall 4: Review-requested query doubles API calls
**What goes wrong:** Adding a second `gh pr list --search "review-requested:@me"` per repo doubles the number of API calls.
**How to avoid:** This is acceptable -- we go from 1 call/repo to 2 calls/repo. With typical 1-3 repos, this is 2-6 total calls. The `timeout=15` per call is already set.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Users typically have >= 120-char terminal width | Grid Expansion | Panes would be too narrow at 80 chars; could add min-width constraint |
| A2 | `glab mr list --reviewer @me` correctly returns MRs where user is reviewer | GitLab CLI | Would need `glab api` fallback; low risk since flag is documented |

## Sources

### Primary (HIGH confidence)
- `gh pr list --json` field list -- verified live on pietercusters/joy repo
- `gh api graphql` -- verified PullRequestReviewDecision enum (3 values)
- `glab mr list --output json` -- verified live on gitlab.com/gitlab-org/gitlab
- Context7 /websites/textual_textualize_io -- grid-size, grid-columns CSS docs
- Existing codebase: app.py, mr_status.py, worktree_pane.py, models.py

### Secondary (MEDIUM confidence)
- [GitLab MR API docs](https://docs.gitlab.com/api/merge_requests/) -- detailed_merge_status values
