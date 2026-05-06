"""Tests for MR/CI status fetch module."""
from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, call, patch

import pytest

from joy.models import MRDetail, MRInfo, Repo, WorktreeInfo


# ---------------------------------------------------------------------------
# Test fixtures -- mock CLI JSON responses
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
        "url": "https://github.com/owner/repo/pull/42",
        "reviewDecision": "APPROVED",
        "title": "Fix login redirect",
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
        "url": "https://github.com/owner/repo/pull/42",
        "reviewDecision": "APPROVED",
        "title": "Fix login redirect",
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
        "url": "https://github.com/owner/repo/pull/99",
        "reviewDecision": "",
        "title": "Unrelated work",
    },
]

GITLAB_MR_JSON = [
    {
        "iid": 43,
        "source_branch": "feat-auth",
        "draft": True,
        "author": {"username": "pieter"},
        "sha": "abcdef0123456789",
        "web_url": "https://gitlab.com/owner/repo/-/merge_requests/43",
        "title": "Add auth flow",
        "detailed_merge_status": "not_approved",
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
        """MRInfo has mr_number, is_draft, ci_status, url."""
        info = MRInfo(
            mr_number=42,
            is_draft=False,
            ci_status="pass",
            url="https://github.com/x/y/pull/42",
        )
        assert info.mr_number == 42
        assert info.is_draft is False
        assert info.ci_status == "pass"
        assert info.url == "https://github.com/x/y/pull/42"

    def test_mrinfo_ci_status_none(self) -> None:
        """MRInfo ci_status can be None."""
        info = MRInfo(mr_number=1, is_draft=False, ci_status=None)
        assert info.ci_status is None


# ---------------------------------------------------------------------------
# Tests: MRDetail dataclass
# ---------------------------------------------------------------------------


class TestMRDetailDataclass:
    """Verify MRDetail dataclass has correct fields."""

    def test_mrdetail_has_all_fields(self) -> None:
        detail = MRDetail(
            mr_number=42,
            title="Fix login",
            is_draft=False,
            ci_status="pass",
            review_status="approved",
            url="https://github.com/x/y/pull/42",
            repo_name="myrepo",
            branch="feat-login",
            is_review_request=False,
        )
        assert detail.mr_number == 42
        assert detail.title == "Fix login"
        assert detail.is_draft is False
        assert detail.ci_status == "pass"
        assert detail.review_status == "approved"
        assert detail.url == "https://github.com/x/y/pull/42"
        assert detail.repo_name == "myrepo"
        assert detail.branch == "feat-login"
        assert detail.is_review_request is False

    def test_mrdetail_defaults(self) -> None:
        detail = MRDetail(
            mr_number=1,
            title="Test",
            is_draft=True,
            ci_status=None,
            review_status=None,
        )
        assert detail.url == ""
        assert detail.repo_name == ""
        assert detail.branch == ""
        assert detail.is_review_request is False


# ---------------------------------------------------------------------------
# Tests: BatchMRResult dataclass
# ---------------------------------------------------------------------------


class TestBatchMRResult:
    """Verify BatchMRResult dataclass structure."""

    def test_empty_batch_result(self) -> None:
        from joy.mr_status import BatchMRResult
        result = BatchMRResult()
        assert result.by_branch == {}
        assert result.authored == []
        assert result.review_requests == []

    def test_batch_result_with_data(self) -> None:
        from joy.mr_status import BatchMRResult
        mr_info = MRInfo(mr_number=1, is_draft=False, ci_status="pass")
        detail = MRDetail(mr_number=1, title="T", is_draft=False, ci_status="pass", review_status=None)
        result = BatchMRResult(
            by_branch={("repo", "branch"): mr_info},
            authored=[detail],
            review_requests=[detail],
        )
        assert len(result.by_branch) == 1
        assert len(result.authored) == 1
        assert len(result.review_requests) == 1


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
# Tests: Review status mapping
# ---------------------------------------------------------------------------


class TestReviewStatusMapping:
    """Tests for GitHub reviewDecision and GitLab detailed_merge_status mapping."""

    def test_gh_approved(self) -> None:
        from joy.mr_status import _map_gh_review_decision
        assert _map_gh_review_decision("APPROVED") == "approved"

    def test_gh_changes_requested(self) -> None:
        from joy.mr_status import _map_gh_review_decision
        assert _map_gh_review_decision("CHANGES_REQUESTED") == "changes_requested"

    def test_gh_review_required(self) -> None:
        from joy.mr_status import _map_gh_review_decision
        assert _map_gh_review_decision("REVIEW_REQUIRED") == "review_required"

    def test_gh_empty_string_returns_none(self) -> None:
        from joy.mr_status import _map_gh_review_decision
        assert _map_gh_review_decision("") is None

    def test_gh_none_returns_none(self) -> None:
        from joy.mr_status import _map_gh_review_decision
        assert _map_gh_review_decision(None) is None

    def test_gh_unknown_returns_none(self) -> None:
        from joy.mr_status import _map_gh_review_decision
        assert _map_gh_review_decision("SOMETHING_ELSE") is None

    def test_gl_not_approved(self) -> None:
        from joy.mr_status import _map_gl_review_status
        assert _map_gl_review_status("not_approved") == "review_required"

    def test_gl_mergeable(self) -> None:
        from joy.mr_status import _map_gl_review_status
        assert _map_gl_review_status("mergeable") == "approved"

    def test_gl_discussions_not_resolved(self) -> None:
        from joy.mr_status import _map_gl_review_status
        assert _map_gl_review_status("discussions_not_resolved") == "changes_requested"

    def test_gl_none_returns_none(self) -> None:
        from joy.mr_status import _map_gl_review_status
        assert _map_gl_review_status(None) is None

    def test_gl_unknown_returns_none(self) -> None:
        from joy.mr_status import _map_gl_review_status
        assert _map_gl_review_status("something_else") is None


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
        assert info.url == "https://github.com/owner/repo/pull/42"

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


# ---------------------------------------------------------------------------
# Tests: _fetch_github_authored_mrs
# ---------------------------------------------------------------------------


class TestFetchGithubAuthoredMrs:
    """Tests for GitHub authored PR fetching via gh pr list --author @me."""

    @patch("joy.mr_status.subprocess.run")
    def test_returns_mrdetail_list(self, mock_run: MagicMock) -> None:
        from joy.mr_status import _fetch_github_authored_mrs

        mock_run.return_value = _mock_result(stdout=json.dumps(GITHUB_PR_JSON))
        repo = Repo(
            name="myrepo",
            local_path="/tmp/repo",
            remote_url="https://github.com/owner/repo",
            forge="github",
        )
        result = _fetch_github_authored_mrs(repo)

        assert len(result) == 1
        detail = result[0]
        assert isinstance(detail, MRDetail)
        assert detail.mr_number == 42
        assert detail.title == "Fix login redirect"
        assert detail.is_draft is False
        assert detail.ci_status == "pass"
        assert detail.review_status == "approved"
        assert detail.repo_name == "myrepo"
        assert detail.branch == "feat-login"
        assert detail.is_review_request is False

    @patch("joy.mr_status.subprocess.run")
    def test_nonzero_returncode_raises(self, mock_run: MagicMock) -> None:
        from joy.mr_status import _fetch_github_authored_mrs

        mock_run.return_value = _mock_result(stderr="auth error", returncode=1)
        repo = Repo(name="r", local_path="/tmp", remote_url="https://github.com/o/r", forge="github")
        with pytest.raises(RuntimeError):
            _fetch_github_authored_mrs(repo)


# ---------------------------------------------------------------------------
# Tests: _fetch_github_review_requests
# ---------------------------------------------------------------------------


class TestFetchGithubReviewRequests:
    """Tests for GitHub review request fetching via gh pr list --search."""

    @patch("joy.mr_status.subprocess.run")
    def test_returns_mrdetail_with_is_review_request(self, mock_run: MagicMock) -> None:
        from joy.mr_status import _fetch_github_review_requests

        mock_run.return_value = _mock_result(stdout=json.dumps(GITHUB_PR_JSON))
        repo = Repo(
            name="myrepo",
            local_path="/tmp/repo",
            remote_url="https://github.com/owner/repo",
            forge="github",
        )
        result = _fetch_github_review_requests(repo)

        assert len(result) == 1
        assert result[0].is_review_request is True
        assert result[0].mr_number == 42

    @patch("joy.mr_status.subprocess.run")
    def test_nonzero_returncode_raises(self, mock_run: MagicMock) -> None:
        from joy.mr_status import _fetch_github_review_requests

        mock_run.return_value = _mock_result(stderr="auth error", returncode=1)
        repo = Repo(name="r", local_path="/tmp", remote_url="https://github.com/o/r", forge="github")
        with pytest.raises(RuntimeError):
            _fetch_github_review_requests(repo)


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
        assert info.url == "https://gitlab.com/owner/repo/-/merge_requests/43"

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
                "web_url": "https://gitlab.com/owner/repo/-/merge_requests/10",
                "title": "Branch A work",
                "detailed_merge_status": "mergeable",
            },
            {
                "iid": 11,
                "source_branch": "branch-b",
                "draft": False,
                "author": {"username": "dev2"},
                "web_url": "https://gitlab.com/owner/repo/-/merge_requests/11",
                "title": "Branch B work",
                "detailed_merge_status": "not_approved",
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
# Tests: _fetch_gitlab_authored_mrs
# ---------------------------------------------------------------------------


class TestFetchGitlabAuthoredMrs:
    """Tests for GitLab authored MR fetching via glab mr list --author @me."""

    @patch("joy.mr_status.subprocess.run")
    def test_returns_mrdetail_list(self, mock_run: MagicMock) -> None:
        from joy.mr_status import _fetch_gitlab_authored_mrs

        # First call: glab mr list; Second call: glab ci get for each MR
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
        result = _fetch_gitlab_authored_mrs(repo)

        assert len(result) == 1
        detail = result[0]
        assert isinstance(detail, MRDetail)
        assert detail.mr_number == 43
        assert detail.title == "Add auth flow"
        assert detail.is_draft is True
        assert detail.review_status == "review_required"  # "not_approved" -> "review_required"
        assert detail.repo_name == "myrepo"
        assert detail.is_review_request is False

    @patch("joy.mr_status.subprocess.run")
    def test_nonzero_returncode_raises(self, mock_run: MagicMock) -> None:
        from joy.mr_status import _fetch_gitlab_authored_mrs

        mock_run.return_value = _mock_result(stderr="auth error", returncode=1)
        repo = Repo(name="r", local_path="/tmp", remote_url="https://gitlab.com/o/r", forge="gitlab")
        with pytest.raises(RuntimeError):
            _fetch_gitlab_authored_mrs(repo)


# ---------------------------------------------------------------------------
# Tests: _fetch_gitlab_review_requests
# ---------------------------------------------------------------------------


class TestFetchGitlabReviewRequests:
    """Tests for GitLab review request fetching via glab mr list --reviewer @me."""

    @patch("joy.mr_status.subprocess.run")
    def test_returns_mrdetail_with_is_review_request(self, mock_run: MagicMock) -> None:
        from joy.mr_status import _fetch_gitlab_review_requests

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
        result = _fetch_gitlab_review_requests(repo)

        assert len(result) == 1
        assert result[0].is_review_request is True
        assert result[0].mr_number == 43

    @patch("joy.mr_status.subprocess.run")
    def test_nonzero_returncode_raises(self, mock_run: MagicMock) -> None:
        from joy.mr_status import _fetch_gitlab_review_requests

        mock_run.return_value = _mock_result(stderr="auth error", returncode=1)
        repo = Repo(name="r", local_path="/tmp", remote_url="https://gitlab.com/o/r", forge="gitlab")
        with pytest.raises(RuntimeError):
            _fetch_gitlab_review_requests(repo)


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

        assert result.by_branch == {}
        assert result.authored == []
        assert result.review_requests == []
        mock_run.assert_not_called()

    @patch("joy.mr_status.subprocess.run")
    def test_catches_per_repo_exception_returns_partial(
        self, mock_run: MagicMock
    ) -> None:
        """Per-repo exception is caught; partial results returned."""
        from joy.mr_status import fetch_mr_data

        # First repo (github): all 3 calls fail (branch list, authored, review requests)
        # Second repo (gitlab): mr list succeeds, ci get succeeds, authored succeeds + ci, review succeeds + ci
        mock_run.side_effect = [
            _mock_result(stderr="auth error", returncode=1),  # github branch list fails
            _mock_result(stderr="auth error", returncode=1),  # github authored fails
            _mock_result(stderr="auth error", returncode=1),  # github review requests fails
            # No fallback calls for github since mr_map is empty (no covered branches)
            # but active branches exist, so fallback for feat-login:
            _mock_result(stderr="auth error", returncode=1),  # github fallback fails
            _mock_result(stdout=json.dumps(GITLAB_MR_JSON)),  # gitlab mr list
            _mock_result(stdout=json.dumps(GITLAB_CI_JSON)),  # gitlab ci get for feat-auth
            _mock_result(stdout=json.dumps(GITLAB_MR_JSON)),  # gitlab authored
            _mock_result(stdout=json.dumps(GITLAB_CI_JSON)),  # gitlab ci get for authored
            _mock_result(stdout=json.dumps(GITLAB_MR_JSON)),  # gitlab review requests
            _mock_result(stdout=json.dumps(GITLAB_CI_JSON)),  # gitlab ci get for review
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

        # GitHub failed, GitLab succeeded -- partial result
        assert ("gh-repo", "feat-login") not in result.by_branch
        assert ("gl-repo", "feat-auth") in result.by_branch

    @patch("joy.mr_status.subprocess.run")
    def test_never_raises_returns_empty_on_total_failure(
        self, mock_run: MagicMock
    ) -> None:
        """fetch_mr_data never raises -- returns empty BatchMRResult on total failure."""
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

        assert result.by_branch == {}
        assert result.authored == []
        assert result.review_requests == []

    @patch("joy.mr_status.subprocess.run")
    def test_mixed_github_gitlab_repos_returns_combined(
        self, mock_run: MagicMock
    ) -> None:
        """Mixed github+gitlab repos return combined results."""
        from joy.mr_status import fetch_mr_data

        mock_run.side_effect = [
            _mock_result(stdout=json.dumps(GITHUB_PR_JSON)),   # github branch list
            _mock_result(stdout=json.dumps(GITHUB_PR_JSON)),   # github authored
            _mock_result(stdout=json.dumps(GITHUB_PR_JSON)),   # github review requests
            # No fallback needed -- feat-login covered by batch
            _mock_result(stdout=json.dumps(GITLAB_MR_JSON)),   # gitlab mr list
            _mock_result(stdout=json.dumps(GITLAB_CI_JSON)),   # gitlab ci get
            _mock_result(stdout=json.dumps(GITLAB_MR_JSON)),   # gitlab authored
            _mock_result(stdout=json.dumps(GITLAB_CI_JSON)),   # gitlab ci get for authored
            _mock_result(stdout=json.dumps(GITLAB_MR_JSON)),   # gitlab review requests
            _mock_result(stdout=json.dumps(GITLAB_CI_JSON)),   # gitlab ci get for review
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

        assert ("gh-repo", "feat-login") in result.by_branch
        assert ("gl-repo", "feat-auth") in result.by_branch
        assert result.by_branch[("gh-repo", "feat-login")].mr_number == 42
        assert result.by_branch[("gl-repo", "feat-auth")].mr_number == 43
        assert len(result.authored) > 0
        assert len(result.review_requests) > 0


# ---------------------------------------------------------------------------
# Tests: Per-branch fallback
# ---------------------------------------------------------------------------


class TestPerBranchFallback:
    """Tests for per-branch fallback queries when batch misses branches."""

    @patch("joy.mr_status.subprocess.run")
    def test_fallback_fills_missing_branch(self, mock_run: MagicMock) -> None:
        """Branch missing from batch result gets queried individually."""
        from joy.mr_status import fetch_mr_data

        # Batch returns MR for feat-login but NOT feat-other
        batch_json = [
            {
                "number": 42,
                "headRefName": "feat-login",
                "isDraft": False,
                "statusCheckRollup": [{"status": "COMPLETED", "conclusion": "SUCCESS"}],
                "url": "https://github.com/owner/repo/pull/42",
                "reviewDecision": "APPROVED",
                "title": "Fix login",
            }
        ]
        # Fallback for feat-other returns a PR
        fallback_json = [
            {
                "number": 55,
                "isDraft": False,
                "statusCheckRollup": [],
                "url": "https://github.com/owner/repo/pull/55",
            }
        ]
        mock_run.side_effect = [
            _mock_result(stdout=json.dumps(batch_json)),       # github branch list
            _mock_result(stdout=json.dumps(batch_json)),       # github authored
            _mock_result(stdout=json.dumps([])),               # github review requests
            _mock_result(stdout=json.dumps(fallback_json)),    # github fallback for feat-other
        ]
        repos = [
            Repo(
                name="myrepo",
                local_path="/tmp/repo",
                remote_url="https://github.com/owner/repo",
                forge="github",
            )
        ]
        worktrees = [
            WorktreeInfo(repo_name="myrepo", branch="feat-login", path="/tmp/wt1"),
            WorktreeInfo(repo_name="myrepo", branch="feat-other", path="/tmp/wt2"),
        ]
        result = fetch_mr_data(repos, worktrees)

        # Both branches should be in by_branch
        assert ("myrepo", "feat-login") in result.by_branch
        assert ("myrepo", "feat-other") in result.by_branch
        assert result.by_branch[("myrepo", "feat-login")].mr_number == 42
        assert result.by_branch[("myrepo", "feat-other")].mr_number == 55

    @patch("joy.mr_status.subprocess.run")
    def test_fallback_returns_none_branch_not_added(self, mock_run: MagicMock) -> None:
        """When fallback returns None (no PR), branch is not in by_branch."""
        from joy.mr_status import fetch_mr_data

        batch_json = [
            {
                "number": 42,
                "headRefName": "feat-login",
                "isDraft": False,
                "statusCheckRollup": [],
                "url": "https://github.com/owner/repo/pull/42",
                "reviewDecision": "",
                "title": "Fix login",
            }
        ]
        mock_run.side_effect = [
            _mock_result(stdout=json.dumps(batch_json)),  # github branch list
            _mock_result(stdout=json.dumps(batch_json)),  # github authored
            _mock_result(stdout=json.dumps([])),           # github review requests
            _mock_result(stdout=json.dumps([])),           # github fallback returns empty
        ]
        repos = [
            Repo(
                name="myrepo",
                local_path="/tmp/repo",
                remote_url="https://github.com/owner/repo",
                forge="github",
            )
        ]
        worktrees = [
            WorktreeInfo(repo_name="myrepo", branch="feat-login", path="/tmp/wt1"),
            WorktreeInfo(repo_name="myrepo", branch="no-pr-branch", path="/tmp/wt2"),
        ]
        result = fetch_mr_data(repos, worktrees)

        assert ("myrepo", "feat-login") in result.by_branch
        assert ("myrepo", "no-pr-branch") not in result.by_branch

    @patch("joy.mr_status.subprocess.run")
    def test_fallback_error_silently_skipped(self, mock_run: MagicMock) -> None:
        """When fallback call fails, branch is silently skipped."""
        from joy.mr_status import fetch_mr_data

        mock_run.side_effect = [
            _mock_result(stdout=json.dumps([])),                 # github branch list (empty)
            _mock_result(stdout=json.dumps([])),                 # github authored (empty)
            _mock_result(stdout=json.dumps([])),                 # github review requests (empty)
            _mock_result(stderr="network error", returncode=1),  # github fallback fails
        ]
        repos = [
            Repo(
                name="myrepo",
                local_path="/tmp/repo",
                remote_url="https://github.com/owner/repo",
                forge="github",
            )
        ]
        worktrees = [
            WorktreeInfo(repo_name="myrepo", branch="orphan-branch", path="/tmp/wt1"),
        ]
        result = fetch_mr_data(repos, worktrees)

        # No crash, just empty
        assert ("myrepo", "orphan-branch") not in result.by_branch
