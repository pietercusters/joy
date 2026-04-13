"""Tests for MR/CI status fetch module."""
from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, call, patch

import pytest

from joy.models import MRInfo, Repo, WorktreeInfo


# ---------------------------------------------------------------------------
# Test fixtures — mock CLI JSON responses
# ---------------------------------------------------------------------------

GITHUB_PR_JSON = [
    {
        "number": 42,
        "headRefName": "feat-login",
        "isDraft": False,
        "author": {"login": "pieter"},
        "commits": [
            {"oid": "abc1234def5678", "messageHeadline": "fix: login redirect"}
        ],
        "statusCheckRollup": [
            {"status": "COMPLETED", "conclusion": "SUCCESS", "name": "build"}
        ],
    }
]

GITHUB_PR_JSON_MULTI = [
    {
        "number": 42,
        "headRefName": "feat-login",
        "isDraft": False,
        "author": {"login": "pieter"},
        "commits": [
            {"oid": "abc1234def5678", "messageHeadline": "fix: login redirect"}
        ],
        "statusCheckRollup": [
            {"status": "COMPLETED", "conclusion": "SUCCESS", "name": "build"}
        ],
    },
    {
        "number": 99,
        "headRefName": "unrelated-branch",
        "isDraft": False,
        "author": {"login": "other"},
        "commits": [
            {"oid": "zzz9999aaa0000", "messageHeadline": "chore: unrelated"}
        ],
        "statusCheckRollup": [],
    },
]

GITLAB_MR_JSON = [
    {
        "iid": 43,
        "source_branch": "feat-auth",
        "draft": True,
        "author": {"username": "pieter"},
        "sha": "abcdef0123456789",
    }
]

GITLAB_CI_JSON = {"status": "success"}


# ---------------------------------------------------------------------------
# Helper to build mock subprocess.run results
# ---------------------------------------------------------------------------


def _mock_result(stdout: str = "", stderr: str = "", returncode: int = 0):
    """Build a mock subprocess.CompletedProcess."""
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.stdout = stdout
    result.stderr = stderr
    result.returncode = returncode
    return result


# ---------------------------------------------------------------------------
# Tests: MRInfo dataclass
# ---------------------------------------------------------------------------


class TestMRInfoDataclass:
    """Verify MRInfo dataclass has correct fields per D-08."""

    def test_mrinfo_has_all_fields(self) -> None:
        """MRInfo has mr_number, is_draft, ci_status, author, last_commit_hash, last_commit_msg."""
        info = MRInfo(
            mr_number=42,
            is_draft=False,
            ci_status="pass",
            author="@pieter",
            last_commit_hash="abc1234",
            last_commit_msg="fix: login redirect",
        )
        assert info.mr_number == 42
        assert info.is_draft is False
        assert info.ci_status == "pass"
        assert info.author == "@pieter"
        assert info.last_commit_hash == "abc1234"
        assert info.last_commit_msg == "fix: login redirect"

    def test_mrinfo_ci_status_none(self) -> None:
        """MRInfo ci_status can be None."""
        info = MRInfo(
            mr_number=1,
            is_draft=False,
            ci_status=None,
            author="@test",
            last_commit_hash="",
            last_commit_msg="",
        )
        assert info.ci_status is None


# ---------------------------------------------------------------------------
# Tests: _map_gh_ci_status
# ---------------------------------------------------------------------------


