"""Tests for the TOML persistence layer (store.py)."""
from __future__ import annotations

import os
import subprocess
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from joy.models import Config, ObjectItem, PresetKind, Project, Repo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(
    name: str = "test-project",
    *,
    created: date = date(2026, 1, 15),
) -> Project:
    return Project(
        name=name,
        objects=[
            ObjectItem(
                kind=PresetKind.MR,
                value="https://gitlab.com/org/repo/-/merge_requests/1",
                label="MR #1",
                open_by_default=True,
            ),
            ObjectItem(
                kind=PresetKind.BRANCH,
                value="feature/my-branch",
                label="Branch",
            ),
        ],
        created=created,
    )


# ---------------------------------------------------------------------------
# Round-trip tests
# ---------------------------------------------------------------------------


def test_round_trip_single_project(tmp_path: Path, sample_project: Project) -> None:
    """Save a project, load it back, assert equality on all fields."""
    from joy.store import load_projects, save_projects

    projects_path = tmp_path / "projects.toml"
    save_projects(projects=[sample_project], path=projects_path)
    loaded = load_projects(path=projects_path)

    assert len(loaded) == 1
    project = loaded[0]
    assert project.name == sample_project.name
    assert project.created == sample_project.created
    assert len(project.objects) == len(sample_project.objects)

    for orig, loaded_obj in zip(sample_project.objects, project.objects):
        assert loaded_obj.kind == orig.kind
        assert loaded_obj.value == orig.value
        assert loaded_obj.label == orig.label
        assert loaded_obj.open_by_default == orig.open_by_default


def test_round_trip_multiple_projects(tmp_path: Path) -> None:
    """Save 2 projects, load back, assert both present with correct data."""
    from joy.store import load_projects, save_projects

    projects_path = tmp_path / "projects.toml"
    alpha = _make_project(name="alpha", created=date(2026, 2, 1))
    beta = _make_project(name="beta", created=date(2026, 3, 10))

    save_projects(projects=[alpha, beta], path=projects_path)
    loaded = load_projects(path=projects_path)

    assert len(loaded) == 2
    loaded_by_name = {p.name: p for p in loaded}

    assert "alpha" in loaded_by_name
    assert "beta" in loaded_by_name
    assert loaded_by_name["alpha"].created == date(2026, 2, 1)
    assert loaded_by_name["beta"].created == date(2026, 3, 10)


def test_round_trip_empty_objects(tmp_path: Path) -> None:
    """Project with no objects round-trips correctly."""
    from joy.store import load_projects, save_projects

    projects_path = tmp_path / "projects.toml"
    empty = Project(name="empty-project", objects=[], created=date(2026, 1, 1))

    save_projects(projects=[empty], path=projects_path)
    loaded = load_projects(path=projects_path)

    assert len(loaded) == 1
    assert loaded[0].name == "empty-project"
    assert loaded[0].objects == []


# ---------------------------------------------------------------------------
# TOML schema tests
# ---------------------------------------------------------------------------


def test_toml_keyed_schema(tmp_path: Path, sample_project: Project) -> None:
    """Save project, read raw TOML text, assert keyed schema [projects.{name}]."""
    from joy.store import save_projects

    projects_path = tmp_path / "projects.toml"
    save_projects(projects=[sample_project], path=projects_path)

    raw = projects_path.read_text(encoding="utf-8")

    # Must use keyed schema, NOT array-of-tables syntax for the top-level project entry
    assert "[projects.test-project]" in raw
    # Must NOT use [[project]] array syntax at top level
    assert "[[project]]" not in raw


# ---------------------------------------------------------------------------
# Directory creation tests
# ---------------------------------------------------------------------------


def test_save_creates_directory(tmp_path: Path) -> None:
    """Save to a non-existent subdirectory, assert the directory is created."""
    from joy.store import save_projects

    projects_path = tmp_path / "deeply" / "nested" / "projects.toml"
    project = _make_project()

    save_projects(projects=[project], path=projects_path)

    assert projects_path.exists()


# ---------------------------------------------------------------------------
# Atomic write tests
# ---------------------------------------------------------------------------


