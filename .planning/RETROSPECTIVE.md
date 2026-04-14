# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-04-12
**Phases:** 5 | **Plans:** 15 | **Sessions:** ~3 days

### What Was Built

- **Foundation (Phase 1):** Python package scaffold, TOML persistence layer with atomic writes, all 9 object-type operations (clipboard, browser, IDE, Obsidian, iTerm2) via subprocess — zero runtime dependencies beyond Textual
- **TUI Shell (Phase 2):** Two-pane Textual app with grouped ObjectRows (Nerd Font icons), j/k cursor navigation, context-sensitive Header/Footer, 5 Textual pilot tests
- **Activation (Phase 3):** `o` (open object), `O` (open all defaults), `space` (toggle default) with toast feedback, background threading, dot indicator per object — the core value proposition delivered
- **CRUD (Phase 4):** Full create/edit/delete cycle for projects and objects via modal forms (NameInputModal, PresetPickerModal, ValueInputModal, ConfirmationModal) with cursor management and background persistence
- **Settings + Search + Distribution (Phase 5):** SettingsModal with 5 Config fields (`s`), real-time project filter (`/`), `--version` CLI flag with importlib.metadata, full README, globally installable via `uv tool install`

### What Worked

- **TDD cycle was clean:** Red→Green→Refactor enforced by GSD executor kept test debt minimal; 131 tests passing at ship
- **Textual architecture fit perfectly:** ModalScreen, @work threading, BINDINGS, and ListView were exactly right for this use case — no fighting the framework
- **Background workers for all mutations:** `@work(thread=True)` pattern from Phase 2 onward kept the TUI responsive; zero freezes reported during UAT
- **Canonical list separation for filter:** Keeping `self.app._projects` as the ground truth (never the display list) prevented subtle state bugs on Escape restore
- **Atomic TOML writes:** `tempfile + os.replace` pattern from Phase 1 paid off — zero data corruption issues throughout
- **Decimal phase numbering (GSD) didn't need insertion:** Clean 5-phase arc from plan held, no mid-phase pivots required

### What Was Inefficient

- **Requirements traceability table never updated:** All 48 requirements show "Pending" at milestone close — the update discipline wasn't enforced during execution. Archive shows actual state but the live doc was stale throughout.
- **ROADMAP.md Progress table also stale at phases 2-5:** Same issue — the progress table showed phases 2-5 as "Not started" throughout the project even as they completed. These were planning artifacts that weren't treated as living docs.
- **One-liner extraction inconsistency in SUMMARY.md:** Several summaries used different field names (`one_liner:` vs. inline text), causing summary-extract to return raw section headers. A stricter frontmatter convention would help.
- **AppleScript iTerm2 test opening a real window:** One test spawned a real iTerm2 window during `pytest` — required a debug session to diagnose and fix with a mock. Subprocess operations need mocking strategy from the start.

### Patterns Established

- **`@work(thread=True, exit_on_error=False)` for all persistence:** Background workers with explicit error tolerance for all save operations
- **`call_after_refresh()` for post-DOM-mutation focus:** After any `mount`/`remove`, use `call_after_refresh(widget.focus)` to restore focus after Textual's async DOM settles
- **`on_key` with `event.stop()` for Escape in filter mode:** Avoids conflict with ModalScreen Escape; explicit key interception over BINDINGS when scope matters
- **Modal screens return typed values via dismiss:** `ModalScreen[T]` + callback pattern keeps modal logic encapsulated and testable
- **Separate canonical list from display list:** Never filter/mutate the list that stores app state; always pass copies to display

### Key Lessons

1. **Plan the persistence pattern in Phase 1 or pay for it later.** Atomic writes, the `~/.joy/` path parameter pattern for test isolation, and the Config dataclass all required zero rework across 5 phases — because they were right from the start.
2. **Textual's async DOM model requires discipline.** `call_after_refresh` is not optional when changing focus after mount/remove. The stale-index bug (WR-02) and filter dismiss cursor loss were both async timing issues — plan for them.
3. **Tests that touch real system resources need mocks at write time.** The iTerm2 AppleScript test was written without mocking and opened a real window during CI. Don't defer mocking subprocess calls to a "cleanup" phase.
4. **Keep living docs alive.** REQUIREMENTS.md traceability and ROADMAP.md progress table were stale throughout. Either enforce updates on every plan completion or acknowledge they're snapshots, not live state.

### Cost Observations

- Model mix: ~80% opus (planning + execution), ~20% sonnet (orchestration)
- Sessions: 3 active coding days (2026-04-10 to 2026-04-12)
- Notable: All 15 plans executed autonomously by gsd-executor agent; human time spent on UAT and course corrections only

---

## Milestone: v1.1 — Workspace Intelligence

**Shipped:** 2026-04-14
**Phases:** 8 (6-13) | **Plans:** 19 | **Sessions:** ~3 days (2026-04-12 to 2026-04-14)

### What Was Built

