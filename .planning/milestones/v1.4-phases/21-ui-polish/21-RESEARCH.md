# Phase 21: UI Polish - Research

**Researched:** 2026-05-08
**Domain:** Textual CSS visual consistency, focus indicators, spacing/alignment audit
**Confidence:** HIGH

## Summary

This phase is an audit-and-fix phase. The codebase has five focusable panes (ProjectList, ProjectDetail, WorktreePane, TerminalPane, MRPane) plus a non-focusable PlaceholderPane, arranged in a 3x2 grid. After reading all widget source files, the app.py layout composition, and the inline Textual CSS across the codebase, I identified **9 concrete visual inconsistencies** ranging from missing focus pseudo-class selectors to unscoped CSS rules that could cause style leakage.

The widget implementations are well-structured and follow consistent patterns for cursor navigation, highlight classes, and scroll containers. The inconsistencies are subtle but real -- primarily: (1) split ownership of border/focus CSS between app.py and individual widgets, (2) missing `:focus` pseudo-class variants for highlight rows in 3 of 5 panes, and (3) unscoped `.section-spacer` CSS rules in 2 of 5 panes.

**Primary recommendation:** Fix all 9 identified CSS inconsistencies, then update snapshot baselines to capture the corrected visual state.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UIPOL-01 | Systematic audit of all panes for visual inconsistencies (spacing, alignment, truncation, focus indicators) | Audit completed via code analysis -- 9 issues documented in "Visual Inconsistency Audit" section below with exact file locations and CSS selectors |
| UIPOL-02 | Identified UI bugs fixed across ProjectList, ProjectDetail, WorktreePane, TerminalPane, MRPane | Each of the 9 issues has a specific fix prescription with code examples; snapshot baselines should be updated after fixes |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Focus indicator styling | Browser/Client (TUI CSS) | -- | All focus states are Textual CSS pseudo-classes |
| Border/highlight consistency | Browser/Client (TUI CSS) | -- | Pure CSS rule fixes, no backend changes |
| Spacing/alignment | Browser/Client (TUI CSS) | -- | Padding, height, and layout rules are CSS-only |
| Snapshot baselines | Test infrastructure | -- | SVG snapshot files updated to reflect corrected CSS |
| Section-spacer scoping | Browser/Client (TUI CSS) | -- | CSS specificity fix to prevent style leakage |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| textual | ^8.2 | TUI framework | Only CSS-based Python TUI framework; already in use [VERIFIED: existing codebase] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-textual-snapshot | existing | SVG snapshot baselines | Update baselines after CSS fixes [VERIFIED: tests/test_snapshots.py exists] |
| pytest | existing | Test runner | Run audit verification tests [VERIFIED: 488 tests collected] |

No new libraries needed for this phase.

## Architecture Patterns

### System Architecture Diagram

```
[Tab/Focus event] --> [Textual focus chain]
    |
    v
[Widget :focus / :focus-within pseudo-class] --> [CSS rule matching]
    |
    v
[Border color change] + [Row highlight background change]
    |
    v
[Terminal render cycle (~12ms)]
```

Data flow for focus indicators:
1. User presses Tab or clicks a pane
2. Textual's focus chain updates the focused widget
3. CSS pseudo-classes `:focus` and `:focus-within` activate
4. Border changes from `$surface-lighten-2` to `$accent`
5. Highlighted row background changes from `$accent 30%` to `$accent` (full)

### Recommended Project Structure

No structural changes needed. All fixes are CSS-only within existing files:
```
src/joy/
  app.py                  # Grid CSS, border rules for ProjectList/ProjectDetail
  widgets/
    project_list.py       # ProjectList DEFAULT_CSS (highlight rules)
    project_detail.py     # ProjectDetail DEFAULT_CSS (highlight rules, spacer scope)
    worktree_pane.py      # WorktreePane DEFAULT_CSS (border + highlight)
    terminal_pane.py      # TerminalPane DEFAULT_CSS (border + highlight)
    mr_pane.py            # MRPane DEFAULT_CSS (border + highlight, spacer scope)
    placeholder_pane.py   # PlaceholderPane DEFAULT_CSS (border only)
    hint_bar.py           # HintBar DEFAULT_CSS (dock: bottom)
tests/
  __snapshots__/test_snapshots/  # SVG baselines to update
```

### Pattern: Focus Indicator Consistency

**What:** Every focusable pane must follow the same border + highlight pattern.
**When to use:** All 5 focusable panes.
**Standard pattern:**
```css
/* Unfocused border */
PaneName {
    border: solid $surface-lighten-2;
}

/* Focused border (both :focus and :focus-within for nested scroll containers) */
PaneName:focus {
    border: solid $accent;
}
PaneName:focus-within {
    border: solid $accent;
}

/* Highlighted row: dim when pane unfocused, full accent when focused */
RowWidget.--highlight {
    background: $accent 30%;
}
PaneName:focus RowWidget.--highlight {
    background: $accent;
}
PaneName:focus-within RowWidget.--highlight {
    background: $accent;
}
```
[VERIFIED: This pattern is already implemented correctly in WorktreePane and TerminalPane; other panes deviate]