class TestMapGhCiStatus:
    """Tests for GitHub statusCheckRollup -> ci_status mapping."""

    def test_empty_rollup_returns_none(self) -> None:
        """Empty rollup means no CI data -> None."""
        from joy.mr_status import _map_gh_ci_status

        assert _map_gh_ci_status([]) is None

    def test_all_completed_success_returns_pass(self) -> None:
        """All checks COMPLETED+SUCCESS -> 'pass'."""
        from joy.mr_status import _map_gh_ci_status

        rollup = [
            {"status": "COMPLETED", "conclusion": "SUCCESS"},
            {"status": "COMPLETED", "conclusion": "SUCCESS"},
        ]
        assert _map_gh_ci_status(rollup) == "pass"

    def test_any_failure_returns_fail(self) -> None:
        """Any check with FAILURE conclusion -> 'fail'."""
        from joy.mr_status import _map_gh_ci_status

        rollup = [
            {"status": "COMPLETED", "conclusion": "SUCCESS"},
            {"status": "COMPLETED", "conclusion": "FAILURE"},
        ]
        assert _map_gh_ci_status(rollup) == "fail"

    def test_timed_out_returns_fail(self) -> None:
        """TIMED_OUT conclusion -> 'fail'."""
        from joy.mr_status import _map_gh_ci_status

        rollup = [{"status": "COMPLETED", "conclusion": "TIMED_OUT"}]
        assert _map_gh_ci_status(rollup) == "fail"

    def test_action_required_returns_fail(self) -> None:
        """ACTION_REQUIRED conclusion -> 'fail'."""
        from joy.mr_status import _map_gh_ci_status

        rollup = [{"status": "COMPLETED", "conclusion": "ACTION_REQUIRED"}]
        assert _map_gh_ci_status(rollup) == "fail"

    def test_cancelled_returns_fail(self) -> None:
        """CANCELLED conclusion -> 'fail'."""
        from joy.mr_status import _map_gh_ci_status

        rollup = [{"status": "COMPLETED", "conclusion": "CANCELLED"}]
        assert _map_gh_ci_status(rollup) == "fail"

    def test_non_completed_status_returns_pending(self) -> None:
        """Any non-COMPLETED status -> 'pending'."""
        from joy.mr_status import _map_gh_ci_status

        rollup = [
            {"status": "IN_PROGRESS", "conclusion": None},
            {"status": "COMPLETED", "conclusion": "SUCCESS"},
        ]
        assert _map_gh_ci_status(rollup) == "pending"

    def test_queued_returns_pending(self) -> None:
        """QUEUED status -> 'pending'."""
        from joy.mr_status import _map_gh_ci_status

        rollup = [{"status": "QUEUED", "conclusion": None}]
        assert _map_gh_ci_status(rollup) == "pending"


# ---------------------------------------------------------------------------
# Tests: _map_glab_ci_status
# ---------------------------------------------------------------------------


class TestMapGlabCiStatus:
    """Tests for GitLab pipeline status -> ci_status mapping."""

    def test_success_returns_pass(self) -> None:
        """'success' -> 'pass'."""
        from joy.mr_status import _map_glab_ci_status

        assert _map_glab_ci_status("success") == "pass"

    def test_failed_returns_fail(self) -> None:
        """'failed' -> 'fail'."""
        from joy.mr_status import _map_glab_ci_status

        assert _map_glab_ci_status("failed") == "fail"

    def test_running_returns_pending(self) -> None:
        """'running' -> 'pending'."""
        from joy.mr_status import _map_glab_ci_status

        assert _map_glab_ci_status("running") == "pending"

    def test_pending_returns_pending(self) -> None:
        """'pending' -> 'pending'."""
        from joy.mr_status import _map_glab_ci_status

        assert _map_glab_ci_status("pending") == "pending"

    def test_canceled_returns_none(self) -> None:
        """'canceled' -> None."""
        from joy.mr_status import _map_glab_ci_status

        assert _map_glab_ci_status("canceled") is None

    def test_none_returns_none(self) -> None:
        """None -> None."""
        from joy.mr_status import _map_glab_ci_status

        assert _map_glab_ci_status(None) is None

    def test_created_returns_pending(self) -> None:
        """'created' -> 'pending'."""
        from joy.mr_status import _map_glab_ci_status

        assert _map_glab_ci_status("created") == "pending"

    def test_skipped_returns_none(self) -> None:
        """'skipped' -> None."""
        from joy.mr_status import _map_glab_ci_status

        assert _map_glab_ci_status("skipped") is None

    def test_manual_returns_none(self) -> None:
        """'manual' -> None."""
        from joy.mr_status import _map_glab_ci_status

        assert _map_glab_ci_status("manual") is None


