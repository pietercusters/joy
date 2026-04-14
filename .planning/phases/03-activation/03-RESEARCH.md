# Phase 3: Activation - Research

**Researched:** 2026-04-11
**Domain:** Textual TUI key bindings, background workers, toast notifications, in-place widget updates
**Confidence:** HIGH

## Summary

Phase 3 wires `o`/`O`/`space` into the existing Textual TUI shell to deliver the core value of instant artifact access. The work is almost entirely integration and plumbing — the operations layer (`operations.py`) is complete, the `highlighted_object` property is in place, and `save_projects()` is established. No new widgets are needed.

The main technical concerns are: (1) keeping the TUI unblocked while subprocess openers run (solved by `@work(thread=True)`), (2) updating an `ObjectRow` dot indicator in-place after `space` (solved by `Static.update()`), and (3) giving `JoyApp.action_open_all_defaults()` reliable access to the currently displayed project (accessible via `ProjectDetail._project`). Config is loaded in `_load_data` but not yet cached on `self._config` — that needs to happen in `_set_projects` or on mount.

All decisions are locked in `03-CONTEXT.md`. No architectural choices remain open. Research confirms every implementation path the planner needs.

**Primary recommendation:** Implement as three focused tasks — (1) config caching + `O` global binding, (2) `o` single-open binding + toast plumbing, (3) `space` toggle + dot indicator. All three tasks share the `@work(thread=True)` + `app.notify()` pattern.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Open-by-default Indicator (ACT-04)**
- D-01: Each `ObjectRow` displays a filled/empty dot (`●`/`○`) to the left of the icon. Row format becomes: `● {icon}  {label}  {value}` (filled = in default set, empty = not). Updates immediately when `space` is pressed.
- D-02: Dot uses muted color when empty, accent color (or white) when filled — subtle contrast without a dedicated column.

**Status Bar Feedback (CORE-05)**
- D-03: Use Textual's `app.notify()` toast for all activation feedback.
- D-04: Message format includes the object value (short with value): `"Copied: feature/auth-refactor"`, `"Opened: notion.so/..."`, `"Opened in iTerm2: joy-agents"`. Trim long values with `…` if over 40 chars.
- D-05: Errors also use `app.notify()` with `severity="error"`.

**Bulk Open — O (ACT-02)**
- D-06: `O` opens default objects sequentially in display order (matching `GROUP_ORDER`). Single background thread loop, not concurrent.
- D-07: On failure, continue — skip failed object, proceed with remaining, show one error toast per failure at the end.
- D-08: One toast per object opened, same format as single `o`.

**Key Binding Scope**
- D-09: `o` and `space` bound on `ProjectDetail` (detail pane only — fires only when detail has focus).
- D-10: `O` bound globally on `JoyApp` — fires from any pane, reads highlighted project directly.
- D-11: If `o` pressed with no highlighted object, show error toast "No object selected". Silent no-op for `O` when no default objects exist.

**Persistence — space toggle (ACT-03)**
- D-12: Toggle writes immediately via `store.save_projects()` in `@work(thread=True)`. No batch-on-exit.

### Claude's Discretion
- Exact dot character encoding and Rich color for filled/empty state
- Whether `O` from the project list requires Enter first or reads the highlighted project directly
- Delay (if any) between sequential opens in `O` — start with 0ms, adjust if needed
- BINDINGS placement for `O` on `JoyApp` vs a priority binding

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within Phase 3 scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ACT-01 | Pressing `o` on a selected object performs its type-specific operation | `operations.open_object()` already implements all 6 types. Wire via `@work(thread=True)` binding on `ProjectDetail`. |
| ACT-02 | Pressing `O` activates all objects marked as "open by default", in display order | `GROUP_ORDER` already defines display order. `@work(thread=True)` sequential loop in `JoyApp.action_open_all_defaults()`. |
| ACT-03 | Pressing `space` toggles an object's "open by default" status, persists across restarts | Flip `item.open_by_default`, call `store.save_projects()` in `@work(thread=True)`. `ObjectItem.open_by_default` already serialized in `to_dict()` and read back in `_toml_to_projects()`. |
| ACT-04 | Each object displays a visual indicator (filled/empty) showing "open by default" status | `ObjectRow._render_text()` needs to prepend dot glyph. `Static.update()` for in-place refresh. Rich `Text.append()` with per-span style for colored dot. |
| CORE-05 | Status bar shows immediate feedback after every action | `app.notify()` is thread-safe — can be called from within `@work(thread=True)` workers without `call_from_thread`. Confirmed via Textual source (has "thread-safe" docstring). |
</phase_requirements>

