"""Left pane: project list widget with keyboard navigation and repo grouping."""
from __future__ import annotations

import re

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static

from joy.models import MRInfo, PresetKind, Project, Repo
from joy.widgets.icons import (
    ICON_BRANCH,
    ICON_TICKET,
    ICON_THREAD,
    ICON_NOTE,
    ICON_TERMINAL,
    ICON_WORKTREE,
    ICON_MR_OPEN,
    ICON_MR_DRAFT,
    ICON_CI_PASS,
    ICON_CI_FAIL,
    ICON_CI_PENDING,
)


# ---------------------------------------------------------------------------
# _ProjectScroll: non-focusable scroll container (same pattern as worktree_pane)
# ---------------------------------------------------------------------------


class _ProjectScroll(VerticalScroll, can_focus=False):
    """Non-focusable scroll container for project rows.

    Prevents VerticalScroll from stealing focus from ProjectList
    (VerticalScroll is focusable by default).
    """


# ---------------------------------------------------------------------------
# GroupHeader: repo section header (duplicated to avoid cross-widget coupling)
# ---------------------------------------------------------------------------


class GroupHeader(Static):
    """Repo section header for project grouping."""

    DEFAULT_CSS = """
    GroupHeader {
        width: 1fr;
        height: 1;
        color: $text-muted;
        text-style: bold;
        padding: 0 1;
    }
    """


# ---------------------------------------------------------------------------
# ProjectRow: single-line row for one project
# ---------------------------------------------------------------------------