# ---------------------------------------------------------------------------
# Tests: _fetch_github_mrs
# ---------------------------------------------------------------------------


class TestFetchGithubMrs:
    """Tests for GitHub PR fetching via gh CLI."""

    @patch("joy.mr_status.subprocess.run")
    def test_returns_mrinfo_for_matching_branches(self, mock_run: MagicMock) -> None:
        """gh pr list JSON returns correct MRInfo for matching branches."""
        from joy.mr_status import _fetch_github_mrs

        mock_run.return_value = _mock_result(stdout=json.dumps(GITHUB_PR_JSON))
        repo = Repo(
            name="myrepo",
            local_path="/tmp/repo",
            remote_url="https://github.com/owner/repo",
            forge="github",
        )
        result = _fetch_github_mrs(repo, {"feat-login"})

        assert ("myrepo", "feat-login") in result
        info = result[("myrepo", "feat-login")]
        assert info.mr_number == 42
        assert info.is_draft is False
        assert info.ci_status == "pass"
        assert info.author == "@pieter"
        assert info.last_commit_hash == "abc1234"
        assert info.last_commit_msg == "fix: login redirect"

    @patch("joy.mr_status.subprocess.run")
    def test_filters_out_non_matching_branches(self, mock_run: MagicMock) -> None:
        """PRs whose headRefName is not in active_branches are filtered out."""
        from joy.mr_status import _fetch_github_mrs

        mock_run.return_value = _mock_result(stdout=json.dumps(GITHUB_PR_JSON_MULTI))
        repo = Repo(
            name="myrepo",
            local_path="/tmp/repo",
            remote_url="https://github.com/owner/repo",
            forge="github",
        )
        # Only request feat-login, not unrelated-branch
        result = _fetch_github_mrs(repo, {"feat-login"})

        assert ("myrepo", "feat-login") in result
        assert ("myrepo", "unrelated-branch") not in result

    @patch("joy.mr_status.subprocess.run")
    def test_nonzero_returncode_raises_runtime_error(
        self, mock_run: MagicMock
    ) -> None:
        """Non-zero returncode from gh raises RuntimeError."""
        from joy.mr_status import _fetch_github_mrs

        mock_run.return_value = _mock_result(
            stderr="not authenticated", returncode=1
        )
        repo = Repo(
            name="myrepo",
            local_path="/tmp/repo",
            remote_url="https://github.com/owner/repo",
            forge="github",
        )
        with pytest.raises(RuntimeError, match="not authenticated"):
            _fetch_github_mrs(repo, {"feat-login"})

    @patch("joy.mr_status.subprocess.run")
    def test_empty_commits_list(self, mock_run: MagicMock) -> None:
        """PR with empty commits list returns empty hash and msg."""
        from joy.mr_status import _fetch_github_mrs

        pr_data = [
            {
                "number": 10,
                "headRefName": "empty-commits",
                "isDraft": False,
                "author": {"login": "dev"},
                "commits": [],
                "statusCheckRollup": [],
            }
        ]
        mock_run.return_value = _mock_result(stdout=json.dumps(pr_data))
        repo = Repo(
            name="myrepo",
            local_path="/tmp/repo",
            remote_url="https://github.com/owner/repo",
            forge="github",
        )
        result = _fetch_github_mrs(repo, {"empty-commits"})

        info = result[("myrepo", "empty-commits")]
        assert info.last_commit_hash == ""
        assert info.last_commit_msg == ""


# ---------------------------------------------------------------------------
# Tests: _fetch_gitlab_mrs
# ---------------------------------------------------------------------------