---

## Standard Stack

### Core (all already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| textual | 8.2.3 (installed) | TUI framework, key bindings, `@work`, `notify()` | Project requirement, locked in CLAUDE.md |
| rich | >=14.2 (textual dep) | `rich.text.Text` per-span styling for dot indicator | Textual dependency, already used in `ObjectRow` |
| tomli_w | ^1.0 | TOML write for `save_projects()` | Already used in `store.py` |

No new dependencies required for Phase 3. [VERIFIED: uv run python -c "import textual; print(textual.__version__)" → 8.2.3]

### Supporting (stdlib)
| Library | Version | Purpose |
|---------|---------|---------|
| subprocess | stdlib | Used inside `operations.py` openers — already implemented |

---

## Architecture Patterns

### Pattern 1: Background Thread Worker (`@work(thread=True)`)

**What:** Decorated method runs in a thread pool, keeping the TUI event loop unblocked.
**When to use:** Any call that does I/O (subprocess, TOML write).
**Key property:** `exit_on_error=True` by default — an unhandled exception crashes the app. Use `exit_on_error=False` for activations where errors should show as toasts, not crash.

```python
# Source: verified via uv run python -c "from textual import work; help(work)"
# Phase 2 established pattern — see app.py _load_data()
@work(thread=True, exit_on_error=False)
def _do_open(self, item: ObjectItem) -> None:
    try:
        open_object(item=item, config=self.app._config)
        self.app.notify(_success_message(item))
    except Exception as exc:
        self.app.notify(f"Failed to open: {_truncate(item.value)}", severity="error")
```

[VERIFIED: app.py line 38 — `@work(thread=True)` already used in `_load_data`]

### Pattern 2: Thread-Safe Notify

**What:** `app.notify()` is explicitly documented as thread-safe in Textual 8.x.
**When to use:** Calling from inside `@work(thread=True)` workers — no `call_from_thread` wrapper needed.

```python
# Source: verified via uv run python -c "from textual.app import App; help(App.notify)"
# Docstring states: "This method is thread-safe."
self.app.notify("Copied: feature/auth-refactor")
self.app.notify("Failed to open: notion.so/...", severity="error")
```

[VERIFIED: Textual 8.2.3 `App.notify` docstring — "This method is thread-safe."]

### Pattern 3: In-Place `ObjectRow` Update via `Static.update()`

**What:** `Static.update(content)` replaces the widget's renderable without remounting.
**When to use:** `space` toggle — flip the dot character and color without destroying/recreating the row.

```python
# Source: verified via uv run python -c "from textual.widgets import Static; help(Static.update)"
# ObjectRow._render_text is a @staticmethod — call it and pass new Text to update()
def refresh_indicator(self) -> None:
    """Rebuild and update the row's rendered text in-place (called after toggle)."""
    self.update(self._render_text(self.item))
```

[VERIFIED: `Static.update()` signature confirmed. `layout=True` is default — fine for single-cell change.]

### Pattern 4: Rich Text Per-Span Styling for Dot Indicator

**What:** `rich.text.Text.append(text, style=style)` adds a styled span. Multiple appends compose naturally.
**When to use:** Dot needs independent color from the rest of the row.

```python
# Source: verified via uv run python -c "t = Text(); t.append('●', style='white'); ..."
# Confirmed: <text '● rest' [Span(0, 1, 'white'), Span(2, 6, 'dim')] ''>
@staticmethod
def _render_text(item: ObjectItem) -> Text:
    dot = "●" if item.open_by_default else "○"
    dot_style = "$text" if item.open_by_default else "$text-muted"  # Textual CSS vars
    icon = PRESET_ICONS.get(item.kind, " ")
    label = item.kind.value
    value = item.label if item.label else item.value
    t = Text(no_wrap=True, overflow="ellipsis")
    t.append(dot, style=dot_style)
    t.append(f" {icon}  {label}  {value}")
    return t
```

[VERIFIED: Rich `Text.append()` with style confirmed working via live Python check]

