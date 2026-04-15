"""Bottom-right pane: grouped worktree list with status indicators."""
from __future__ import annotations

import subprocess
import webbrowser
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static

from joy.models import MRInfo, WorktreeInfo

# ---------------------------------------------------------------------------
# Nerd Font icon constants (per D-08, verified codepoints from RESEARCH.md)
# ---------------------------------------------------------------------------

ICON_BRANCH = "\ue0a0"           # nf-pl-branch (same as PRESET_ICONS[BRANCH])
ICON_DIRTY = "\uf111"            # nf-fa-circle
ICON_NO_UPSTREAM = "\U000f0be1"  # nf-md-cloud_off (verified, NOT nf-fa-cloud_off)

# Phase 11: MR/CI status icons (D-04, D-05)
ICON_MR_OPEN    = "\uea64"      # nf-cod-git_pull_request (green for open)
ICON_MR_DRAFT   = "\uebdb"      # nf-cod-git_pull_request_draft (dim for draft)
ICON_CI_PASS    = "\uf00c"      # nf-fa-check (green)
ICON_CI_FAIL    = "\uf00d"      # nf-fa-times (red)
ICON_CI_PENDING = "\uf192"      # nf-fa-dot_circle_o (yellow) -- distinct from ICON_DIRTY


# ---------------------------------------------------------------------------
# Pure functions for path processing (D-13, D-14)
# ---------------------------------------------------------------------------


def abbreviate_home(path_str: str) -> str:
    """Replace leading home directory prefix with ~. (D-13)

    Examples:
        /Users/pieter/Github/joy -> ~/Github/joy
        /Users/pieter           -> ~
        /tmp/other/wt/hotfix    -> /tmp/other/wt/hotfix (unchanged)
    """
    home = str(Path.home())
    if path_str.startswith(home):
        return "~" + path_str[len(home):]
    return path_str


def middle_truncate(path: str, max_width: int) -> str:
    """Truncate path in the middle with ellipsis if wider than max_width. (D-14)

    Preserves the home-relative prefix and the leaf segment so both
    "which area of disk" and "which specific worktree" remain readable.

    Examples:
        ~/Github/joy/wt/feat-x (short)  -> unchanged
        ~/Projects/very/deeply/nested/repo/wt/long-branch (long)
            -> ~/Projects/\u2026/long-branch
    """
    if len(path) <= max_width:
        return path
    parts = path.split("/")
    if len(parts) <= 3:
        # Too few segments for meaningful middle-truncation; right-truncate
        return path[:max_width - 1] + "\u2026"
    head = parts[0] + "/" + parts[1]   # e.g. "~/Github"
    tail = parts[-1]                    # e.g. "feature-branch"
    ellipsis = "/\u2026/"
    if len(head) + len(ellipsis) + len(tail) > max_width:
        # Even head + \u2026 + tail doesn't fit; right-truncate
        return path[:max_width - 1] + "\u2026"
    return head + ellipsis + tail


# ---------------------------------------------------------------------------
# _WorktreeScroll: non-focusable scroll container (per _DetailScroll pattern)
# ---------------------------------------------------------------------------


class _WorktreeScroll(VerticalScroll, can_focus=False):
    """Non-focusable scroll container for worktree rows.

    Prevents VerticalScroll from stealing focus from WorktreePane (Pitfall 1
    from RESEARCH.md — VerticalScroll is focusable by default).
    """


# ---------------------------------------------------------------------------
# GroupHeader: repo section header (duplicated from project_detail to avoid
# cross-widget coupling, per Pitfall 5 resolution in RESEARCH.md)
# ---------------------------------------------------------------------------


class GroupHeader(Static):
    """Repo section header. Duplicated from project_detail to avoid cross-widget coupling."""

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
# WorktreeRow: two-line row for a single worktree entry (D-07, D-08)
# ---------------------------------------------------------------------------