class TestFetchGitlabMrs:
    """Tests for GitLab MR fetching via glab CLI."""

    @patch("joy.mr_status.subprocess.run")
    def test_returns_mrinfo_for_matching_branches(self, mock_run: MagicMock) -> None:
        """glab mr list JSON returns correct MRInfo for matching branches."""
        from joy.mr_status import _fetch_gitlab_mrs

        # First call: glab mr list; Second call: glab ci get
        mock_run.side_effect = [
            _mock_result(stdout=json.dumps(GITLAB_MR_JSON)),
            _mock_result(stdout=json.dumps(GITLAB_CI_JSON)),
        ]
        repo = Repo(
            name="myrepo",
            local_path="/tmp/repo",
            remote_url="https://gitlab.com/owner/repo",
            forge="gitlab",
        )
        result = _fetch_gitlab_mrs(repo, {"feat-auth"})

        assert ("myrepo", "feat-auth") in result
        info = result[("myrepo", "feat-auth")]
        assert info.mr_number == 43
        assert info.is_draft is True
        assert info.ci_status == "pass"  # "success" maps to "pass"
        assert info.author == "@pieter"
        assert info.last_commit_hash == "abcdef0"  # sha[:7] from list endpoint
        assert info.last_commit_msg == ""

    @patch("joy.mr_status.subprocess.run")
    def test_calls_glab_ci_get_per_branch_with_mr(self, mock_run: MagicMock) -> None:
        """glab ci get is called for each branch that has an MR."""
        from joy.mr_status import _fetch_gitlab_mrs

        mr_data = [
            {
                "iid": 10,
                "source_branch": "branch-a",
                "draft": False,
                "author": {"username": "dev1"},
            },
            {
                "iid": 11,
                "source_branch": "branch-b",
                "draft": False,
                "author": {"username": "dev2"},
            },
        ]
        mock_run.side_effect = [
            _mock_result(stdout=json.dumps(mr_data)),
            _mock_result(stdout=json.dumps({"status": "success"})),
            _mock_result(stdout=json.dumps({"status": "failed"})),
        ]
        repo = Repo(
            name="myrepo",
            local_path="/tmp/repo",
            remote_url="https://gitlab.com/owner/repo",
            forge="gitlab",
        )
        result = _fetch_gitlab_mrs(repo, {"branch-a", "branch-b"})

        # Verify two ci get calls were made (one per branch with MR)
        assert mock_run.call_count == 3  # 1 mr list + 2 ci get
        assert result[("myrepo", "branch-a")].ci_status == "pass"
        assert result[("myrepo", "branch-b")].ci_status == "fail"

    @patch("joy.mr_status.subprocess.run")
    def test_nonzero_returncode_raises_runtime_error(
        self, mock_run: MagicMock
    ) -> None:
        """Non-zero returncode from glab mr list raises RuntimeError."""
        from joy.mr_status import _fetch_gitlab_mrs

        mock_run.return_value = _mock_result(
            stderr="not authenticated", returncode=1
        )
        repo = Repo(
            name="myrepo",
            local_path="/tmp/repo",
            remote_url="https://gitlab.com/owner/repo",
            forge="gitlab",
        )
        with pytest.raises(RuntimeError, match="not authenticated"):
            _fetch_gitlab_mrs(repo, {"feat-auth"})


# ---------------------------------------------------------------------------
# Tests: fetch_mr_data (integration-level)
# ---------------------------------------------------------------------------