### Pattern 5: `O` Global Binding — Reading Highlighted Project

**What:** `JoyApp.action_open_all_defaults()` needs the currently displayed project. `ProjectDetail._project` holds it (set every time `set_project()` is called).
**When to use:** Global binding that fires from any pane.

```python
# Source: project_detail.py — _project attribute set in __init__ and set_project()
def action_open_all_defaults(self) -> None:
    detail = self.query_one(ProjectDetail)
    project = detail._project
    if project is None:
        return
    defaults = [
        item for kind in GROUP_ORDER
        for item in project.objects
        if item.kind == kind and item.open_by_default
    ]
    if not defaults:
        return  # silent no-op per D-11
    self._open_defaults(defaults)
```

[VERIFIED: `project_detail.py` line 87 — `self._project: Project | None = None`, set in `set_project()` line 94]

### Pattern 6: Config Caching on JoyApp

**What:** `open_object()` requires a `Config` instance. `load_config()` is called in `_load_data` but currently the result is not stored on `self`. Need to cache it as `self._config`.
**Gap identified:** Current `app.py` does not store `_config`. Must be added in the same `_set_projects` callback or in a separate `load_config()` call in `_load_data`.

```python
# Current _load_data (app.py line 39-44) only loads projects.
# Fix: also load config and cache it.
@work(thread=True)
def _load_data(self) -> None:
    from joy.store import load_projects, load_config  # noqa: PLC0415
    projects = load_projects()
    config = load_config()
    self.app.call_from_thread(self._set_projects, projects, config)

def _set_projects(self, projects: list[Project], config: Config) -> None:
    self._projects = projects
    self._config = config
    ...
```

[VERIFIED: `app.py` lines 39–51 — no `_config` attribute currently stored. `store.load_config()` exists at `store.py` line 101.]

### Architecture: Binding Placement

| Binding | Widget | Scope | Justification |
|---------|--------|-------|---------------|
| `o` | `ProjectDetail.BINDINGS` | Detail pane only | Only meaningful when an object is highlighted |
| `space` | `ProjectDetail.BINDINGS` | Detail pane only | Toggles the highlighted object |
| `O` | `JoyApp.BINDINGS` | Global | Works from any pane; reads `ProjectDetail._project` directly |

[VERIFIED: Context D-09, D-10. Confirmed by existing BINDINGS pattern in `ProjectDetail` and `JoyApp`.]

### Anti-Patterns to Avoid

- **Calling `open_object()` on the main thread:** Subprocess calls block the event loop. Always wrap in `@work(thread=True)`.
- **Using `call_from_thread` for `notify()`:** Unnecessary — `app.notify()` is already thread-safe. Adds noise.
- **Remounting `ObjectRow` on toggle:** `Static.update()` is sufficient and avoids cursor position loss.
- **Concurrent threads for bulk `O`:** Decision D-06 mandates sequential opens in a single worker. Concurrent threads would race and produce unpredictable toast ordering.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Non-blocking subprocess | Custom threading | `@work(thread=True)` | Already established in Phase 2; handles worker lifecycle, error propagation |
| Toast feedback | Custom overlay widget | `app.notify()` | Built-in, thread-safe, auto-dismissing, severity levels included |
| Dot color styling | Custom rich markup strings | `Text.append(style=...)` | Per-span styles are the correct Rich API for mixed-style text; markup strings are fragile with user-provided values |
| Toggle persistence | Custom file watcher | `store.save_projects()` in worker | Atomic write pattern already established and tested |

---

## Common Pitfalls

### Pitfall 1: `exit_on_error=True` crashing the app on failed open

**What goes wrong:** Default `@work(thread=True)` has `exit_on_error=True`. A `subprocess.CalledProcessError` (e.g., app not found) tears down the entire TUI.
**Why it happens:** Textual's default is "crash on worker exception" to surface programming errors.
**How to avoid:** Add `exit_on_error=False` to all activation workers. Handle exceptions inside the worker with `try/except` and `app.notify(..., severity="error")`.
**Warning signs:** App disappears silently when `o` is pressed on a broken object.

[VERIFIED: `work()` signature — `exit_on_error: bool = True` is the default]

### Pitfall 2: Config not available when `action_open_object()` fires

