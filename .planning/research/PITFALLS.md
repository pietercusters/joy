# Domain Pitfalls: Refactoring Monolithic Textual App to Ports & Adapters

**Domain:** Incremental refactoring of a 1,058 LOC Textual TUI (Python) to hexagonal architecture
**Researched:** 2026-05-07
**Codebase:** joy v1.3 -> v1.4, ~520 tests across 26 files, Textual 8.x

---

## Critical Pitfalls

Mistakes that cause test suite collapse, runtime regressions, or rewrites of the refactoring itself.

### Pitfall 1: Widget Private Field Access Creates Hidden Contracts

**What goes wrong:** app.py accesses `detail._project`, `detail._rows`, `detail._cursor`, `pane._cursor`, `pane._rows`, `project_list._cursor`, `project_list._rows` directly. Widgets also reach up into `self.app._projects`, `self.app._config`, `self.app._save_projects_bg()`, `self.app._close_tab_bg()`, `self.app._current_worktrees`, `self.app._update_badges()`, and more. These bidirectional private-field accesses form an undocumented contract. When you extract services, moving `_projects` off the App object breaks every widget that reads `self.app._projects` -- but the breakage is silent (AttributeError at runtime, not caught by type checkers because the access is through `self.app` which is typed as `App`, not `JoyApp`).

**Why it happens:** Textual's `self.app` returns the `App` base type. Widgets access `self.app._projects` through dynamic attribute lookup, which mypy/pyright cannot verify. The coupling accumulated organically across v1.0-v1.3 because private field access was the fastest path.

**Consequences:** Moving state off JoyApp to a service layer breaks at least 28 call sites across 4 widget files (project_list.py: 18 sites, project_detail.py: 4 sites, terminal_pane.py: 3 sites, worktree_pane.py: 1 site, dispatch.py: 4 comment references). These break silently -- tests that mock `self.app._projects` continue to pass while production code crashes.

**Prevention:**
1. Before extracting any state, create **facade methods** on JoyApp that wrap every private-field access pattern. Example: `detail._project` becomes `detail.current_project` (a property); `self.app._projects` becomes `self.app.get_projects()` or is replaced by a service the widget receives.
2. Use `grep -rn "self.app._\|app\._" src/joy/widgets/` as a living checklist. Every hit must be converted to a facade call before the underlying state moves.
3. Do this facade step FIRST, in a dedicated phase, before any service extraction. This lets you run the full test suite after each facade replacement to verify behavioral equivalence.

**Detection:** Run `grep -rn "\._" src/joy/widgets/ | grep -v "__"` regularly. Any private-field cross-boundary access is a warning sign.

**Phase guidance:** Phase 1 (facade creation), before any service extraction begins.

---

### Pitfall 2: Session-Scoped Test Fixture Fragility During Module Reorganization

**What goes wrong:** The `_isolated_store_paths` fixture (conftest.py) patches 5 constants on `joy.store` at session scope: `JOY_DIR`, `PROJECTS_PATH`, `CONFIG_PATH`, `REPOS_PATH`, `ARCHIVE_PATH`. Session-scoped monkeypatch is manually constructed (`mp = pytest.MonkeyPatch()`) because pytest's built-in `monkeypatch` fixture is function-scoped. If you refactor `joy.store` -- for example, splitting it into `joy.adapters.toml_store` or renaming the module -- the patch targets become stale strings. The fixture silently patches non-existent attributes (monkeypatch.setattr raises no error if the module path is wrong and the attribute happens to exist on a different imported name). Tests then read/write to the real `~/.joy/` directory.

**Why it happens:** `mp.setattr("joy.store.JOY_DIR", ...)` uses string-based patching. Moving `JOY_DIR` to a different module means the string target misses. Python's import system caches the old module, so some tests may still work (they imported `joy.store` before the rename) while others fail -- creating nondeterministic test behavior.

**Consequences:** Tests silently escape isolation. On a developer machine, this corrupts `~/.joy/projects.toml`. On CI, tests may pass because the directory does not exist (creating it instead). The failure mode is data loss on the developer's machine, not a test failure.

