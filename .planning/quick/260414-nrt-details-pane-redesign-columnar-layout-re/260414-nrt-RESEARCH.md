# Quick Task 260414-nrt: Details Pane Redesign - Research

**Researched:** 2026-04-14
**Domain:** Textual TUI widget layout, ModalScreen pattern, icon catalog
**Confidence:** HIGH — all findings verified directly from codebase

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Modal overlay centered over current pane, dismissed with Escape or `l` again
- Icon column: fixed ~3 chars wide
- Kind column: fixed ~12 chars wide, right-aligned
- Value column: fills remaining space, wraps if content too long
- 1 blank line before each section header (subtle separation)
- "label" column dropped — only icon, value, kind remain

### Claude's Discretion
- Exact Textual widget type for modal (Screen vs ModalScreen vs custom widget)
- Exact icons and their grouping/organization in the legend
- CSS implementation details for column layout

### Deferred Ideas (OUT OF SCOPE)
None specified.
</user_constraints>

---

## Summary

Four targeted UI changes to joy's TUI. All are self-contained within existing widgets with no new dependencies. The current `ObjectRow` renders a flat `rich.Text` string — it must be redesigned to a multi-child `Horizontal` layout for the 3-column requirement. The legend modal follows the exact same `ModalScreen[None]` pattern already used by `ConfirmationModal` and `SettingsModal`. Repo field already exists on the `Project` model.

**Primary recommendation:** Replace `ObjectRow` (Static + rich.Text) with a `Horizontal`-based row using fixed-width child `Static` widgets. Use `ModalScreen[None]` for the legend popup, wired to a new `l` binding on the app or `ProjectDetail`. Add blank lines before `GroupHeader` by emitting a `Static("")` spacer before each header during render.

---

## Finding 1: Current Details Pane Rendering

**File:** `src/joy/widgets/project_detail.py` + `src/joy/widgets/object_row.py`

`ObjectRow` is a `Static` widget. It takes an `ObjectItem` and builds a single `rich.Text` object via `_render_text()`, appending: dot indicator, icon, kind label (`item.kind.value`), and value/label — all concatenated with spaces. The `no_wrap=True, overflow="ellipsis"` settings mean long values are truncated.

```python
# Current render (object_row.py line 79-89):
dot = "\u25cf" if item.open_by_default else "\u25cb"
t.append(dot, style=dot_style)
t.append(f" {icon}  {label}  {value}")
```

**Redesign impact:** The flat `rich.Text` approach cannot support independent column widths or value wrapping. Must switch to a `Horizontal` container with three `Static` children (icon, value, kind).

**The dot indicator** (open_by_default marker) needs a decision: fold it into the icon column, or drop it in the redesign. Context says "only icon, value, kind remain" — so dot is dropped per user decision.

---

## Finding 2: Repo Field on Project Model

**File:** `src/joy/models.py` line 78

`Project.repo: str | None = None` — the field exists. It stores the repo name (string key matching a `Repo.name`), not a path or URL. May be `None` for unassigned projects.

The Details pane currently never renders `project.repo`. The repo field should be added as a static "overview" line at the top of the details pane — before the grouped object rows.

**Where to inject:** In `_render_project()` in `project_detail.py`, before the `GROUP_ORDER` loop, mount an overview row (or rows) for the project name and repo.

---

## Finding 3: Textual Column Layout Approach

**Verified from codebase:** `app.py` uses `Grid` with CSS `grid-columns: 1fr 1fr`. The `textual.containers` module is imported there.

**For 3-column row layout, two options:**

### Option A: Horizontal container (recommended) [VERIFIED: codebase]
Replace `ObjectRow(Static)` with `ObjectRow(Horizontal)`, mounting three `Static` children. Each child gets fixed or expanding width via CSS:

```python
# ObjectRow extends Horizontal instead of Static
class ObjectRow(Horizontal, can_focus=False):
    DEFAULT_CSS = """
    ObjectRow {
        width: 1fr;
        height: auto;   /* auto to allow value wrapping */
        padding: 0 1;
    }
    ObjectRow .col-icon  { width: 3; }
    ObjectRow .col-value { width: 1fr; }
    ObjectRow .col-kind  { width: 12; text-align: right; }
    """
```

```python
def compose(self) -> ComposeResult:
    yield Static(icon, classes="col-icon")
    yield Static(value_text, classes="col-value")
    yield Static(kind_label, classes="col-kind")
```

**Height:** Use `height: auto` (not `height: 1`) to allow the value column to wrap to multiple lines when content is long.

**Highlight:** The `--highlight` CSS class applied by `ProjectDetail._update_highlight()` targets `ObjectRow` — this continues to work unchanged because the class goes on the container, not the children.

**refresh_indicator():** Must be updated — currently calls `self.update(...)` which only works on `Static`. With `Horizontal` children, update the value child: `self.query_one(".col-value", Static).update(...)`.

### Option B: rich.Text columns via fixed-width padding [ASSUMED]
Use Rich's `.pad()` or manual space padding. Fragile with variable-width Nerd Font icons (double-width glyphs). Not recommended.

**Recommendation:** Option A (Horizontal container).

---

## Finding 4: GroupHeader Whitespace (1 blank line before each header)

**Current:** `GroupHeader` is a `Static` with `height: 1`, `padding: 0 1`. No spacing before it.

**Two implementation options:**

### Option A: Spacer Static widget before each header (recommended)
In `_render_project()`, mount a `Static("", classes="section-spacer")` with `height: 1` before each `GroupHeader`. Simple, explicit, no CSS change to `GroupHeader` itself.

```python
scroll.mount(Static("", classes="section-spacer"))
scroll.mount(GroupHeader(GROUP_LABELS[kind]))
```

Add CSS: `.section-spacer { height: 1; }` to `ProjectDetail.DEFAULT_CSS`.

**Don't add spacer before the very first section** — that would add a top gap before the first group. Only add when `row_index > 0` or when the group is not the first one rendered.

### Option B: margin-top on GroupHeader
```css
GroupHeader { margin-top: 1; }
```
This affects all `GroupHeader` instances including the first one, adding unwanted top padding. Not recommended unless scoped.

**Same change needed in WorktreePane and TerminalPane** — both also use `GroupHeader` classes (duplicated per the existing "no cross-widget coupling" convention). Each file has its own `GroupHeader` class; the spacer approach must be replicated in each pane's render loop.

---

## Finding 5: Legend Popup — ModalScreen Pattern

**Verified pattern:** `ConfirmationModal` and `SettingsModal` both use `ModalScreen[T]` from `textual.screen`. This is the established project pattern.

```python
# Established pattern (confirmation.py):
class ConfirmationModal(ModalScreen[bool]):
    BINDINGS = [("escape", "cancel", "Cancel")]
    DEFAULT_CSS = """
    ConfirmationModal { align: center middle; }
    ConfirmationModal > Vertical {
        width: 60; height: auto;
        background: $surface; border: thick $background 80%; padding: 1 2;
    }
    """
    def action_cancel(self) -> None:
        self.dismiss(False)
```

**Legend modal:** Use `ModalScreen[None]`, dismiss on Escape. For dismissing on `l` again: add `("l", "dismiss_legend", "Legend")` binding. [VERIFIED: pattern from existing screens]

**Wiring:** The `l` binding goes on the **app** level (`JoyApp.BINDINGS`) so it works from any pane. The binding calls `action_legend()` which calls `push_screen(LegendModal())`. When the modal is active, pressing `l` again hits the modal's own binding — use `priority=True` or rely on the modal taking focus.

**Alternative:** Add binding to `ProjectDetail` only. But `l` on the ProjectList or WorktreePane would then do nothing. App-level is cleaner for a global help popup.

---

## Finding 6: Complete Icon Catalog

All icons across all panes — for the legend content.