**What goes wrong:** `self.app._config` is `None` (or raises `AttributeError`) if Config wasn't cached.
**Why it happens:** Current `app.py` does not store `_config` after `_load_data`. The attribute doesn't exist.
**How to avoid:** Add `_config: Config | None = None` to `JoyApp.__init__` or as a class attribute. Set it in `_set_projects` alongside `_projects`. Guard with a None check before calling `open_object()`.
**Warning signs:** `AttributeError: 'JoyApp' object has no attribute '_config'`.

[VERIFIED: `app.py` — no `_config` stored. `store.load_config()` confirmed at `store.py` line 101.]

### Pitfall 3: `space` losing cursor position when row is remounted

**What goes wrong:** If `ObjectRow` is removed and re-created, the cursor `_cursor` index still points to the correct position but focus and scroll may jump.
**Why it happens:** Full remount triggers layout recalculation and scroll reset.
**How to avoid:** Use `Static.update()` on the existing `ObjectRow` instance. The row stays in place, `_cursor` remains valid.
**Warning signs:** Detail pane scrolls to top after every `space` press.

[VERIFIED: `Static.update()` API confirmed. No remount required.]

### Pitfall 4: Toast message containing Rich markup from user data

**What goes wrong:** `app.notify()` has `markup=True` by default. If a project value contains `[...]` (e.g., a branch name like `[JIRA-123]-fix`), it gets interpreted as Rich markup and may render incorrectly or raise.
**Why it happens:** Textual passes the message string through Rich's markup parser.
**How to avoid:** Pass `markup=False` to `app.notify()` when message contains user-supplied data. Or escape the value portion. The message formats in the UI spec are simple concatenations with user values — use `markup=False`.
**Warning signs:** Toast shows garbled text or empty when value contains brackets.

[VERIFIED: `App.notify()` signature — `markup: bool = True` is the default. Confirmed via live help().]

### Pitfall 5: `O` accessing `_project` before data loads

**What goes wrong:** User presses `O` before the background `_load_data` worker completes. `ProjectDetail._project` is `None`.
**Why it happens:** App mounts before data is available (by design for fast startup).
**How to avoid:** `action_open_all_defaults()` must guard: `if project is None: return`. Already covered by D-11 silent no-op.
**Warning signs:** `AttributeError` or no-op when `O` is pressed immediately after launch.

[VERIFIED: `project_detail.py` line 87 — `_project` initialized to `None`.]

---

## Code Examples

### Complete ObjectRow `_render_text` with dot indicator
```python
# Source: UI-SPEC.md + Rich Text.append verified pattern
@staticmethod
def _render_text(item: ObjectItem) -> Text:
    """Build display text: dot  icon  label  value."""
    dot = "\u25cf" if item.open_by_default else "\u25cb"  # ● or ○
    dot_style = "white" if item.open_by_default else "dim"
    icon = PRESET_ICONS.get(item.kind, " ")
    label = item.kind.value
    value = item.label if item.label else item.value
    t = Text(no_wrap=True, overflow="ellipsis")
    t.append(dot, style=dot_style)
    t.append(f" {icon}  {label}  {value}")
    return t
```

### Toast message helper
```python
# Source: UI-SPEC.md Copywriting Contract
def _truncate(value: str, max_len: int = 40) -> str:
    return value[:37] + "..." if len(value) > max_len else value

def _success_message(item: ObjectItem, config: Config) -> str:
    display = _truncate(item.label if item.label else item.value)
    match item.object_type:
        case ObjectType.STRING:
            return f"Copied: {display}"
        case ObjectType.URL:
            url = item.value
            if "notion.so" in url:
                return f"Opened in Notion: {display}"
            elif "slack.com" in url:
                return f"Opened in Slack: {display}"
            else:
                return f"Opened: {display}"
        case ObjectType.OBSIDIAN:
            return f"Opened in Obsidian: {display}"
        case ObjectType.FILE:
            return f"Opened in {config.editor}: {display}"
        case ObjectType.WORKTREE:
            return f"Opened in {config.ide}: {display}"
        case ObjectType.ITERM:
            return f"Opened in iTerm2: {display}"
        case _:
            return f"Opened: {display}"
```

