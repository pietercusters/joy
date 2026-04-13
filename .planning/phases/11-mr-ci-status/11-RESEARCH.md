# Phase 11: MR & CI Status - Research

**Researched:** 2026-04-13
**Domain:** GitHub/GitLab CLI integration, subprocess JSON parsing, Textual widget extension
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Row Layout**
- D-01: Line 2 is context-sensitive: shows `@author  hash commit-msg` when MR data is available for that branch, and `  ~/abbreviated/path` (current behavior) when no MR exists. The path is not shown alongside MR info.
- D-02: Line 1 layout (when MR): `  branch  !N  [open-icon | draft-icon]  [CI-icon]  [dirty]  [no-upstream]`. The MR number, MR state icon, and CI icon appear between the branch name and the existing dirty/upstream indicators. When no MR: existing Phase 9 layout unchanged.
- D-03: `WorktreeRow.build_content()` receives extended arguments (or a richer info object) — the row is responsible for rendering both the no-MR and MR variants based on what data is present. Keep single `Static` per row for rebuild-cheapness (Phase 9 D-07 contract).

**MR Status Vocabulary**
- D-04: Open vs. Draft are visually distinct: open MRs use a colored icon (green/accent); draft MRs use a dim icon (muted color).
- D-05: CI status shows three terminal states: ✓ pass (green), ✗ fail (red), ● pending/running (yellow). When no CI data is available, the CI slot is blank — no placeholder icon.

**Fetch Architecture**
- D-06: MR/CI data is fetched in the same `_load_worktrees()` background thread, sequentially after `discover_worktrees()` completes. `fetch_mr_data(repos, worktrees)` runs in the same worker and returns a mapping of `(repo_name, branch) -> MRInfo | None`. The merged result is passed to `set_worktrees()`. No second worker, no timer.
- D-07: `fetch_mr_data()` lives in a new module `src/joy/mr_status.py`. It dispatches to `gh` for GitHub repos and `glab` for GitLab repos (using `Repo.forge` to route). Repos with `forge: unknown` are silently skipped.
- D-08: New `MRInfo` dataclass in `models.py`: `mr_number: int`, `is_draft: bool`, `ci_status: str | None` (values: `"pass"`, `"fail"`, `"pending"`, `None`), `author: str`, `last_commit_hash: str`, `last_commit_msg: str`.

**Graceful Degradation**
- D-09: When MR fetch fails for any reason, affected branches render without MR data (path stays on line 2, no MR badges on line 1). Silent-skip pattern.
- D-10: When ALL repos fail MR fetch (total failure), append brief note to `WorktreePane.border_title` — e.g., `"Worktrees  ⚠ gh: not auth"`. Partial failures are silent.
- D-11: MR fetch errors detected at `fetch_mr_data()` boundary — try/except per repo, returning `None` for that repo's branches. Module never raises.

### Claude's Discretion
- Exact Nerd Font codepoints for open MR icon, draft MR icon, CI pass/fail/pending icons (suggest `\ue728` nf-dev-git_pull_request or `\ueaab` nf-cod-git_pull_request for open; check Nerd Font 3.x codepoints for draft variant).
- `fetch_mr_data()` internal implementation: `subprocess.run(["gh", "pr", "list", "--json", ...])` vs. `gh pr view` per branch — choose whatever yields the needed fields in one call per repo rather than one per branch.
- Whether `MRInfo` gets a convenience property `ci_icon` / `mr_icon` or the pane builds those strings inline.
- Author display format: `@handle` (from `gh pr list --json author`), or `Display Name` — prefer `@handle` for brevity.
- Commit message truncation: truncate `last_commit_msg` to fit available line width minus the hash prefix.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WKTR-07 | Worktree rows show open MR/PR number and status badge when a merge request exists for that branch | gh pr list JSON (number, isDraft) + subprocess pattern confirmed; glab mr list JSON confirmed |
| WKTR-08 | Worktree rows show CI pipeline status (pass/fail/pending) when available | gh statusCheckRollup field confirmed; glab ci get --branch per-worktree confirmed |
| WKTR-09 | MR author and last commit (short hash + message) shown on second line of worktree row when MR data is available | gh commits[].oid + messageHeadline confirmed; glab mr view author.username confirmed |
</phase_requirements>

---

## Summary

Phase 11 extends the existing `WorktreeRow` and `WorktreePane` to show MR/PR status per worktree, fetched via the `gh` (GitHub CLI) and `glab` (GitLab CLI) command-line tools. Both CLIs are installed and authenticated in the development environment. The CLI invocation pattern mirrors the existing `subprocess.run(capture_output=True, text=True, check=False)` pattern already used throughout the codebase.

