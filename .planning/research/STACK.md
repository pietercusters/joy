# Technology Stack: v1.4 Additions

**Project:** joy v1.4 Frontend Refactor & UI Polish
**Researched:** 2026-05-07
**Scope:** Only NEW stack additions/changes for Ports & Adapters refactoring and three-layer test strategy. Existing stack (Textual 8.x, tomllib/tomli_w, subprocess, hatchling) is validated and unchanged.

## Recommended Stack Additions

### Testing: pytest-textual-snapshot (for snapshot layer)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pytest-textual-snapshot | 1.1.0 | Visual regression testing for Textual apps | Official Textualize plugin. Provides `snap_compare` fixture that takes SVG screenshots of running apps and diffs them across runs. Built on syrupy for snapshot storage. Catches visual regressions that unit and widget tests miss entirely. |
| syrupy | 4.8.0 (transitive) | Snapshot storage/comparison engine | Pulled in by pytest-textual-snapshot (hard-pinned to ==4.8.0). Zero external dependencies. Provides the assertion framework for SVG comparison. |
| jinja2 | >=3.0.0 (transitive) | HTML snapshot report rendering | Pulled in by pytest-textual-snapshot for generating visual diff reports. |

**Installation note:** Adding pytest-textual-snapshot will downgrade pytest from 9.0.3 to 8.4.2 due to syrupy 4.8.0's upper bound. Verified via `uv pip install --dry-run` that this resolves cleanly on Python 3.14.2 with no conflicts against pytest-asyncio 1.3.0 or other existing deps.

**Confidence:** HIGH -- verified resolution on exact Python 3.14.2 / Textual 8.2.3 / pytest-asyncio 1.3.0 environment.

**Snapshot test example (from official docs):**
```python
def test_joy_initial_layout(snap_compare):
    app = JoyApp()
    assert snap_compare(app, terminal_size=(120, 40))

def test_joy_after_navigation(snap_compare):
    async def run_before(pilot):
        await pilot.press("j", "j", "enter")
    assert snap_compare(JoyApp(), run_before=run_before)
```

### Architecture: typing.Protocol (stdlib -- no new dependency)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| typing.Protocol | stdlib (3.8+) | Port contracts for Ports & Adapters | Structural subtyping ("duck typing for type checkers"). Classes satisfy a Protocol by having matching methods -- no inheritance required. Perfect for defining service boundaries where the TUI layer depends on abstract ports, not concrete implementations. |

**No new dependency.** Protocol is part of the `typing` stdlib module. Already available on the project's Python >=3.11 target (and running on 3.14.2).

**Why Protocol over ABC:**

| Criterion | Protocol | ABC |
|-----------|----------|-----|
| Coupling | Zero -- no inheritance needed | Tight -- must inherit from ABC |
| Third-party compat | Any class with matching methods works | Must explicitly subclass |
| Test doubles | Plain classes/dataclasses just work | Must subclass the ABC |
| Runtime enforcement | Optional via @runtime_checkable (avoid) | Yes, via abstractmethod |
| Type checker support | mypy, pyright, basedpyright | mypy, pyright |
| Pythonic for this use case | Yes -- structural contracts at system edges | Better for shared implementation hierarchies |

**Recommendation: Use Protocol exclusively.** Joy's ports are system-edge contracts (storage, terminal sessions, worktree discovery, MR fetching). No shared implementation to inherit. Protocol keeps test doubles trivial -- a plain class or dataclass that has the right methods satisfies the contract without any import or inheritance.

**Do NOT use @runtime_checkable.** isinstance() checks against Protocols are slow (especially pre-3.12), check only method presence (not signatures), and can trigger side effects on properties. Joy doesn't need runtime Protocol checks -- static type checking (mypy/pyright) catches mismatches at development time. The extra overhead buys nothing for a single-user TUI.

**Confidence:** HIGH -- Protocol is stdlib, well-documented in PEP 544, mypy docs, and typing spec. Patterns verified against multiple authoritative sources.

**Protocol pattern for joy's ports:**
```python
from typing import Protocol

class ProjectStore(Protocol):
    """Port: project persistence operations."""
    def load_projects(self) -> list[Project]: ...
    def save_projects(self, projects: list[Project]) -> None: ...
    def load_config(self) -> Config: ...
    def save_config(self, config: Config) -> None: ...
    def load_repos(self) -> list[Repo]: ...

class WorktreeDiscovery(Protocol):
    """Port: worktree scanning."""
    def discover_worktrees(self, repos: list[Repo], branch_filter: list[str]) -> list[WorktreeInfo]: ...

class TerminalProvider(Protocol):
    """Port: terminal session enumeration."""
    async def list_sessions(self) -> list[TerminalSession]: ...

class MRProvider(Protocol):
    """Port: MR/CI data fetching."""
    def fetch_mr_data(self, repos: list[Repo], worktrees: list[WorktreeInfo]) -> BatchMRResult: ...
```

### Dependency Injection: Manual Constructor Injection (no framework)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Manual constructor injection | N/A (pattern) | Wire Protocol implementations into services | Joy has ~4-5 ports and ~3 service objects. A DI framework (dependency-injector, injector) adds import-time overhead, learning curve, and magic for a problem that doesn't exist at this scale. Constructor parameters with Protocol type hints are sufficient and transparent. |