### Anti-Patterns to Avoid
- **Split CSS ownership:** Border/focus rules for one widget defined in a different file (e.g., ProjectList borders in app.py instead of ProjectList DEFAULT_CSS). This makes it hard to audit and maintain.
- **Unscoped class selectors:** `.section-spacer { height: 1; }` without a parent scope can leak into other widgets that mount children with the same class.
- **Missing `:focus` variant:** Only having `:focus-within` means the pane itself doesn't get the accent border when it holds focus directly (before any child is focused).

## Visual Inconsistency Audit

### Issue 1: ProjectList and ProjectDetail border/focus CSS defined in app.py instead of widget
**Severity:** Consistency (not a visual bug per se, but prevents self-contained widgets)
**Location:** `app.py` lines 51-65 (JoyApp.CSS)
**Problem:** ProjectList and ProjectDetail border and `:focus-within` rules are in `JoyApp.CSS`, while WorktreePane, TerminalPane, and MRPane define their own border/focus rules in `DEFAULT_CSS`. This split ownership means:
- ProjectList and ProjectDetail lack `:focus` pseudo-class rules (only `:focus-within`)
- Adding a new instance of these widgets elsewhere would lose styling
**Fix:** Move border + focus rules from `JoyApp.CSS` into each widget's `DEFAULT_CSS`. Add both `:focus` and `:focus-within` variants. [VERIFIED: WorktreePane/TerminalPane/MRPane already follow this self-contained pattern]

### Issue 2: ProjectDetail missing `:focus` highlight variant
**Severity:** Visual bug (highlight row may show dim when pane itself has focus)
**Location:** `project_detail.py` lines 68-87 (DEFAULT_CSS)
**Problem:** `ProjectDetail:focus-within ObjectRow.--highlight` exists but `ProjectDetail:focus ObjectRow.--highlight` does not. Since ProjectDetail is `can_focus=True`, when focus is directly on ProjectDetail (not a child), the highlight row shows at 30% opacity instead of full accent.
**Fix:** Add `ProjectDetail:focus ObjectRow.--highlight { background: $accent; }` [VERIFIED: ProjectList has both `:focus` and `:focus-within` variants]

### Issue 3: WorktreePane missing `:focus` row highlight variant
**Severity:** Visual inconsistency
**Location:** `worktree_pane.py` lines 247-278 (DEFAULT_CSS)
**Problem:** Has `WorktreePane:focus-within WorktreeRow.--highlight` but no `WorktreePane:focus WorktreeRow.--highlight`. The pane border correctly changes on `:focus`, but the row highlight stays at 30%.
**Fix:** Add `WorktreePane:focus WorktreeRow.--highlight { background: $accent; }` [VERIFIED: ProjectList has both variants as reference]

### Issue 4: TerminalPane missing `:focus` row highlight variant
**Severity:** Visual inconsistency
**Location:** `terminal_pane.py` lines 193-220 (DEFAULT_CSS)
**Problem:** Same as Issue 3 but for TerminalPane/SessionRow.
**Fix:** Add `TerminalPane:focus SessionRow.--highlight { background: $accent; }` [VERIFIED: same pattern]

### Issue 5: MRPane missing `:focus` row highlight variant
**Severity:** Visual inconsistency
**Location:** `mr_pane.py` lines 176-203 (DEFAULT_CSS)
**Problem:** Same as Issues 3-4 but for MRPane/MRRow.
**Fix:** Add `MRPane:focus MRRow.--highlight { background: $accent; }` [VERIFIED: same pattern]

### Issue 6: Unscoped `.section-spacer` in ProjectDetail CSS
**Severity:** Style leakage risk
**Location:** `project_detail.py` line 85
**Problem:** `.section-spacer { height: 1; }` is not scoped to `ProjectDetail .section-spacer`. In a Textual DOM, this rule could match section-spacers in other widgets if specificity allows. WorktreePane, TerminalPane, and ProjectList all properly scope theirs.
**Fix:** Change to `ProjectDetail .section-spacer { height: 1; }` [VERIFIED: WorktreePane uses `WorktreePane .section-spacer` as correct pattern]

### Issue 7: Unscoped `.section-spacer` in MRPane CSS
**Severity:** Style leakage risk
**Location:** `mr_pane.py` line 200-202
**Problem:** Same as Issue 6 but for MRPane.
**Fix:** Change to `MRPane .section-spacer { height: 1; }` [VERIFIED: same scoping pattern needed]