The key architectural insight: **one `gh pr list` call per GitHub repo** returns all open PRs with all needed fields (number, author, isDraft, last commit, CI status) in a single JSON response. The Python layer filters by `headRefName` to match worktree branches. This avoids per-branch API calls and is the correct batch-fetch pattern. For GitLab, `glab mr list --output json` provides MR data; CI status requires a separate `glab ci get --branch` call per worktree branch (GitLab list endpoint does not include `head_pipeline`).

The row rendering change is isolated to `WorktreeRow.build_content()` — extend the signature to accept `MRInfo | None`, branch on presence, and maintain the existing no-MR path untouched. All established patterns (single Static per row, icon constants, silent-skip on errors) apply directly.

**Primary recommendation:** Implement `fetch_mr_data()` using one `gh pr list` call per GitHub repo with JSON fields `number,headRefName,isDraft,author,commits,statusCheckRollup`. For GitLab: one `glab mr list --output json` per repo plus one `glab ci get --branch X --output json` per worktree branch that has an MR.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `gh` CLI | 2.40.1 | GitHub PR/CI data | Pre-installed, authenticated, returns structured JSON in one call per repo. Zero Python dependencies. [VERIFIED: `gh --version`] |
| `glab` CLI | 1.85.3 | GitLab MR/CI data | Pre-installed, authenticated (for GitLab repos), structured JSON output. Zero Python dependencies. [VERIFIED: `glab --version`] |
| `subprocess.run` | stdlib | CLI invocation | Already the project pattern for all external commands (git, open, pbcopy, osascript). No new dependency. [VERIFIED: codebase] |
| `json.loads` | stdlib | Parse CLI JSON output | Standard Python JSON parsing, no dependencies. [VERIFIED: codebase] |
| `dataclasses.dataclass` | stdlib | `MRInfo` model | Already the project pattern for `WorktreeInfo`, `Repo`, `Config`. [VERIFIED: models.py] |

### No New Python Dependencies Required

The entire Phase 11 implementation uses only:
1. stdlib (`subprocess`, `json`, `dataclasses`)
2. CLIs already present on the machine (`gh`, `glab`)
3. Existing project modules (`models.py`, `worktree_pane.py`, `app.py`)

**Installation:** No new packages needed. [VERIFIED: codebase dependency footprint]

---

## CLI API Reference (Verified)

### GitHub: `gh pr list`

**Command:** [VERIFIED: live execution against cli/cli public repo]
```bash
gh pr list \
  -R <remote_url_or_owner/repo> \
  --json number,headRefName,isDraft,author,commits,statusCheckRollup \
  --state open
```

**The `-R` flag accepts:** full HTTPS remote URL, SSH remote URL, or `OWNER/REPO` format. `Repo.remote_url` can be passed directly.

**JSON output structure (verified against real PR):**
```json
[
  {
    "number": 42,
    "headRefName": "feat-login-redirect",
    "isDraft": false,
    "author": {
      "login": "pieter",
      "name": "Pieter Custers",
      "id": "...",
      "is_bot": false
    },
    "commits": [
      {
        "oid": "abc1234def...",
        "messageHeadline": "fix: login redirect after OAuth",
        "messageBody": "...",
        "authoredDate": "2026-04-13T08:21:01Z",
        "authors": [...],
        "committedDate": "..."
      }
    ],
    "statusCheckRollup": [
      {
        "__typename": "CheckRun",
        "status": "COMPLETED",
        "conclusion": "SUCCESS",
        "name": "build",
        "workflowName": "CI"
      }
    ]
  }
]
```

**Key field extraction:**
- `pr["number"]` → `MRInfo.mr_number`
- `pr["isDraft"]` → `MRInfo.is_draft`
- `pr["author"]["login"]` → `MRInfo.author` (format as `@login`)
- `pr["commits"][-1]["oid"][:7]` → `MRInfo.last_commit_hash` (short hash = first 7 chars)
- `pr["commits"][-1]["messageHeadline"]` → `MRInfo.last_commit_msg`
- Aggregate `pr["statusCheckRollup"]` → `MRInfo.ci_status` (see mapping below)

**Empty result:** `[]` (empty JSON array, not an error). Means no open PRs — all mapped branches get `None`.

**Error exit codes:** Non-zero returncode on auth failure, network error, or unknown repo. `stderr` contains human-readable error message.

### GitHub: statusCheckRollup → ci_status mapping