**Why NOT use a DI framework:**
- Joy has 4-5 ports total (store, worktree, terminal, MR, maybe opener). This is trivially wired by hand.
- DI frameworks (dependency-injector at 4.49.0, injector at 0.22) add 200-500ms import time -- directly impacting the "snappy startup" constraint.
- Constructor injection is explicit, debuggable, and grep-able. No container magic.
- Every major Python architecture guide recommends manual DI for small-medium apps, graduating to frameworks only when the dependency graph becomes complex.

**Wiring pattern for joy:**
```python
# In app.py (composition root)
class JoyApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Wire real implementations
        store = TomlProjectStore()         # implements ProjectStore protocol
        wt_discovery = GitWorktreeDiscovery()  # implements WorktreeDiscovery protocol
        self._coordinator = PaneCoordinator(store=store, worktrees=wt_discovery, ...)
        self._data_orchestrator = DataOrchestrator(store=store, ...)

# In tests (fake implementations)
class FakeProjectStore:
    """Test double -- satisfies ProjectStore protocol without any inheritance."""
    def __init__(self, projects=None, config=None):
        self.projects = projects or []
        self.config = config or Config()
    def load_projects(self) -> list[Project]:
        return self.projects
    def save_projects(self, projects):
        self.projects = projects
    # ... etc
```

**Confidence:** HIGH -- standard Python DI pattern. No framework needed at this scale.

### Refactoring Tools: None Required (IDE-assisted manual refactoring)

| Technology | Status | Why Not |
|------------|--------|---------|
| rope 1.14.0 | NOT RECOMMENDED | Only classifiers through Python 3.12 (resolves on 3.14 but untested). Extract/move operations are useful but PyCharm/VS Code refactoring tools provide the same functionality interactively with undo support. Adding a dev dependency for one-time refactoring work is unnecessary overhead. |
| libcst | NOT RECOMMENDED | Powerful CST-based code transformation, but designed for automated codemods across large codebases. Joy's refactoring is a one-time manual decomposition of ~1,058 LOC. Interactive IDE refactoring is faster and safer for this scope. |
| bowler (Facebook) | NOT RECOMMENDED | Built on deprecated lib2to3. Inactive development. Not suitable for Python 3.14. |

**Recommendation: Use IDE refactoring tools (Extract Method, Move to Module, Rename) for the manual decomposition.** The v1.4 refactoring is a one-time architectural change, not an ongoing automated codemod pipeline. IDE tools provide immediate feedback, undo, and preview -- all more valuable than scriptable but opaque code transformations.

**Confidence:** HIGH -- rope's Python 3.14 support is unverified; IDE refactoring is the standard approach for this scope of work.

## What NOT to Add

| Library | Why Skip |
|---------|----------|
| dependency-injector / injector | Overkill for 4-5 ports. Adds import overhead. Manual constructor injection is sufficient. |
| attrs | dataclasses (stdlib) already handle all model needs. attrs adds dependency for zero benefit. |
| pydantic | Runtime validation overkill for trusted TOML data. Would add 500ms+ import time. |
| pytest-mock | unittest.mock (stdlib) already works. pytest-mock's mocker fixture is a convenience wrapper with no functional advantage for joy's test patterns. |
| rope / libcst / bowler | One-time refactoring; IDE tools are better for this. |
| mypy / pyright (as deps) | Type checkers run in dev environment, not as package dependencies. Install separately via `uv tool install mypy` or use IDE integration. |
| abc (ABC/abstractmethod) | Protocol is strictly better for joy's use case (no inheritance needed, test doubles are simpler). |

## Updated Dev Dependencies

```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.25",
    "pytest-textual-snapshot>=1.1.0",
]
```

**Changes from current:**
- `pytest>=9.0.3` relaxed to `pytest>=8.0` to accommodate syrupy 4.8.0's upper bound (pytest-textual-snapshot hard-pins syrupy==4.8.0 which caps pytest at <9.1). In practice, uv resolves to pytest 8.4.2.
- Added `pytest-textual-snapshot>=1.1.0` for the snapshot testing layer.
- pytest-asyncio>=0.25 unchanged.

**Runtime dependencies unchanged:**
```toml
dependencies = [
    "tomli-w>=1.0",
    "textual>=8.2",
    "iterm2>=2.15",
]
```

## Three-Layer Test Strategy: Stack Requirements

| Layer | What It Tests | Stack Needed | Speed |
|-------|--------------|-------------|-------|
| **Backend service tests** | PaneCoordinator, DataOrchestrator, ProjectService as pure Python (no TUI) | pytest + fake Protocol implementations (plain classes) | Fast (<1ms each) |
| **Widget tests** | Individual widgets with Textual pilot, fake backend injected | pytest + pytest-asyncio + `app.run_test()` pilot | Medium (100-500ms each) |
| **Snapshot tests** | Full app visual regression | pytest + pytest-textual-snapshot + `snap_compare` fixture | Slow (1-3s each, sparingly) |

