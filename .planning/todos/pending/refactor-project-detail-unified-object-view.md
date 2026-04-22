---
name: Refactor ProjectDetail and keystroke dispatch for unified object view
description: Implement virtual object layer in ProjectDetail and modular per-kind dispatch table for consistent keystroke behavior
type: todo
date: 2026-04-22
priority: medium
---

# Refactor ProjectDetail and keystroke dispatch for unified object view

**Context:** See `.planning/notes/project-detail-virtual-layer-design.md` for full design rationale.

## What to build

### 1. Virtual row assembly in ProjectDetail

Assemble a unified list of renderable rows from all sources:
- `project.objects[]` (stored ObjectItems)
- Synthesized REPO row from `project.repo`
- Synthesized TERMINALS row from `project.iterm_tab_id`
- Resolver-matched worktrees as virtual WORKTREE rows (read-only, no delete)

### 2. Modular per-kind dispatch table

Each kind declares a config covering 4 states:
- `exists_openable` → open action
- `exists_not_openable` → copy action
- `missing_auto_create` → create action (or None)
- `missing_needs_input` → prompt action (or None)

Dispatch is table-driven. No scattered if/else in app logic.

### 3. REPO keystroke

Add `r` keybinding that copies the repo name (exists + not-openable behavior).

### 4. Consistent quick-open shortcuts

All existing shortcuts (b, m, i, y, u, t, h, r) route through the same dispatch table. Behavior for missing objects follows the taxonomy above.

## Acceptance criteria

- [ ] All linked objects visible in detail pane (repo, terminal, resolver worktrees)
- [ ] Resolver-matched worktree rows show but have no delete action
- [ ] `r` key copies repo name (or prompts to assign repo if not set)
- [ ] `h` key behavior unchanged (auto-creates terminal if missing)
- [ ] All quick-open shortcuts behave consistently per the 4-state taxonomy
- [ ] Adding a new kind requires only updating the dispatch config, not app logic