class ProjectRow(Static):
    """Single-line row: status dot + name + optional MR strip + 6-icon ribbon."""

    DEFAULT_CSS = """
    ProjectRow {
        width: 1fr;
        height: 1;
        padding: 0 1;
    }
    """

    def __init__(self, project: Project, avail_width: int = 80, **kwargs) -> None:
        self.project = project
        self._avail_width = avail_width
        self._mr_info: MRInfo | None = None
        self._has: dict[str, bool] = self._compute_has(project)
        self._wt_count: int = 0
        self._agent_count: int = 0
        content = self.build_content(project, avail_width, mr_info=None, has=self._has, wt_count=0, agent_count=0)
        super().__init__(content, **kwargs)

    @staticmethod
    def _compute_has(project: Project) -> dict[str, bool]:
        """Compute which object kinds are present in the project."""
        kinds = {obj.kind for obj in project.objects}
        return {
            "branch":   PresetKind.BRANCH in kinds,
            "ticket":   PresetKind.TICKET in kinds,
            "thread":   PresetKind.THREAD in kinds,
            "note":     PresetKind.NOTE in kinds,
            "terminal": PresetKind.TERMINALS in kinds,
            "worktree": PresetKind.WORKTREE in kinds,
        }

    @staticmethod
    def build_content(
        project: Project,
        avail_width: int,
        mr_info: "MRInfo | None",
        has: dict[str, bool],
        wt_count: int = 0,
        agent_count: int = 0,
    ) -> Text:
        """Build a single-line Rich.Text row:
        [status-dot] [space] [name...padding...] [MR-strip] [space] [icon-ribbon]
        """
        t = Text(no_wrap=True, overflow="ellipsis")

        # Status dot (leftmost)
        status = project.status
        if status == "prio":
            t.append("●", style="green")
        elif status == "hold":
            t.append("●", style="dim")
        else:  # idle
            t.append("○", style="dim")
        t.append(" ")

        # MR strip (built first so we know its length for padding)
        mr_strip = Text()
        if mr_info is not None:
            mr_strip.append(f"!{mr_info.mr_number} ", style="dim")
            if mr_info.is_draft:
                mr_strip.append(ICON_MR_DRAFT, style="dim")
            else:
                mr_strip.append(ICON_MR_OPEN, style="green")
            if mr_info.ci_status == "pass":
                mr_strip.append(f" {ICON_CI_PASS}", style="green")
            elif mr_info.ci_status == "fail":
                mr_strip.append(f" {ICON_CI_FAIL}", style="red")
            elif mr_info.ci_status == "pending":
                mr_strip.append(f" {ICON_CI_PENDING}", style="yellow")
            mr_strip.append(" ")

        # Live connections override: active worktrees/terminals turn cyan even if not in stored objects
        effective_has = dict(has)
        if wt_count > 0:
            effective_has["worktree"] = True
        if agent_count > 0:
            effective_has["terminal"] = True

        # Icon ribbon: branch ticket thread note terminal worktree (space-separated)
        ribbon_icons = [
            (ICON_BRANCH,   effective_has.get("branch",   False)),
            (ICON_TICKET,   effective_has.get("ticket",   False)),
            (ICON_THREAD,   effective_has.get("thread",   False)),
            (ICON_NOTE,     effective_has.get("note",     False)),
            (ICON_TERMINAL, effective_has.get("terminal", False)),
            (ICON_WORKTREE, effective_has.get("worktree", False)),
        ]
        ribbon = Text()
        for i, (icon, present) in enumerate(ribbon_icons):
            if i > 0:
                ribbon.append(" ")
            if present:
                ribbon.append(icon, style="cyan")
            else:
                ribbon.append(icon, style="grey50 dim")

        # Compute fixed right width: mr_strip_len + separator + ribbon
        # Ribbon is 6 icons + 5 spaces between them = 11 chars.
        # When mr_info is present, mr_strip already ends with a trailing space so no extra
        # separator is needed. When absent, we add 1 space before the ribbon.
        mr_plain_len = len(mr_strip.plain)
        separator = 0 if mr_info is not None else 1
        ribbon_width = 2 * len(ribbon_icons) - 1  # icons + single spaces between them
        fixed_right = mr_plain_len + separator + ribbon_width

        # Fixed left: status-dot (1) + space (1) = 2
        name_budget = avail_width - 2 - fixed_right
        name = project.name
        if len(name) > name_budget and name_budget > 1:
            name = name[:name_budget - 1] + "…"
        elif name_budget <= 1:
            name = "…"

        # Padding between name and right section
        pad = max(0, name_budget - len(name))
        t.append(name)
        t.append(" " * pad)

        # MR strip (if any)
        if mr_info is not None:
            t.append_text(mr_strip)
        else:
            t.append(" ")  # single space before ribbon when no MR strip

        # Ribbon
        t.append_text(ribbon)
        return t

    def set_counts(
        self,
        wt_count: int,
        agent_count: int,
        mr_info: "MRInfo | None" = None,
        avail_width: int | None = None,
    ) -> None:
        """Update badge counts, MR info and re-render content."""
        self._mr_info = mr_info
        self._wt_count = wt_count
        self._agent_count = agent_count
        if avail_width is not None:
            self._avail_width = avail_width
        self._has = self._compute_has(self.project)  # refresh in case objects changed
        self.update(self.build_content(
            self.project, self._avail_width, mr_info, self._has,
            wt_count=wt_count, agent_count=agent_count,
        ))


# ---------------------------------------------------------------------------
# pick_best_mr: helper to select the most relevant MR for a project row
# ---------------------------------------------------------------------------


def _parse_mr_number(url: str, label: str) -> int:
    """Parse MR/PR number from URL or label string. Returns -1 if not parseable."""
    # Try URL first: .../pull/42 or .../merge_requests/42
    m = re.search(r"/(?:pull|merge_requests)/(\d+)", url)
    if m:
        return int(m.group(1))
    # Try label: "PR #42" or "MR !42"
    m = re.search(r"[#!](\d+)", label)
    if m:
        return int(m.group(1))
    return -1


def pick_best_mr(
    project: "Project",
    mr_data: dict,
    rel_index: object,
) -> "MRInfo | None":
    """Select the most relevant MR for a project row.

    Priority:
    1. Live API data for a linked worktree's branch (via rel_index, same repo only)
    2. Project's own stored MR objects (PresetKind.MR in project.objects)

    Deliberately avoids broad repo-wide fallback to prevent the same MR
    appearing on multiple projects that share a repo.
    """
    # Priority 1: live MR for a linked worktree's branch
    if mr_data and project.repo is not None:
        for wt in rel_index.worktrees_for(project):  # type: ignore[union-attr]
            if wt.repo_name != project.repo:
                continue
            mr = mr_data.get((wt.repo_name, wt.branch))
            if mr is not None:
                return mr

    # Priority 2: project's own stored MR objects (highest-numbered wins)
    mr_objects = [obj for obj in project.objects if obj.kind == PresetKind.MR]
    if mr_objects:
        best_num = -1
        best_obj = None
        for obj in mr_objects:
            num = _parse_mr_number(obj.value, obj.label)
            if num > best_num:
                best_num = num
                best_obj = obj
        if best_obj is not None and best_num >= 0:
            return MRInfo(
                mr_number=best_num,
                is_draft=False,
                ci_status=None,
                url=best_obj.value,
            )

    return None