**Backend tests (bulk of new tests):** Test extracted services with fake implementations of Protocol ports. No Textual import needed. These should be synchronous (not async) where possible since the services themselves are pure Python. Example: test that PaneCoordinator computes correct sync targets given fake worktree and session lists.

**Widget tests (existing pattern):** Already using `app.run_test()` pilot pattern in test_tui.py. The change is injecting fake backends into the app before calling run_test, rather than patching store functions.

**Snapshot tests (new, use sparingly):** Guard against unintended visual regressions during the refactoring. Establish baseline snapshots before refactoring, verify they don't change after. Use `pytest.mark.slow` marker (already configured in pyproject.toml) so they don't run by default.

**pytest marker configuration (already in place, extend):**
```toml
[tool.pytest.ini_options]
markers = [
    "macos_integration: tests requiring live macOS apps (iTerm2, Notion, etc.)",
    "slow: tests using Textual pilot or snapshot tests -- run with -m slow",
    "snapshot: visual regression snapshot tests -- run with --snapshot-update to regenerate",
]
```

## Protocol Best Practices for Python 3.11+ (joy's minimum)

### Pattern 1: Keep Protocols Narrow
One Protocol per port responsibility. Don't create a god-Protocol with 20 methods. Joy's natural boundaries: store, worktree discovery, terminal provider, MR provider, opener.

### Pattern 2: Protocols in a Dedicated Module
Create `src/joy/ports.py` (or `src/joy/ports/` package if it grows). All Protocol definitions live here. Both production adapters and test fakes import from this single location.

### Pattern 3: No @runtime_checkable
Skip `@runtime_checkable` entirely. It adds no value when type checking catches violations. Performance overhead on isinstance() is measurable and unnecessary.

### Pattern 4: Use Simple Return Types
Protocol methods should return plain dataclasses/dicts, not framework-specific types. This ensures backend tests don't import Textual.

### Pattern 5: Async Protocols Where Needed
Terminal session fetching is inherently async (iTerm2 Python API). Define the Protocol method as async:
```python
class TerminalProvider(Protocol):
    async def list_sessions(self) -> list[TerminalSession]: ...
```
The fake in tests can still be a simple class with an async method returning a fixed list.

### Pattern 6: Optional Protocol Members via Default Arguments
If a port method has optional behavior, use default arguments in the Protocol definition:
```python
class ProjectStore(Protocol):
    def load_projects(self, *, path: Path | None = None) -> list[Project]: ...
```

## Confidence Assessment

| Decision | Confidence | Reasoning |
|----------|------------|-----------|
| pytest-textual-snapshot 1.1.0 | HIGH | Official Textualize plugin, verified resolution on Python 3.14.2, verified compatible with Textual 8.2.3 and pytest-asyncio 1.3.0 |
| Protocol (stdlib) for ports | HIGH | PEP 544, mypy docs, typing spec all confirm. Standard practice for Python hexagonal architecture. |
| Manual constructor injection | HIGH | Universal recommendation for small apps. No credible source recommends DI frameworks at this scale. |
| No refactoring tools as deps | HIGH | One-time refactoring, IDE tools superior for interactive work |
| Skip @runtime_checkable | HIGH | CPython docs, typing spec, and python/cpython#102936 all document performance and correctness issues |
| Pytest downgrade to 8.4.2 | MEDIUM | Functional but means pinning below pytest 9.x. Risk: if a future pytest-asyncio version requires pytest >=9. Mitigation: monitor pytest-textual-snapshot for syrupy pin relaxation. |

## Sources

- pytest-textual-snapshot PyPI: https://pypi.org/project/pytest-textual-snapshot/
- pytest-textual-snapshot GitHub: https://github.com/Textualize/pytest-textual-snapshot
- pytest-textual-snapshot README (Context7): snap_compare fixture API, terminal_size, run_before, press parameters
- syrupy PyPI: https://pypi.org/project/syrupy/ (5.1.0 latest, but pytest-textual-snapshot pins 4.8.0)
- Textual testing guide: https://textual.textualize.io/guide/testing/
- Textual testing guide (Context7): run_test() API, Pilot.press(), Pilot.click()
- PEP 544 -- Protocols: https://peps.python.org/pep-0544/
- typing.Protocol spec: https://typing.python.org/en/latest/spec/protocol.html
- mypy Protocol docs: https://mypy.readthedocs.io/en/stable/protocols.html
- runtime_checkable discussion: https://discuss.python.org/t/is-there-a-downside-to-typing-runtime-checkable/20731
- CPython runtime_checkable issue: https://github.com/python/cpython/issues/102936
- Python DI patterns: https://www.glukhov.org/post/2025/12/dependency-injection-in-python/
- Hexagonal Architecture in Python: https://blog.szymonmiks.pl/p/hexagonal-architecture-in-python/
- rope PyPI: https://pypi.org/project/rope/ (1.14.0, classifiers through Python 3.12 only)
- libcst docs: https://libcst.readthedocs.io/en/latest/index.html
- ABC vs Protocol comparison: https://jellis18.github.io/post/2022-01-11-abc-vs-protocol/