**Prevention:**
1. When moving store constants, update the session fixture **in the same commit**. Never merge a module rename without updating patch targets.
2. Add a CI assertion at the top of the session fixture: verify that the patched path actually resolves. Example: `assert hasattr(joy.store, "JOY_DIR"), "store path constants moved -- update _isolated_store_paths"`.
3. Consider switching from string-based patching to direct attribute patching: `mp.setattr(joy.store, "JOY_DIR", tmp)` -- this fails immediately if the module structure changes.
4. If you create an adapter module that wraps store functions, the adapter should accept paths as constructor arguments (dependency injection), making the session fixture unnecessary for adapter-level tests.

**Detection:** If any test creates files in `~/.joy/` during a CI run, something is wrong. Add a post-test check: `assert not (Path.home() / ".joy" / "projects.toml.tmp").exists()`.

**Phase guidance:** Must be addressed in the same phase as any store module refactoring. Do not defer.

---

### Pitfall 3: The `_is_syncing` Guard Cannot Be Extracted Naively

**What goes wrong:** `_is_syncing` is a mutable boolean on JoyApp that acts as a reentrant-call guard. It prevents infinite loops in the cross-pane sync chain (project highlights worktree, worktree highlights project, etc.). It is set/cleared in 6 methods across app.py (`_set_worktrees`, `_set_terminal_sessions`, `_propagate_changes`, `_sync_from_project`, `_sync_from_worktree`, `_sync_from_session`). If you extract sync logic into a PaneCoordinator service, you must decide who owns the guard: the service or the app. If the service owns it, the app's event handlers (`on_project_list_project_highlighted`, etc.) must check the service's guard -- but they currently check `self._is_syncing` at the top of the handler, BEFORE calling any sync method. If the app owns it, the service cannot set it, creating a split-brain guard.

**Why it happens:** The guard protects against Textual message cascading (highlight change -> message -> handler -> sync -> highlight change -> message...). This is inherently a UI-layer concern, but the sync logic (which pane to move, what to look up in RelationshipIndex) is business logic. The guard straddles both layers.

**Consequences:** If you get the guard ownership wrong, you get either infinite recursion (sync loop) or dead sync (guard never cleared after exception). Both are hard to reproduce in unit tests because they require the full Textual message pipeline.

**Prevention:**
1. The PaneCoordinator should own the guard and expose it as a context manager: `with coordinator.syncing():`. The app's event handlers call `if coordinator.is_syncing: return` at the top.
2. All sync methods must use try/finally to clear the guard -- this pattern already exists in app.py and must be preserved.
3. Write a dedicated test that verifies the guard prevents reentrance: simulate a highlight change during a sync operation and assert no infinite loop.
4. The guard must remain on the main thread only -- never accessed from worker threads. This is currently true and must stay true.

**Detection:** Any `RecursionError` or frozen UI during cursor movement means the guard is broken.

**Phase guidance:** Address during PaneCoordinator extraction. Do not split the guard across layers.

---

### Pitfall 4: Worker Thread Lifecycle Breaks When Methods Move Off JoyApp

**What goes wrong:** JoyApp has 14+ methods decorated with `@work(thread=True)`: `_load_data`, `_load_worktrees`, `_load_terminal`, `_save_projects_bg`, `_do_create_tab_for_project`, `_do_activate_tab`, `_save_config_bg`, `_reload_repos`, `_open_defaults`, `_close_sessions_bg`, `_close_tab_bg`, `_copy_value_bg`, `_do_open_global`, `_open_worktree_path`, `_append_to_archive_bg`, `_remove_from_archive_bg`. Textual's `@work` decorator is an instance method decorator that registers the worker with `self` (the widget/app). If you move these methods to a service class, `@work` no longer works -- the service is not a Textual Widget and has no worker management. Additionally, `call_from_thread` is a method on App/Widget, not available on plain Python objects.

**Why it happens:** Textual workers are tightly coupled to the widget lifecycle. `@work` calls `self.run_worker()` internally, which requires the widget's event loop. A service extracted from the app loses access to this infrastructure.