# ---------------------------------------------------------------------------
# ProjectList: main widget with cursor navigation and repo grouping
# ---------------------------------------------------------------------------


class ProjectList(Widget, can_focus=True):
    """Left pane: project list grouped by repo with cursor navigation.

    Replaces the old ListView-based approach with VerticalScroll + GroupHeader
    + cursor/_rows/--highlight pattern (same as ProjectDetail, TerminalPane,
    WorktreePane). Projects are grouped under repo headers; unmatched projects
    appear under 'Other' (shown last).
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("enter", "select_project", "Open"),
        Binding("n", "new_project", "New", show=True),
        Binding("e", "rename_project", "Rename", show=True),
        Binding("D", "delete_project", "Delete", show=True),
        Binding("delete", "delete_project", "Delete", show=False),
        Binding("R", "assign_repo", "Assign Repo", show=True),
        Binding("a", "archive_project", "Archive", show=True),
        Binding("A", "open_archive_browser", "Archives", show=True),
        Binding("g", "toggle_status", "Status", show=True),
    ]

    DEFAULT_CSS = """
    ProjectList:focus-within ProjectRow.--highlight {
        background: $accent;
    }
    ProjectList:focus ProjectRow.--highlight {
        background: $accent;
    }
    ProjectRow.--highlight {
        background: $accent 30%;
    }
    ProjectList .section-spacer {
        height: 1;
    }
    """

    class ProjectHighlighted(Message):
        """Fired when highlight moves to a different project."""

        def __init__(self, project: Project) -> None:
            self.project = project
            super().__init__()

    class ProjectSelected(Message):
        """Fired when user presses Enter on a project (D-04)."""

        def __init__(self, project: Project) -> None:
            self.project = project
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._projects: list[Project] = []
        self._repos: list[Repo] = []
        self._cursor: int = -1
        self._rows: list[ProjectRow] = []
        self._render_generation: int = 0
        self.border_title = "Projects"

    def compose(self) -> ComposeResult:
        yield _ProjectScroll(id="project-scroll")

    def set_projects(self, projects: list[Project], repos: list[Repo] | None = None) -> None:
        """Populate the grouped project list. Called from JoyApp._set_projects.

        Args:
            projects: List of projects to display.
            repos: Optional list of repos for grouping. Falls back to self._repos.
        """
        self._projects = projects
        if repos is not None:
            self._repos = repos
        self._render_generation += 1
        gen = self._render_generation
        self.call_after_refresh(lambda: self._rebuild(gen))

    def _rebuild(self, gen: int = 0) -> None:
        """Rebuild the grouped project view inside the scroll container."""
        if gen != self._render_generation:
            return  # superseded by a newer set_projects call
        scroll = self.query_one("#project-scroll", _ProjectScroll)
        if not scroll.is_attached:
            # Scroll container not yet mounted -- reschedule
            self.call_after_refresh(lambda: self._rebuild(gen))
            return
        # Save cursor identity before DOM rebuild
        saved_name: str | None = None
        saved_index = self._cursor
        had_rows_before = len(self._rows) > 0
        if 0 <= self._cursor < len(self._rows):
            saved_name = self._rows[self._cursor].project.name

        scroll.remove_children()

        # Group projects by repo
        repo_names = {r.name for r in self._repos} if self._repos else set()
        grouped: dict[str, list[Project]] = {}
        other: list[Project] = []
        for p in self._projects:
            if p.repo and p.repo in repo_names:
                grouped.setdefault(p.repo, []).append(p)
            else:
                other.append(p)

        new_rows: list[ProjectRow] = []
        avail_width = self._get_available_width()
        first_group = True

        # Mount repo groups alphabetically (D-09)
        for repo_name in sorted(grouped, key=str.lower):
            if not first_group:
                scroll.mount(Static("", classes="section-spacer"))
            first_group = False
            scroll.mount(GroupHeader(repo_name))
            for p in grouped[repo_name]:
                row = ProjectRow(p, avail_width=avail_width)
                scroll.mount(row)
                new_rows.append(row)

        # Mount "Other" group last (D-09)
        if other:
            if grouped:  # only show "Other" header when there are also repo groups
                scroll.mount(Static("", classes="section-spacer"))
                scroll.mount(GroupHeader("Other"))
            for p in other:
                row = ProjectRow(p, avail_width=avail_width)
                scroll.mount(row)
                new_rows.append(row)

        self._rows = new_rows
        # Restore cursor by identity match (same pattern as TerminalPane/WorktreePane)
        if saved_name is not None and new_rows:
            for i, row in enumerate(new_rows):
                if row.project.name == saved_name:
                    self._cursor = i
                    break
            else:
                self._cursor = min(saved_index, len(new_rows) - 1)
        elif new_rows and not had_rows_before and saved_index == -1:
            # First-time population: auto-select first item
            self._cursor = 0
        elif new_rows and saved_index >= 0:
            # Had cursor but identity lost: clamp to valid range
            self._cursor = min(saved_index, len(new_rows) - 1)
        else:
            # Preserve cleared selection (-1) or empty
            self._cursor = -1
        self._update_highlight()

    def _update_highlight(self) -> None:
        """Apply '--highlight' CSS class to the row at the current cursor position."""
        for row in self._rows:
            row.remove_class("--highlight")
        if 0 <= self._cursor < len(self._rows):
            self._rows[self._cursor].add_class("--highlight")
            self._rows[self._cursor].scroll_visible()
            self.post_message(self.ProjectHighlighted(self._rows[self._cursor].project))

    def action_cursor_up(self) -> None:
        """Move cursor up one row."""
        if self._cursor > 0:
            self._cursor -= 1
            self._update_highlight()

    def action_cursor_down(self) -> None:
        """Move cursor down one row."""
        if self._cursor < len(self._rows) - 1:
            self._cursor += 1
            self._update_highlight()

    def action_select_project(self) -> None:
        """Fire ProjectSelected message for the highlighted project (D-04)."""
        if 0 <= self._cursor < len(self._rows):
            self.post_message(self.ProjectSelected(self._rows[self._cursor].project))

    def action_rename_project(self) -> None:
        """Rename the highlighted project via a modal pre-filled with the current name."""
        from joy.screens.name_input import NameInputModal  # noqa: PLC0415 -- lazy import

        if self._cursor < 0 or self._cursor >= len(self._rows):
            return
        project = self._rows[self._cursor].project

        def on_name(name: str | None) -> None:
            if name is None:
                return  # Escape
            if name == project.name:
                return  # no change
            # Check for duplicate name
            if any(p.name == name and p is not project for p in self.app._projects):
                self.app.notify(f"Project '{name}' already exists", severity="error", markup=False)
                return
            project.name = name
            self.app._save_projects_bg()
            self.set_projects(list(self.app._projects), self._repos)

            def _restore_cursor() -> None:
                for i, row in enumerate(self._rows):
                    if row.project is project:
                        self.select_index(i)
                        break

            self.call_after_refresh(_restore_cursor)
            self.app.notify(f"Renamed to: '{name}'", markup=False)
            # Re-render the detail pane
            from joy.widgets.project_detail import ProjectDetail  # noqa: PLC0415

            try:
                self.app.query_one("#project-detail", ProjectDetail).set_project(project)
            except Exception:
                pass  # detail pane not mounted yet

        self.app.push_screen(
            NameInputModal(title="Rename Project", initial_value=project.name),
            on_name,
        )

    def action_delete_project(self) -> None:
        """Delete the highlighted project after confirmation (PROJ-05, D-12, D-13)."""
        from joy.screens import ConfirmationModal  # noqa: PLC0415 -- lazy import avoids circular dep

        if self._cursor < 0 or self._cursor >= len(self._rows):
            return
        project = self._rows[self._cursor].project
        cursor_at = self._cursor

        def on_confirm(confirmed: bool) -> None:
            if not confirmed:
                return
            # Close iTerm2 tab if linked (D-09, D-12: skip silently if None)
            if project.iterm_tab_id:
                self.app._close_tab_bg(project.iterm_tab_id)
            projects = self.app._projects
            try:
                projects.remove(project)
            except ValueError:
                return  # already removed
            self.app._save_projects_bg()
            self.set_projects(projects, self._repos)
            if projects:
                # Select adjacent: next if available, else previous (D-13).
                new_index = min(cursor_at, len(projects) - 1)

                def _restore_selection() -> None:
                    self.focus()
                    self.select_index(new_index)

                self.call_after_refresh(_restore_selection)
            else:
                # No projects left -- clear detail pane
                from joy.widgets.project_detail import ProjectDetail  # noqa: PLC0415

                detail = self.app.query_one("#project-detail", ProjectDetail)
                detail._project = None
                detail._rows = []
                detail._cursor = -1
                scroll = detail.query_one("#detail-scroll")
                scroll.remove_children()
            self.app.notify(f"Deleted project: '{project.name}'", markup=False)

        self.app.push_screen(
            ConfirmationModal(
                title="Delete Project",
                prompt=f"Delete project '{project.name}'? This will remove it and all its objects.",
            ),
            on_confirm,
        )

    def action_assign_repo(self) -> None:
        """Assign (or clear) the highlighted project's repo field (FLOW-01)."""
        from joy.screens.repo_picker import RepoPickerModal  # noqa: PLC0415

        if self._cursor < 0 or self._cursor >= len(self._rows):
            return
        if not self._repos:
            self.app.notify("No repos registered. Add one via Settings (s).", markup=False)
            return
        project = self._rows[self._cursor].project

        def on_pick(result: object) -> None:
            if result is RepoPickerModal.CANCELLED:
                return  # Escape — no change
            # result is str (repo name) or None (unassign)
            project.repo = result  # type: ignore[assignment]
            self.app._save_projects_bg()
            label = result if result else "(none)"
            self.app.notify(f"Assigned repo: {label} → '{project.name}'", markup=False)
            # Re-render to reflect new grouping
            self.set_projects(list(self.app._projects), self._repos)

        self.app.push_screen(
            RepoPickerModal(self._repos, current_repo=project.repo),
            on_pick,
        )

    def action_new_project(self) -> None:
        """Delegate to JoyApp.action_new_project (n only fires from project list focus)."""
        self.app.action_new_project()

    def action_archive_project(self) -> None:
        """Archive the highlighted project to cold storage (~/.joy/archive.toml)."""
        from joy.screens import ConfirmationModal  # noqa: PLC0415

        if self._cursor < 0 or self._cursor >= len(self._rows):
            return
        project = self._rows[self._cursor].project
        cursor_at = self._cursor

        def on_archive(confirmed: bool) -> None:
            if not confirmed:
                return

            # Always close iTerm2 tab if linked (D-10, D-12: skip silently if None)
            if project.iterm_tab_id:
                self.app._close_tab_bg(project.iterm_tab_id)

            # 1. Strip WORKTREE + TERMINALS objects; preserve all others
            stripped_objects = [
                obj for obj in project.objects
                if obj.kind not in (PresetKind.WORKTREE, PresetKind.TERMINALS)
            ]
            from joy.models import ArchivedProject, Project as _Project  # noqa: PLC0415
            from datetime import datetime, timezone  # noqa: PLC0415
            archived_project_data = _Project(
                name=project.name,
                objects=stripped_objects,
                created=project.created,
                repo=project.repo,
            )

            # 2. Remove from live projects list
            projects = self.app._projects
            try:
                projects.remove(project)
            except ValueError:
                return  # already removed
            self.app._save_projects_bg()

            # 3. Append to archive
            archived = ArchivedProject(
                project=archived_project_data,
                archived_at=datetime.now(timezone.utc),
            )
            self.app._append_to_archive_bg(archived)

            # 4. Refresh list and restore cursor
            self.set_projects(projects, self._repos)
            if projects:
                new_index = min(cursor_at, len(projects) - 1)

                def _restore() -> None:
                    self.focus()
                    self.select_index(new_index)

                self.call_after_refresh(_restore)
            self.app.notify(f"Archived: '{project.name}'", markup=False)

        self.app.push_screen(
            ConfirmationModal(
                title="Archive Project",
                prompt=f"Archive project '{project.name}'? This will archive it and close its iTerm2 tab.",
                hint="Enter to archive, Escape to cancel",
            ),
            on_archive,
        )

    def action_open_archive_browser(self) -> None:
        """Open the archive browser to view and unarchive projects (A key)."""
        from joy.screens.archive_browser import ArchiveBrowserModal  # noqa: PLC0415
        from joy.store import load_archived_projects  # noqa: PLC0415
        from joy.models import ArchivedProject  # noqa: PLC0415

        archived = load_archived_projects()
        if not archived:
            self.app.notify("No archived projects.", markup=False)
            return

        # Build active branch set from last worktree refresh snapshot
        active_branches: set[str] = {
            wt.branch for wt in self.app._current_worktrees
            if wt.branch != "HEAD"
        }

        def on_unarchive(result: ArchivedProject | None) -> None:
            if result is None:
                return
            # Restore project (already stripped of WORKTREE/TERMINALS on archive)
            self.app._projects.append(result.project)
            self.app._save_projects_bg()
            self.app._remove_from_archive_bg(result)
            self.set_projects(list(self.app._projects), self._repos)
            self.app.notify(f"Unarchived: '{result.project.name}'", markup=False)

        self.app.push_screen(
            ArchiveBrowserModal(archived=archived, active_branches=active_branches),
            on_unarchive,
        )

    def sync_to(self, project_name: str) -> bool:
        """Move cursor to matching project_name row without posting ProjectHighlighted.

        Silent cursor mutation for cross-pane sync. Does NOT call .focus(). (D-09, D-10)
        Returns True if a match was found, False otherwise. (D-08)

        IMPORTANT: Do NOT use select_index() here — it calls _update_highlight() which
        posts ProjectHighlighted, creating a sync loop even with the _is_syncing guard.
        """
        for i, row in enumerate(self._rows):
            if row.project.name == project_name:
                self._cursor = i
                for r in self._rows:
                    r.remove_class("--highlight")
                row.add_class("--highlight")
                row.scroll_visible()
                return True
        # No match: leave _cursor unchanged (D-08)
        return False

    def select_first(self) -> None:
        """Auto-select the first project (PROJ-02)."""
        if self._rows:
            self._cursor = 0
            self._update_highlight()

    def select_index(self, index: int) -> None:
        """Select project at given index."""
        if 0 <= index < len(self._rows):
            self._cursor = index
            self._update_highlight()

    def _get_available_width(self) -> int:
        """Return usable content width for row rendering."""
        width = self.content_region.width
        if width == 0:
            return 80
        return max(width - 2, 20)  # subtract 2 for left+right padding

    def update_badges(self, index: object, mr_data: dict | None = None) -> None:
        """Push badge counts and MR info from RelationshipIndex to all project rows.

        Called by JoyApp._update_badges() after every completed refresh cycle.
        """
        from joy.resolver import RelationshipIndex  # noqa: PLC0415 — avoid circular at module level
        avail_width = self._get_available_width()
        for row in self._rows:
            wt_count = len(index.worktrees_for(row.project))  # type: ignore[union-attr]
            agent_count = len(index.terminals_for(row.project))  # type: ignore[union-attr]
            mr_info = pick_best_mr(row.project, mr_data or {}, index) if mr_data else None
            row.set_counts(wt_count, agent_count, mr_info=mr_info, avail_width=avail_width)

    def action_toggle_status(self) -> None:
        """Cycle project status: idle → prio → hold → idle (g key)."""
        if self._cursor < 0 or self._cursor >= len(self._rows):
            return
        project = self._rows[self._cursor].project
        cycle = {"idle": "prio", "prio": "hold", "hold": "idle"}
        # Unknown status (e.g. hand-edited TOML) resets to "idle" on first g press
        project.status = cycle.get(project.status, "idle")
        self.app._save_projects_bg()
        # Re-render just this row
        row = self._rows[self._cursor]
        row._has = ProjectRow._compute_has(project)
        row.update(ProjectRow.build_content(
            project, row._avail_width, row._mr_info, row._has,
            wt_count=row._wt_count, agent_count=row._agent_count,
        ))