### Issue 8: ProjectList lacks border in DEFAULT_CSS
**Severity:** Architecture consistency
**Location:** `project_list.py` lines 370-383 (DEFAULT_CSS)
**Problem:** ProjectList DEFAULT_CSS has no `border` rule. It relies entirely on `app.py` CSS for its border. If the app.py CSS is removed (per Issue 1 fix), the border disappears.
**Fix:** When moving CSS from app.py to widget (Issue 1), ensure ProjectList DEFAULT_CSS includes: `ProjectList { border: solid $surface-lighten-2; }` + focus variants.

### Issue 9: ProjectDetail lacks border in DEFAULT_CSS
**Severity:** Architecture consistency
**Location:** `project_detail.py` lines 68-87 (DEFAULT_CSS)
**Problem:** Same as Issue 8 but for ProjectDetail. The DEFAULT_CSS has `width: 1fr; height: 1fr; overflow-y: auto;` but no `border` rule.
**Fix:** Same approach as Issue 8.

### Summary Table

| # | Widget | Issue | Type | Severity |
|---|--------|-------|------|----------|
| 1 | ProjectList + ProjectDetail | Border/focus CSS in app.py not widget | Consistency | Medium |
| 2 | ProjectDetail | Missing `:focus` highlight variant | Visual bug | High |
| 3 | WorktreePane | Missing `:focus` row highlight variant | Inconsistency | Medium |
| 4 | TerminalPane | Missing `:focus` row highlight variant | Inconsistency | Medium |
| 5 | MRPane | Missing `:focus` row highlight variant | Inconsistency | Medium |
| 6 | ProjectDetail | Unscoped `.section-spacer` | Style leakage | Low |
| 7 | MRPane | Unscoped `.section-spacer` | Style leakage | Low |
| 8 | ProjectList | No border in DEFAULT_CSS | Architecture | Medium |
| 9 | ProjectDetail | No border in DEFAULT_CSS | Architecture | Medium |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Focus state management | Custom focus tracking | Textual `:focus` / `:focus-within` pseudo-classes | Built-in CSS pseudo-classes handle focus state automatically [VERIFIED: Textual docs] |
| Highlight dimming on blur | Manual opacity toggling | CSS specificity with/without `:focus` parent selector | Textual CSS already supports this; just need correct selectors |
| Snapshot regression | Manual visual comparison | pytest-textual-snapshot | Already in use; SVG baselines catch regressions automatically |

## Common Pitfalls

### Pitfall 1: CSS Specificity with DEFAULT_CSS vs App CSS
**What goes wrong:** Rules in `JoyApp.CSS` (app-level) and widget `DEFAULT_CSS` (widget-level) compete on specificity. If both define `#project-list { border: ... }`, the app-level rule may override the widget's intended style depending on declaration order.
**Why it happens:** Textual merges CSS from multiple sources. App CSS is typically higher specificity than DEFAULT_CSS when using ID selectors.
**How to avoid:** After moving border rules from app.py to widget DEFAULT_CSS, remove the duplicate rules from app.py CSS entirely. Do not leave orphaned selectors.
**Warning signs:** Border not changing color on focus, or border always showing accent color.

### Pitfall 2: `:focus` vs `:focus-within` Behavior Difference
**What goes wrong:** Developers assume `:focus-within` covers the `:focus` case. It does NOT. `:focus-within` fires when a DESCENDANT has focus. `:focus` fires when the widget ITSELF has focus. For `can_focus=True` widgets with no focusable children, only `:focus` triggers.
**Why it happens:** Most panes have non-focusable scroll containers (`can_focus=False`), so `:focus-within` may not fire at all when the pane itself holds focus.
**How to avoid:** Always define both `:focus` and `:focus-within` for any `can_focus=True` widget that contains children.
**Warning signs:** Border flashes on focus then reverts; highlight row stays dim.

### Pitfall 3: Snapshot Baseline Update After CSS Changes
**What goes wrong:** CSS fixes change the visual appearance, causing existing snapshot tests to fail. Developer forgets to update baselines, or updates them incorrectly.
**Why it happens:** `pytest-textual-snapshot` compares against stored SVG files. Any pixel-level change fails the test.
**How to avoid:** After all CSS fixes, run `uv run pytest tests/test_snapshots.py --update-snapshot` to regenerate baselines. Review the diff to ensure changes match expectations.
**Warning signs:** All snapshot tests fail after CSS changes.

### Pitfall 4: Removing App CSS Without Adding Widget CSS First
**What goes wrong:** If app.py CSS rules are deleted before equivalent rules are added to widget DEFAULT_CSS, the intermediate commit has no border styling at all.
**Why it happens:** Two-step migration (delete old, add new) with a commit between.
**How to avoid:** Add the new rules to widget DEFAULT_CSS FIRST, then remove the old rules from app.py CSS in the same commit.
**Warning signs:** Borders disappear entirely during development.

