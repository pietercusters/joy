# Phase 12: iTerm2 Integration & Terminal Pane - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-13
**Phase:** 12-iterm2-integration-terminal-pane
**Mode:** discuss
**Areas analyzed:** API approach, Session row layout, Claude detection heuristic, Navigation model

## Areas Discussed

### API Approach

| Question | Options Presented | Selected |
|----------|-------------------|----------|
| How should joy enumerate iTerm2 sessions? | iterm2 Python package (Recommended), AppleScript only, iterm2 package as optional dep | **iterm2 Python package** |

### Session Row Layout

| Question | Options Presented | Selected |
|----------|-------------------|----------|
| How should each session row be displayed? | Two-line rows (Recommended), Single-line compact | **Single-line compact** |
| How to label the two groups? | "Claude" + "Other" (Recommended), "Agents" + "Terminals", No grouping if homogeneous | **"Claude" + "Other"** |

### Claude Detection Heuristic

| Question | Options Presented | Selected |
|----------|-------------------|----------|
| What makes a session a "Claude agent" session? | Foreground process named "claude" (Recommended), Session name contains "claude", Either | **Foreground process named "claude"** |
| How to show busy vs waiting? | Running vs idle via foreground process (Recommended), Always show ● (no distinction), iTerm2 session variable | **Running vs idle via foreground process** |

### Navigation Model

| Question | Options Presented | Selected |
|----------|-------------------|----------|
| How to implement j/k cursor navigation? | (User asked to clarify — "can it be similar to the Details pane?") | **ProjectDetail pattern: _cursor + --highlight CSS** |
| Should r-key and timer also refresh terminal? | Yes — same r-key and timer (Recommended), On mount + r-key only, Separate key | **Yes — r refreshes both panes** |

## Corrections Made

No corrections — user confirmed or selected all recommended options except row layout (user chose single-line over the recommended two-line).

## User Clarification

> "Can it be similar to the Details pane?"

Prompted reading `project_detail.py`. The `ProjectDetail` uses `_cursor: int` + `_rows: list[ObjectRow]` + `--highlight` CSS class (not Textual's ListView). GroupHeaders are excluded from `_rows`. Decision: replicate this pattern verbatim in `TerminalPane`.
