"""TOML persistence for joy projects and configuration."""
from __future__ import annotations

import os
import subprocess
import tempfile
import tomllib
import warnings
from datetime import date, datetime, timezone
from pathlib import Path

import tomli_w

from joy.models import ArchivedProject, Config, ObjectItem, PresetKind, Project, Repo

JOY_DIR = Path.home() / ".joy"
PROJECTS_PATH = JOY_DIR / "projects.toml"
CONFIG_PATH = JOY_DIR / "config.toml"
REPOS_PATH = JOY_DIR / "repos.toml"
ARCHIVE_PATH = JOY_DIR / "archive.toml"


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
        objects = []
        for obj in proj_data.get("objects", []):
            raw_kind = obj["kind"]
            if raw_kind == "agents":
                raw_kind = "terminals"  # backward compat: old TOML files
            try:
                kind = PresetKind(raw_kind)
            except ValueError:
                warnings.warn(
                    f"Unknown object kind {obj['kind']!r} in project {name!r} — skipping object",
                    UserWarning,
                    stacklevel=2,
                )
                continue
            try:
                value = obj["value"]
            except KeyError:
                warnings.warn(
                    f"Object in project {name!r} is missing required 'value' field — skipping object",
                    UserWarning,
                    stacklevel=2,
                )
                continue
            objects.append(
                ObjectItem(
                    kind=kind,
                    value=value,
                    label=obj.get("label", ""),
                    open_by_default=obj.get("open_by_default", False),
                )
            )
        created_raw = proj_data.get("created")
        if isinstance(created_raw, date):
            created = created_raw
        elif isinstance(created_raw, str):
            try:
                created = date.fromisoformat(created_raw)
            except ValueError:
                warnings.warn(
                    f"Cannot parse created date {created_raw!r} for project {name!r}, using today",
                    UserWarning,
                    stacklevel=2,
                )
                created = date.today()
        else:
            created = date.today()
        repo = proj_data.get("repo")  # None if absent (backward compat)
        status = proj_data.get("status", "idle")
        projects.append(Project(name=name, objects=objects, created=created, repo=repo, status=status))
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
    defaults = Config()
    raw_kinds = data.get("default_open_kinds", defaults.default_open_kinds)
    # backward compat: old config files may have "agents" instead of "terminals"
    default_open_kinds = ["terminals" if k == "agents" else k for k in raw_kinds]
    return Config(
        ide=data.get("ide", defaults.ide),
        editor=data.get("editor", defaults.editor),
        obsidian_vault=data.get("obsidian_vault", defaults.obsidian_vault),
        terminal=data.get("terminal", defaults.terminal),
        default_open_kinds=default_open_kinds,
        refresh_interval=data.get("refresh_interval", defaults.refresh_interval),
        branch_filter=data.get("branch_filter", defaults.branch_filter),
    )


def save_config(config: Config, *, path: Path = CONFIG_PATH) -> None:
    """Atomically write config to TOML file."""
    content = tomli_w.dumps(config.to_dict()).encode("utf-8")
    _atomic_write(path=path, data=content)


def _repos_to_toml(repos: list[Repo]) -> dict:
    """Convert repo list to TOML-serializable dict using keyed schema (D-02).

    name is the TOML table key — it is NOT stored as a field inside the table.
    """
    result: dict = {"repos": {}}
    for repo in repos:
        d = repo.to_dict()
        d.pop("name", None)  # name is the key, not a field inside the table
        result["repos"][repo.name] = d
    return result


def _toml_to_repos(data: dict) -> list[Repo]:
    """Convert parsed TOML dict to repo list."""
    repos = []
    known_fields = {"local_path", "remote_url", "forge"}
    for name, repo_data in data.get("repos", {}).items():
        for key in repo_data:
            if key not in known_fields:
                warnings.warn(
                    f"Unknown field {key!r} in repo {name!r} — skipping field",
                    UserWarning,
                    stacklevel=2,
                )
        repos.append(
            Repo(
                name=name,
                local_path=repo_data.get("local_path", ""),
                remote_url=repo_data.get("remote_url", ""),
                forge=repo_data.get("forge", "unknown"),
            )
        )
    return repos