## Code Examples

### Fix Pattern: Moving Border CSS from app.py to Widget

Before (app.py):
```python
# In JoyApp.CSS:
CSS = """
    #project-list {
        height: 1fr;
        border: solid $surface-lighten-2;
    }
    #project-list:focus-within {
        border: solid $accent;
    }
"""
```

After (project_list.py DEFAULT_CSS):
```python
# Source: existing pattern from worktree_pane.py [VERIFIED: codebase]
DEFAULT_CSS = """
    ProjectList {
        height: 1fr;
        border: solid $surface-lighten-2;
    }
    ProjectList:focus {
        border: solid $accent;
    }
    ProjectList:focus-within {
        border: solid $accent;
    }
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
```

### Fix Pattern: Scoping Section Spacer

Before:
```css
.section-spacer {
    height: 1;
}
```

After:
```css
ProjectDetail .section-spacer {
    height: 1;
}
```

### Fix Pattern: Adding `:focus` Row Highlight

Before:
```css
WorktreePane:focus-within WorktreeRow.--highlight {
    background: $accent;
}
WorktreeRow.--highlight {
    background: $accent 30%;
}
```

After (add the `:focus` variant):
```css
WorktreePane:focus WorktreeRow.--highlight {
    background: $accent;
}
WorktreePane:focus-within WorktreeRow.--highlight {
    background: $accent;
}
WorktreeRow.--highlight {
    background: $accent 30%;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Border CSS in app.py | Self-contained widget DEFAULT_CSS | Best practice since Textual 0.30+ | Widgets are reusable and auditable |
| `:focus-within` only | Both `:focus` and `:focus-within` | Always recommended | Handles direct focus on `can_focus=True` widgets |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Textual resolves DEFAULT_CSS with lower specificity than app-level CSS when both use ID selectors | Pitfall 1 | CSS migration may need specificity adjustments (use type selectors instead of IDs in DEFAULT_CSS) |

**Most claims verified:** All issues identified through direct code reading of the existing codebase. CSS patterns verified against Textual documentation via Context7.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-textual-snapshot + pytest-asyncio |
| Config file | pyproject.toml (pytest section) |
| Quick run command | `uv run pytest tests/test_pane_layout.py tests/test_snapshots.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UIPOL-01 | Audit checklist documented | Documentation | N/A (audit in RESEARCH.md) | Yes (this file) |
| UIPOL-02-a | Focus borders consistent across 5 panes | Integration (TUI) | `uv run pytest tests/test_pane_layout.py -x -q` | Yes |
| UIPOL-02-b | Highlight rows show full accent when pane focused | Snapshot | `uv run pytest tests/test_snapshots.py --update-snapshot` then `uv run pytest tests/test_snapshots.py -x -q` | Yes |
| UIPOL-02-c | Section-spacer CSS scoped per widget | Unit (CSS check) | Manual code review | N/A |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_pane_layout.py tests/test_snapshots.py -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before /gsd-verify-work

### Wave 0 Gaps
- None -- existing test infrastructure covers all phase requirements. Snapshot baselines need updating after fixes, not before.

## Open Questions

1. **CSS Specificity after migration**
   - What we know: Textual DEFAULT_CSS uses widget type selectors (e.g., `ProjectList { ... }`), app CSS uses ID selectors (e.g., `#project-list { ... }`). ID selectors have higher specificity.
   - What's unclear: After moving rules from app.py to DEFAULT_CSS, whether the type-selector rules in DEFAULT_CSS will take effect or be overridden by any remaining app-level CSS.
   - Recommendation: Remove ALL `#project-list` and `#project-detail` rules from `JoyApp.CSS` when adding equivalent rules to widget DEFAULT_CSS. Test with `uv run pytest tests/test_pane_layout.py -x` to verify focus cycling still works.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: All widget files in `src/joy/widgets/` read in full
- Codebase analysis: `app.py` JoyApp.CSS block read in full
- Context7 `/websites/textual_textualize_io` -- topics: "CSS focus styles border pseudo-classes focus-within", "border styles border-title padding spacing alignment"

### Secondary (MEDIUM confidence)
- Textual official site: https://textual.textualize.io/guide/CSS/ (CSS pseudo-class documentation)
- Textual official site: https://textual.textualize.io/guide/input/ (focus styling examples)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, using existing Textual CSS
- Architecture: HIGH -- all findings verified by reading actual source code
- Pitfalls: HIGH -- derived from concrete code analysis, not hypothetical

**Research date:** 2026-05-08
**Valid until:** 2026-06-08 (stable -- CSS patterns don't change rapidly)
