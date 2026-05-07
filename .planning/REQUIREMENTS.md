# Requirements: joy

**Defined:** 2026-05-07
**Core Value:** Every artifact for the active project, openable instantly from one keyboard-driven interface — no hunting through tabs, terminals, or bookmarks.

## v1.4 Requirements

Requirements for v1.4 Frontend Refactor & UI Polish. Each maps to roadmap phases.

### Contracts & Facades

- [ ] **CNTR-01**: Protocol definitions exist in ports.py for StoragePort, GitDataPort, TerminalPort, OpenerPort
- [ ] **CNTR-02**: SyncablePane Protocol defines sync_to() and clear_selection() contracts used by PaneCoordinator
- [ ] **CNTR-03**: All widget private-field access from app.py replaced with public facade properties (current_project, highlighted_item, cursor_index)
- [ ] **CNTR-04**: ProjectDetail exposes clear(), show_project(), default_items via public methods instead of direct _project/_rows/_cursor mutation
- [ ] **CNTR-05**: WorktreePane and TerminalPane expose highlighted_worktree/highlighted_session as public properties

### Service Extraction

- [ ] **SRVC-01**: PaneCoordinator extracted from app.py handling all 6 sync directions with _is_syncing guard as context manager
- [ ] **SRVC-02**: DataOrchestrator extracted handling background data loading, _worktrees_ready/_sessions_ready coordination, and relationship computation
- [ ] **SRVC-03**: ProjectService extracted handling project CRUD, archive/unarchive, MR auto-add propagation, and project persistence
- [ ] **SRVC-04**: app.py reduced to thin Textual wrapper (under 400 LOC, under 10 instance variables)
- [ ] **SRVC-05**: All @work(thread=True) decorators remain on app.py; services are synchronous pure Python

### Test Infrastructure

- [ ] **TEST-01**: Backend service tests for PaneCoordinator (sync logic tested without TUI, plain pytest)
- [ ] **TEST-02**: Backend service tests for DataOrchestrator (data loading coordination tested without TUI)
- [ ] **TEST-03**: Backend service tests for ProjectService (CRUD operations tested without TUI)
- [ ] **TEST-04**: Widget tests with fake backend injection (FakeBackend adapters replacing @patch-based mocking)
- [ ] **TEST-05**: Snapshot baselines captured for key screens (initial render, project selected, sync active) using pytest-textual-snapshot
- [ ] **TEST-06**: Existing failing tests fixed (test_propagation.py + test_sync.py tech debt resolved)

### UI Polish

- [ ] **UIPOL-01**: Systematic audit of all panes for visual inconsistencies (spacing, alignment, truncation, focus indicators)
- [ ] **UIPOL-02**: Identified UI bugs fixed across ProjectList, ProjectDetail, WorktreePane, TerminalPane, MRPane

### Architecture Integrity

- [ ] **ARCH-01**: No widget imports Protocol adapters directly — dependency flows through app.py composition root
- [ ] **ARCH-02**: Test isolation fixture updated for any module renames (session-scoped paths remain correct)
- [ ] **ARCH-03**: All tests pass at every intermediate refactoring step (incremental migration, no big-bang)

## Future Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Advanced Testing

- **ATEST-01**: Property-based testing for data models and serialization
- **ATEST-02**: CI pipeline integration for snapshot regression detection

### Architecture Extensions

- **AEXT-01**: Reactive data flow using Textual reactive attributes for cross-widget communication
- **AEXT-02**: Event bus for decoupled widget-to-widget messaging
- **AEXT-03**: Plugin architecture for custom object types

## Out of Scope

| Feature | Reason |
|---------|--------|
| DI framework (dependency-injector, etc.) | Manual constructor injection sufficient at 4-5 ports; framework adds import overhead |
| ABC base classes for ports | typing.Protocol provides structural subtyping without inheritance |
| Widget rewrites | Refactor in place; widgets work correctly, just need facade methods |
| Package splitting (src/joy → subpackages) | Flat module structure adequate at ~7,400 LOC |
| Async services | Services are synchronous; @work decorators stay on Textual layer |
| Event bus | Over-engineering for current scale; direct method calls sufficient |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CNTR-01 | TBD | Pending |
| CNTR-02 | TBD | Pending |
| CNTR-03 | TBD | Pending |
| CNTR-04 | TBD | Pending |
| CNTR-05 | TBD | Pending |
| SRVC-01 | TBD | Pending |
| SRVC-02 | TBD | Pending |
| SRVC-03 | TBD | Pending |
| SRVC-04 | TBD | Pending |
| SRVC-05 | TBD | Pending |
| TEST-01 | TBD | Pending |
| TEST-02 | TBD | Pending |
| TEST-03 | TBD | Pending |
| TEST-04 | TBD | Pending |
| TEST-05 | TBD | Pending |
| TEST-06 | TBD | Pending |
| UIPOL-01 | TBD | Pending |
| UIPOL-02 | TBD | Pending |
| ARCH-01 | TBD | Pending |
| ARCH-02 | TBD | Pending |
| ARCH-03 | TBD | Pending |

**Coverage:**
- v1.4 requirements: 21 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 21 ⚠️

---
*Requirements defined: 2026-05-07*
*Last updated: 2026-05-07 after initial definition*
