---
phase: quick
plan: 260411-ivh
type: execute
wave: 1
depends_on: []
files_modified:
  - src/joy/widgets/project_list.py
  - src/joy/widgets/project_detail.py
  - src/joy/operations.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "After deleting a project, the adjacent project is visually highlighted in the list"
    - "When the project list has focus, the detail pane rows appear dimmed (subdued accent)"
    - "When the detail pane has focus, the highlighted row shows full accent color"
    - "Opening a Slack thread URL navigates to the specific thread in Slack"
  artifacts:
    - path: "src/joy/widgets/project_list.py"
      provides: "Deferred select_index call after project delete"
    - path: "src/joy/widgets/project_detail.py"
      provides: "Focus-aware highlight CSS for ObjectRow"
    - path: "src/joy/operations.py"
      provides: "Slack URL opened via macOS URL scheme (not -a flag)"
  key_links:
    - from: "JoyListView.action_delete_project"
      to: "parent.call_after_refresh(parent.select_index, new_index)"
      via: "deferred callback after DOM rebuild"
    - from: "ObjectRow.--highlight"
      to: "ProjectDetail:focus-within"
      via: "CSS :focus-within pseudo-class"
    - from: "_open_url (slack branch)"
      to: "macOS URL scheme handler"
      via: "open url (no -a flag)"
---

<objective>
Fix three UAT bugs in the joy TUI.

Purpose: Restore correct post-delete selection, symmetric focus dimming, and Slack thread navigation.
Output: Three targeted line-level fixes across three files.
</objective>

<execution_context>
@/Users/pieter/Github/joy/.claude/get-shit-done/workflows/execute-plan.md
@/Users/pieter/Github/joy/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix post-delete list selection (defer select_index)</name>
  <files>src/joy/widgets/project_list.py</files>
  <action>
In `JoyListView.action_delete_project`, inside the `on_confirm` callback, the call
`parent.select_index(new_index)` is made synchronously right after `parent.set_projects(projects)`.
`set_projects` calls `listview.clear()` followed by `listview.append()` for each project. The DOM
rebuild hasn't rendered yet when `listview.index = new_index` fires, so the visual highlight is
lost even though `ProjectHighlighted` fires correctly.

Replace:
```python
parent.select_index(new_index)
```
with:
```python
parent.call_after_refresh(parent.select_index, new_index)
```

This defers the index assignment until after Textual has processed the DOM mutations from
`set_projects`, so the ListView has its new items rendered before the selection is applied.

Location: `src/joy/widgets/project_list.py`, line 49 (inside `on_confirm` in `action_delete_project`).
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && /Users/pieter/.nvm/versions/node/v22.17.1/bin/node -e "const fs=require('fs'); const src=fs.readFileSync('src/joy/widgets/project_list.py','utf8'); if(!src.includes('call_after_refresh(parent.select_index')) throw new Error('Fix not applied'); console.log('OK: call_after_refresh present');"</automated>
  </verify>
  <done>
`parent.call_after_refresh(parent.select_index, new_index)` is used in `on_confirm` instead of
the synchronous `parent.select_index(new_index)`. The old direct call is gone.
  </done>
</task>

<task type="auto">
  <name>Task 2: Fix asymmetric focus dimming (CSS :focus-within guard)</name>
  <files>src/joy/widgets/project_detail.py</files>
  <action>
In `ProjectDetail.DEFAULT_CSS`, the current rule:

```css
ObjectRow.--highlight {
    background: $accent;
}
```

applies full accent regardless of whether `ProjectDetail` has focus. When focus is on the
project list, `ObjectRow.--highlight` should show a subdued accent to signal "not active".

Replace that single rule with two rules:

```css
ProjectDetail:focus-within ObjectRow.--highlight {
    background: $accent;
}
ObjectRow.--highlight {
    background: $accent 30%;
}
```

The `:focus-within` rule takes precedence (higher specificity) when `ProjectDetail` or any
descendant has focus, showing full `$accent`. The fallback rule (no focus-within) shows a
dimmed 30% opacity accent, matching how the project list pane dims when detail has focus.

This is a CSS-only change — no Python logic changes needed.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && /Users/pieter/.nvm/versions/node/v22.17.1/bin/node -e "const fs=require('fs'); const src=fs.readFileSync('src/joy/widgets/project_detail.py','utf8'); if(!src.includes(':focus-within')) throw new Error('focus-within missing'); if(!src.includes('\$accent 30%')) throw new Error('subdued accent missing'); console.log('OK: focus-within CSS present');"</automated>
  </verify>
  <done>
`DEFAULT_CSS` has two `ObjectRow.--highlight` rules: one scoped to `ProjectDetail:focus-within`
showing full `$accent`, and one unscoped fallback showing `$accent 30%`. The original single
rule is replaced.
  </done>
</task>

<task type="auto">
  <name>Task 3: Fix Slack URL navigation (remove -a flag)</name>
  <files>src/joy/operations.py</files>
  <action>
In `_open_url` in `src/joy/operations.py`, the Slack branch uses:

```python
subprocess.run(["open", "-a", "Slack", url], check=True)
```

The `-a Slack` flag tells macOS to open the URL with the Slack application directly, bypassing
macOS URL scheme routing. Slack's registered URL scheme handler (`slack://`) is what translates
`https://app.slack.com/client/...` links into in-app navigation to the specific thread.
Using `-a` skips that handler, so Slack opens but doesn't navigate.

Replace:
```python
subprocess.run(["open", "-a", "Slack", url], check=True)
```
with:
```python
subprocess.run(["open", url], check=True)
```

This routes through macOS's URL handler dispatch, which invokes Slack's registered scheme
handler and performs deep-link navigation to the thread. The behaviour is identical to the
`else` branch below it, so the `elif "slack.com"` branch can optionally be collapsed into
the generic `else` — but keeping the branch is also fine for explicitness.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && /Users/pieter/.nvm/versions/node/v22.17.1/bin/node -e "const fs=require('fs'); const src=fs.readFileSync('src/joy/operations.py','utf8'); if(src.includes('-a\", \"Slack')) throw new Error('old -a Slack still present'); if(!src.includes('slack.com')) throw new Error('slack branch missing entirely'); console.log('OK: Slack fix applied');"</automated>
  </verify>
  <done>
The `subprocess.run(["open", "-a", "Slack", url])` call is replaced with `subprocess.run(["open", url])`.
No `-a Slack` argument remains in the Slack branch.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user config → subprocess | URL values from TOML config passed to `open` |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-ivh-01 | Tampering | `_open_url` / Slack branch | accept | URL value originates from user-controlled TOML config; no new attack surface introduced by removing `-a Slack`. Existing T-1-03 covers injection in iTerm2 branch. |
</threat_model>

<verification>
After all three tasks:
1. Delete a project — the adjacent project should be visually highlighted in the list immediately.
2. Focus on project list — detail pane highlighted row should appear dimmed (subdued).
3. Focus on detail pane — highlighted row should show full accent color.
4. Open a Slack thread URL — Slack should navigate to the specific thread.
</verification>

<success_criteria>
- `call_after_refresh` defers selection in delete flow — visual highlight appears after DOM rebuild
- `:focus-within` CSS produces symmetric dimming in both panes
- Slack thread URLs route through macOS URL scheme, opening the correct thread
</success_criteria>

<output>
After completion, create `.planning/quick/260411-ivh-fix-three-uat-bugs-project-list-selectio/260411-ivh-SUMMARY.md`
</output>
