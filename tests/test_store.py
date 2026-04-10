"""Tests for the TOML persistence layer (store.py)."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from joy.models import Config, ObjectItem, PresetKind, Project


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
