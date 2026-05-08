"""Tests for ProjectService (Phase 19, SRVC-03, TEST-03).

All tests are pure Python — no TUI, no Textual, no pilot.
"""
from __future__ import annotations

import pytest

from joy.models import ObjectItem, PresetKind, Project
from joy.project_service import ProjectService


# ---------------------------------------------------------------------------
# TestProjectService
# ---------------------------------------------------------------------------


class TestProjectService:
    def test_create_project_basic(self):
        svc = ProjectService()
        project = svc.create_project("myproject")
        assert project.name == "myproject"
        assert project in svc.projects

    def test_create_project_with_repo(self):
        svc = ProjectService()
        project = svc.create_project("p", repo="myrepo")
        assert project.repo == "myrepo"

    def test_create_project_with_branch(self):
        svc = ProjectService()
        project = svc.create_project("p", branch="feature-x")
        assert any(o.kind == PresetKind.BRANCH and o.value == "feature-x" for o in project.objects)

    def test_create_project_duplicate_name_raises(self):
        svc = ProjectService()
        svc.create_project("dup")
        with pytest.raises(ValueError, match="already exists"):
            svc.create_project("dup")

    def test_add_object_appends(self):
        svc = ProjectService()
        project = svc.create_project("p")
        obj = svc.add_object(project, PresetKind.MR, "https://pr/1")
        assert obj in project.objects
        assert obj.kind == PresetKind.MR
        assert obj.value == "https://pr/1"

    def test_add_object_respects_default_open_kinds(self):
        svc = ProjectService()
        project = svc.create_project("p")
        obj = svc.add_object(project, PresetKind.MR, "https://pr/1", default_open_kinds=["mr"])
        assert obj.open_by_default is True

    def test_add_object_not_default(self):
        svc = ProjectService()
        project = svc.create_project("p")
        obj = svc.add_object(project, PresetKind.MR, "https://pr/1", default_open_kinds=["worktree"])
        assert obj.open_by_default is False

    def test_find_project_exists(self):
        svc = ProjectService()
        created = svc.create_project("findme")
        found = svc.find_project("findme")
        assert found is created

    def test_find_project_missing(self):
        svc = ProjectService()
        assert svc.find_project("nope") is None

    def test_has_project_true(self):
        svc = ProjectService()
        svc.create_project("exists")
        assert svc.has_project("exists") is True

    def test_has_project_false(self):
        svc = ProjectService()
        assert svc.has_project("nope") is False

    def test_build_archived(self):
        svc = ProjectService()
        project = svc.create_project("arch")
        archived = svc.build_archived(project)
        assert archived.project is project
        assert archived.archived_at is not None

    def test_remove_project(self):
        svc = ProjectService()
        project = svc.create_project("removeme")
        assert svc.remove_project(project) is True
        assert project not in svc.projects

    def test_remove_project_not_found(self):
        svc = ProjectService()
        orphan = Project(name="orphan")
        assert svc.remove_project(orphan) is False

    def test_set_projects_replaces_list(self):
        svc = ProjectService()
        svc.create_project("old")
        new_list = [Project(name="new1"), Project(name="new2")]
        svc.set_projects(new_list)
        assert svc.projects == new_list
        assert len(svc.projects) == 2
