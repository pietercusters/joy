"""Fetch MR/PR status and CI pipeline results from GitHub (gh) and GitLab (glab) CLIs.

This is the data layer for Phase 11: all MR/CI enrichment data flows through
fetch_mr_data() before reaching the UI. The module is robust against missing
CLIs, auth failures, network errors, and unknown forges -- returning partial
results safely.

Per D-11: module never raises to its caller.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field

from joy.models import MRDetail, MRInfo, Repo, WorktreeInfo


@dataclass
class BatchMRResult:
    """Complete MR fetch result for all repos."""

    by_branch: dict[tuple[str, str], MRInfo] = field(default_factory=dict)
    authored: list[MRDetail] = field(default_factory=list)
    review_requests: list[MRDetail] = field(default_factory=list)


def fetch_mr_data(
    repos: list[Repo],
    worktrees: list[WorktreeInfo],
) -> BatchMRResult:
    """Fetch MR/CI data for all worktrees.

    Returns a BatchMRResult containing:
    - by_branch: mapping of ``(repo_name, branch) -> MRInfo`` for worktree badges
    - authored: list of MRDetail for MRs authored by the user
    - review_requests: list of MRDetail for MRs where user is reviewer

    Never raises -- per-repo errors are caught and silently skipped (D-11).
    Returns partial results (some repos may have data, others not).
    """
    result = BatchMRResult()

    # Build set of active branches per repo for filtering
    branches_by_repo: dict[str, set[str]] = {}
    for wt in worktrees:
        branches_by_repo.setdefault(wt.repo_name, set()).add(wt.branch)

    for repo in repos:
        if repo.forge == "unknown":
            continue  # D-07: skip unknown forges silently

        # Fetch branch-keyed data (existing behavior for worktree pane)
        try:
            if repo.forge == "github":
                mr_map = _fetch_github_mrs(
                    repo, branches_by_repo.get(repo.name, set())
                )
            elif repo.forge == "gitlab":
                mr_map = _fetch_gitlab_mrs(
                    repo, branches_by_repo.get(repo.name, set())
                )
            else:
                mr_map = {}
            result.by_branch.update(mr_map)
        except Exception:
            mr_map = {}  # D-11: per-repo error silently skipped

        # Fetch authored MRs for MR pane
        try:
            if repo.forge == "github":
                authored = _fetch_github_authored_mrs(repo)
            elif repo.forge == "gitlab":
                authored = _fetch_gitlab_authored_mrs(repo)
            else:
                authored = []
            result.authored.extend(authored)
        except Exception:
            pass  # D-11: per-repo error silently skipped

        # Fetch review requests for MR pane
        try:
            if repo.forge == "github":
                reviews = _fetch_github_review_requests(repo)
            elif repo.forge == "gitlab":
                reviews = _fetch_gitlab_review_requests(repo)
            else:
                reviews = []
            result.review_requests.extend(reviews)
        except Exception:
            pass  # D-11: per-repo error silently skipped

        # Per-branch fallback: active branches missing from batch by_branch
        active_branches = branches_by_repo.get(repo.name, set())
        covered_branches = {
            branch for (rname, branch) in mr_map if rname == repo.name
        }
        leftover_branches = active_branches - covered_branches
        for branch in leftover_branches:
            try:
                if repo.forge == "github":
                    fallback = _fetch_github_branch_mr(repo, branch)
                elif repo.forge == "gitlab":
                    fallback = _fetch_gitlab_branch_mr(repo, branch)
                else:
                    fallback = None
                if fallback is not None:
                    result.by_branch[(repo.name, branch)] = fallback
            except Exception:
                pass  # D-11: per-branch fallback error silently skipped

    return result


def _fetch_github_mrs(
    repo: Repo,
    active_branches: set[str],
) -> dict[tuple[str, str], MRInfo]:
    """Fetch open PRs from a GitHub repo via ``gh pr list``.

    One CLI call per repo -- filters by active worktree branches in Python.
    Raises RuntimeError on non-zero exit code.
    """
    result = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "-R",
            repo.remote_url,
            "--json",
            "number,headRefName,isDraft,statusCheckRollup,url,reviewDecision,title",
            "--state",
            "open",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    prs = json.loads(result.stdout)
    out: dict[tuple[str, str], MRInfo] = {}
    for pr in prs:
        branch = pr["headRefName"]
        if branch not in active_branches:
            continue  # Not a current worktree branch -- skip
        out[(repo.name, branch)] = MRInfo(
            mr_number=pr["number"],
            is_draft=pr.get("isDraft", False),
            ci_status=_map_gh_ci_status(pr.get("statusCheckRollup", [])),
            url=pr.get("url", ""),
        )
    return out


def _fetch_github_authored_mrs(repo: Repo) -> list[MRDetail]:
    """Fetch open PRs authored by the current user via ``gh pr list --author @me``.

    Returns list[MRDetail] with is_review_request=False.
    Raises RuntimeError on non-zero exit code.
    """
    result = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "-R",
            repo.remote_url,
            "--author",
            "@me",
            "--state",
            "open",
            "--json",
            "number,headRefName,isDraft,statusCheckRollup,url,reviewDecision,title",
            "--limit",
            "100",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    prs = json.loads(result.stdout)
    out: list[MRDetail] = []
    for pr in prs:
        out.append(MRDetail(
            mr_number=pr["number"],
            title=pr.get("title", ""),
            is_draft=pr.get("isDraft", False),
            ci_status=_map_gh_ci_status(pr.get("statusCheckRollup", [])),
            review_status=_map_gh_review_decision(pr.get("reviewDecision", "")),
            url=pr.get("url", ""),
            repo_name=repo.name,
            branch=pr.get("headRefName", ""),
            is_review_request=False,
        ))
    return out


def _fetch_github_review_requests(repo: Repo) -> list[MRDetail]:
    """Fetch open PRs where the current user is a requested reviewer.

    Returns list[MRDetail] with is_review_request=True.
    Raises RuntimeError on non-zero exit code.
    """
    result = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "-R",
            repo.remote_url,
            "--state",
            "open",
            "--search",
            "review-requested:@me",
            "--json",
            "number,headRefName,isDraft,statusCheckRollup,url,reviewDecision,title",
            "--limit",
            "100",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    prs = json.loads(result.stdout)
    out: list[MRDetail] = []
    for pr in prs:
        out.append(MRDetail(
            mr_number=pr["number"],
            title=pr.get("title", ""),
            is_draft=pr.get("isDraft", False),
            ci_status=_map_gh_ci_status(pr.get("statusCheckRollup", [])),
            review_status=_map_gh_review_decision(pr.get("reviewDecision", "")),
            url=pr.get("url", ""),
            repo_name=repo.name,
            branch=pr.get("headRefName", ""),
            is_review_request=True,
        ))
    return out


def _fetch_github_branch_mr(repo: Repo, branch: str) -> MRInfo | None:
    """Fetch open PR for a specific branch (per-branch fallback for worktree badges).

    Returns MRInfo for the first result, or None if no result / error.
    """
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "-R",
                repo.remote_url,
                "--head",
                branch,
                "--state",
                "open",
                "--json",
                "number,isDraft,statusCheckRollup,url",
                "--limit",
                "1",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        if result.returncode != 0:
            return None
        prs = json.loads(result.stdout)
        if not prs:
            return None
        pr = prs[0]
        return MRInfo(
            mr_number=pr["number"],
            is_draft=pr.get("isDraft", False),
            ci_status=_map_gh_ci_status(pr.get("statusCheckRollup", [])),
            url=pr.get("url", ""),
        )
    except Exception:
        return None


def _fetch_gitlab_mrs(
    repo: Repo,
    active_branches: set[str],
) -> dict[tuple[str, str], MRInfo]:
    """Fetch open MRs from a GitLab repo via ``glab mr list``.

    One ``glab mr list`` call per repo, plus one ``glab ci get`` per branch
    that has an MR (CI status not available from list endpoint).
    Raises RuntimeError on non-zero exit code from mr list.
    """
    result = subprocess.run(
        [
            "glab",
            "mr",
            "list",
            "-R",
            repo.remote_url,
            "--output",
            "json",
            "--per-page",
            "100",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    mrs = json.loads(result.stdout)
    out: dict[tuple[str, str], MRInfo] = {}
    for mr in mrs:
        branch = mr["source_branch"]
        if branch not in active_branches:
            continue
        ci_status = _fetch_glab_ci_status(repo, branch)
        out[(repo.name, branch)] = MRInfo(
            mr_number=mr["iid"],
            is_draft=mr.get("draft", False),
            ci_status=ci_status,
            url=mr.get("web_url", ""),
        )
    return out


def _fetch_gitlab_authored_mrs(repo: Repo) -> list[MRDetail]:
    """Fetch open MRs authored by the current user via ``glab mr list --author @me``.

    Returns list[MRDetail] with is_review_request=False.
    Raises RuntimeError on non-zero exit code.
    """
    result = subprocess.run(
        [
            "glab",
            "mr",
            "list",
            "-R",
            repo.remote_url,
            "--author",
            "@me",
            "--output",
            "json",
            "--per-page",
            "100",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    mrs = json.loads(result.stdout)
    out: list[MRDetail] = []
    for mr in mrs:
        ci_status = _fetch_glab_ci_status(repo, mr.get("source_branch", ""))
        out.append(MRDetail(
            mr_number=mr["iid"],
            title=mr.get("title", ""),
            is_draft=mr.get("draft", False),
            ci_status=ci_status,
            review_status=_map_gl_review_status(mr.get("detailed_merge_status")),
            url=mr.get("web_url", ""),
            repo_name=repo.name,
            branch=mr.get("source_branch", ""),
            is_review_request=False,
        ))
    return out


def _fetch_gitlab_review_requests(repo: Repo) -> list[MRDetail]:
    """Fetch open MRs where the current user is a reviewer via ``glab mr list --reviewer @me``.

    Returns list[MRDetail] with is_review_request=True.
    Raises RuntimeError on non-zero exit code.
    """
    result = subprocess.run(
        [
            "glab",
            "mr",
            "list",
            "-R",
            repo.remote_url,
            "--reviewer",
            "@me",
            "--output",
            "json",
            "--per-page",
            "100",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    mrs = json.loads(result.stdout)
    out: list[MRDetail] = []
    for mr in mrs:
        ci_status = _fetch_glab_ci_status(repo, mr.get("source_branch", ""))
        out.append(MRDetail(
            mr_number=mr["iid"],
            title=mr.get("title", ""),
            is_draft=mr.get("draft", False),
            ci_status=ci_status,
            review_status=_map_gl_review_status(mr.get("detailed_merge_status")),
            url=mr.get("web_url", ""),
            repo_name=repo.name,
            branch=mr.get("source_branch", ""),
            is_review_request=True,
        ))
    return out


def _fetch_gitlab_branch_mr(repo: Repo, branch: str) -> MRInfo | None:
    """Fetch open MR for a specific branch (per-branch fallback for worktree badges).

    Returns MRInfo for the first result, or None if no result / error.
    """
    try:
        result = subprocess.run(
            [
                "glab",
                "mr",
                "list",
                "-R",
                repo.remote_url,
                "--source-branch",
                branch,
                "--state",
                "opened",
                "--output",
                "json",
                "--per-page",
                "1",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        if result.returncode != 0:
            return None
        mrs = json.loads(result.stdout)
        if not mrs:
            return None
        mr = mrs[0]
        ci_status = _fetch_glab_ci_status(repo, branch)
        return MRInfo(
            mr_number=mr["iid"],
            is_draft=mr.get("draft", False),
            ci_status=ci_status,
            url=mr.get("web_url", ""),
        )
    except Exception:
        return None


def _fetch_glab_ci_status(repo: Repo, branch: str) -> str | None:
    """Fetch CI pipeline status for a specific branch via ``glab ci get``.

    Returns mapped ci_status or None on any error.
    """
    try:
        result = subprocess.run(
            [
                "glab",
                "ci",
                "get",
                "-R",
                repo.remote_url,
                "--branch",
                branch,
                "--output",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        return _map_glab_ci_status(data.get("status"))
    except (json.JSONDecodeError, Exception):
        return None


# ---------------------------------------------------------------------------
# Status mapping functions
# ---------------------------------------------------------------------------


def _map_gh_ci_status(rollup: list[dict]) -> str | None:
    """Map GitHub statusCheckRollup to ci_status.

    Returns:
        "pass"    -- all checks COMPLETED with SUCCESS/NEUTRAL/SKIPPED/STALE
        "fail"    -- any check COMPLETED with FAILURE/TIMED_OUT/ACTION_REQUIRED/CANCELLED
        "pending" -- any check not yet COMPLETED
        None      -- no CI checks (empty rollup)
    """
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


def _map_glab_ci_status(status: str | None) -> str | None:
    """Map GitLab pipeline status string to ci_status.

    Returns:
        "pass"    -- success
        "fail"    -- failed
        "pending" -- running, pending, created, preparing, waiting_for_resource, scheduled
        None      -- canceled, skipped, manual, or None
    """
    if status in (
        "running",
        "pending",
        "created",
        "preparing",
        "waiting_for_resource",
        "scheduled",
    ):
        return "pending"
    if status == "success":
        return "pass"
    if status == "failed":
        return "fail"
    return None


def _map_gh_review_decision(decision: str | None) -> str | None:
    """Map GitHub reviewDecision to review_status.

    Returns:
        "approved"          -- APPROVED
        "changes_requested" -- CHANGES_REQUESTED
        "review_required"   -- REVIEW_REQUIRED
        None                -- empty string, missing, or unknown
    """
    if not decision:
        return None
    mapping = {
        "APPROVED": "approved",
        "CHANGES_REQUESTED": "changes_requested",
        "REVIEW_REQUIRED": "review_required",
    }
    return mapping.get(decision)


def _map_gl_review_status(detailed_merge_status: str | None) -> str | None:
    """Map GitLab detailed_merge_status to review_status.

    Returns:
        "review_required"   -- not_approved
        "approved"          -- mergeable
        "changes_requested" -- discussions_not_resolved
        None                -- others or None
    """
    if not detailed_merge_status:
        return None
    mapping = {
        "not_approved": "review_required",
        "mergeable": "approved",
        "discussions_not_resolved": "changes_requested",
    }
    return mapping.get(detailed_merge_status)
