"""Bottom-right pane: grouped worktree list with status indicators."""
from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Static

from joy.models import WorktreeInfo

# ---------------------------------------------------------------------------
# Nerd Font icon constants (per D-08, verified codepoints from RESEARCH.md)
# ---------------------------------------------------------------------------

ICON_BRANCH = "\ue0a0"           # nf-pl-branch (same as PRESET_ICONS[BRANCH])
ICON_DIRTY = "\uf111"            # nf-fa-circle
ICON_NO_UPSTREAM = "\U000f0be1"  # nf-md-cloud_off (verified, NOT nf-fa-cloud_off)


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
        **kwargs,
    ) -> None:
        path = display_path if display_path is not None else abbreviate_home(worktree.path)
        content = self.build_content(
            worktree.branch,
            worktree.is_dirty,
            worktree.has_upstream,
            path,
        )
        super().__init__(content, **kwargs)

    @staticmethod
    def build_content(
        branch: str,
        is_dirty: bool,
        has_upstream: bool,
        display_path: str,
    ) -> Text:
        """Build the rich.Text renderable for a two-line worktree row."""
        t = Text(no_wrap=True, overflow="ellipsis")
        t.append(f" {ICON_BRANCH} ", style="bold")
        t.append(branch)
        if is_dirty:
            t.append(f" {ICON_DIRTY}", style="yellow")
        if not has_upstream:
            t.append(f" {ICON_NO_UPSTREAM}", style="dim")
        t.append("\n")
        t.append(f"  {display_path}", style="dim")
        return t


# ---------------------------------------------------------------------------
# WorktreePane: main pane widget (D-01 through D-18)
# ---------------------------------------------------------------------------


class WorktreePane(Widget, can_focus=True):
    """Bottom-right pane: grouped worktree list with status indicators.

    Read-only — no BINDINGS, no selection cursor. Focusable for Tab cycling
    (preserved from Phase 8 stub, D-10). Data is pushed via set_worktrees().
    """

    BINDINGS = []  # Read-only pane (WKTR-10)

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
    """

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("id", "worktrees-pane")
        super().__init__(**kwargs)
        self.border_title = "Worktrees"
        self._loaded = False

    def compose(self) -> ComposeResult:
        """Mount initial Loading\u2026 placeholder (D-05)."""
        yield _WorktreeScroll(
            Static("Loading\u2026", classes="empty-state"),
            id="worktree-scroll",
        )

    def set_worktrees(
        self,
        worktrees: list[WorktreeInfo],
        *,
        repo_count: int = 0,
        branch_filter: str = "",
    ) -> None:
        """Populate the pane with grouped worktree rows. Idempotent (D-03).

        Args:
            worktrees: Flat list from discover_worktrees(). Grouping happens here (D-04).
            repo_count: Number of registered repos — used to distinguish empty states (D-15/D-16).
            branch_filter: Comma-separated filter string for the empty-state hint (D-16).
        """
        scroll = self.query_one("#worktree-scroll", _WorktreeScroll)
        scroll.remove_children()
        self._loaded = True

        if not worktrees:
            if repo_count == 0:
                # D-15: no repos registered at all
                scroll.mount(
                    Static(
                        "No repos registered. Add one via settings.",
                        classes="empty-state",
                    )
                )
            else:
                # D-16: repos exist but all worktrees filtered or errored (D-17)
                scroll.mount(
                    Static(
                        f"No active worktrees. (filtered: {branch_filter})",
                        classes="empty-state",
                    )
                )
            return

        # Group worktrees by repo_name — repos with no worktrees are naturally hidden (D-10)
        grouped: dict[str, list[WorktreeInfo]] = {}
        for wt in worktrees:
            grouped.setdefault(wt.repo_name, []).append(wt)

        available_width = self._get_available_width()

        # Render repo sections alphabetically (D-11)
        for repo_name in sorted(grouped, key=str.lower):
            scroll.mount(GroupHeader(repo_name))
            # Sort worktrees within repo by branch, case-insensitive (D-12)
            for wt in sorted(grouped[repo_name], key=lambda w: w.branch.lower()):
                display_path = abbreviate_home(wt.path)
                display_path = middle_truncate(display_path, available_width)
                scroll.mount(WorktreeRow(wt, display_path=display_path))

    def _get_available_width(self) -> int:
        """Return usable content width for path truncation (Pitfall 3 mitigation)."""
        width = self.content_region.width
        if width == 0:
            return 80  # safe default when widget not yet laid out
        return max(width - 2, 20)  # subtract 2 for border, floor at 20
