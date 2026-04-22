---
name: Project detail — virtual object layer design
description: Design decisions for unified object view in ProjectDetail pane — Option B virtual layer, keystroke taxonomy, modular dispatch
type: note
---

# Project Detail — Virtual Object Layer Design

**Date:** 2026-04-22
**Context:** Exploration of how Joy adds/links objects to projects, and how to make the experience consistent and discoverable.

## Problem

The current system has three different shapes of "linked object", each behaving differently:

1. **`project.objects[]`** — stored ObjectItems in TOML (MR, BRANCH, TICKET, NOTE, etc.)
2. **Direct project fields** — `project.repo` and `project.iterm_tab_id` (not in objects[])
3. **Transient resolver matches** — discovered worktrees matched by (repo, branch), never stored

This creates cognitive friction: the user has to remember *how* each kind is linked, and the detail pane doesn't show the full picture.

## Design Decision: Option B — Virtual Layer

**Keep the data model as-is.** Add a virtual object layer in `ProjectDetail` that assembles a unified list of renderable rows from all three sources:

- `project.objects[]` — all stored ObjectItems
- Synthesized REPO row from `project.repo` (already partially done)
- Synthesized TERMINALS row from `project.iterm_tab_id`
- Resolver-matched worktrees as virtual WORKTREE rows (read-only)

**Why Option B over Option A (model migration):** Keeps the refactor additive and non-breaking. The data model already works; the problem is purely in presentation and dispatch.

## Keystroke Taxonomy

Each kind's keystroke follows a consistent 4-state decision tree:

| State | Behavior | Examples |
|-------|----------|---------|
| Exists + openable | Open it | MR (browser), worktree (IDE), note (Obsidian), file (editor), thread (Slack), URL |
| Exists + not openable | Copy value to clipboard | BRANCH, REPO |
| Missing + can auto-create | Create immediately | TERMINALS (creates iTerm2 tab) |
| Missing + needs info | Prompt user for input | TICKET (needs URL), NOTE (needs path), etc. |

REPO gets a keystroke (`r`) — copies the repo name (exists + not-openable).

## Modularity Requirement

Each kind declares its behavior via a per-kind config/dataclass. No scattered if/else logic. Dispatch is table-driven so adding a new kind or changing an action requires only updating the config, not hunting through app logic.

## Virtual Row Rules

- Synthesized REPO and TERMINALS rows: appear in the detail pane, deletable (clears `project.repo` or `project.iterm_tab_id`)
- Resolver-matched worktree rows: appear in the detail pane, **read-only** (no delete) — they are informational, not owned by the project
- All virtual rows participate in the same keystroke dispatch as stored ObjectItems
