"""Unit tests for joy data models."""
from datetime import date

import pytest

from joy.models import (
    PRESET_MAP,
    Config,
    ObjectItem,
    ObjectType,
    PresetKind,
    Project,
    Repo,
    detect_forge,
)


class TestObjectType:
    """Tests for the ObjectType enum."""

    def test_object_type_has_exactly_6_members(self) -> None:
        assert len(ObjectType) == 6

    def test_object_type_values(self) -> None:
        assert ObjectType.STRING.value == "string"
        assert ObjectType.URL.value == "url"
        assert ObjectType.OBSIDIAN.value == "obsidian"
        assert ObjectType.FILE.value == "file"
        assert ObjectType.WORKTREE.value == "worktree"
        assert ObjectType.ITERM.value == "iterm"

    def test_object_type_is_str(self) -> None:
        """ObjectType values should be usable as plain strings."""
        assert ObjectType.STRING == "string"
        assert ObjectType.URL == "url"


class TestPresetKind:
    """Tests for the PresetKind enum."""

    def test_preset_kind_has_exactly_9_members(self) -> None:
        assert len(PresetKind) == 9

    def test_preset_kind_values(self) -> None:
        assert PresetKind.MR.value == "mr"
        assert PresetKind.BRANCH.value == "branch"
        assert PresetKind.TICKET.value == "ticket"
        assert PresetKind.THREAD.value == "thread"
        assert PresetKind.FILE.value == "file"
        assert PresetKind.NOTE.value == "note"
        assert PresetKind.WORKTREE.value == "worktree"
        assert PresetKind.AGENTS.value == "agents"
        assert PresetKind.URL.value == "url"

    def test_preset_kind_is_str(self) -> None:
        """PresetKind values should be usable as plain strings."""
        assert PresetKind.MR == "mr"
        assert PresetKind.BRANCH == "branch"


class TestPresetMap:
    """Tests for the PRESET_MAP mapping."""

    def test_preset_map_has_9_entries(self) -> None:
        assert len(PRESET_MAP) == 9

    def test_preset_map_covers_all_preset_kinds(self) -> None:
        for kind in PresetKind:
            assert kind in PRESET_MAP, f"Missing PresetKind.{kind.name} in PRESET_MAP"

    def test_preset_map_mr_maps_to_url(self) -> None:
        assert PRESET_MAP[PresetKind.MR] == ObjectType.URL

    def test_preset_map_branch_maps_to_string(self) -> None:
        assert PRESET_MAP[PresetKind.BRANCH] == ObjectType.STRING

    def test_preset_map_ticket_maps_to_url(self) -> None:
        assert PRESET_MAP[PresetKind.TICKET] == ObjectType.URL

    def test_preset_map_thread_maps_to_url(self) -> None:
        assert PRESET_MAP[PresetKind.THREAD] == ObjectType.URL

    def test_preset_map_file_maps_to_file(self) -> None:
        assert PRESET_MAP[PresetKind.FILE] == ObjectType.FILE

    def test_preset_map_note_maps_to_obsidian(self) -> None:
        assert PRESET_MAP[PresetKind.NOTE] == ObjectType.OBSIDIAN

    def test_preset_map_worktree_maps_to_worktree(self) -> None:
        assert PRESET_MAP[PresetKind.WORKTREE] == ObjectType.WORKTREE

    def test_preset_map_agents_maps_to_iterm(self) -> None:
        assert PRESET_MAP[PresetKind.AGENTS] == ObjectType.ITERM

    def test_preset_map_url_maps_to_url(self) -> None:
        assert PRESET_MAP[PresetKind.URL] == ObjectType.URL


