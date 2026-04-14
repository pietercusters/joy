# Quick Task 260414-k2u: Worktree Pane Cursor Navigation — Research

**Researched:** 2026-04-14
**Domain:** Textual cursor pattern (WorktreePane), MRInfo model, IDE open via subprocess
**Confidence:** HIGH — all findings verified from codebase source [VERIFIED: codebase grep]

---

## Summary

WorktreePane is currently a read-only widget (BINDINGS = [], no `_cursor`, no `_rows`). The TerminalPane is the exact model to follow. The diff required is straightforward with one blocking gap: `MRInfo` has no `url` field, so `webbrowser.open(mr_info.url)` as described in CONTEXT.md cannot work until `url` is added to the dataclass and populated in `mr_status.py`.

**Primary recommendation:** Add `url: str` to `MRInfo`, populate it in `_fetch_github_mrs` and `_fetch_gitlab_mrs`, then apply the TerminalPane cursor pattern to WorktreePane with a two-branch Enter handler (MR URL vs. IDE open).

---

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Mirror TerminalPane exactly: j/k (and up/down arrows) move the cursor, Enter activates, Escape returns focus to projects pane
- GroupHeader rows are skipped — cursor only lands on WorktreeRow items
- Cursor highlight uses `--highlight` CSS class
- Enter with MR: `webbrowser.open(mr_info.url)`
- Enter without MR: `subprocess.run(["open", "-a", config.ide, worktree.path], check=False)`

### Claude's Discretion
- Footer hint update: context-sensitive sub_title when WorktreePane is focused (already handled by `on_descendant_focus` in app.py — sets `sub_title = "Worktrees"`)
- Test additions: mirror test_terminal_pane.py patterns

### Deferred Ideas (OUT OF SCOPE)
- None stated

---

## Finding 1: MRInfo Has No `url` Field — Must Add

[VERIFIED: src/joy/models.py lines 152-161]

Current `MRInfo` dataclass:
```python
@dataclass
class MRInfo:
    mr_number: int
    is_draft: bool
    ci_status: str | None
    author: str
    last_commit_hash: str
    last_commit_msg: str
    # NO url field
```

The CONTEXT.md decision `webbrowser.open(mr_info.url)` requires adding `url: str = ""` to `MRInfo`.

**Where to populate it:**
- GitHub (`_fetch_github_mrs`, mr_status.py line 96): the `gh pr list` JSON output includes `url` field. Must add `"url"` to the `--json` flag list and pass `url=pr["url"]` when constructing `MRInfo`.
- GitLab (`_fetch_gitlab_mrs`, mr_status.py line 145): the `glab mr list` JSON output includes `"web_url"` key. Pass `url=mr.get("web_url", "")`.

[VERIFIED: GitHub CLI gh pr list JSON fields include `url`; GitLab glab mr list JSON includes `web_url` — standard forge API fields, consistent with codebase forge detection pattern]

---

## Finding 2: WorktreeRow Does Not Store `repo_name` or `branch`

[VERIFIED: src/joy/widgets/worktree_pane.py lines 131-147]

`WorktreeRow.__init__` accepts a `WorktreeInfo` and `mr_info` but does NOT store them as instance attributes — it immediately converts them to a `rich.Text` renderable and calls `super().__init__(content)`. The `worktree` and `mr_info` objects are not retained.

**Required change:** Store `repo_name`, `branch`, `path`, and `mr_info` as attributes in `WorktreeRow.__init__` before calling `super()`:

```python
def __init__(self, worktree: WorktreeInfo, *, display_path=None, mr_info=None, **kwargs):
    self.repo_name = worktree.repo_name   # for mr_data lookup key
    self.branch = worktree.branch          # for mr_data lookup key
    self.path = worktree.path              # for IDE open fallback
    self.mr_info = mr_info                 # for Enter handler — may be None
    # ... existing content build + super().__init__
```

Note: `self.session_id` is the analogous attribute in `SessionRow` (terminal_pane.py line 111).

---

## Finding 3: Exact Cursor Pattern to Apply to WorktreePane

[VERIFIED: src/joy/widgets/terminal_pane.py — full TerminalPane implementation]

**State variables to add to `WorktreePane.__init__`:**
```python
self._cursor: int = -1
self._rows: list[WorktreeRow] = []
# _mr_data needed by Enter handler; stored from set_worktrees()
self._mr_data: dict[tuple[str, str], MRInfo] = {}
```

**BINDINGS to replace the existing `BINDINGS = []`:**
```python
BINDINGS = [
    Binding("escape", "focus_projects", "Back"),
    Binding("up", "cursor_up", "Up"),
    Binding("down", "cursor_down", "Down"),
    Binding("k", "cursor_up", "Up"),
    Binding("j", "cursor_down", "Down"),
    Binding("enter", "activate_row", "Open"),
]
```

**CSS additions** (append to `DEFAULT_CSS`, mirroring TerminalPane lines 178-183):
```css
WorktreePane:focus-within WorktreeRow.--highlight {
    background: $accent;
}
WorktreeRow.--highlight {
    background: $accent 30%;
}
```

**Methods to add — exact mirrors of TerminalPane equivalents:**

```python
def _update_highlight(self) -> None:
    for row in self._rows:
        row.remove_class("--highlight")
    if 0 <= self._cursor < len(self._rows):
        self._rows[self._cursor].add_class("--highlight")
        self._rows[self._cursor].scroll_visible()

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
```

**`set_worktrees` changes:**
- After building rows and calling `scroll.mount(WorktreeRow(...))`, append each row to `new_rows`.
- After the loop: `self._rows = new_rows; self._cursor = 0 if new_rows else -1; self._update_highlight()`
- On empty worktrees path: `self._rows = []; self._cursor = -1`
- Store `self._mr_data = mr_data` at the top of `set_worktrees` for the Enter handler.

