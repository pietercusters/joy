"""Unit tests for the LegendModal screen."""
from __future__ import annotations

from joy.screens.legend import LegendModal


def test_legend_modal_has_l_dismiss_binding():
    """LegendModal BINDINGS contain 'l' mapped to a dismiss action."""
    bindings = LegendModal.BINDINGS
    keys = [b[0] if isinstance(b, tuple) else b.key for b in bindings]
    assert "l" in keys


def test_legend_modal_has_escape_dismiss_binding():
    """LegendModal BINDINGS contain 'escape' mapped to a dismiss action."""
    bindings = LegendModal.BINDINGS
    keys = [b[0] if isinstance(b, tuple) else b.key for b in bindings]
    assert "escape" in keys