### Bulk open worker (sequential, continue-on-error)
```python
# Source: CONTEXT.md D-06, D-07, D-08
@work(thread=True, exit_on_error=False)
def _open_defaults(self, defaults: list[ObjectItem]) -> None:
    errors: list[str] = []
    for item in defaults:
        try:
            open_object(item=item, config=self._config)
            self.app.notify(_success_message(item, self._config), markup=False)
        except Exception:
            errors.append(_truncate(item.label if item.label else item.value))
    for err in errors:
        self.app.notify(f"Failed to open: {err}", severity="error", markup=False)
```

### space toggle action
```python
# Source: CONTEXT.md D-12, project_detail.py pattern
def action_toggle_default(self) -> None:
    item = self.highlighted_object
    if item is None:
        return
    item.open_by_default = not item.open_by_default
    # Update the row's dot in-place
    row = self._rows[self._cursor]
    row.refresh_indicator()
    # Persist in background
    self._save_toggle()

@work(thread=True, exit_on_error=False)
def _save_toggle(self) -> None:
    from joy.store import save_projects  # noqa: PLC0415
    save_projects(self.app._projects)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `call_from_thread(notify, ...)` | Direct `app.notify()` from thread | Textual 0.x → 8.x | Simpler worker code; no wrapper needed |
| `markup=True` (default) | `markup=False` for user data | Always recommended | Prevents bracket injection from user values |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ProjectDetail._project` is the correct way for `JoyApp.action_open_all_defaults()` to read the current project | Architecture Patterns (Pattern 5) | If `_project` is `None` due to timing, `O` silently no-ops — acceptable fallback |
| A2 | Using Textual CSS variable names (`"white"`, `"dim"`) as Rich style strings works correctly in `Static` widgets | Code Examples (ObjectRow) | If not, use literal hex colors or `$text`/`$text-muted` — needs a live test pass to confirm exact style string |

**Notes:** A2 is LOW risk — fallback is to use `"bright_white"` and `"grey50"` as explicit Rich color names, which are verified to work. The planner should include a verification step to confirm dot colors render as intended.

---

## Open Questions (RESOLVED)

1. **`O` — priority binding vs standard BINDINGS on `JoyApp`**
   - What we know: `O` is in `JoyApp.BINDINGS`. Standard bindings on App are effectively global since App is the root.
   - What's unclear: Whether `O` needs `priority=True` to fire before child widgets consume it. Currently no child widget uses `O`.
   - Recommendation: Use standard BINDINGS. If a future widget needs `O`, revisit with `priority=True`.
   - RESOLVED: Use standard BINDINGS on JoyApp (no priority=True needed).

2. **Rich style string for Textual CSS variables in Static widgets**
   - What we know: `Text.append(dot, style="white")` works in the shell. `Text.append(dot, style="$text")` may or may not resolve in non-CSS Rich contexts.
   - What's unclear: Whether Textual CSS variable names (`$text`, `$text-muted`) resolve as Rich style strings inside `Static.update()`.
   - Recommendation: Use explicit Rich color names (`"bright_white"` and `"grey50"`) as the safe fallback. Add a visual test step to verify appearance.
   - RESOLVED: Use explicit Rich color names bright_white and grey50.

---

## Environment Availability

All dependencies are already installed in the uv environment. No new dependencies needed.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| textual | Key bindings, `@work`, `notify()` | Yes | 8.2.3 | — |
| rich | `Text.append()` with per-span style | Yes | Textual dep | — |
| tomli_w | `store.save_projects()` | Yes | ^1.0 | — |
| pytest + pytest-asyncio | Test suite | Yes | 9.0.3 + 0.25 | — |

