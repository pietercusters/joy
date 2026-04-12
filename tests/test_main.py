"""Unit tests for the joy CLI main() entry point."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock


def test_version_flag(capsys):
    """DIST-04: joy --version prints version and exits without TUI."""
    from joy.app import main
    with patch("sys.argv", ["joy", "--version"]):
        main()
    captured = capsys.readouterr()
    assert "joy" in captured.out
    # Version should be present (0.1.0 or whatever is installed)
    assert captured.out.strip().startswith("joy ")


def test_version_flag_unknown(capsys):
    """DIST-04: joy --version prints 'joy unknown' when package not found."""
    import importlib.metadata
    from joy.app import main
    with patch("sys.argv", ["joy", "--version"]), \
         patch("importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError("joy")):
        main()
    captured = capsys.readouterr()
    assert captured.out.strip() == "joy unknown"


def test_no_version_flag_launches_app():
    """DIST-04: Running joy without --version launches TUI."""
    with patch("sys.argv", ["joy"]), \
         patch("joy.app.JoyApp") as MockApp:
        mock_instance = MagicMock()
        MockApp.return_value = mock_instance
        from joy.app import main
        main()
        MockApp.assert_called_once()
        mock_instance.run.assert_called_once()
