# Phase 6: Models, Config & Store - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-13
**Phase:** 06-models-config-store
**Mode:** discuss
**Areas analyzed:** Repo TOML location, Repo identity & keying, Config extension style, Forge detection scope

## Areas Presented

| Area | Selected for Discussion |
|------|------------------------|
| Repo TOML location | No — defaulted |
| Repo identity & keying | Yes |
| Config extension style | Yes |
| Forge detection scope | Yes |

## Assumptions Made (Not Discussed)

### Repo TOML location
- **Decision:** Separate `repos.toml` file (not folded into config.toml)
- **Rationale:** Mirrors the `projects.toml` / `config.toml` separation already established. User did not select this for discussion — defaulted to the consistent choice.

## Decisions Made

### Repo identity & keying
| Question | Answer |
|----------|--------|
| How should repos be keyed in TOML? | Keyed by name (auto-deduced from path basename) |

- User confirmed `[repos.joy]` / `[repos.other-project]` schema — matches `[projects.<name>]` pattern.

### Config extension style
| Question | Answer |
|----------|--------|
| How to add refresh_interval and branch_filter? | Flat fields on Config (not nested section) |

- User confirmed flat extension: `refresh_interval = 30` and `branch_filter = ["main", "testing"]` at config top level.

### Forge detection scope
| Question | Answer |
|----------|--------|
| How to detect forge type? | Simple pattern match only |

- User confirmed simple function: `github.com` → github, `gitlab.com` → gitlab, else unknown. No configurable forge URLs.

## Corrections Made

None — all recommended options were confirmed.