class TestObjectItem:
    """Tests for the ObjectItem dataclass."""

    def test_object_item_creation(self) -> None:
        item = ObjectItem(
            kind=PresetKind.MR,
            value="https://example.com",
            label="MR #1",
            open_by_default=True,
        )
        assert item.kind == PresetKind.MR
        assert item.value == "https://example.com"
        assert item.label == "MR #1"
        assert item.open_by_default is True

    def test_object_item_defaults(self) -> None:
        item = ObjectItem(kind=PresetKind.BRANCH, value="feature/my-branch")
        assert item.label == ""
        assert item.open_by_default is False

    def test_object_type_property_mr(self) -> None:
        item = ObjectItem(kind=PresetKind.MR, value="https://example.com")
        assert item.object_type == ObjectType.URL

    def test_object_type_property_branch(self) -> None:
        item = ObjectItem(kind=PresetKind.BRANCH, value="main")
        assert item.object_type == ObjectType.STRING

    def test_object_type_property_all_kinds(self) -> None:
        for kind in PresetKind:
            item = ObjectItem(kind=kind, value="test")
            assert item.object_type == PRESET_MAP[kind]

    def test_object_item_to_dict_uses_string_values(self) -> None:
        item = ObjectItem(
            kind=PresetKind.MR,
            value="https://example.com",
            label="MR #1",
            open_by_default=True,
        )
        result = item.to_dict()
        assert result == {
            "kind": "mr",
            "value": "https://example.com",
            "label": "MR #1",
            "open_by_default": True,
        }

    def test_object_item_to_dict_kind_is_string_not_enum(self) -> None:
        item = ObjectItem(kind=PresetKind.BRANCH, value="main")
        result = item.to_dict()
        assert isinstance(result["kind"], str)
        assert not isinstance(result["kind"], PresetKind)
        assert result["kind"] == "branch"

    def test_object_item_equality(self) -> None:
        item1 = ObjectItem(kind=PresetKind.MR, value="https://example.com", label="MR")
        item2 = ObjectItem(kind=PresetKind.MR, value="https://example.com", label="MR")
        assert item1 == item2


class TestProject:
    """Tests for the Project dataclass."""

    def test_project_creation_minimal(self) -> None:
        project = Project(name="my-project")
        assert project.name == "my-project"
        assert project.objects == []
        assert isinstance(project.created, date)

    def test_project_creation_with_objects(self) -> None:
        item = ObjectItem(kind=PresetKind.MR, value="https://example.com")
        project = Project(
            name="test-project",
            objects=[item],
            created=date(2026, 1, 15),
        )
        assert project.name == "test-project"
        assert len(project.objects) == 1
        assert project.created == date(2026, 1, 15)

    def test_project_to_dict(self) -> None:
        item = ObjectItem(
            kind=PresetKind.MR,
            value="https://example.com",
            label="MR #1",
            open_by_default=True,
        )
        project = Project(
            name="test-project",
            objects=[item],
            created=date(2026, 1, 15),
        )
        result = project.to_dict()
        assert result["name"] == "test-project"
        assert result["created"] == date(2026, 1, 15)
        assert len(result["objects"]) == 1
        assert result["objects"][0] == {
            "kind": "mr",
            "value": "https://example.com",
            "label": "MR #1",
            "open_by_default": True,
        }

    def test_project_to_dict_empty_objects(self) -> None:
        project = Project(name="empty-project", created=date(2026, 3, 1))
        result = project.to_dict()
        assert result["objects"] == []

    def test_project_objects_default_is_empty_list(self) -> None:
        """Each project instance should get its own list, not share one."""
        p1 = Project(name="p1")
        p2 = Project(name="p2")
        p1.objects.append(ObjectItem(kind=PresetKind.MR, value="x"))
        assert p2.objects == []