**Consequences:** Moving a `@work(thread=True)` method to a service results in either: (a) `AttributeError: 'Service' object has no attribute 'run_worker'` at runtime, or (b) if you make the service inherit from Widget (antipattern), it gets mounted into the DOM and receives events it should not handle.

**Prevention:**
1. Keep `@work`-decorated methods on JoyApp (or on widgets). The service layer should be **synchronous pure functions** or **synchronous methods that the app wraps in workers**. Example: service has `def load_worktrees() -> list[WorktreeInfo]` (blocking, pure); app has `@work(thread=True) def _load_worktrees_worker(self): result = self.service.load_worktrees(); self.call_from_thread(self._apply_worktrees, result)`.
2. The service layer boundary is: "everything that happens inside the thread." The `@work` decorator and `call_from_thread` bridge stay on the Textual side.
3. Never pass `self.app` or `self` (widget reference) into a service. Pass only data. Services return data. The caller (widget/app) applies it to the UI.

**Detection:** Any import of `textual` in a service module is a warning sign. Service modules should have zero Textual imports.

**Phase guidance:** Establish this boundary BEFORE extracting any service. Document it as a project convention.

---

### Pitfall 5: Nested Worker Calls Crash Textual

**What goes wrong:** Textual crashes when a `@work(thread=True)` method calls another `@work(thread=True)` method directly. In the current codebase, `_do_create_tab_for_project` calls `self._save_projects_bg()` and `self._load_terminal()` via `call_from_thread`, which triggers new workers from the main thread. This works because the inner calls are scheduled on the main thread (via `call_from_thread`), not called directly from the worker thread. But if during refactoring someone removes the `call_from_thread` wrapper and calls the worker method directly from another worker, Textual raises `RuntimeError` or deadlocks.

**Why it happens:** Textual workers register with the app's worker manager on the thread they are created on. Creating a worker from a worker thread bypasses the event loop's worker tracking, leading to crashes. The current code carefully uses `call_from_thread` to bounce back to the main thread before spawning new workers.

**Consequences:** Hard crash with no useful traceback, or a deadlock where the app freezes silently.

**Prevention:**
1. Document the rule: **never call a @work method from another @work method directly**. Always go through `call_from_thread` to bounce to the main thread first.
2. In the extracted service layer, this becomes moot: services are synchronous functions called from within a single worker. The worker calls multiple service methods sequentially, then uses `call_from_thread` once to push all results back.
3. During refactoring, audit every `@work` method's call chain to ensure no direct worker-to-worker calls are introduced.

**Detection:** `RuntimeError: Cannot call run_worker from a worker thread` or app freeze during background operations.

**Phase guidance:** Address during DataOrchestrator extraction. The orchestrator should consolidate multiple background operations into fewer workers.

---

## Moderate Pitfalls

### Pitfall 6: Protocol Over-Engineering (Port Explosion)

**What goes wrong:** Creating one Protocol per method or per widget interaction leads to 15+ Protocol classes for a ~1,000 LOC app. Each Protocol needs a production implementation and a fake for tests. The cognitive overhead exceeds the benefit. Developers spend more time navigating Protocol definitions than writing features.

**Prevention:**
1. Use coarse-grained Protocols. Three is likely the right number for joy: `ProjectServiceProtocol` (CRUD + archive), `DataOrchestratorProtocol` (load/refresh worktrees, terminals, MR data), `PaneCoordinatorProtocol` (sync, guard, badge updates). Maybe a fourth for `TerminalServiceProtocol` if iTerm2 operations are complex enough.
2. Do NOT create Protocols for: individual store functions (load_projects, save_projects), widget-internal operations, or formatting helpers.
3. Protocols should have 3-8 methods. If a Protocol has 1-2 methods, it is probably too granular. If it has 10+, split it.
4. Do NOT use `@runtime_checkable`. It adds overhead and false confidence -- `isinstance` checks on Protocols only verify method names exist, not signatures. Rely on mypy/pyright for Protocol conformance checking.