### Details Pane / ObjectRow (src/joy/widgets/object_row.py)

| Icon | Codepoint | Nerd Font Name | Meaning |
|------|-----------|----------------|---------|
| `\ue725` | U+E725 | nf-dev-git_merge | MR (Merge Request) |
| `\ue0a0` | U+E0A0 | nf-pl-branch | Branch |
| `\uf0ea` | U+F0EA | nf-fa-clipboard | Ticket |
| `\uf086` | U+F086 | nf-fa-comment | Thread |
| `\uf15b` | U+F15B | nf-fa-file | File |
| `\uf040` | U+F040 | nf-fa-pencil | Note |
| `\uf07b` | U+F07B | nf-fa-folder | Worktree |
| `\uf120` | U+F120 | nf-fa-terminal | Agents |
| `\uf0ac` | U+F0AC | nf-fa-globe | URL |
| `\u25cf` | U+25CF | BLACK CIRCLE | Open by default (filled) |
| `\u25cb` | U+25CB | WHITE CIRCLE | Not default (open) |

### WorktreePane (src/joy/widgets/worktree_pane.py)

| Icon | Codepoint | Nerd Font Name | Meaning | Color |
|------|-----------|----------------|---------|-------|
| `\ue0a0` | U+E0A0 | nf-pl-branch | Branch name | bold |
| `\uf111` | U+F111 | nf-fa-circle | Dirty (uncommitted changes) | yellow |
| `\U000f0be1` | U+F0BE1 | nf-md-cloud_off | No upstream remote | dim |
| `\uea64` | U+EA64 | nf-cod-git_pull_request | MR open | green |
| `\uebdb` | U+EBDB | nf-cod-git_pull_request_draft | MR draft | dim |
| `\uf00c` | U+F00C | nf-fa-check | CI pass | green |
| `\uf00d` | U+F00D | nf-fa-times | CI fail | red |
| `\uf192` | U+F192 | nf-fa-dot_circle_o | CI pending | yellow |

### TerminalPane (src/joy/widgets/terminal_pane.py)

| Icon | Codepoint | Nerd Font Name | Meaning | Color |
|------|-----------|----------------|---------|-------|
| `\uf120` | U+F120 | nf-fa-terminal | Terminal session | bold |
| `\U000f1325` | U+F1325 | nf-md-robot | Claude agent session | bold |
| `\u25cf` | U+25CF | BLACK CIRCLE | Claude busy (running) | green |
| `\u25cb` | U+25CB | WHITE CIRCLE | Claude waiting (at prompt) | dim |

**Shared icon:** U+F120 (terminal) appears in both ObjectRow (Agents kind) and TerminalPane (regular sessions) — legend should clarify context.

---

## Architecture Patterns

### How to add the repo field to Details overview

Mount a top "overview" section before object rows in `_render_project()`. Use a `Static` or a dedicated `OverviewRow` widget. The repo field renders as a row with no kind/object icon — use a neutral icon or leave icon column blank.

```python
# In _render_project(), before the GROUP_ORDER loop:
if self._project.repo:
    # Mount repo overview row at top of details
    scroll.mount(OverviewRow(icon="\uf401", label=self._project.repo, kind="repo"))
    # \uf401 = nf-md-source_repository or use \uf07c (open folder)
```

Alternatively, display repo in the `border_title`: `Details — {project.name} [{project.repo}]`. Simpler but less visible.

**Recommendation:** An `OverviewRow` at the top (not in `_rows` / not cursor-navigable) is cleanest — consistent with the new 3-column design and makes repo clearly visible without cluttering the border title.

### Modal dismissal with `l` again

```python
class LegendModal(ModalScreen[None]):
    BINDINGS = [
        ("escape", "dismiss_modal", "Close"),
        ("l", "dismiss_modal", "Close"),
    ]
    def action_dismiss_modal(self) -> None:
        self.dismiss(None)
```