class TestConfig:
    """Tests for the Config dataclass."""

    def test_config_defaults(self) -> None:
        config = Config()
        assert config.ide == "PyCharm"
        assert config.editor == "Sublime Text"
        assert config.obsidian_vault == ""
        assert config.terminal == "iTerm2"
        assert config.default_open_kinds == ["worktree", "agents"]

    def test_config_custom_values(self) -> None:
        config = Config(
            ide="VSCode",
            editor="Vim",
            obsidian_vault="/Users/dev/Obsidian",
            terminal="Terminal",
            default_open_kinds=["mr", "branch"],
        )
        assert config.ide == "VSCode"
        assert config.editor == "Vim"
        assert config.obsidian_vault == "/Users/dev/Obsidian"
        assert config.terminal == "Terminal"
        assert config.default_open_kinds == ["mr", "branch"]

    def test_config_default_open_kinds_not_shared(self) -> None:
        """Each Config instance should have its own default_open_kinds list."""
        c1 = Config()
        c2 = Config()
        c1.default_open_kinds.append("file")
        assert c2.default_open_kinds == ["worktree", "agents"]

    def test_config_to_dict(self) -> None:
        config = Config()
        result = config.to_dict()
        assert result == {
            "ide": "PyCharm",
            "editor": "Sublime Text",
            "obsidian_vault": "",
            "terminal": "iTerm2",
            "default_open_kinds": ["worktree", "agents"],
        }

    def test_config_to_dict_custom(self) -> None:
        config = Config(ide="VSCode", obsidian_vault="/vault")
        result = config.to_dict()
        assert result["ide"] == "VSCode"
        assert result["obsidian_vault"] == "/vault"


class TestRepo:
    """Tests for the Repo dataclass."""

    def test_repo_creation_minimal(self) -> None:
        repo = Repo(name="joy", local_path="/Users/dev/joy")
        assert repo.name == "joy"
        assert repo.local_path == "/Users/dev/joy"
        assert repo.remote_url == ""
        assert repo.forge == "unknown"

    def test_repo_creation_full(self) -> None:
        repo = Repo(
            name="joy",
            local_path="/Users/dev/joy",
            remote_url="git@github.com:user/joy.git",
            forge="github",
        )
        assert repo.name == "joy"
        assert repo.local_path == "/Users/dev/joy"
        assert repo.remote_url == "git@github.com:user/joy.git"
        assert repo.forge == "github"

    def test_repo_to_dict(self) -> None:
        repo = Repo(name="joy", local_path="/Users/dev/joy")
        result = repo.to_dict()
        assert result == {
            "name": "joy",
            "local_path": "/Users/dev/joy",
            "remote_url": "",
            "forge": "unknown",
        }

    def test_repo_to_dict_full(self) -> None:
        repo = Repo(
            name="joy",
            local_path="/Users/dev/joy",
            remote_url="git@github.com:user/joy.git",
            forge="github",
        )
        result = repo.to_dict()
        assert result == {
            "name": "joy",
            "local_path": "/Users/dev/joy",
            "remote_url": "git@github.com:user/joy.git",
            "forge": "github",
        }

    def test_repo_equality(self) -> None:
        repo1 = Repo(name="joy", local_path="/Users/dev/joy")
        repo2 = Repo(name="joy", local_path="/Users/dev/joy")
        assert repo1 == repo2

    def test_repo_forge_is_str_not_enum(self) -> None:
        repo = Repo(name="joy", local_path="/Users/dev/joy", forge="github")
        assert isinstance(repo.forge, str)
        # forge must NOT be an Enum subclass
        from enum import Enum
        assert not isinstance(repo.forge, Enum)


class TestDetectForge:
    """Tests for the detect_forge pure function."""

    def test_github_ssh(self) -> None:
        assert detect_forge("git@github.com:user/repo.git") == "github"

    def test_github_https(self) -> None:
        assert detect_forge("https://github.com/user/repo") == "github"

    def test_gitlab_ssh(self) -> None:
        assert detect_forge("git@gitlab.com:user/repo.git") == "gitlab"

    def test_gitlab_https(self) -> None:
        assert detect_forge("https://gitlab.com/user/repo") == "gitlab"

    def test_unknown_host(self) -> None:
        assert detect_forge("https://bitbucket.org/user/repo") == "unknown"

    def test_empty_string(self) -> None:
        assert detect_forge("") == "unknown"

    def test_no_dot_com_substring(self) -> None:
        assert detect_forge("https://notgithub.example.com/repo") == "unknown"