**Detection:** Count Protocol files. If there are more Protocol definitions than service implementations, you have over-engineered.

**Phase guidance:** Define Protocols in the FIRST extraction phase. Get the granularity right before building implementations.

---

### Pitfall 7: Test Migration Creates a Dual-World Period That Never Ends

**What goes wrong:** You plan to migrate from `@patch("joy.store.load_projects")` to injecting `FakeProjectService`. But 520 tests cannot be migrated at once. You create the new service and write new tests using fakes, but the old tests still use `@patch`. Both patterns coexist. Over time, the `@patch` tests rot because they patch the old module path (before refactoring), and nobody migrates them because "they still pass." You end up with two testing philosophies, both partially maintained.

**Prevention:**
1. Do NOT plan to migrate all existing tests. Many existing tests (test_models.py: 47 tests, test_store.py: 36 tests, test_operations.py: 14 tests, test_resolver.py: 10 tests, test_worktrees.py: 16 tests) test pure functions/modules that will NOT be affected by the refactoring. They do not need migration.
2. Identify the tests that WILL break: tests that mock `joy.store.load_projects` inside `JoyApp._load_data` (test_tui.py, test_refresh.py, test_pane_layout.py) and tests that access `self.app._*` private fields (test_sync.py fakes, test_propagation.py `_PropContext`).
3. For the breaking tests: rewrite them to use fake adapters in the SAME commit that changes the production code. Do not create a separate "migrate tests" phase.
4. For test_propagation.py's `_PropContext`: this is already a manual DI fake. When `_propagate_mr_auto_add` moves to a service, `_PropContext` becomes unnecessary -- the service method takes plain arguments. This is a simplification, not a migration.
5. Set a deadline: by the end of v1.4, no test should use `@patch` on a path that goes through the service layer. Tests of pure modules (operations.py, worktrees.py, mr_status.py) can keep `@patch` for subprocess mocking -- that is a different concern.

**Detection:** `grep -rn "@patch" tests/ | grep -v "subprocess\|operations\|terminal_sessions\|worktrees\|mr_status"` should return zero results after migration.

**Phase guidance:** Test migration happens IN each extraction phase, not as a separate phase.

---

### Pitfall 8: Losing the `call_after_refresh` Timing Guarantee

**What goes wrong:** Several places in app.py and widgets use `call_after_refresh` to schedule work after the Textual DOM rebuilds (e.g., `detail.call_after_refresh(detail.focus)` in `on_project_list_project_selected`, cursor restoration after `set_projects`). When extracting logic into services, it is tempting to move the "what to do after refresh" logic into the service. But `call_after_refresh` is a Widget method. If the service tells the app "now focus the detail pane," the app must still use `call_after_refresh` to schedule it correctly. If the app forgets the timing wrapper, focus lands on a widget that has been removed and remounted, causing focus to silently fall to the root screen.

**Prevention:**
1. Services should never schedule UI timing. They return results. The app/widget applies results and handles any `call_after_refresh` scheduling.
2. Document every `call_after_refresh` site (there are at least 4) and ensure they stay in the widget layer.
3. Write Textual pilot tests for each `call_after_refresh` site to verify focus behavior survives the refactoring.

**Detection:** After refactoring, if pressing Enter on a project no longer focuses the detail pane, or if cursor restoration after project deletion fails, `call_after_refresh` timing was lost.

**Phase guidance:** Verify during each extraction phase. No dedicated phase needed.

---

### Pitfall 9: Breaking Textual Message Routing by Changing Widget Hierarchy

**What goes wrong:** Textual routes messages (like `ProjectList.ProjectHighlighted`) by walking up the DOM tree to find a handler. JoyApp handles these messages because it is the root App. If during refactoring you introduce an intermediary container widget (e.g., a `MainPane` wrapper), messages may be caught at the wrong level or not propagated. Similarly, the `on_descendant_focus` handler in app.py walks the DOM tree manually to determine which pane has focus -- changing the widget hierarchy (adding/removing containers) breaks this traversal.