class WorktreeRow(Static):
    """Two-line row: branch + indicators on line 1, abbreviated path on line 2.

    Accepts a WorktreeInfo and builds its own rich.Text content. An optional
    display_path argument overrides the default abbreviate_home result (used by
    WorktreePane.set_worktrees to apply middle-truncation before row creation).

    Intentionally a single DOM node per worktree for refresh-cheapness.
    """

    DEFAULT_CSS = """
    WorktreeRow {
        width: 1fr;
        height: 2;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        worktree: WorktreeInfo,
        *,
        display_path: str | None = None,
        mr_info: MRInfo | None = None,
        **kwargs,
    ) -> None:
        self.repo_name: str = worktree.repo_name
        self.branch: str = worktree.branch
        self.path: str = worktree.path
        self.mr_info: MRInfo | None = mr_info
        self.is_default_branch: bool = worktree.is_default_branch
        path = display_path if display_path is not None else abbreviate_home(worktree.path)
        content = self.build_content(
            worktree.branch,
            worktree.is_dirty,
            worktree.has_upstream,
            path,
            mr_info=mr_info,
            is_default_branch=worktree.is_default_branch,
        )
        super().__init__(content, **kwargs)

    @staticmethod
    def build_content(
        branch: str,
        is_dirty: bool,
        has_upstream: bool,
        display_path: str,
        mr_info: MRInfo | None = None,
        is_default_branch: bool = False,
    ) -> Text:
        """Build the rich.Text renderable for a two-line worktree row.

        Per D-01/D-02: When mr_info is present, line 1 shows MR badges between
        branch and dirty/upstream indicators; line 2 shows @author + commit.
        When mr_info is None, layout is unchanged from Phase 9.

        When is_default_branch is True, the entire row renders in dim style
        with no dirty/upstream indicators (default branches are not interesting).
        """
        t = Text(no_wrap=True, overflow="ellipsis")

        if is_default_branch:
            t.append(f" {ICON_BRANCH} ", style="dim")
            t.append(branch, style="dim")
            t.append("\n")
            t.append(f"  {display_path}", style="dim")
            return t

        t.append(f" {ICON_BRANCH} ", style="bold")
        t.append(branch)

        # D-02: MR badges between branch name and dirty/upstream indicators
        if mr_info is not None:
            t.append(f"  !{mr_info.mr_number} ", style="dim")
            if mr_info.is_draft:
                t.append(ICON_MR_DRAFT, style="dim")
            else:
                t.append(ICON_MR_OPEN, style="green")
            # D-05: CI status icons (blank when None)
            if mr_info.ci_status == "pass":
                t.append(f" {ICON_CI_PASS}", style="green")
            elif mr_info.ci_status == "fail":
                t.append(f" {ICON_CI_FAIL}", style="red")
            elif mr_info.ci_status == "pending":
                t.append(f" {ICON_CI_PENDING}", style="yellow")

        if is_dirty:
            t.append(f" {ICON_DIRTY}", style="yellow")
        if not has_upstream:
            t.append(f" {ICON_NO_UPSTREAM}", style="dim")
        t.append("\n")

        # D-01: Line 2 is context-sensitive
        if mr_info is not None and (mr_info.author or mr_info.last_commit_hash):
            parts = []
            if mr_info.author:
                parts.append(mr_info.author)
            if mr_info.last_commit_hash:
                commit_text = mr_info.last_commit_hash
                if mr_info.last_commit_msg:
                    commit_text += f" {mr_info.last_commit_msg}"
                parts.append(commit_text)
            t.append(f"  {'  '.join(parts)}", style="dim")
        else:
            t.append(f"  {display_path}", style="dim")

        return t


# ---------------------------------------------------------------------------
# WorktreePane: main pane widget (D-01 through D-18)
# ---------------------------------------------------------------------------


class WorktreePane(Widget, can_focus=True):
    """Bottom-right pane: grouped worktree list with status indicators.

    Interactive — j/k/arrows for cursor navigation, Enter to open MR or IDE.
    Data is pushed via set_worktrees().
    """

    class WorktreeHighlighted(Message):
        """Fired when highlight moves to a different worktree row. (D-01, D-02)"""

        def __init__(self, worktree: WorktreeInfo) -> None:
            self.worktree = worktree
            super().__init__()

    BINDINGS = [
        Binding("escape", "focus_projects", "Back"),
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
        Binding("k", "cursor_up", "Up"),
        Binding("j", "cursor_down", "Down"),
        Binding("enter", "activate_row", "Open"),
    ]

    DEFAULT_CSS = """
    WorktreePane {
        height: 1fr;
        border: solid $surface-lighten-2;
    }
    WorktreePane:focus-within {
        border: solid $accent;
    }
    WorktreePane:focus {
        border: solid $accent;
    }
    WorktreePane .empty-state {
        width: 1fr;
        height: 1fr;
        content-align: center middle;
        color: $text-muted;
        text-style: dim;
    }
    WorktreePane:focus-within WorktreeRow.--highlight {
        background: $accent;
    }
    WorktreeRow.--highlight {
        background: $accent 30%;
    }
    WorktreePane .section-spacer {
        height: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("id", "worktrees-pane")
        super().__init__(**kwargs)
        self.border_title = "Worktrees"
        self._loaded = False
        self._cursor: int = -1
        self._rows: list[WorktreeRow] = []

    def compose(self) -> ComposeResult:
        """Mount initial Loading\u2026 placeholder (D-05)."""
        yield _WorktreeScroll(
            Static("Loading\u2026", classes="empty-state"),
            id="worktree-scroll",
        )

    async def set_worktrees(
        self,
        worktrees: list[WorktreeInfo],
        *,
        repo_count: int = 0,
        branch_filter: str = "",
        mr_data: dict[tuple[str, str], MRInfo] | None = None,
    ) -> None:
        """Populate the pane with grouped worktree rows. Idempotent (D-03).

        Args:
            worktrees: Flat list from discover_worktrees(). Grouping happens here (D-04).
            repo_count: Number of registered repos — used to distinguish empty states (D-15/D-16).
            branch_filter: Comma-separated filter string for the empty-state hint (D-16).
            mr_data: Mapping of (repo_name, branch) -> MRInfo from fetch_mr_data (Phase 11).
        """
        if mr_data is None:
            mr_data = {}
        scroll = self.query_one("#worktree-scroll", _WorktreeScroll)
        saved_scroll_y = scroll.scroll_y
        # FOUND-03: save cursor identity before DOM rebuild (D-12, D-13)
        saved_identity: tuple[str, str] | None = None
        saved_index = self._cursor
        if 0 <= self._cursor < len(self._rows):
            row = self._rows[self._cursor]
            saved_identity = (row.repo_name, row.branch)
        await scroll.remove_children()
        self._loaded = True
        new_rows: list[WorktreeRow] = []

        if not worktrees:
            self._rows = []
            self._cursor = -1
            if repo_count == 0:
                # D-15: no repos registered at all
                await scroll.mount(
                    Static(
                        "No repos registered. Add one via settings.",
                        classes="empty-state",
                    )
                )
            else:
                # D-16: repos exist but all worktrees filtered or errored (D-17)
                await scroll.mount(
                    Static(
                        f"No active worktrees. (filtered: {branch_filter})",
                        classes="empty-state",
                    )
                )
            scroll.call_after_refresh(lambda: scroll.scroll_to(y=saved_scroll_y, animate=False))
            return

        # Group worktrees by repo_name — repos with no worktrees are naturally hidden (D-10)
        grouped: dict[str, list[WorktreeInfo]] = {}
        for wt in worktrees:
            grouped.setdefault(wt.repo_name, []).append(wt)

        available_width = self._get_available_width()

        # Render repo sections alphabetically (D-11)
        first_group = True
        for repo_name in sorted(grouped, key=str.lower):
            if not first_group:
                await scroll.mount(Static("", classes="section-spacer"))
            first_group = False
            await scroll.mount(GroupHeader(repo_name))
            # Sort worktrees: non-default first, then default; alphabetical within each group (D-12)
            for wt in sorted(grouped[repo_name], key=lambda w: (w.is_default_branch, w.branch.lower())):
                display_path = abbreviate_home(wt.path)
                display_path = middle_truncate(display_path, available_width)
                mr_info = mr_data.get((wt.repo_name, wt.branch))
                row = WorktreeRow(wt, display_path=display_path, mr_info=mr_info)
                await scroll.mount(row)
                new_rows.append(row)

        self._rows = new_rows
        # FOUND-03: restore cursor by identity (D-13, D-14)
        if saved_identity is not None and new_rows:
            for i, row in enumerate(new_rows):
                if (row.repo_name, row.branch) == saved_identity:
                    self._cursor = i
                    break
            else:
                # Item gone: clamp to saved index (D-14) — never reset to 0
                self._cursor = min(saved_index, len(new_rows) - 1)
        elif new_rows:
            self._cursor = 0
        else:
            self._cursor = -1
        self._update_highlight(emit=False)  # refresh restore — no sync message

        scroll.call_after_refresh(lambda: scroll.scroll_to(y=saved_scroll_y, animate=False))

    def set_refresh_label(self, timestamp: str, *, stale: bool = False, mr_error: bool = False) -> None:
        """Update border_title with refresh timestamp. Stale adds warning icon.
        mr_error adds MR fetch failure note per D-10. Both indicators shown when
        both are active simultaneously.

        Args:
            timestamp: Human-readable time string (e.g., "2m ago", "14:32").
            stale: If True, prefix timestamp with warning icon (U+26A0).
            mr_error: If True, show MR fetch failure warning (D-10).
        """
        parts = ["Worktrees"]
        if stale or mr_error:
            parts.append("\u26a0")
        if mr_error:
            parts.append("mr fetch failed")
        parts.append(timestamp)
        self.border_title = "  ".join(parts)

    def _update_highlight(self, *, emit: bool = True) -> None:
        for row in self._rows:
            row.remove_class("--highlight")
        if 0 <= self._cursor < len(self._rows):
            self._rows[self._cursor].add_class("--highlight")
            self._rows[self._cursor].scroll_visible()
            # Post message only on user navigation, not during refresh or sync (D-03, Pitfall 1)
            if emit and not getattr(self.app, "_is_syncing", False):
                row = self._rows[self._cursor]
                wt = WorktreeInfo(
                    repo_name=row.repo_name,
                    branch=row.branch,
                    path=row.path,
                )
                self.post_message(self.WorktreeHighlighted(wt))

    def sync_to(self, repo_name: str, branch: str) -> None:
        """Move cursor to matching (repo_name, branch) row without posting WorktreeHighlighted.

        Silent cursor mutation for cross-pane sync. Does NOT call .focus(). (D-09, D-10)
        If no row matches, _cursor is left unchanged. (D-08)
        """
        for i, row in enumerate(self._rows):
            if row.repo_name == repo_name and row.branch == branch:
                self._cursor = i
                # Inline highlight-only path: CSS + scroll, no post_message (Pitfall 1)
                for r in self._rows:
                    r.remove_class("--highlight")
                row.add_class("--highlight")
                row.scroll_visible()
                return
        # No match: leave _cursor unchanged (D-08)

    def action_cursor_up(self) -> None:
        if self._cursor > 0:
            self._cursor -= 1
            self._update_highlight()

    def action_cursor_down(self) -> None:
        if self._cursor < len(self._rows) - 1:
            self._cursor += 1
            self._update_highlight()

    def action_focus_projects(self) -> None:
        self.app.query_one("#project-list").focus()

    def action_activate_row(self) -> None:
        if self._cursor < 0 or self._cursor >= len(self._rows):
            return
        row = self._rows[self._cursor]
        mr_info = row.mr_info
        if mr_info is not None and mr_info.url:
            from urllib.parse import urlparse
            parsed = urlparse(mr_info.url)
            if parsed.scheme in ("https", "http"):
                webbrowser.open(mr_info.url)
        else:
            config = getattr(self.app, "_config", None)
            ide = config.ide if config else "Cursor"
            subprocess.run(
                ["open", "-a", ide, row.path],
                check=False,
            )

    def _get_available_width(self) -> int:
        """Return usable content width for path truncation (Pitfall 3 mitigation)."""
        width = self.content_region.width
        if width == 0:
            return 80  # safe default when widget not yet laid out
        return max(width - 2, 20)  # subtract 2 for border, floor at 20
