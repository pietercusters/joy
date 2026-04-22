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

## Milestone: v1.3 — Unified Object View

**Shipped:** 2026-04-22
**Phases:** 1 (Phase 17) + 21 quick tasks | **Plans:** 3 | **Sessions:** 7 days (2026-04-15 to 2026-04-22)

### What Was Built

- **Phase 17 (iTerm2 bug hardening):** Session-scoped autouse fixture isolating all tests from ~/.joy/; `close_tab()` for tab-level iTerm2 control; removed auto-sync tab creation (tabs only via `h`); delete/archive closes linked tab; new tabs focused immediately
- **Quick tasks (UOV + KEY):** ProjectDetail assembles virtual rows (REPO, TERMINALS, resolver worktrees) alongside stored ObjectItems; per-kind DISPATCH table in dispatch.py routes all quick-open shortcuts — replaces scattered if/else in app.py
- **Quick tasks (polish sprint):** cross-pane sync redesign (`clear_selection()` on no-match), icon ribbon with status dot and 6-icon presence ribbon, project archive/unarchive with cold-storage archive.toml and ArchiveBrowserModal, new-project modal extended with repo + branch ListViews, filter textboxes removed from all panes

### What Worked

- **Quick-task workflow for a polish sprint was efficient:** v1.3 was primarily a rapid iteration cycle — 21 quick tasks rather than formal phases. Each task was atomic, reviewed, and merged. The GSD quick-task machinery handled this pattern well.
- **DISPATCH table as data eliminated a class of bugs:** Moving keystroke routing from imperative if/else in app.py to a declarative per-kind config in dispatch.py made adding or changing key behavior a one-line diff. The pattern is extensible and readable.
- **clear_selection() beats dimmed state:** The earlier dimmed-state concept (set_dimmed()) was reverted in the same sprint it was introduced. clear_selection() is simpler — no visual state to manage, unlinked items remain usable. Reverting fast prevented the pattern from spreading.
- **Test isolation fixture paid for itself immediately:** The autouse session fixture was a Phase 17 plan 01 deliverable. Every test from that point on ran in isolation without developer thought. No "I accidentally touched ~/.joy/" incidents after.

### What Was Inefficient

- **v1.2 REQUIREMENTS.md was never deleted at v1.2 close:** The v1.2 milestone was "shipped" but the REQUIREMENTS.md cleanup step was skipped. This left both v1.2 requirements (unchecked, but already delivered) and future v1.3 requirements in the same file for weeks. Cleanup happened at v1.3 close instead.
- **Pre-existing test failures accumulated silently:** test_propagation.py::TestTerminalAutoRemove and several test_sync.py terminal tests reference non-existent methods. These were noted as "pre-existing" in every Phase 17 summary, but never addressed. They're now explicitly tracked as tech debt.
- **audit-open gsd-tools bug:** The pre-close artifact audit crashed (`output is not defined` in gsd-tools.cjs). The audit had to be done manually instead. Bug should be filed.

### Patterns Established

- **`clear_selection()` (cursor=-1) for sync no-match:** All three panes follow the same contract — if sync finds no related item, cursor is cleared; the pane becomes unfiltered and all items are independently openable
- **DISPATCH table per kind:** `dispatch.py` holds a `DISPATCH` dict keyed by kind string, each entry a `KindDispatch(open_fn, create_fn, label)` — adding a new kind requires only one dict entry
- **Virtual row assembly in ProjectDetail:** REPO and TERMINALS are synthesized at render time from `project.repo` and `project.iterm_tab_id`; resolver worktrees come from RelationshipIndex — none mutate project data
- **Session-scoped autouse fixture for all store paths:** Single fixture in conftest.py patches JOY_DIR, PROJECTS_PATH, CONFIG_PATH, REPOS_PATH, ARCHIVE_PATH — zero per-test overhead, guaranteed isolation

### Key Lessons

1. **Close milestones completely.** Skipping REQUIREMENTS.md deletion at v1.2 close created confusing state that persisted for a full week. The five minutes to run `git rm` is worth it every time.
2. **Quick-task sprints need explicit milestone scoping.** v1.3 was mostly quick tasks, but they weren't formally scoped to v1.3 during execution. Retroactive attribution at milestone close works but costs more effort than tagging tasks as you go.
3. **Reverting fast is a feature, not a failure.** The dimmed-state → clear_selection() flip happened within the same sprint. Shipping a bad pattern and reverting it the same day is healthy — it means the feedback loop is tight.
4. **Pre-existing test failures need a plan, not just documentation.** Noting "pre-existing" in every summary is better than nothing, but the failures don't go away by themselves. The next milestone should include an explicit cleanup task.

### Cost Observations

- Model mix: ~70% sonnet (quick tasks), ~30% opus (dispatch/UOV design)
- Sessions: 7 days (2026-04-15 to 2026-04-22), ~105 commits
- Notable: Highest quick-task density of any milestone (21 quick tasks vs. 1 formal phase); demonstrates the project has shifted from greenfield build to iterative refinement

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 MVP | 3 days | 5 | First milestone — baseline established |
| v1.1 Workspace Intelligence | 3 days | 8 | Parallel phase execution (11+12); slow-test marker convention added |
| v1.2 Cross-Pane Intelligence | 1 day | 3 | Tight dependency chain; milestone close was incomplete (REQUIREMENTS.md not deleted) |
| v1.3 Unified Object View | 7 days | 1 + 21 quick tasks | Polish sprint pattern; quick-task velocity high; test isolation fixture established |

### Cumulative Quality

| Milestone | Src LOC | Tests (fast) | New Dependencies | Commits |
|-----------|---------|-------------|-----------------|---------|
| v1.0 MVP | ~3,641 | 131 | textual, tomli_w, pytest-asyncio | ~50 |
| v1.1 Workspace Intelligence | 3,606 | 276 | iterm2>=2.15 | 158 |
| v1.2 Cross-Pane Intelligence | ~5,500 | ~300 | — | ~60 |
| v1.3 Unified Object View | 6,180 | ~320 | — | ~105 |

### Top Lessons (Verified Across Milestones)

1. Get the data layer and persistence pattern right in Phase 1 — it propagates cleanly across all subsequent phases
2. Async UI frameworks require explicit post-mutation focus management — plan for it from the first TUI phase
3. Graceful degradation for optional integrations (iTerm2, gh, glab) must be specced in success criteria, not discovered in UAT
4. Mark slow tests at the phase that creates them — accumulated test debt compounds silently and wastes every dev cycle until addressed
5. Close milestones completely — skipping cleanup steps (REQUIREMENTS.md, git tag) creates confusing state that costs more to untangle later than to do right the first time
6. Quick-task sprints are an efficient pattern for iterative polish, but need explicit milestone scoping to avoid retroactive attribution debt
