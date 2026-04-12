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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 MVP | 3 days | 5 | First milestone — baseline established |

### Cumulative Quality

| Milestone | Tests | Coverage | New Dependencies |
|-----------|-------|----------|-----------------|
| v1.0 MVP | 131 | ~70% (est) | textual, tomli_w, pytest-asyncio |

### Top Lessons (Verified Across Milestones)

1. Get the data layer and persistence pattern right in Phase 1 — it propagates cleanly across all subsequent phases
2. Async UI frameworks require explicit post-mutation focus management — plan for it from the first TUI phase