def load_repos(*, path: Path = REPOS_PATH) -> list[Repo]:
    """Load repos from TOML file. Returns empty list if file missing."""
    if not path.exists():
        return []
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return _toml_to_repos(data)


def save_repos(repos: list[Repo], *, path: Path = REPOS_PATH) -> None:
    """Atomically write repos to TOML file."""
    data = _repos_to_toml(repos)
    content = tomli_w.dumps(data).encode("utf-8")
    _atomic_write(path=path, data=content)


def _archived_to_toml(archived_projects: list[ArchivedProject]) -> dict:
    """Convert archived project list to TOML-serializable dict (keyed schema).

    Top-level key is 'archive' to distinguish from projects.toml.
    archived_at stored as offset-aware datetime — tomli_w serializes natively.
    """
    result: dict = {"archive": {}}
    for ap in archived_projects:
        d = ap.project.to_dict()
        d["archived_at"] = ap.archived_at  # datetime with tzinfo — tomli_w handles it
        result["archive"][ap.project.name] = d
    return result


def _toml_to_archived(data: dict) -> list[ArchivedProject]:
    """Convert parsed archive.toml dict to ArchivedProject list."""
    archived = []
    for name, entry in data.get("archive", {}).items():
        objects = []
        for obj in entry.get("objects", []):
            raw_kind = obj["kind"]
            if raw_kind == "agents":
                raw_kind = "terminals"  # backward compat
            try:
                kind = PresetKind(raw_kind)
            except ValueError:
                warnings.warn(
                    f"Unknown object kind {obj['kind']!r} in archived project {name!r} — skipping object",
                    UserWarning,
                    stacklevel=2,
                )
                continue
            try:
                value = obj["value"]
            except KeyError:
                warnings.warn(
                    f"Object in archived project {name!r} is missing required 'value' field — skipping object",
                    UserWarning,
                    stacklevel=2,
                )
                continue
            objects.append(
                ObjectItem(
                    kind=kind,
                    value=value,
                    label=obj.get("label", ""),
                    open_by_default=obj.get("open_by_default", False),
                )
            )
        created_raw = entry.get("created")
        if isinstance(created_raw, date):
            created = created_raw
        elif isinstance(created_raw, str):
            try:
                created = date.fromisoformat(created_raw)
            except ValueError:
                warnings.warn(
                    f"Cannot parse created date {created_raw!r} for archived project {name!r}, using today",
                    UserWarning,
                    stacklevel=2,
                )
                created = date.today()
        else:
            created = date.today()
        repo = entry.get("repo")
        status = entry.get("status", "idle")
        archived_at = entry.get("archived_at")
        if not isinstance(archived_at, datetime):
            # Fallback: if somehow not a datetime, use epoch (should not happen with valid TOML)
            archived_at = datetime(1970, 1, 1, tzinfo=timezone.utc)
        project = Project(name=name, objects=objects, created=created, repo=repo, status=status)
        archived.append(ArchivedProject(project=project, archived_at=archived_at))
    return archived


def load_archived_projects(*, path: Path = ARCHIVE_PATH) -> list[ArchivedProject]:
    """Load archived projects from TOML file. Returns empty list if file missing."""
    if not path.exists():
        return []
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return _toml_to_archived(data)


def save_archived_projects(
    projects: list[ArchivedProject], *, path: Path = ARCHIVE_PATH
) -> None:
    """Atomically write archived projects to TOML file.

    Note: This is a full read-replace-write. Not safe for concurrent callers,
    but acceptable for a single-user TUI where archive + unarchive never overlap.
    """
    data = _archived_to_toml(projects)
    content = tomli_w.dumps(data).encode("utf-8")
    _atomic_write(path=path, data=content)


def get_remote_url(local_path: str) -> str:
    """Get git remote origin URL from a local repo path.

    Per D-07: returns empty string on any error (non-zero exit, timeout, path not found).
    Uses list-form subprocess (never shell=True) per T-06-03.
    Never raises.
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=local_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def validate_repo_path(local_path: str) -> bool:
    """Check that local_path is an existing directory. Per D-08."""
    return Path(local_path).is_dir()
