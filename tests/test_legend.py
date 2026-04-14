"""Unit tests for LegendModal — icon legend popup for all panes."""
from __future__ import annotations

from textual.screen import ModalScreen


def test_legend_modal_importable_from_joy_screens():
    """LegendModal is importable from joy.screens."""
    from joy.screens import LegendModal
    assert LegendModal is not None


def test_legend_modal_is_modal_screen_subclass():
    """LegendModal is a subclass of ModalScreen."""
    from joy.screens.legend import LegendModal
    assert issubclass(LegendModal, ModalScreen)


def test_legend_modal_has_escape_and_l_bindings():
    """LegendModal has bindings for 'escape' and 'l' that both dismiss the modal."""
    from joy.screens.legend import LegendModal
    # BINDINGS can be tuples or Binding objects — extract key from either
    binding_keys = set()
    for b in LegendModal.BINDINGS:
        if isinstance(b, tuple):
            binding_keys.add(b[0])
        else:
            binding_keys.add(b.key)
    assert "escape" in binding_keys
    assert "l" in binding_keys


def test_legend_modal_build_legend_content():
    """LegendModal._build_legend_content() returns a non-empty list of Static widgets."""
    from joy.screens.legend import LegendModal
    modal = LegendModal()
    content = modal._build_legend_content()
    assert len(content) > 0


def test_legend_modal_contains_detail_icons():
    """Legend content contains representative Detail pane icons (PRESET_ICONS values)."""
    from joy.screens.legend import LegendModal

    modal = LegendModal()
    all_text = _collect_text_from_statics(modal._build_legend_content())

    # Check that key detail icons appear
    assert "\ue725" in all_text  # MR
    assert "\ue0a0" in all_text  # Branch
    assert "\uf0ac" in all_text  # URL


def test_legend_modal_contains_worktree_icons():
    """Legend content contains worktree pane icons."""
    from joy.screens.legend import LegendModal

    modal = LegendModal()
    all_text = _collect_text_from_statics(modal._build_legend_content())

    assert "\uf111" in all_text  # ICON_DIRTY
    assert "\uea64" in all_text  # ICON_MR_OPEN
    assert "\uf00c" in all_text  # ICON_CI_PASS
    assert "\uf00d" in all_text  # ICON_CI_FAIL
    assert "\uf192" in all_text  # ICON_CI_PENDING


def test_legend_modal_contains_terminal_icons():
    """Legend content contains terminal pane icons."""
    from joy.screens.legend import LegendModal

    modal = LegendModal()
    all_text = _collect_text_from_statics(modal._build_legend_content())

    assert "\U000f1325" in all_text  # ICON_CLAUDE
    assert "\u25cf" in all_text      # INDICATOR_BUSY
    assert "\u25cb" in all_text      # INDICATOR_WAITING


def _collect_text_from_statics(widgets) -> str:
    """Collect text content from a list of Static widgets."""
    parts = []
    for widget in widgets:
        content = getattr(widget, '_Static__content', '')
        if hasattr(content, 'plain'):
            parts.append(content.plain)
        else:
            parts.append(str(content))
    return "".join(parts)
