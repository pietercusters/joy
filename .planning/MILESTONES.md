# Milestones

## v1.0 MVP (Shipped: 2026-04-12)

**Phases completed:** 5 phases, 15 plans, 18 tasks

**Key accomplishments:**

- Atomic TOML persistence layer (tomllib/tomli_w) with keyed schema, atomic writes, and test-isolation via path parameterization — zero-dependency data layer
- Two-pane Textual TUI: ProjectList + ProjectDetail with grouped ObjectRows (Nerd Font icons), j/k cursor navigation, and context-sensitive Header/Footer
- Core value delivered: `o` opens selected object, `O` opens all defaults, `space` toggles default set — all via background workers with toast feedback
- Full CRUD: new project (n), add/edit/delete objects (a/e/d), delete project (D) via modal forms with confirmation dialogs
- SettingsModal (`s`) for all 5 Config fields, real-time project filter (`/`), `--version` CLI flag, full README — globally installable via `uv tool install`

---