class TestFetchMrData:
    """Tests for the top-level fetch_mr_data function."""

    @patch("joy.mr_status.subprocess.run")
    def test_skips_repos_with_unknown_forge(self, mock_run: MagicMock) -> None:
        """Repos with forge='unknown' are silently skipped."""
        from joy.mr_status import fetch_mr_data

        repos = [
            Repo(
                name="unknown-repo",
                local_path="/tmp/repo",
                remote_url="https://example.com/repo",
                forge="unknown",
            )
        ]
        worktrees = [
            WorktreeInfo(
                repo_name="unknown-repo", branch="main", path="/tmp/repo"
            )
        ]
        result = fetch_mr_data(repos, worktrees)

        assert result == {}
        mock_run.assert_not_called()

    @patch("joy.mr_status.subprocess.run")
    def test_catches_per_repo_exception_returns_partial(
        self, mock_run: MagicMock
    ) -> None:
        """Per-repo exception is caught; partial results returned."""
        from joy.mr_status import fetch_mr_data

        # First repo (github) fails, second repo (gitlab) succeeds
        mock_run.side_effect = [
            _mock_result(stderr="auth error", returncode=1),  # github fails
            _mock_result(stdout=json.dumps(GITLAB_MR_JSON)),  # gitlab mr list
            _mock_result(stdout=json.dumps(GITLAB_CI_JSON)),  # gitlab ci get
        ]
        repos = [
            Repo(
                name="gh-repo",
                local_path="/tmp/gh",
                remote_url="https://github.com/owner/gh-repo",
                forge="github",
            ),
            Repo(
                name="gl-repo",
                local_path="/tmp/gl",
                remote_url="https://gitlab.com/owner/gl-repo",
                forge="gitlab",
            ),
        ]
        worktrees = [
            WorktreeInfo(
                repo_name="gh-repo", branch="feat-login", path="/tmp/gh/wt"
            ),
            WorktreeInfo(
                repo_name="gl-repo", branch="feat-auth", path="/tmp/gl/wt"
            ),
        ]
        result = fetch_mr_data(repos, worktrees)

        # GitHub failed, GitLab succeeded — partial result
        assert ("gh-repo", "feat-login") not in result
        assert ("gl-repo", "feat-auth") in result

    @patch("joy.mr_status.subprocess.run")
    def test_never_raises_returns_empty_on_total_failure(
        self, mock_run: MagicMock
    ) -> None:
        """fetch_mr_data never raises — returns {} on total failure."""
        from joy.mr_status import fetch_mr_data

        mock_run.return_value = _mock_result(stderr="network error", returncode=1)
        repos = [
            Repo(
                name="gh-repo",
                local_path="/tmp/gh",
                remote_url="https://github.com/owner/gh-repo",
                forge="github",
            ),
        ]
        worktrees = [
            WorktreeInfo(
                repo_name="gh-repo", branch="main", path="/tmp/gh/wt"
            ),
        ]
        result = fetch_mr_data(repos, worktrees)

        assert result == {}

    @patch("joy.mr_status.subprocess.run")
    def test_mixed_github_gitlab_repos_returns_combined(
        self, mock_run: MagicMock
    ) -> None:
        """Mixed github+gitlab repos return combined results."""
        from joy.mr_status import fetch_mr_data

        mock_run.side_effect = [
            _mock_result(stdout=json.dumps(GITHUB_PR_JSON)),  # github pr list
            _mock_result(stdout=json.dumps(GITLAB_MR_JSON)),  # gitlab mr list
            _mock_result(stdout=json.dumps(GITLAB_CI_JSON)),  # gitlab ci get
        ]
        repos = [
            Repo(
                name="gh-repo",
                local_path="/tmp/gh",
                remote_url="https://github.com/owner/gh-repo",
                forge="github",
            ),
            Repo(
                name="gl-repo",
                local_path="/tmp/gl",
                remote_url="https://gitlab.com/owner/gl-repo",
                forge="gitlab",
            ),
        ]
        worktrees = [
            WorktreeInfo(
                repo_name="gh-repo",
                branch="feat-login",
                path="/tmp/gh/wt",
            ),
            WorktreeInfo(
                repo_name="gl-repo",
                branch="feat-auth",
                path="/tmp/gl/wt",
            ),
        ]
        result = fetch_mr_data(repos, worktrees)

        assert ("gh-repo", "feat-login") in result
        assert ("gl-repo", "feat-auth") in result
        assert result[("gh-repo", "feat-login")].mr_number == 42
        assert result[("gl-repo", "feat-auth")].mr_number == 43