**Enter handler (differs from TerminalPane's `action_focus_session`):**
```python
def action_activate_row(self) -> None:
    if self._cursor < 0 or self._cursor >= len(self._rows):
        return
    row = self._rows[self._cursor]
    mr_info = row.mr_info
    if mr_info is not None and mr_info.url:
        import webbrowser  # noqa: PLC0415
        webbrowser.open(mr_info.url)
    else:
        import subprocess  # noqa: PLC0415
        subprocess.run(["open", "-a", self.app._config.ide, row.path], check=False)
```

Config access: `self.app._config` — this is how JoyApp exposes config (verified: app.py line 60 `self._config: Config = Config()`). The IDE open pattern matches `_open_worktree` in operations.py exactly (line 70).

---

## Finding 4: IDE Open Pattern

[VERIFIED: src/joy/operations.py line 70]

```python
subprocess.run(["open", "-a", config.ide, item.value], check=True)
```

For the WorktreePane action, use `check=False` (consistent with CONTEXT.md decision; avoids TUI crash if IDE not found).

---

## Finding 5: Footer Sub-title Already Handled

[VERIFIED: src/joy/app.py lines 254-271]

`on_descendant_focus` in `JoyApp` already sets `self.sub_title = "Worktrees"` when `node.id == "worktrees-pane"`. No changes to app.py needed for the sub_title update. The Footer widget renders BINDINGS automatically — adding BINDINGS to WorktreePane will surface them in the footer when focused.

---

## Finding 6: `webbrowser` Import

[VERIFIED: src/joy/app.py — webbrowser not currently imported in worktree_pane.py]

`webbrowser` is Python stdlib. Add lazy import inside `action_activate_row` to match the project's lazy-import pattern (per CLAUDE.md conventions).

---

## Test Approach (Mirror test_terminal_pane.py)

[VERIFIED: tests/test_terminal_pane.py — full test file reviewed]

The test file uses `asyncio.run()` wrapping `async with app.run_test() as pilot` with `await pilot.pause(0.1)` between actions. No `@pytest.mark.asyncio` — synchronous wrapper pattern.

**Key test cases needed (4 core + 2 edge):**

| Test | What to assert |
|------|---------------|
| `test_worktree_pane_has_bindings` | BINDINGS contains escape, up, down, k, j, enter — pure unit test, no TUI |
| `test_cursor_starts_at_0_after_set_worktrees` | After set_worktrees with rows, `_cursor == 0` |
| `test_cursor_navigation_j_moves_down` | press("j") moves `_cursor` from 0 to 1 |
| `test_enter_opens_mr_url` | patch `webbrowser.open`, press Enter on row with `mr_info.url`, assert called |
| `test_enter_opens_ide_when_no_mr` | patch `subprocess.run`, press Enter on row with `mr_info=None`, assert called with `["open", "-a", ...]` |
| `test_enter_noop_when_no_rows` | `_cursor == -1`, press Enter, webbrowser.open not called |

**Helper needed:**
```python
def _make_worktree(repo_name="repo-a", branch="feat-x", path="/tmp/wt") -> WorktreeInfo:
    return WorktreeInfo(repo_name=repo_name, branch=branch, path=path)

def _make_mr_info(url="https://github.com/x/y/pull/1") -> MRInfo:
    return MRInfo(mr_number=1, is_draft=False, ci_status=None,
                  author="@dev", last_commit_hash="abc1234",
                  last_commit_msg="feat: thing", url=url)
```

---

## Gotchas / Pitfalls

**Gotcha 1: WorktreeRow height is 2** (two-line row, terminal_pane.py SessionRow is height 1). `scroll_visible()` call in `_update_highlight` still works — it scrolls to the widget regardless of height.

**Gotcha 2: `_mr_data` storage not strictly needed** — since `mr_info` is stored on each `WorktreeRow` directly (Finding 2), the Enter handler can use `row.mr_info` without needing a separate `_mr_data` dict. Storing `_mr_data` on the pane for tests or refresh use is optional.

**Gotcha 3: Empty-state path must reset cursor** — the current `set_worktrees` returns early on empty worktrees. Must add `self._rows = []; self._cursor = -1` before that early return. Same as TerminalPane's empty-path handling (lines 218-222).

**Gotcha 4: `_WorktreeScroll` already non-focusable** — [VERIFIED: worktree_pane.py line 80] `can_focus=False` already set, same as TerminalPane. No change needed.

**Gotcha 5: `MRInfo.url` default** — adding `url: str = ""` with a default keeps all existing `MRInfo(...)` call sites in tests valid without modification. The Enter handler checks `if mr_info is not None and mr_info.url:` which correctly handles empty string.

---

## Sources

- [VERIFIED: codebase] `src/joy/widgets/worktree_pane.py` — current WorktreePane state
- [VERIFIED: codebase] `src/joy/widgets/terminal_pane.py` — cursor pattern to replicate
- [VERIFIED: codebase] `src/joy/models.py` — MRInfo dataclass (no url field confirmed)
- [VERIFIED: codebase] `src/joy/mr_status.py` — GitHub/GitLab MR fetch; url/web_url available in API responses
- [VERIFIED: codebase] `src/joy/operations.py` line 70 — IDE open subprocess pattern
- [VERIFIED: codebase] `src/joy/app.py` lines 60, 254-271 — config access, sub_title handling
- [VERIFIED: codebase] `tests/test_terminal_pane.py` — test patterns to mirror
