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

from joy.models import MRInfo, Repo, WorktreeInfo


def fetch_mr_data(
    repos: list[Repo],
    worktrees: list[WorktreeInfo],
) -> dict[tuple[str, str], MRInfo]:
    """Fetch MR/CI data for all worktrees.

    Returns a mapping of ``(repo_name, branch) -> MRInfo`` for branches
    that have an open MR/PR on their forge.

    Never raises -- per-repo errors are caught and silently skipped (D-11).
    Returns partial results (some repos may have data, others not).
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
                mr_map = _fetch_github_mrs(
                    repo, branches_by_repo.get(repo.name, set())
                )
            elif repo.forge == "gitlab":
                mr_map = _fetch_gitlab_mrs(
                    repo, branches_by_repo.get(repo.name, set())
                )
            else:
                continue
            result.update(mr_map)
        except Exception:
            continue  # D-11: per-repo error silently skipped

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
            "number,headRefName,isDraft,author,commits,statusCheckRollup",
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
        commits = pr.get("commits", [])
        last_commit = commits[-1] if commits else {}
        author_obj = pr.get("author") or {}
        out[(repo.name, branch)] = MRInfo(
            mr_number=pr["number"],
            is_draft=pr.get("isDraft", False),
            ci_status=_map_gh_ci_status(pr.get("statusCheckRollup", [])),
            author=f"@{author_obj.get('login', 'unknown')}",
            last_commit_hash=last_commit.get("oid", "")[:7],
            last_commit_msg=last_commit.get("messageHeadline", ""),
        )
    return out


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
        author_obj = mr.get("author") or {}
        out[(repo.name, branch)] = MRInfo(
            mr_number=mr["iid"],
            is_draft=mr.get("draft", False),
            ci_status=ci_status,
            author=f"@{author_obj.get('username', 'unknown')}",
            last_commit_hash=mr.get("sha", "")[:7],
            last_commit_msg="",  # Commit message not available from list endpoint
        )
    return out


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