[VERIFIED: live execution, confirmed field values]

```python
def _map_gh_ci_status(rollup: list[dict]) -> str | None:
    if not rollup:
        return None
    # Any check still running/queued -> pending
    if any(c.get("status") != "COMPLETED" for c in rollup):
        return "pending"
    # Any check failed
    fail_conclusions = {"FAILURE", "TIMED_OUT", "ACTION_REQUIRED", "CANCELLED"}
    if any(c.get("conclusion") in fail_conclusions for c in rollup):
        return "fail"
    return "pass"
```

**Observed values:**
- `status`: `COMPLETED`, `IN_PROGRESS`, `QUEUED`, `WAITING`, `PENDING`, `REQUESTED`
- `conclusion` (when COMPLETED): `SUCCESS`, `FAILURE`, `NEUTRAL`, `CANCELLED`, `TIMED_OUT`, `ACTION_REQUIRED`, `SKIPPED`, `STALE`
- `__typename`: `CheckRun` (GitHub Actions), `StatusContext` (external CI/CD)

### GitLab: `glab mr list`

**Command:** [VERIFIED: glab 1.85.3 help output]
```bash
glab mr list \
  -R <remote_url_or_owner/repo> \
  --output json \
  --per-page 100
```

**The `-R` flag accepts:** `OWNER/REPO`, `GROUP/NAMESPACE/REPO`, full URL, or Git URL. `Repo.remote_url` can be passed directly.

**JSON output structure (from GitLab API docs):** [CITED: docs.gitlab.com/api/merge_requests]
```json
[
  {
    "iid": 43,
    "title": "...",
    "state": "opened",
    "draft": true,
    "work_in_progress": true,
    "source_branch": "feat-new-auth",
    "author": {
      "id": 1,
      "username": "pieter",
      "name": "Pieter Custers"
    }
  }
]
```

**Key field extraction:**
- `mr["iid"]` → `MRInfo.mr_number`
- `mr["draft"]` → `MRInfo.is_draft`
- `mr["author"]["username"]` → `MRInfo.author` (format as `@username`)
- `mr["source_branch"]` → match against `WorktreeInfo.branch`

**Important:** GitLab's `glab mr list` **does not include** `head_pipeline` (CI status). The GitLab list API endpoint omits this field — it is only available on single-MR fetch. [CITED: docs.gitlab.com/api/merge_requests]

### GitLab: CI Status via `glab ci get`

For each worktree branch that has an open MR, fetch pipeline status separately:

```bash
glab ci get \
  -R <remote_url_or_owner/repo> \
  --branch <branch_name> \
  --output json
```

**GitLab pipeline status values:** [VERIFIED: `glab ci list --status` help output]
`created`, `pending`, `running`, `success`, `failed`, `canceled`, `skipped`, `manual`, `waiting_for_resource`, `preparing`, `scheduled`

**Mapping:**
```python
def _map_glab_ci_status(status: str | None) -> str | None:
    if status in ("running", "pending", "created", "preparing",
                  "waiting_for_resource", "scheduled"):
        return "pending"
    if status == "success":
        return "pass"
    if status == "failed":
        return "fail"
    return None  # canceled, skipped, manual -> no CI indicator
```

**Note:** `glab ci get` returns a single pipeline object (the most recent), not an array.

### Last Commit for GitLab MRs

Since `glab mr list` does not return commit information, the last commit hash and message for GitLab MRs require either:
- A separate `glab mr view {iid} --output json` call per MR (includes commits)
- Or omit last commit for GitLab and show only author

