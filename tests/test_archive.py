"""Tests for archive store functions (load_archived_projects / save_archived_projects)."""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from joy.models import ObjectItem, PresetKind, Project


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(
    name: str = "test-project",
    *,
    created: date = date(2026, 1, 15),
    with_worktree: bool = False,
    with_terminals: bool = False,
) -> Project:
    objects = [
        ObjectItem(kind=PresetKind.BRANCH, value="feature/my-branch", label="Branch"),
        ObjectItem(kind=PresetKind.MR, value="https://github.com/org/repo/pull/1", label="MR #1"),
    ]
    if with_worktree:
        objects.append(ObjectItem(kind=PresetKind.WORKTREE, value="/dev/worktrees/proj"))
    if with_terminals:
        objects.append(ObjectItem(kind=PresetKind.TERMINALS, value="proj-session"))
    return Project(name=name, objects=objects, created=created)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Round-trip tests
# ---------------------------------------------------------------------------


def test_round_trip_single_entry(tmp_path: Path) -> None:
    """Save one ArchivedProject, load it back, assert all fields match."""
    from joy.models import ArchivedProject
    from joy.store import load_archived_projects, save_archived_projects

    archive_path = tmp_path / "archive.toml"
    project = _make_project("alpha")
    archived_at = datetime(2026, 4, 16, 14, 30, 0, tzinfo=timezone.utc)
    ap = ArchivedProject(project=project, archived_at=archived_at)

    save_archived_projects([ap], path=archive_path)
    loaded = load_archived_projects(path=archive_path)

    assert len(loaded) == 1
    result = loaded[0]
    assert result.project.name == "alpha"
    assert result.project.created == date(2026, 1, 15)
    assert len(result.project.objects) == 2
    assert result.archived_at == archived_at
    # archived_at must be timezone-aware after round-trip
    assert result.archived_at.tzinfo is not None


def test_round_trip_multiple_entries(tmp_path: Path) -> None:
    """Save multiple ArchivedProjects, load all back."""
    from joy.models import ArchivedProject
    from joy.store import load_archived_projects, save_archived_projects

    archive_path = tmp_path / "archive.toml"
    t1 = datetime(2026, 4, 10, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc)

    alpha = ArchivedProject(project=_make_project("alpha"), archived_at=t1)
    beta = ArchivedProject(project=_make_project("beta", created=date(2026, 2, 1)), archived_at=t2)

    save_archived_projects([alpha, beta], path=archive_path)
    loaded = load_archived_projects(path=archive_path)

    assert len(loaded) == 2
    by_name = {ap.project.name: ap for ap in loaded}
    assert "alpha" in by_name
    assert "beta" in by_name
    assert by_name["alpha"].archived_at == t1
    assert by_name["beta"].project.created == date(2026, 2, 1)


def test_round_trip_timezone_preserved(tmp_path: Path) -> None:
    """archived_at round-trips as a timezone-aware datetime, not naive."""
    from joy.models import ArchivedProject
    from joy.store import load_archived_projects, save_archived_projects

    archive_path = tmp_path / "archive.toml"
    archived_at = datetime(2026, 4, 16, 9, 0, 0, tzinfo=timezone.utc)
    ap = ArchivedProject(project=_make_project("tz-test"), archived_at=archived_at)

    save_archived_projects([ap], path=archive_path)
    loaded = load_archived_projects(path=archive_path)

    assert len(loaded) == 1
    loaded_at = loaded[0].archived_at
    assert loaded_at.tzinfo is not None  # must not be naive
    assert loaded_at == archived_at


def test_round_trip_no_objects(tmp_path: Path) -> None:
    """ArchivedProject with a project containing no objects round-trips correctly."""
    from joy.models import ArchivedProject
    from joy.store import load_archived_projects, save_archived_projects

    archive_path = tmp_path / "archive.toml"
    project = Project(name="empty-proj", objects=[], created=date(2026, 3, 1))
    ap = ArchivedProject(project=project, archived_at=_utc_now())

    save_archived_projects([ap], path=archive_path)
    loaded = load_archived_projects(path=archive_path)

    assert len(loaded) == 1
    assert loaded[0].project.name == "empty-proj"
    assert loaded[0].project.objects == []


def test_round_trip_objects_preserved(tmp_path: Path) -> None:
    """All object fields (kind, value, label, open_by_default) round-trip correctly."""
    from joy.models import ArchivedProject
    from joy.store import load_archived_projects, save_archived_projects

    archive_path = tmp_path / "archive.toml"
    objects = [
        ObjectItem(kind=PresetKind.BRANCH, value="main", label="Main branch", open_by_default=True),
        ObjectItem(kind=PresetKind.MR, value="https://github.com/org/repo/pull/42", label="PR #42"),
        ObjectItem(kind=PresetKind.WORKTREE, value="/dev/worktree/main"),
        ObjectItem(kind=PresetKind.TERMINALS, value="main-session"),
    ]
    project = Project(name="full-proj", objects=objects, created=date(2026, 1, 1))
    ap = ArchivedProject(project=project, archived_at=_utc_now())

    save_archived_projects([ap], path=archive_path)
    loaded = load_archived_projects(path=archive_path)

    assert len(loaded) == 1
    loaded_objs = loaded[0].project.objects
    assert len(loaded_objs) == 4
    branch = next(o for o in loaded_objs if o.kind == PresetKind.BRANCH)
    assert branch.label == "Main branch"
    assert branch.open_by_default is True
    wt = next(o for o in loaded_objs if o.kind == PresetKind.WORKTREE)
    assert wt.value == "/dev/worktree/main"


# ---------------------------------------------------------------------------
# Missing file tests
# ---------------------------------------------------------------------------


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    """load_archived_projects from non-existent path returns []."""
    from joy.store import load_archived_projects

    result = load_archived_projects(path=tmp_path / "nonexistent.toml")
    assert result == []


# ---------------------------------------------------------------------------
# TOML schema tests
# ---------------------------------------------------------------------------


def test_keyed_schema(tmp_path: Path) -> None:
    """archive.toml uses [archive.{name}] keyed schema, not [[archive]] array-of-tables."""
    from joy.models import ArchivedProject
    from joy.store import save_archived_projects

    archive_path = tmp_path / "archive.toml"
    ap = ArchivedProject(project=_make_project("my-proj"), archived_at=_utc_now())

    save_archived_projects([ap], path=archive_path)
    raw = archive_path.read_text(encoding="utf-8")

    assert "[archive.my-proj]" in raw
    assert "[[archive]]" not in raw
    assert "archived_at" in raw


# ---------------------------------------------------------------------------
# Atomic write test
# ---------------------------------------------------------------------------


def test_atomic_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """save_archived_projects uses os.replace with a .tmp source file."""
    import os as _os
    from joy.models import ArchivedProject
    from joy import store

    archive_path = tmp_path / "archive.toml"
    replace_calls: list[tuple[str, str]] = []
    original_replace = _os.replace

    def mock_replace(src: str, dst: str) -> None:
        replace_calls.append((str(src), str(dst)))
        original_replace(src, dst)

    monkeypatch.setattr(_os, "replace", mock_replace)

    from joy.store import save_archived_projects

    ap = ArchivedProject(project=_make_project("atomic-proj"), archived_at=_utc_now())
    save_archived_projects([ap], path=archive_path)

    assert len(replace_calls) == 1
    src, dst = replace_calls[0]
    assert src.endswith(".tmp")
    assert dst == str(archive_path)
    assert archive_path.exists()
