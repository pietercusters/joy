"""Pure data models for joy. No I/O, no side effects."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class ObjectType(str, Enum):
    """Operation-facing object types. Values are the literal strings written to TOML."""

    STRING = "string"
    URL = "url"
    OBSIDIAN = "obsidian"
    FILE = "file"
    WORKTREE = "worktree"
    ITERM = "iterm"


class PresetKind(str, Enum):
    """User-facing preset names. Each maps to an ObjectType via PRESET_MAP."""

    MR = "mr"
    BRANCH = "branch"
    TICKET = "ticket"
    THREAD = "thread"
    FILE = "file"
    NOTE = "note"
    WORKTREE = "worktree"
    AGENTS = "agents"
    URL = "url"


PRESET_MAP: dict[PresetKind, ObjectType] = {
    PresetKind.MR: ObjectType.URL,
    PresetKind.BRANCH: ObjectType.STRING,
    PresetKind.TICKET: ObjectType.URL,
    PresetKind.THREAD: ObjectType.URL,
    PresetKind.FILE: ObjectType.FILE,
    PresetKind.NOTE: ObjectType.OBSIDIAN,
    PresetKind.WORKTREE: ObjectType.WORKTREE,
    PresetKind.AGENTS: ObjectType.ITERM,
    PresetKind.URL: ObjectType.URL,
}


@dataclass
class ObjectItem:
    """A single object within a project."""

    kind: PresetKind
    value: str
    label: str = ""
    open_by_default: bool = False

    @property
    def object_type(self) -> ObjectType:
        """Resolve this item's operation type via PRESET_MAP."""
        return PRESET_MAP[self.kind]

    def to_dict(self) -> dict:
        """Serialize to a TOML-compatible dict. Uses .value for enums."""
        return {
            "kind": self.kind.value,
            "value": self.value,
            "label": self.label,
            "open_by_default": self.open_by_default,
        }


@dataclass
class Project:
    """A coding project with its associated objects."""

    name: str
    objects: list[ObjectItem] = field(default_factory=list)
    created: date = field(default_factory=date.today)

    def to_dict(self) -> dict:
        """Serialize to a TOML-compatible dict for the keyed schema."""
        return {
            "name": self.name,
            "created": self.created,
            "objects": [obj.to_dict() for obj in self.objects],
        }


@dataclass
class Config:
    """Global configuration loaded from ~/.joy/config.toml."""

    ide: str = "PyCharm"
    editor: str = "Sublime Text"
    obsidian_vault: str = ""
    terminal: str = "iTerm2"
    default_open_kinds: list[str] = field(
        default_factory=lambda: ["worktree", "agents"]
    )

    def to_dict(self) -> dict:
        """Serialize to a TOML-compatible dict."""
        return {
            "ide": self.ide,
            "editor": self.editor,
            "obsidian_vault": self.obsidian_vault,
            "terminal": self.terminal,
            "default_open_kinds": self.default_open_kinds,
        }