**Missing dependencies with no fallback:** None.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 0.25 |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]`, `asyncio_mode = "auto"` |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

**Baseline:** 64 passed, 1 deselected (macos_integration marker) — confirmed green. [VERIFIED: live run]

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ACT-01 | `o` on highlighted object calls `open_object()` in background | unit (mock subprocess) | `uv run pytest tests/test_tui.py -k "open_object" -x` | Wave 0 (new test) |
| ACT-01 | `o` with no highlighted object shows error toast | unit (Textual pilot) | `uv run pytest tests/test_tui.py -k "no_object" -x` | Wave 0 (new test) |
| ACT-02 | `O` opens all default objects sequentially | unit (mock subprocess) | `uv run pytest tests/test_tui.py -k "open_all" -x` | Wave 0 (new test) |
| ACT-02 | `O` is silent no-op when no defaults exist | unit (Textual pilot) | `uv run pytest tests/test_tui.py -k "no_defaults" -x` | Wave 0 (new test) |
| ACT-03 | `space` flips `open_by_default` on item | unit (Textual pilot) | `uv run pytest tests/test_tui.py -k "toggle" -x` | Wave 0 (new test) |
| ACT-03 | Toggle persists after save (round-trip TOML) | integration (temp file) | `uv run pytest tests/test_store.py -k "toggle" -x` | Wave 0 (new test) |
| ACT-04 | ObjectRow renders `●` when `open_by_default=True` | unit (render check) | `uv run pytest tests/test_object_row.py -x` | Wave 0 (new test) |
| ACT-04 | ObjectRow renders `○` when `open_by_default=False` | unit (render check) | `uv run pytest tests/test_object_row.py -x` | Wave 0 (new test) |
| CORE-05 | Successful `o` produces notify call with correct message | unit (mock notify) | `uv run pytest tests/test_tui.py -k "notify" -x` | Wave 0 (new test) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green (64+ tests passing) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_object_row.py` — unit tests for `ObjectRow._render_text()` dot indicator (ACT-04)
- [ ] `tests/test_tui.py` — extend with activation tests: `o`, `O`, `space` bindings + toast assertions (ACT-01, ACT-02, ACT-03, CORE-05)
- [ ] `tests/test_store.py` — add toggle round-trip test (ACT-03)

Note: `tests/conftest.py` already has `sample_project` and `sample_config` fixtures with full object coverage. No conftest changes needed.

---

## Security Domain

Phase 3 has no new attack surface. `operations.py` already handles all subprocess calls including AppleScript injection prevention (backslash/quote escaping, documented in T-1-03-01 in `_open_iterm`). The space toggle only flips a boolean on an existing `ObjectItem`; no user input is parsed. Toast messages use user-supplied values — the pitfall of Rich markup injection is documented above (use `markup=False`).

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | Minimal — display only | `markup=False` on `app.notify()` calls with user data |
| V6 Cryptography | No | — |
| V2 Authentication | No | — |

No new threat patterns beyond what Phase 1 addressed for the operations layer.

---

## Sources

### Primary (HIGH confidence)
- `src/joy/operations.py` — complete opener implementation, all 6 ObjectTypes covered [VERIFIED: read directly]
- `src/joy/widgets/object_row.py` — current ObjectRow render, `Static` base class [VERIFIED: read directly]
- `src/joy/widgets/project_detail.py` — `highlighted_object`, `_rows`, `GROUP_ORDER`, `_project` attribute [VERIFIED: read directly]
- `src/joy/app.py` — `JoyApp`, `@work(thread=True)` pattern, missing `_config` gap [VERIFIED: read directly]
- `src/joy/models.py` — `ObjectItem.open_by_default` field, `to_dict()` serialization [VERIFIED: read directly]
- `src/joy/store.py` — `save_projects()`, `load_config()`, atomic write pattern [VERIFIED: read directly]
- `tests/` — baseline 64 passed confirmed [VERIFIED: live pytest run]
- Textual 8.2.3 `App.notify()` signature + thread-safe docstring [VERIFIED: live help()]
- Textual 8.2.3 `work()` decorator signature, `exit_on_error` default [VERIFIED: live help()]
- Textual 8.2.3 `Static.update()` signature [VERIFIED: live help()]
- Rich `Text.append()` per-span styling [VERIFIED: live Python evaluation]
- `.planning/phases/03-activation/03-CONTEXT.md` — locked decisions D-01 through D-12
- `.planning/phases/03-activation/03-UI-SPEC.md` — row layout contract, toast copywriting contract

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — ACT-01–ACT-04, CORE-05 definitions

### Tertiary (LOW confidence)
- None. All claims verified against live code or live Textual introspection.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed, versions confirmed
- Architecture patterns: HIGH — all APIs verified via live Python introspection against installed Textual 8.2.3
- Pitfalls: HIGH — identified from code gaps (missing `_config`), API defaults (`exit_on_error=True`, `markup=True`), and existing patterns
- Test mapping: HIGH — existing test infrastructure understood, gaps clearly identified

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (Textual 8.x stable; no fast-moving dependencies)
