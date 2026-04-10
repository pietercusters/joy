"""TOML persistence for joy projects and configuration."""
from __future__ import annotations

import os
import tempfile
import tomllib
from datetime import date
from pathlib import Path

import tomli_w

from joy.models import Config, ObjectItem, PresetKind, Project

JOY_DIR = Path.home() / ".joy"
PROJECTS_PATH = JOY_DIR / "projects.toml"
CONFIG_PATH = JOY_DIR / "config.toml"


def _atomic_write(path: Path, data: bytes) -> None:
    """Write data atomically using temp file + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _projects_to_toml(projects: list[Project]) -> dict:
    """Convert project list to TOML-serializable dict using keyed schema (D-01)."""
    result: dict = {"projects": {}}
    for project in projects:
        result["projects"][project.name] = project.to_dict()
    return result


def _toml_to_projects(data: dict) -> list[Project]:
    """Convert parsed TOML dict to project list."""
    projects = []
    for name, proj_data in data.get("projects", {}).items():
        objects = [
            ObjectItem(
                kind=PresetKind(obj["kind"]),
                value=obj["value"],
                label=obj.get("label", ""),
                open_by_default=obj.get("open_by_default", False),
            )
            for obj in proj_data.get("objects", [])
        ]
        created_raw = proj_data.get("created")
        if isinstance(created_raw, date):
            created = created_raw
        else:
            created = date.today()
        projects.append(Project(name=name, objects=objects, created=created))
    return projects


def load_projects(*, path: Path = PROJECTS_PATH) -> list[Project]:
    """Load projects from TOML file. Returns empty list if file missing."""
    if not path.exists():
        return []
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return _toml_to_projects(data)


def save_projects(projects: list[Project], *, path: Path = PROJECTS_PATH) -> None:
    """Atomically write projects to TOML file."""
    data = _projects_to_toml(projects)
    content = tomli_w.dumps(data).encode("utf-8")
    _atomic_write(path=path, data=content)


def load_config(*, path: Path = CONFIG_PATH) -> Config:
    """Load config from TOML file. Returns default Config if file missing."""
    if not path.exists():
        return Config()
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return Config(
        ide=data.get("ide", "PyCharm"),
        editor=data.get("editor", "Sublime Text"),
        obsidian_vault=data.get("obsidian_vault", ""),
        terminal=data.get("terminal", "iTerm2"),
        default_open_kinds=data.get("default_open_kinds", ["worktree", "agents"]),
    )


def save_config(config: Config, *, path: Path = CONFIG_PATH) -> None:
    """Atomically write config to TOML file."""
    content = tomli_w.dumps(config.to_dict()).encode("utf-8")
    _atomic_write(path=path, data=content)