- **Models + Store (Phase 6):** Repo dataclass with detect_forge, TOML-backed repo registry with atomic writes, get_remote_url via git subprocess, validate_repo_path
- **Worktree Discovery (Phase 7):** WorktreeInfo dataclass + discover_worktrees — git porcelain parsing, dirty detection (diff-index), upstream tracking (rev-parse), exact-match branch filter
- **4-Pane Layout (Phase 8):** JoyApp refactored from Horizontal 2-pane to CSS Grid 2x2; Tab/Shift+Tab focus cycling with accent-border focus indicator; stub TerminalPane + WorktreePane
- **Worktree Pane (Phase 9):** Live grouped WorktreePane with repo section headers, Nerd Font dirty/no-remote indicators, two-line rows — read-only via VerticalScroll non-focusable pattern
- **Background Refresh (Phase 10):** set_interval timer + r keybinding, relative timestamp in border_title, stale-data detection at 2× interval, scroll position preservation across DOM rebuilds
- **MR/CI Status (Phase 11):** MRInfo dataclass + mr_status.py fetching via gh/glab CLI; PR number, draft icon, CI pass/fail/pending badges on worktree rows; author + commit on line 2
- **iTerm2 Terminal Pane (Phase 12):** TerminalSession model + fetch_sessions via iterm2 Python API; Claude agent grouping at top; j/k navigation + Enter to focus window; graceful "unavailable" fallback
- **Project Workflow + Docs (Phase 13):** Project.repo field + project grouping in ProjectList; SettingsModal Repos section with add/remove/navigate; README Prerequisites section

### What Worked

- **cursor/_rows/--highlight pattern scaled cleanly:** Established in WorktreePane, replicated in TerminalPane and ProjectList with no conceptual overhead — consistent mental model across all scrollable panes
- **Parallel phase execution (11 + 12) succeeded:** Both phases ran independently from Phase 10 and merged cleanly into Phase 13, demonstrating the dependency graph was correctly modeled
- **Graceful degradation was designed in, not bolted on:** lazy import + catch-all in terminal_sessions.py means the whole pane fails safely when iTerm2 is unavailable — no crashes
- **TDD discipline paid off at Phase 9:** Wave-0 test scaffolding (09-01) meant the implementation phase (09-02) had a clear contract to satisfy; green-phase was straightforward
- **iterm2 Python API was better than AppleScript for introspection:** AppleScript can activate a window but can't enumerate sessions; the Python API was the right call despite slightly more setup

### What Was Inefficient

- **ROADMAP.md progress table entries for phases 7-9 were never updated to "Complete":** Same stale-doc pattern from v1.0. These required manual correction at milestone close. Discipline or automation needed.
- **One-liner extraction from SUMMARY.md still inconsistent:** Several phase-09 and phase-12 summaries didn't populate `one_liner:` cleanly, causing summary-extract to return raw section content. Frontmatter schema needs enforcement.
- **Phase 13 needed a RepoPickerModal mid-execution:** An unplanned interactive step (assign-repo binding 'r', later 'R' to avoid conflict) was discovered during UAT — required a quick fix outside the plan. More thorough UAT design upfront would catch this.
- **Slow test problem accumulated invisibly:** TUI/filter tests grew to ~264s total before being addressed by a quick task. Should add slow-marker convention at the phase that introduces slow tests, not retroactively.

### Patterns Established

- **`VerticalScroll` (non-focusable) + cursor widget for read-only panes:** WorktreePane/TerminalPane pattern — scroll without focus trap, cursor navigation via j/k at widget level
- **Border title as status channel:** `pane.border_title = f"Pane [{timestamp}]"` for live refresh timestamps and stale warnings — no separate status widget needed
- **`call_from_thread` for worker→widget updates:** Background workers use `self.app.call_from_thread(widget.set_data, ...)` to push data safely from worker threads into Textual's main thread
- **Inner widget messaging for modal CRUD:** `_RepoListWidget` posts `_AddRepoRequest`/`_DeleteRepoRequest` to parent `SettingsModal` — clean separation of list logic from persistence logic
- **`pytest.mark.slow` for TUI/integration tests:** Exclude by default with `-m "not slow"`; run full suite with `--run-slow` when needed

### Key Lessons

1. **Parallel phases need clean dependency graphs.** Phases 11 and 12 running in parallel worked because they had zero shared mutable state. When phases share a widget or data structure, they can't parallelize safely — model this explicitly.
2. **Design stale-data UX in the same phase as the refresh logic.** Phase 10 designed both timer and stale indicator together — the UX was coherent. Defer one and you get a bolted-on warning that doesn't match the mental model.
3. **"Unavailable" graceful fallback is a first-class feature.** The iTerm2 pane's "unavailable" state was specced in Phase 12 success criteria, not discovered during UAT. This prevented a last-minute scramble and kept the app stable on machines without iTerm2.
4. **Mark tests as slow at the phase that creates them.** The slow-test problem was a 264-second tax on every dev cycle, accumulated silently over v1.1. The fix was trivial; the cost was paid for weeks before it was addressed.

### Cost Observations

- Model mix: ~80% opus (planning + execution), ~20% sonnet (orchestration)
- Sessions: 3 days (2026-04-12 to 2026-04-14), 158 commits
- Notable: 8 phases in 3 days; phases 11 and 12 executed in parallel, shaving ~1 day vs. sequential execution

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 MVP | 3 days | 5 | First milestone — baseline established |
| v1.1 Workspace Intelligence | 3 days | 8 | Parallel phase execution (11+12); slow-test marker convention added |

### Cumulative Quality

| Milestone | Tests (fast) | New Dependencies | Commits |
|-----------|-------------|-----------------|---------|
| v1.0 MVP | 131 | textual, tomli_w, pytest-asyncio | ~50 |
| v1.1 Workspace Intelligence | 276 | iterm2>=2.15 | 158 |

### Top Lessons (Verified Across Milestones)

1. Get the data layer and persistence pattern right in Phase 1 — it propagates cleanly across all subsequent phases
2. Async UI frameworks require explicit post-mutation focus management — plan for it from the first TUI phase
3. Graceful degradation for optional integrations (iTerm2, gh, glab) must be specced in success criteria, not discovered in UAT
4. Mark slow tests at the phase that creates them — accumulated test debt compounds silently and wastes every dev cycle until addressed