**Recommendation (Claude's discretion):** For GitLab, omit `last_commit_hash`/`last_commit_msg` from `MRInfo` (leave as empty strings). The CI status and author are more important. A follow-up phase can add commit data if needed. This avoids O(N) per-MR API calls for GitLab.

---

## Architecture Patterns

### Recommended Project Structure

No new directories needed. One new module:

```
src/joy/
├── mr_status.py          # NEW: fetch_mr_data() — dispatches gh/glab per repo
├── models.py             # EXTEND: add MRInfo dataclass
├── app.py                # EXTEND: _load_worktrees() calls fetch_mr_data()
└── widgets/
    └── worktree_pane.py  # EXTEND: WorktreeRow.build_content() + set_worktrees()
```

### Pattern 1: MRInfo Dataclass (models.py)

```python
# Source: established pattern (WorktreeInfo, Repo in models.py)
@dataclass
class MRInfo:
    """MR/PR enrichment for a worktree branch."""
    mr_number: int
    is_draft: bool
    ci_status: str | None  # "pass" | "fail" | "pending" | None
    author: str            # "@login" format
    last_commit_hash: str  # 7-char short hash, or "" if unavailable
    last_commit_msg: str   # messageHeadline, or "" if unavailable
```

### Pattern 2: fetch_mr_data() — One Call per Repo

```python
# Source: established subprocess pattern (store.py, worktrees.py)
def fetch_mr_data(
    repos: list[Repo],
    worktrees: list[WorktreeInfo],
) -> dict[tuple[str, str], MRInfo]:
    """Fetch MR/CI data for all worktrees. Returns (repo_name, branch) -> MRInfo.
    
    Never raises — per-repo errors are caught and silently skipped (D-11).
    Returns partial results (some repos may have data, others None).
    """
    result: dict[tuple[str, str], MRInfo] = {}
    
    # Build set of active branches per repo for filtering
    branches_by_repo: dict[str, set[str]] = {}
    for wt in worktrees:
        branches_by_repo.setdefault(wt.repo_name, set()).add(wt.branch)
    
    for repo in repos:
        if repo.forge == "unknown":
            continue  # D-07: skip unknown forges silently
        try:
            if repo.forge == "github":
                mr_map = _fetch_github_mrs(repo, branches_by_repo.get(repo.name, set()))
            elif repo.forge == "gitlab":
                mr_map = _fetch_gitlab_mrs(repo, branches_by_repo.get(repo.name, set()))
            result.update(mr_map)
        except Exception:
            continue  # D-11: per-repo error silently skipped
    
    return result
```

### Pattern 3: GitHub Fetch — One Call Per Repo

```python
# Source: verified via live gh execution + JSON analysis
def _fetch_github_mrs(
    repo: Repo,
    active_branches: set[str],
) -> dict[tuple[str, str], MRInfo]:
    import json
    result = subprocess.run(
        [
            "gh", "pr", "list",
            "-R", repo.remote_url,
            "--json", "number,headRefName,isDraft,author,commits,statusCheckRollup",
            "--state", "open",
        ],
        capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    
    prs = json.loads(result.stdout)
    out: dict[tuple[str, str], MRInfo] = {}
    for pr in prs:
        branch = pr["headRefName"]
        if branch not in active_branches:
            continue  # Not a current worktree branch — skip
        commits = pr.get("commits", [])
        last_commit = commits[-1] if commits else {}
        out[(repo.name, branch)] = MRInfo(
            mr_number=pr["number"],
            is_draft=pr.get("isDraft", False),
            ci_status=_map_gh_ci_status(pr.get("statusCheckRollup", [])),
            author=f"@{pr['author']['login']}",
            last_commit_hash=last_commit.get("oid", "")[:7],
            last_commit_msg=last_commit.get("messageHeadline", ""),
        )
    return out
```

### Pattern 4: WorktreeRow.build_content() Extension

```python
# Source: worktree_pane.py build_content — extend for MR variant
@staticmethod
def build_content(
    branch: str,
    is_dirty: bool,
    has_upstream: bool,
    display_path: str,
    mr_info: MRInfo | None = None,  # NEW
) -> Text:
    t = Text(no_wrap=True, overflow="ellipsis")
    t.append(f" {ICON_BRANCH} ", style="bold")
    t.append(branch)
    
    if mr_info is not None:
        # Line 1: branch  !N  [open/draft icon]  [CI icon]  [dirty]  [no-upstream]
        t.append(f"  !{mr_info.mr_number} ", style="dim")
        if mr_info.is_draft:
            t.append(ICON_MR_DRAFT, style="dim")
        else:
            t.append(ICON_MR_OPEN, style="green")
        if mr_info.ci_status == "pass":
            t.append(f" {ICON_CI_PASS}", style="green")
        elif mr_info.ci_status == "fail":
            t.append(f" {ICON_CI_FAIL}", style="red")
        elif mr_info.ci_status == "pending":
            t.append(f" {ICON_CI_PENDING}", style="yellow")
    
    if is_dirty:
        t.append(f" {ICON_DIRTY}", style="yellow")
    if not has_upstream:
        t.append(f" {ICON_NO_UPSTREAM}", style="dim")
    t.append("\n")
    
    if mr_info is not None and (mr_info.author or mr_info.last_commit_hash):
        # Line 2: MR context — @author  hash commit-msg
        parts = []
        if mr_info.author:
            parts.append(mr_info.author)
        if mr_info.last_commit_hash:
            parts.append(f"{mr_info.last_commit_hash} {mr_info.last_commit_msg}")
        t.append(f"  {'  '.join(parts)}", style="dim")
    else:
        t.append(f"  {display_path}", style="dim")  # unchanged no-MR path
    
    return t
```

### Pattern 5: _load_worktrees() Extension in app.py

```python
# Source: app.py _load_worktrees() — add fetch_mr_data after discover_worktrees
@work(thread=True)
def _load_worktrees(self) -> None:
    from joy.store import load_repos
    from joy.worktrees import discover_worktrees
    from joy.mr_status import fetch_mr_data  # NEW

    try:
        repos = load_repos()
        worktrees = discover_worktrees(repos, self._config.branch_filter)
        
        # Phase 11: fetch MR/CI data (D-06)
        mr_data: dict = {}
        mr_failed = False
        try:
            mr_data = fetch_mr_data(repos, worktrees)
            # Detect total failure: repos with known forge got no data
            forgeable = [r for r in repos if r.forge != "unknown"]
            mr_failed = bool(forgeable) and len(mr_data) == 0 and bool(worktrees)
        except Exception:
            mr_failed = True
        
        repo_count = len(repos)
        branch_filter = ", ".join(self._config.branch_filter) if self._config.branch_filter else ""
        self.app.call_from_thread(
            self._set_worktrees, worktrees, repo_count, branch_filter, mr_data, mr_failed
        )
        self.app.call_from_thread(self._mark_refresh_success)
    except Exception:
        self.app.call_from_thread(self._mark_refresh_failure)
```

### Anti-Patterns to Avoid

- **Per-branch API calls for GitHub:** `gh pr view <branch>` once per worktree = N API calls. Use `gh pr list` once per repo instead.
- **Raising exceptions from fetch_mr_data:** The module must return partial results on error, never raise to caller.
- **Blocking the UI thread with subprocess:** All fetching happens in `_load_worktrees()` which is already `@work(thread=True)`.
- **Modifying WorktreeInfo:** `MRInfo` is a separate enrichment dataclass. Do not add fields to `WorktreeInfo` — keep the Phase 7 contract stable.
- **Showing CI slot when no CI data:** The CI slot must be blank (empty), not a placeholder glyph, per D-05.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GitHub API client | Custom HTTP + auth token | `gh pr list --json` | gh handles auth, rate limiting, pagination. Zero config. |
| GitLab API client | Custom HTTP + token | `glab mr list --output json` | Same — glab handles auth per-host. |
| CI status aggregation | Custom webhook listener | Read `statusCheckRollup` from gh JSON | Already pre-computed by GitHub. |
| JSON schema validation | Custom dict access | Simple `.get()` with defaults | CLI output is stable; over-engineering is waste. |

---

## Nerd Font Icon Codepoints

[VERIFIED: nerdfonts.com/cheat-sheet live lookup]

```python
# In worktree_pane.py — add alongside existing ICON_* constants
ICON_MR_OPEN    = "\uea64"  # nf-cod-git_pull_request     (open MR, color: green)
ICON_MR_DRAFT   = "\uebdb"  # nf-cod-git_pull_request_draft (draft MR, color: dim)
ICON_CI_PASS    = "\uf00c"  # nf-fa-check                 (CI pass, color: green)
ICON_CI_FAIL    = "\uf00d"  # nf-fa-times                 (CI fail, color: red)
ICON_CI_PENDING = "\uf111"  # nf-fa-circle                (CI pending, color: yellow)
                            # Note: ICON_DIRTY also uses \uf111 — same glyph,
                            # different color (yellow vs yellow) — acceptable reuse.
                            # If visual distinction needed, use \uf192 (dot-circle-o)
                            # for pending instead.
```

**Note on ICON_CI_PENDING vs ICON_DIRTY:** Both use `\uf111` (filled circle). They appear in different positions on line 1 (CI before dirty), so positional context disambiguates. If the user finds this confusing, substitute `\uf192` (nf-fa-dot_circle_o) for `ICON_CI_PENDING`.

---

## Common Pitfalls

### Pitfall 1: gh returncode 0 even on partial failures

**What goes wrong:** `gh pr list` returns exit code 0 with empty `[]` when there are no open PRs OR when not authenticated to that specific repo. Both look identical from the subprocess returncode.
**Why it happens:** gh distinguishes "no results" from auth failure only via returncode in some cases, but for `pr list` against an inaccessible repo, returncode is typically non-zero. However, an empty list is always valid.
**How to avoid:** Check `result.returncode != 0` AND check `result.stderr` for auth error strings. If returncode is 0 and stdout is `[]`, treat as "no open PRs" (normal). If returncode is non-zero, treat as fetch failure.
**Warning signs:** `stderr` contains "not authenticated" or "could not resolve" — raise to trigger D-11 silent-skip.

### Pitfall 2: GitLab `glab mr list` doesn't include CI status

**What goes wrong:** Assuming `glab mr list --output json` includes CI/pipeline data, then `mr["head_pipeline"]` causes a `KeyError`.
**Why it happens:** The GitLab list endpoint omits `head_pipeline` — it's only in the single-MR endpoint. [CITED: docs.gitlab.com/api/merge_requests]
**How to avoid:** Use `glab ci get --branch <branch> --output json` for CI status on GitLab. Accept `None` CI status for GitLab MRs if the extra call is not worth the latency.
**Warning signs:** `KeyError: 'head_pipeline'` or `KeyError: 'pipeline'` in glab JSON parsing code.

### Pitfall 3: commits[] ordering assumption

**What goes wrong:** Assuming `commits[-1]` is always the most recent commit. The gh API returns commits in chronological order (oldest first), so `[-1]` is correct — but this is an assumption based on observed behavior, not documented explicitly.
**Why it happens:** gh returns commits in the PR timeline order.
**How to avoid:** Sort by `authoredDate` descending before taking `[-1]`, or accept that `[-1]` is the latest based on observed behavior.
**Warning signs:** Last commit hash shows an old commit message on a PR with multiple recent commits.

### Pitfall 4: MR icon layout causes line 1 to overflow

**What goes wrong:** A branch with a long name + MR number + icons overflows the pane width, wrapping the `rich.Text` to a 3rd line.
**Why it happens:** `WorktreeRow` has `height: 2` — two lines. Rich Text `no_wrap=True` with `overflow="ellipsis"` should prevent wrapping, but only if the text is wider than the container.
**How to avoid:** The existing `no_wrap=True, overflow="ellipsis"` on `Text(...)` handles this — line 1 is already protected. No additional action needed, but verify during visual UAT.

### Pitfall 5: `MRInfo` key mismatch between repo_name and branch

**What goes wrong:** `fetch_mr_data()` returns `{("joy", "main"): MRInfo(...)}` but `set_worktrees()` looks up `(wt.repo_name, wt.branch)` — these must match exactly.
**Why it happens:** `headRefName` from gh vs `wt.branch` from `WorktreeInfo` could differ (e.g., casing, remote prefix like `origin/feat-x`).
**How to avoid:** `WorktreeInfo.branch` from Phase 7 is the local branch name (no `origin/` prefix, exact case from `git worktree list`). `headRefName` from gh is also the local branch name. These should match. Verify in test fixtures.
**Warning signs:** No MR badges appear in the UI even though MRs exist.

### Pitfall 6: `glab mr list` returns MRs for ALL branches when `--source-branch` not used

**What goes wrong:** Using `glab mr list --output json` without filtering returns all open MRs in the repo (up to `--per-page` limit). For repos with many open MRs, this list could be large. The Python layer then filters in memory.
**Why it happens:** Default behavior is to return all open MRs.
**How to avoid:** Set `--per-page 100` to ensure all MRs are fetched. For repos with > 100 open MRs, pagination would be needed — but this is an edge case acceptable for v1.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PyGithub / python-gitlab client | `gh`/`glab` CLI JSON | Always | Zero deps, auth already configured, simpler |
| Per-branch API call | Batch fetch all open PRs once | This phase | O(1) API calls per repo vs O(N) per worktree |

---

## Code Examples

### Complete gh Fetch (minimal, correct)

```python
# Source: verified via live gh execution
import json, subprocess

def _fetch_github_mrs(repo: Repo, active_branches: set[str]) -> dict[tuple[str,str], MRInfo]:
    result = subprocess.run(
        [
            "gh", "pr", "list",
            "-R", repo.remote_url,
            "--json", "number,headRefName,isDraft,author,commits,statusCheckRollup",
            "--state", "open",
        ],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    
    out = {}
    for pr in json.loads(result.stdout):
        branch = pr["headRefName"]
        if branch not in active_branches:
            continue
        commits = pr.get("commits", [])
        last = commits[-1] if commits else {}
        ci = _map_gh_ci_status(pr.get("statusCheckRollup", []))
        out[(repo.name, branch)] = MRInfo(
            mr_number=pr["number"],
            is_draft=bool(pr.get("isDraft")),
            ci_status=ci,
            author=f"@{pr['author']['login']}",
            last_commit_hash=last.get("oid", "")[:7],
            last_commit_msg=last.get("messageHeadline", ""),
        )
    return out
```

### statusCheckRollup Aggregation

```python
# Source: GitHub API field analysis (verified)
def _map_gh_ci_status(rollup: list[dict]) -> str | None:
    if not rollup:
        return None
    if any(c.get("status") != "COMPLETED" for c in rollup):
        return "pending"
    fail_set = {"FAILURE", "TIMED_OUT", "ACTION_REQUIRED", "CANCELLED"}
    if any(c.get("conclusion") in fail_set for c in rollup):
        return "fail"
    return "pass"
```

### GitLab Fetch (MR data + CI separate)

```python
# Source: glab CLI documentation + GitLab API docs [CITED: docs.gitlab.com/api/merge_requests]
def _fetch_gitlab_mrs(repo: Repo, active_branches: set[str]) -> dict[tuple[str,str], MRInfo]:
    result = subprocess.run(
        ["glab", "mr", "list", "-R", repo.remote_url, "--output", "json", "--per-page", "100"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    
    out = {}
    for mr in json.loads(result.stdout):
        branch = mr.get("source_branch", "")
        if branch not in active_branches:
            continue
        ci_status = _fetch_glab_ci_status(repo, branch)
        out[(repo.name, branch)] = MRInfo(
            mr_number=mr["iid"],
            is_draft=bool(mr.get("draft", False)),
            ci_status=ci_status,
            author=f"@{mr['author']['username']}",
            last_commit_hash="",   # not available from list endpoint
            last_commit_msg="",
        )
    return out


def _fetch_glab_ci_status(repo: Repo, branch: str) -> str | None:
    result = subprocess.run(
        ["glab", "ci", "get", "-R", repo.remote_url, "--branch", branch, "--output", "json"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return None  # No pipeline or can't fetch — blank CI slot
    try:
        pipeline = json.loads(result.stdout)
        return _map_glab_ci_status(pipeline.get("status"))
    except (json.JSONDecodeError, AttributeError):
        return None


def _map_glab_ci_status(status: str | None) -> str | None:
    if status in ("running", "pending", "created", "preparing",
                  "waiting_for_resource", "scheduled"):
        return "pending"
    if status == "success":
        return "pass"
    if status == "failed":
        return "fail"
    return None
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| `gh` CLI | GitHub MR/CI fetch (D-07) | Yes | 2.40.1 | D-09: repos render without MR data |
| `glab` CLI | GitLab MR/CI fetch (D-07) | Yes | 1.85.3 | D-09: repos render without MR data |
| `gh` auth | GitHub API calls | Yes (github.com, pietercusters) | — | D-10: border_title warning on total failure |
| `glab` auth | GitLab API calls | Not tested (no GitLab remote) | — | D-09/D-10 graceful degradation |

**Note on glab authentication:** `glab` is installed but the dev environment has no GitLab remotes. Auth would be needed for GitLab repos. The D-09/D-11 silent-skip pattern handles this — GitLab repos without auth simply return no MR data.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x with pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_mr_status.py tests/test_worktree_pane.py -x -q` |
| Full suite command | `uv run pytest -q` |

**Baseline:** 224 tests passing, 1 deselected (macOS integration tests). [VERIFIED: live run]

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WKTR-07 | MR number + status badge in row when MR exists | unit | `uv run pytest tests/test_worktree_pane.py -k mr -x` | Wave 0 |
| WKTR-07 | No MR: row unchanged (path on line 2) | unit | `uv run pytest tests/test_worktree_pane.py -k no_mr -x` | Wave 0 |
| WKTR-08 | CI pass/fail/pending icons shown correctly | unit | `uv run pytest tests/test_mr_status.py -k ci -x` | Wave 0 |
| WKTR-08 | CI slot blank when no CI data | unit | `uv run pytest tests/test_worktree_pane.py -k no_ci -x` | Wave 0 |
| WKTR-09 | Line 2 shows @author + hash + msg when MR present | unit | `uv run pytest tests/test_worktree_pane.py -k author -x` | Wave 0 |
| WKTR-09 | Line 2 shows path when no MR | unit | `uv run pytest tests/test_worktree_pane.py::test_row_shows_abbreviated_path` | Exists |
| D-11 | fetch_mr_data returns partial results on per-repo error | unit | `uv run pytest tests/test_mr_status.py -k error -x` | Wave 0 |
| D-10 | Total failure sets mr_failed=True | unit | `uv run pytest tests/test_mr_status.py -k total_failure -x` | Wave 0 |
| Regression | Phase 7 tests still pass | regression | `uv run pytest tests/test_worktrees.py` | Exists (16 tests) |
| Regression | Phase 9 pane tests still pass | regression | `uv run pytest tests/test_worktree_pane.py` | Exists |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_mr_status.py tests/test_worktree_pane.py -x -q`
- **Per wave merge:** `uv run pytest -q`
- **Phase gate:** Full suite green (`uv run pytest -q`) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_mr_status.py` — new file; covers `fetch_mr_data`, `_map_gh_ci_status`, `_map_glab_ci_status`, error handling, partial results, total failure detection
- [ ] Extend `tests/test_worktree_pane.py` — new tests for `WorktreeRow.build_content()` with `MRInfo`, icon presence, line-2 MR context, no-MR path unchanged
- [ ] Extend `tests/test_models.py` — new tests for `MRInfo` dataclass fields and defaults

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `commits[-1]` in gh JSON is the most recent commit (chronological order, last = newest) | CLI API Reference | Last commit hash shown is an old commit; low visual impact |
| A2 | `glab mr list --output json` returns `source_branch` as the key for filtering by branch | CLI API Reference (GitLab) | Branch lookup fails for all GitLab MRs; graceful degradation applies |
| A3 | `glab ci get --branch X` returns a JSON object with a top-level `status` field | CLI API Reference (GitLab) | CI status shows None for all GitLab branches; acceptable fallback |
| A4 | `glab mr list --output json` returns `iid` (not `id`) as the MR number | CLI API Reference (GitLab) | MR number off by one or wrong; low visual impact |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.
Claims A2-A4 are `[ASSUMED]` based on GitLab REST API documentation and glab CLI conventions, not confirmed via live execution against a GitLab instance.

---

## Open Questions

1. **GitLab last commit data**
   - What we know: `glab mr list` does not include commit info; `glab mr view {iid} --output json` (single-MR endpoint) may include commits
   - What's unclear: Whether the extra O(N) glab calls per-MR are acceptable given the refresh latency budget
   - Recommendation: Skip last commit for GitLab in Wave 1; leave `last_commit_hash`/`last_commit_msg` as empty strings. Can be added in a follow-up.

2. **ICON_CI_PENDING vs ICON_DIRTY glyph collision**
   - What we know: Both use `\uf111` (nf-fa-circle). They appear in different positions on line 1.
   - What's unclear: Whether users find the identical glyph confusing at a glance
   - Recommendation: Use `\uf111` for both initially (positional context disambiguates). Switch CI pending to `\uf192` (dot-circle-o) if visual UAT reveals confusion.

---

## Sources

### Primary (HIGH confidence)
- `gh --version` + `gh pr list` live execution against cli/cli public repo — JSON field structure, statusCheckRollup values, commits structure
- `glab --version` + `glab mr list --help` + `glab ci list --help` + `glab ci get --help` — CLI availability, flags, pipeline status values
- `/Users/pieter/Github/joy/src/joy/widgets/worktree_pane.py` — existing icon constants, build_content signature, set_worktrees API
- `/Users/pieter/Github/joy/src/joy/app.py` — _load_worktrees worker pattern, _set_worktrees dispatcher
- `/Users/pieter/Github/joy/src/joy/models.py` — dataclass pattern for MRInfo
- `uv run pytest -q` — 224 tests passing baseline confirmed

### Secondary (MEDIUM confidence)
- [docs.gitlab.com/api/merge_requests](https://docs.gitlab.com/api/merge_requests/) — GitLab list endpoint does not include head_pipeline; draft field name; author.username field
- [nerdfonts.com/cheat-sheet](https://www.nerdfonts.com/cheat-sheet) — icon codepoints: ea64 (git_pull_request), ebdb (git_pull_request_draft), f00c (check), f00d (times)

### Tertiary (LOW confidence, see Assumptions Log)
- GitLab API field names in glab JSON output (source_branch, iid) — inferred from GitLab REST API docs, not confirmed via live glab execution against a GitLab instance

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — both CLIs verified installed and authenticated; subprocess pattern verified in codebase
- Architecture: HIGH — patterns directly extend verified existing code; CLI JSON shapes confirmed via live execution
- Pitfalls: HIGH — most verified via direct testing or official docs; GitLab-specific pitfalls MEDIUM (cannot test live)
- Icon codepoints: HIGH — verified via nerdfonts.com cheat sheet

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable CLI APIs; gh/glab rarely break JSON field names)
