"""Tests for Protocol contracts (Phase 18, CNTR-01, CNTR-02).

All tests are pure Python -- no TUI, no I/O, no mocking needed.
Validates Protocol classes exist with correct signatures and
@runtime_checkable isinstance() checks pass for structural conformance.
"""
from __future__ import annotations

from joy.ports import GitDataPort, OpenerPort, StoragePort, SyncablePane, TerminalPort


# ---------------------------------------------------------------------------
# Test 1: StoragePort structural conformance (CNTR-01)
# ---------------------------------------------------------------------------


def test_storage_port_structural_conformance():
    """A class with matching methods satisfies StoragePort via isinstance."""

    class FakeStorage:
        def load_projects(self): return []
        def save_projects(self, projects): pass
        def load_config(self): return None
        def save_config(self, config): pass
        def load_repos(self): return []
        def save_repos(self, repos): pass
        def load_archived_projects(self): return []
        def save_archived_projects(self, projects): pass

    assert isinstance(FakeStorage(), StoragePort)


def test_storage_port_rejects_incomplete():
    """A class missing methods does NOT satisfy StoragePort."""

    class Incomplete:
        def load_projects(self): return []

    assert not isinstance(Incomplete(), StoragePort)


# ---------------------------------------------------------------------------
# Test 2: GitDataPort structural conformance (CNTR-01)
# ---------------------------------------------------------------------------


def test_git_data_port_structural_conformance():
    """A class with discover_worktrees satisfies GitDataPort."""

    class FakeGitData:
        def discover_worktrees(self, repos, branch_filter): return []

    assert isinstance(FakeGitData(), GitDataPort)


# ---------------------------------------------------------------------------
# Test 3: TerminalPort structural conformance (CNTR-01)
# ---------------------------------------------------------------------------


def test_terminal_port_structural_conformance():
    """A class with all terminal methods satisfies TerminalPort."""

    class FakeTerminal:
        def fetch_sessions(self): return None
        def create_tab(self, name): return None
        def activate_session(self, session_id): return True
        def close_session(self, session_id, *, force=False): return True
        def close_tab(self, tab_id, *, force=False): return True
        def create_session(self, name): return None
        def rename_session(self, session_id, new_name): return True

    assert isinstance(FakeTerminal(), TerminalPort)


# ---------------------------------------------------------------------------
# Test 4: OpenerPort structural conformance (CNTR-01)
# ---------------------------------------------------------------------------


def test_opener_port_structural_conformance():
    """A class with open_object satisfies OpenerPort."""

    class FakeOpener:
        def open_object(self, *, item, config): pass

    assert isinstance(FakeOpener(), OpenerPort)


# ---------------------------------------------------------------------------
# Test 5: SyncablePane structural conformance (CNTR-02)
# ---------------------------------------------------------------------------


def test_syncable_pane_structural_conformance():
    """A class with sync_to and clear_selection satisfies SyncablePane."""

    class FakePane:
        def sync_to(self, *args): return True
        def clear_selection(self): pass

    assert isinstance(FakePane(), SyncablePane)


def test_syncable_pane_rejects_missing_clear():
    """A class with only sync_to does NOT satisfy SyncablePane."""

    class IncompletePane:
        def sync_to(self, *args): return True

    assert not isinstance(IncompletePane(), SyncablePane)


# ---------------------------------------------------------------------------
# Test 6: Protocol classes are importable (CNTR-01 smoke test)
# ---------------------------------------------------------------------------


def test_all_protocols_importable():
    """All 5 Protocol classes can be imported from joy.ports."""
    from joy.ports import StoragePort, GitDataPort, TerminalPort, OpenerPort, SyncablePane

    for cls in (StoragePort, GitDataPort, TerminalPort, OpenerPort, SyncablePane):
        assert hasattr(cls, '__protocol_attrs__') or hasattr(cls, '_is_protocol'), (
            f"{cls.__name__} should be a Protocol class"
        )


# ---------------------------------------------------------------------------
# Test 7: ARCH-01 enforcement -- no widget imports ports
# ---------------------------------------------------------------------------


def test_arch01_no_widget_imports_ports():
    """No widget module imports from joy.ports (ARCH-01 invariant)."""
    import importlib
    import inspect

    widget_modules = [
        "joy.widgets.project_detail",
        "joy.widgets.project_list",
        "joy.widgets.worktree_pane",
        "joy.widgets.terminal_pane",
        "joy.widgets.mr_pane",
    ]
    for mod_name in widget_modules:
        mod = importlib.import_module(mod_name)
        source = inspect.getsource(mod)
        assert "from joy.ports" not in source, f"{mod_name} imports from joy.ports (ARCH-01 violation)"
        assert "import joy.ports" not in source, f"{mod_name} imports joy.ports (ARCH-01 violation)"
