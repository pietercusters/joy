"""Tests for ProjectRow display."""
from __future__ import annotations

from rich.text import Text

from joy.models import ObjectItem, PresetKind, Project
from joy.widgets.project_list import ProjectRow
from joy.widgets.icons import ICON_WORKTREE, ICON_TERMINAL


def _make_project(name: str = "my-project", has_worktree: bool = False, has_terminals: bool = False, repo: str | None = None) -> Project:
    objects = []
    if has_worktree:
        objects.append(ObjectItem(kind=PresetKind.WORKTREE, label="wt", value="/path/to/wt"))
    if has_terminals:
        objects.append(ObjectItem(kind=PresetKind.TERMINALS, label="term", value="session"))
    return Project(name=name, objects=objects, repo=repo)


def _spans_for_icon(text: Text, icon_char: str) -> list:
    """Return style strings for spans containing icon_char."""
    return [str(span.style) for span in text._spans
            if icon_char in text.plain[span.start:span.end]]


def test_project_row_shows_project_name():
    """ProjectRow content includes the project name."""
    project = _make_project("test-project")
    row = ProjectRow(project)
    assert "test-project" in str(row.content)


# --- Test A: no WORKTREE object, wt_count=0 → worktree icon is grey50 dim ---

def test_worktree_icon_grey_when_no_object_and_no_live_count():
    """Test A: no stored WORKTREE, wt_count=0 → worktree icon style is 'grey50 dim'."""
    project = _make_project(has_worktree=False)
    has = ProjectRow._compute_has(project)
    content = ProjectRow.build_content(project, 80, mr_info=None, has=has, wt_count=0, agent_count=0)
    spans = _spans_for_icon(content, ICON_WORKTREE)
    assert spans, "Worktree icon should have a span"
    assert all("grey50" in s and "dim" in s for s in spans), (
        f"Expected 'grey50 dim' style but got: {spans}"
    )


# --- Test B: no WORKTREE object, wt_count=1 → worktree icon is cyan ---

def test_worktree_icon_cyan_when_live_count_nonzero():
    """Test B: no stored WORKTREE, wt_count=1 → worktree icon style is 'cyan'."""
    project = _make_project(has_worktree=False)
    has = ProjectRow._compute_has(project)
    content = ProjectRow.build_content(project, 80, mr_info=None, has=has, wt_count=1, agent_count=0)
    spans = _spans_for_icon(content, ICON_WORKTREE)
    assert spans, "Worktree icon should have a span"
    assert any("cyan" in s for s in spans), (
        f"Expected 'cyan' style but got: {spans}"
    )


# --- Test C: has WORKTREE object, wt_count=0 → worktree icon is still cyan ---

def test_worktree_icon_cyan_when_stored_object_even_without_live_count():
    """Test C: stored WORKTREE exists, wt_count=0 → worktree icon style is 'cyan'."""
    project = _make_project(has_worktree=True)
    has = ProjectRow._compute_has(project)
    content = ProjectRow.build_content(project, 80, mr_info=None, has=has, wt_count=0, agent_count=0)
    spans = _spans_for_icon(content, ICON_WORKTREE)
    assert spans, "Worktree icon should have a span"
    assert any("cyan" in s for s in spans), (
        f"Expected 'cyan' style (stored object) but got: {spans}"
    )


# --- Test D: no TERMINALS object, agent_count=0 → terminal icon is grey50 dim ---

def test_terminal_icon_grey_when_no_object_and_no_live_count():
    """Test D: no stored TERMINALS, agent_count=0 → terminal icon style is 'grey50 dim'."""
    project = _make_project(has_terminals=False)
    has = ProjectRow._compute_has(project)
    content = ProjectRow.build_content(project, 80, mr_info=None, has=has, wt_count=0, agent_count=0)
    spans = _spans_for_icon(content, ICON_TERMINAL)
    assert spans, "Terminal icon should have a span"
    assert all("grey50" in s and "dim" in s for s in spans), (
        f"Expected 'grey50 dim' style but got: {spans}"
    )


# --- Test E: no TERMINALS object, agent_count=1 → terminal icon is cyan ---

def test_terminal_icon_cyan_when_live_count_nonzero():
    """Test E: no stored TERMINALS, agent_count=1 → terminal icon style is 'cyan'."""
    project = _make_project(has_terminals=False)
    has = ProjectRow._compute_has(project)
    content = ProjectRow.build_content(project, 80, mr_info=None, has=has, wt_count=0, agent_count=1)
    spans = _spans_for_icon(content, ICON_TERMINAL)
    assert spans, "Terminal icon should have a span"
    assert any("cyan" in s for s in spans), (
        f"Expected 'cyan' style but got: {spans}"
    )


# --- Repo name display tests ---


def test_project_row_shows_repo_name_when_set():
    """Repo name appears dim in row content when project has a repo."""
    project = _make_project(repo="my-repo")
    has = ProjectRow._compute_has(project)
    content = ProjectRow.build_content(project, 80, mr_info=None, has=has, wt_count=0, agent_count=0, repo_name="my-repo")
    assert "my-repo" in content.plain, f"Expected 'my-repo' in plain text: {content.plain!r}"
    # Verify dim style on the repo name span
    repo_spans = [str(span.style) for span in content._spans
                  if "my-repo" in content.plain[span.start:span.end]]
    assert repo_spans, "Repo name should have a span"
    assert all("dim" in s for s in repo_spans), (
        f"Expected 'dim' style on repo name but got: {repo_spans}"
    )


def test_project_row_hides_repo_name_when_none():
    """No extra repo text when repo_name is None."""
    project = _make_project(repo=None)
    has = ProjectRow._compute_has(project)
    content_no_repo = ProjectRow.build_content(project, 80, mr_info=None, has=has, wt_count=0, agent_count=0, repo_name=None)
    # Verify the plain text does NOT contain any repo label
    # The content should just be: status dot + space + name + padding + space + ribbon
    assert "my-repo" not in content_no_repo.plain


def test_project_row_constructor_passes_repo():
    """ProjectRow constructor passes repo to build_content."""
    project = _make_project(repo="test-repo")
    row = ProjectRow(project)
    assert "test-repo" in str(row.content), f"Expected 'test-repo' in row content: {str(row.content)!r}"