def test_atomic_write(tmp_path: Path, sample_project: Project, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify os.replace is called and a .tmp file pattern is used."""
    from joy import store

    projects_path = tmp_path / "projects.toml"

    replace_calls: list[tuple[str, str]] = []
    original_replace = os.replace

    def mock_replace(src: str, dst: str) -> None:
        replace_calls.append((str(src), str(dst)))
        original_replace(src, dst)

    monkeypatch.setattr(os, "replace", mock_replace)

    from joy.store import save_projects

    save_projects(projects=[sample_project], path=projects_path)

    # os.replace must have been called exactly once
    assert len(replace_calls) == 1
    src, dst = replace_calls[0]
    # The temp file must have a .tmp suffix
    assert src.endswith(".tmp")
    # The destination must be the target path
    assert dst == str(projects_path)
    # The temp file must have been cleaned up (moved to destination)
    assert projects_path.exists()


# ---------------------------------------------------------------------------
# Missing file tests
# ---------------------------------------------------------------------------


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    """load_projects from non-existent path returns empty list."""
    from joy.store import load_projects

    projects_path = tmp_path / "nonexistent.toml"
    result = load_projects(path=projects_path)

    assert result == []


def test_load_config_missing_returns_default(tmp_path: Path) -> None:
    """load_config from non-existent path returns Config() with defaults."""
    from joy.store import load_config

    config_path = tmp_path / "nonexistent_config.toml"
    result = load_config(path=config_path)

    expected = Config()
    assert result == expected


# ---------------------------------------------------------------------------
# Config round-trip
# ---------------------------------------------------------------------------


def test_config_round_trip(tmp_path: Path) -> None:
    """Save config with custom values, load back, assert equality."""
    from joy.store import load_config, save_config

    config_path = tmp_path / "config.toml"
    custom = Config(
        ide="VSCode",
        editor="Vim",
        obsidian_vault="/Users/dev/vault",
        terminal="Alacritty",
        default_open_kinds=["worktree", "mr"],
    )

    save_config(config=custom, path=config_path)
    loaded = load_config(path=config_path)

    assert loaded == custom


# ---------------------------------------------------------------------------
# Field preservation tests
# ---------------------------------------------------------------------------


def test_object_fields_preserved(tmp_path: Path) -> None:
    """Save project with open_by_default=True and label set, load back, verify both."""
    from joy.store import load_projects, save_projects

    projects_path = tmp_path / "projects.toml"
    obj = ObjectItem(
        kind=PresetKind.WORKTREE,
        value="/Users/dev/worktrees/project",
        label="My Worktree",
        open_by_default=True,
    )
    project = Project(name="field-test", objects=[obj], created=date(2026, 4, 1))

    save_projects(projects=[project], path=projects_path)
    loaded = load_projects(path=projects_path)

    assert len(loaded) == 1
    loaded_obj = loaded[0].objects[0]
    assert loaded_obj.kind == PresetKind.WORKTREE
    assert loaded_obj.value == "/Users/dev/worktrees/project"
    assert loaded_obj.label == "My Worktree"
    assert loaded_obj.open_by_default is True


# ---------------------------------------------------------------------------
# Toggle round-trip test (ACT-03)
# ---------------------------------------------------------------------------


def test_toggle_round_trip(tmp_path: Path) -> None:
    """ACT-03: Toggling open_by_default persists through save/load cycle."""
    from joy.store import load_projects, save_projects

    projects_path = tmp_path / "projects.toml"
    obj = ObjectItem(kind=PresetKind.BRANCH, value="main", open_by_default=False)
    project = Project(name="toggle-test", objects=[obj])
    save_projects(projects=[project], path=projects_path)
    # Toggle
    loaded = load_projects(path=projects_path)
    loaded[0].objects[0].open_by_default = True
    save_projects(projects=loaded, path=projects_path)
    reloaded = load_projects(path=projects_path)
    assert reloaded[0].objects[0].open_by_default is True


# ---------------------------------------------------------------------------
# Config new fields round-trip tests
# ---------------------------------------------------------------------------


def test_config_round_trip_new_fields(tmp_path: Path) -> None:
    """Save Config with new fields, load back, assert both fields match."""
    from joy.store import load_config, save_config

    config_path = tmp_path / "config.toml"
    custom = Config(refresh_interval=45, branch_filter=["develop"])
    save_config(config=custom, path=config_path)
    loaded = load_config(path=config_path)
    assert loaded.refresh_interval == 45
    assert loaded.branch_filter == ["develop"]


def test_config_backward_compat_missing_new_fields(tmp_path: Path) -> None:
    """Old config.toml files without new fields load with correct defaults."""
    import tomllib

    config_path = tmp_path / "config.toml"
    # Write raw TOML with only old fields (no refresh_interval or branch_filter)
    old_toml = (
        'ide = "VSCode"\n'
        'editor = "Vim"\n'
        'obsidian_vault = ""\n'
        'terminal = "iTerm2"\n'
        'default_open_kinds = ["worktree", "agents"]\n'
    )
    config_path.write_bytes(old_toml.encode("utf-8"))

    from joy.store import load_config

    loaded = load_config(path=config_path)
    assert loaded.refresh_interval == 30
    assert loaded.branch_filter == ["main", "testing"]


# ---------------------------------------------------------------------------
# Repo store tests
# ---------------------------------------------------------------------------


class TestRepoStore:
    """Tests for Repo TOML persistence (load_repos / save_repos)."""

    def test_repo_round_trip_single(self, tmp_path: Path) -> None:
        """Save a single Repo, load it back, assert all 4 fields match."""
        from joy.store import load_repos, save_repos

        repos_path = tmp_path / "repos.toml"
        repo = Repo(
            name="joy",
            local_path="/dev/joy",
            remote_url="git@github.com:user/joy.git",
            forge="github",
        )
        save_repos([repo], path=repos_path)
        loaded = load_repos(path=repos_path)

        assert len(loaded) == 1
        r = loaded[0]
        assert r.name == "joy"
        assert r.local_path == "/dev/joy"
        assert r.remote_url == "git@github.com:user/joy.git"
        assert r.forge == "github"

    def test_repo_round_trip_multiple(self, tmp_path: Path) -> None:
        """Save 2 repos, load back, both present with correct fields."""
        from joy.store import load_repos, save_repos

        repos_path = tmp_path / "repos.toml"
        alpha = Repo(name="alpha", local_path="/dev/alpha")
        beta = Repo(name="beta", local_path="/dev/beta", remote_url="https://gitlab.com/user/beta.git", forge="gitlab")
        save_repos([alpha, beta], path=repos_path)
        loaded = load_repos(path=repos_path)

        assert len(loaded) == 2
        by_name = {r.name: r for r in loaded}
        assert "alpha" in by_name
        assert "beta" in by_name
        assert by_name["alpha"].local_path == "/dev/alpha"
        assert by_name["beta"].forge == "gitlab"

    def test_repo_round_trip_defaults(self, tmp_path: Path) -> None:
        """Repo with only required fields round-trips with correct defaults."""
        from joy.store import load_repos, save_repos

        repos_path = tmp_path / "repos.toml"
        repo = Repo(name="bare", local_path="/dev/bare")
        save_repos([repo], path=repos_path)
        loaded = load_repos(path=repos_path)

        assert len(loaded) == 1
        r = loaded[0]
        assert r.remote_url == ""
        assert r.forge == "unknown"

    def test_load_repos_missing_file(self, tmp_path: Path) -> None:
        """load_repos from non-existent path returns empty list."""
        from joy.store import load_repos

        result = load_repos(path=tmp_path / "nope.toml")
        assert result == []

    def test_save_repos_creates_directory(self, tmp_path: Path) -> None:
        """save_repos creates parent directories that do not yet exist."""
        from joy.store import save_repos

        repos_path = tmp_path / "deep" / "repos.toml"
        save_repos([Repo(name="r", local_path="/dev/r")], path=repos_path)
        assert repos_path.exists()

    def test_repo_toml_keyed_schema(self, tmp_path: Path) -> None:
        """Saved repos.toml uses [repos.<name>] keyed schema, not array-of-tables."""
        from joy.store import save_repos

        repos_path = tmp_path / "repos.toml"
        save_repos([Repo(name="joy", local_path="/dev/joy")], path=repos_path)
        raw = repos_path.read_text(encoding="utf-8")
        assert "[repos.joy]" in raw
        assert "[[repos]]" not in raw

    def test_repo_unknown_field_warns(self, tmp_path: Path) -> None:
        """Unknown fields in repos.toml emit UserWarning and are skipped."""
        from joy.store import load_repos

        repos_path = tmp_path / "repos.toml"
        repos_path.write_bytes(
            b'[repos.test]\nlocal_path = "/dev/test"\nunknown_field = "surprise"\n'
        )
        with pytest.warns(UserWarning, match="unknown_field"):
            loaded = load_repos(path=repos_path)
        assert len(loaded) == 1
        assert loaded[0].local_path == "/dev/test"
        assert not hasattr(loaded[0], "unknown_field")

    def test_save_repos_atomic_write(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """save_repos uses atomic write (os.replace called with .tmp source)."""
        from joy import store

        repos_path = tmp_path / "repos.toml"
        replace_calls: list[tuple[str, str]] = []
        original_replace = os.replace

        def mock_replace(src: str, dst: str) -> None:
            replace_calls.append((str(src), str(dst)))
            original_replace(src, dst)

        monkeypatch.setattr(os, "replace", mock_replace)
        from joy.store import save_repos

        save_repos([Repo(name="r", local_path="/dev/r")], path=repos_path)

        assert len(replace_calls) == 1
        src, dst = replace_calls[0]
        assert src.endswith(".tmp")
        assert dst == str(repos_path)
        assert repos_path.exists()


# ---------------------------------------------------------------------------
# get_remote_url tests
# ---------------------------------------------------------------------------


class TestGetRemoteUrl:
    """Tests for get_remote_url() subprocess git integration."""

    def test_get_remote_url_real_git_repo(self, tmp_path: Path) -> None:
        """Returns origin remote URL from a real initialized git repo.

        Uses an SSH URL directly to avoid git url.insteadOf rewrite rules that
        may be present in the developer's global git config.
        """
        from joy.store import get_remote_url

        # Use SSH URL directly — not subject to HTTPS→SSH rewrite rules
        origin_url = "git@github.com:test/repo.git"
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(
            ["git", "remote", "add", "origin", origin_url],
            cwd=str(tmp_path),
            check=True,
            capture_output=True,
        )
        url = get_remote_url(str(tmp_path))
        assert url == origin_url

    def test_get_remote_url_no_git_repo(self, tmp_path: Path) -> None:
        """Returns '' when directory exists but has no .git."""
        from joy.store import get_remote_url

        result = get_remote_url(str(tmp_path))
        assert result == ""

    def test_get_remote_url_nonexistent_path(self) -> None:
        """Returns '' for a path that does not exist."""
        from joy.store import get_remote_url

        result = get_remote_url("/nonexistent/path/abc123")
        assert result == ""

    def test_get_remote_url_no_remote(self, tmp_path: Path) -> None:
        """Returns '' when repo exists but has no remote configured."""
        from joy.store import get_remote_url

        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        result = get_remote_url(str(tmp_path))
        assert result == ""


# ---------------------------------------------------------------------------
# validate_repo_path tests
# ---------------------------------------------------------------------------


class TestValidateRepoPath:
    """Tests for validate_repo_path() path existence checks."""

    def test_validate_existing_dir(self, tmp_path: Path) -> None:
        """Returns True for an existing directory."""
        from joy.store import validate_repo_path

        assert validate_repo_path(str(tmp_path)) is True

    def test_validate_nonexistent(self) -> None:
        """Returns False for a path that does not exist."""
        from joy.store import validate_repo_path

        assert validate_repo_path("/nonexistent/abc123") is False

    def test_validate_file_not_dir(self, tmp_path: Path) -> None:
        """Returns False for a path that points to a file, not a directory."""
        from joy.store import validate_repo_path

        file_path = tmp_path / "somefile.txt"
        file_path.write_text("content")
        assert validate_repo_path(str(file_path)) is False