**Prevention:**
1. Do NOT change the widget composition (`compose()` method) during the Ports & Adapters refactoring. The widget tree should remain identical. Only the code behind it changes.
2. If you must change the hierarchy later, update `on_descendant_focus` and all message handlers in the same commit.
3. Message routing is tested by TUI pilot tests (test_tui.py, test_refresh.py). Run these after any structural change.

**Detection:** Footer hints stop updating, or cursor movement in one pane stops syncing to other panes.

**Phase guidance:** Explicitly out of scope for the service extraction phases. Note: the v1.4 "UI polish" work should NOT restructure the widget tree until after service extraction is complete.

---

### Pitfall 10: Circular Import Between Service and App Layers

**What goes wrong:** The current codebase uses lazy imports (`from joy.store import ...` inside method bodies) specifically to avoid import cycles. When you create a service layer (e.g., `joy.services.project_service`), it needs to import models from `joy.models`. If the service also needs types from `joy.app` (even just for type annotations), you get a circular import: `app -> service -> app`. Similarly, if widgets import the service Protocol from `joy.ports`, and the Protocol references types from `joy.models` that also reference widget types, you get a cycle.

**Prevention:**
1. **Strict layering:** `joy.models` imports nothing from `joy`. `joy.ports` imports only from `joy.models`. `joy.services` imports from `joy.ports` and `joy.models`. `joy.widgets` imports from `joy.ports` and `joy.models`. `joy.app` imports everything. No upward dependencies.
2. Protocols go in `joy.ports` (or a similar module), NOT in the same file as their implementation.
3. Use `TYPE_CHECKING` guards for any type annotations that would create import cycles:
   ```python
   from __future__ import annotations
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from joy.app import JoyApp
   ```
4. The existing lazy import pattern (`from joy.store import load_projects` inside method bodies) can be preserved in the thin app wrapper -- it is a valid Python pattern for breaking cycles.

**Detection:** `ImportError: cannot import name 'X' from partially initialized module 'joy.Y'` at startup.

**Phase guidance:** Establish the import hierarchy in Phase 1. Enforce it with a simple test that imports each layer independently.

---

## Minor Pitfalls

### Pitfall 11: Fake Adapters That Drift from Real Behavior

**What goes wrong:** You create `FakeProjectService` for tests. Over time, the real `ProjectService` gains edge-case handling (e.g., duplicate name checking, archival stripping of WORKTREE objects) that the fake does not replicate. Tests pass with the fake but fail in production.

**Prevention:**
1. Keep fakes minimal -- they should store and return data, not implement business logic. The business logic lives in the service, which is what you are testing.
2. For critical behaviors (like duplicate detection), write a shared contract test that runs against BOTH the real implementation and the fake.
3. Accept that fakes will drift slightly. This is fine for unit tests. Integration tests (Textual pilot) use the real service with a test TOML directory.

---

### Pitfall 12: Premature Extraction of Widget-Internal Logic

**What goes wrong:** You extract `_update_highlight`, `_update_badges`, or cursor management into a service. But these are purely widget concerns -- they manipulate CSS classes, scroll positions, and DOM nodes. Extracting them into a service that returns "set highlight to index 3" just adds indirection without enabling independent testing, because you still need a Textual pilot to verify the visual result.

**Prevention:**
1. Only extract logic that is testable WITHOUT Textual: data loading, relationship computation, persistence, cross-pane sync decisions (which pane to move, not how to move it).
2. Leave widget rendering, cursor management, highlight application, and scroll preservation on the widgets.
3. Rule of thumb: if the method calls `self.query_one()`, `self.add_class()`, `self.scroll_visible()`, or `self.post_message()`, it belongs on the widget.

---

### Pitfall 13: Over-Typing the Sync Direction Decision

**What goes wrong:** You create an elaborate type system for sync directions (project->worktree, worktree->project, terminal->project, etc.) with generic types and Union returns. The current implementation is 3 methods (`_sync_from_project`, `_sync_from_worktree`, `_sync_from_session`), each ~20 lines. Adding type-level modeling of sync directions makes the code harder to read without making it safer.