The app-level `l` binding must not fire when the modal is on top. Since `ModalScreen` takes over the focus stack, the app's `l` binding won't fire while the modal is active — the modal's own `l` binding handles it. No `priority=True` needed. [VERIFIED: how Textual screen stack works — modal screens intercept all input]

---

## Common Pitfalls

### Pitfall 1: ObjectRow height with wrapping value
When switching `ObjectRow` from `height: 1` (fixed) to `height: auto`, the `_update_highlight()` scroll behavior changes. `scroll_visible()` on the row still works, but if the row is taller than 1 line, cursor navigation "feel" changes slightly. Acceptable.

### Pitfall 2: Spacer before first section
Adding a spacer before every `GroupHeader` adds unwanted whitespace at the very top of the pane. Add spacer only when it's not the first group (track with a boolean or check `row_index > 0`).

### Pitfall 3: Horizontal container focus
`Horizontal` containers are not focusable by default — good. But ensure `can_focus=False` is explicit on `ObjectRow` since it changes base class from `Static` to `Horizontal`. The existing `can_focus = False` class attribute on `ObjectRow` should be preserved.

### Pitfall 4: `refresh_indicator()` after redesign
`ObjectRow.refresh_indicator()` currently calls `self.update(...)` — this is a `Static` method. After switching to `Horizontal`, this call will fail. Must query the child `.col-icon` or `.col-value` instead. Or the dot indicator is dropped entirely (per user decision to show only icon/value/kind).

### Pitfall 5: `l` binding conflicts
Check that no existing widget has an `l` binding. Current bindings use: q, O/shift+o, n, s, r (app level); j, k, up, down, o, space, a, e, d, escape (ProjectDetail); j, k, up, down, enter, escape (WorktreePane/TerminalPane). `l` is free everywhere. [VERIFIED: grep of all BINDINGS in codebase]

### Pitfall 6: GroupHeader duplication across files
The spacer-before-header pattern must be applied in **three** files separately: `project_detail.py`, `worktree_pane.py`, `terminal_pane.py`. Each has its own `GroupHeader` class and its own render loop.

---

## Implementation Checklist (for planner)

1. **Repo field in Details** — mount `OverviewRow` (new non-navigable widget) at top of `_render_project()` showing `project.repo` when set.

2. **ObjectRow redesign** — change base class `Static` → `Horizontal`, three `Static` children with CSS column widths. Update `refresh_indicator()`. Update `ProjectDetail.DEFAULT_CSS` to target new structure.

3. **Whitespace before headers** — add `Static("", classes="section-spacer")` before `GroupHeader` in `_render_project()` (skip first), `set_worktrees()` (WorktreePane), `set_sessions()` (TerminalPane).

4. **Legend modal** — new `src/joy/screens/legend.py` with `LegendModal(ModalScreen[None])`. Register `l` binding in `JoyApp.BINDINGS`. Add `LegendModal` to `src/joy/screens/__init__.py`.

---

## Sources

- `src/joy/widgets/object_row.py` — PRESET_ICONS catalog, ObjectRow rendering [VERIFIED: direct read]
- `src/joy/widgets/project_detail.py` — _render_project(), GroupHeader, ObjectRow usage [VERIFIED: direct read]
- `src/joy/widgets/worktree_pane.py` — WorktreePane icon constants, GroupHeader, render loop [VERIFIED: direct read]
- `src/joy/widgets/terminal_pane.py` — TerminalPane icon constants, GroupHeader, render loop [VERIFIED: direct read]
- `src/joy/screens/confirmation.py` — ModalScreen[bool] pattern [VERIFIED: direct read]
- `src/joy/screens/settings.py` — ModalScreen[Config|None] pattern, push_screen usage [VERIFIED: direct read]
- `src/joy/models.py` — Project.repo field [VERIFIED: direct read]
- `src/joy/app.py` — JoyApp.BINDINGS, Grid container usage [VERIFIED: direct read]

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (stable codebase — no third-party API surface to expire)
