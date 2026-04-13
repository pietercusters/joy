# Phase 6: Models, Config & Store - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Define all data structures and persistence for the repo registry, worktree state, terminal sessions, and new settings. Everything round-trips through TOML. No UI in this phase — that is Phase 8+ territory. Downstream phases (7, 9, 10, 11, 12) consume these models as their data layer.

</domain>

<decisions>
## Implementation Decisions

### Repo registry storage
- **D-01:** Repo registry lives in a new `~/.joy/repos.toml` file — separate from `config.toml`, consistent with the `projects.toml` pattern. `config.toml` stays settings-only.
- **D-02:** Repos are keyed by name in TOML (e.g. `[repos.joy]`). Name is auto-deduced from the path basename by default; user can override. Matches the `[projects.<name>]` schema already in use.

### Repo model fields
- **D-03:** `Repo` dataclass fields: `name: str`, `local_path: str`, `remote_url: str = ""`, `forge: str = "unknown"`. `remote_url` is optional (auto-deduced via `git remote get-url origin` when path is provided). `forge` is auto-detected from remote URL.
- **D-04:** `forge` is a plain `str` field (`"github"`, `"gitlab"`, `"unknown"`) — not an Enum, to keep it forward-compatible if more forges are added later.

### Config extension
- **D-05:** Add `refresh_interval: int = 30` and `branch_filter: list[str] = ["main", "testing"]` as flat fields on the existing `Config` dataclass. No nested sections — consistent with current flat schema. Backward-compatible: old config.toml files missing these fields get defaults.

### Forge detection
- **D-06:** Simple pattern match only — `"github.com" in url → "github"`, `"gitlab.com" in url → "gitlab"`, else `"unknown"`. Pure function in `models.py` or `store.py`. No config-driven forge URLs in this phase.

### Git subprocess approach
- **D-07:** `git remote get-url origin` runs via `subprocess.run(["git", "remote", "get-url", "origin"], cwd=local_path, capture_output=True, text=True, timeout=5)`. Returns empty string on any error (non-zero exit, timeout, path not found). Never raises — callers get `""` and handle gracefully.
- **D-08:** Path validation (`REPO-06`) uses `Path(local_path).is_dir()` — synchronous, no subprocess needed.

### Claude's Discretion
- TOML key sanitization if repo name contains characters invalid for TOML bare keys (replace with `-` or quote)
- Whether `Repo.to_dict()` follows the same pattern as `Project.to_dict()`
- Store function signatures (e.g. `load_repos` / `save_repos` pattern matching existing functions)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing persistence layer
- `src/joy/models.py` — Current dataclass structure (ObjectItem, Project, Config); extend here
- `src/joy/store.py` — Atomic write pattern, TOML keyed schema, load/save function signatures to match

### Requirements for this phase
- `.planning/REQUIREMENTS.md` §REPO — REPO-01 through REPO-06 (repo registry CRUD + validation + auto-deduction)
- `.planning/REQUIREMENTS.md` §SETT — SETT-07 (refresh_interval), SETT-08 (branch_filter)

### Roadmap phase spec
- `.planning/ROADMAP.md` §Phase 6 — Success criteria 1-5

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_atomic_write(path, data)` in `store.py` — reuse directly for `save_repos`
- `Config.to_dict()` pattern — follow the same `to_dict()` / `from_dict()` convention for `Repo`
- `_toml_to_projects` / `_projects_to_toml` — reference pattern for `_toml_to_repos` / `_repos_to_toml`

### Established Patterns
- Pure dataclasses in `models.py` (no I/O, no side effects)
- All I/O in `store.py`
- Keyed TOML schema: `result["<collection>"][item.name] = item.to_dict()`
- Unknown/invalid fields in TOML emit `warnings.warn` and skip gracefully (see `_toml_to_projects`)
- `load_*` returns default/empty if file missing; `save_*` creates parent dirs

### Integration Points
- Phase 7 (Git Worktree Discovery) consumes `Repo` objects from `load_repos()`
- Phase 10 (Background Refresh) reads `Config.refresh_interval`
- Phase 9 (Worktree Pane) reads `Config.branch_filter`
- Phase 11 (MR & CI) uses `Repo.forge` to route to `gh` vs `glab`
- Phase 13 (Settings UI) will add `load_repos`/`save_repos` calls in the settings screen

</code_context>

<specifics>
## Specific Ideas

- TOML schema confirmed by user: `[repos.joy]` with `local_path`, `remote_url`, `forge` fields
- Config flat extension confirmed: `refresh_interval = 30`, `branch_filter = ["main", "testing"]` at top level
- Forge detection confirmed as simple function — no config-driven approach

</specifics>

<deferred>
## Deferred Ideas

- Configurable forge hosts for self-hosted GitLab — future phase or backlog
- `name` field user-override UI — settings screen in Phase 13
- Ahead/behind remote count explicitly excluded from scope (see REQUIREMENTS.md Out of Scope)

</deferred>

---
*Phase: 06-models-config-store*
*Context gathered: 2026-04-13*