**Prevention:**
1. The PaneCoordinator should have 3 concrete methods matching the current 3 sync methods. No generics, no strategy pattern, no enum of directions.
2. The `_is_syncing` guard and `try/finally` pattern are the important things to preserve. The method structure is already clean.

---

### Pitfall 14: The `_PropContext` Pattern Implies Easy Extraction but Hides Coupling

**What goes wrong:** test_propagation.py already uses a `_PropContext` class that mimics JoyApp's interface for propagation methods. This makes it look like extracting `_propagate_mr_auto_add` into a standalone service is trivial. But the method mutates `project.objects` in-place AND checks `self._config.default_open_kinds`. When moved to a service, you must decide: does the service mutate projects, or does it return a list of mutations for the caller to apply? The current tests assume mutation. Changing to return-mutations breaks test assertions.

**Prevention:**
1. Decide the mutation strategy before extracting: either the service mutates (simpler, matches current behavior) or it returns deltas (purer, but requires rewriting 9 propagation tests).
2. Recommendation: keep mutation. The projects list is owned by the app and passed by reference. The service mutates it and returns notification messages. This matches the current behavior and minimizes test changes.
3. The service should receive `config.default_open_kinds` as a parameter, not `config` as a whole object. This makes the dependency explicit without creating a config port.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Facade methods on widgets | Pitfall 1 (hidden contracts) | grep all `._` cross-boundary access; convert one file at a time; full test run after each |
| PaneCoordinator extraction | Pitfall 3 (syncing guard ownership), Pitfall 5 (nested workers) | Guard stays on coordinator as context manager; no worker spawning inside coordinator |
| DataOrchestrator extraction | Pitfall 4 (worker lifecycle), Pitfall 5 (nested workers) | Orchestrator is sync; @work stays on App; orchestrator called from within worker body |
| ProjectService extraction | Pitfall 2 (session fixture), Pitfall 7 (dual test world), Pitfall 14 (mutation) | Update fixture in same commit; rewrite breaking tests immediately; keep mutation strategy |
| Protocol definition | Pitfall 6 (port explosion), Pitfall 10 (circular imports) | 3-4 coarse Protocols; strict layering; ports/ module imports only models |
| Test migration | Pitfall 7 (dual world), Pitfall 11 (fake drift) | Migrate in same commit as production change; shared contract tests for critical fakes |
| UI polish (separate from extraction) | Pitfall 9 (message routing), Pitfall 12 (premature extraction) | Do NOT change widget tree during extraction phases; save UI work for after services are stable |

---

## Sources

- Textual workers documentation: https://textual.textualize.io/guide/workers/
- Textual nested worker crash: https://github.com/Textualize/textual/issues/3472
- Textual call_from_thread discussion: https://github.com/Textualize/textual/discussions/1828
- Python Protocol spec: https://typing.python.org/en/latest/spec/protocol.html
- runtime_checkable limitations: https://discuss.python.org/t/is-there-a-downside-to-typing-runtime-checkable/20731
- isinstance on runtime_checkable side effects: https://github.com/python/cpython/issues/102433
- Hexagonal architecture pitfalls (2026): https://elpic.medium.com/hexagonal-architecture-in-the-real-world-trade-offs-pitfalls-and-when-not-to-use-it-1f304095f983
- Hexagonal architecture in Python: https://blog.szymonmiks.pl/p/hexagonal-architecture-in-python/
- pytest monkeypatch session scope: https://github.com/pytest-dev/pytest/issues/1872
- Mock.patch as code smell: http://mauveweb.co.uk/posts/2014/09/every-mock-patch-is-a-little-smell.html
- DI vs mocking in Python: https://betterprogramming.pub/testing-in-python-dependency-injection-vs-mocking-5e542783cb20
- Strangler fig for incremental migration: https://shopify.engineering/refactoring-legacy-code-strangler-fig-pattern
- Codebase analysis: grep of app.py, widgets/, tests/ in joy repo (28+ cross-boundary private-field access sites identified)
