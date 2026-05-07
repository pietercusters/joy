"""Tests for joy.hooks module: setup_hooks(), hook script generation, settings.json merging."""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_home(tmp_path):
    """Patch Path.home() to return tmp_path for isolation."""
    with patch.object(Path, "home", return_value=tmp_path):
        yield tmp_path


# ---------------------------------------------------------------------------
# setup_hooks: script file creation
# ---------------------------------------------------------------------------


class TestSetupHooksScript:
    def test_setup_hooks_creates_script_file(self, fake_home):
        """setup_hooks() creates ~/.joy/bin/claude-state-hook.sh."""
        from joy.hooks import setup_hooks

        setup_hooks()
        script = fake_home / ".joy" / "bin" / "claude-state-hook.sh"
        assert script.exists(), f"Expected script at {script}"

    def test_setup_hooks_script_is_executable(self, fake_home):
        """The created script has executable permission (0o755)."""
        from joy.hooks import setup_hooks

        setup_hooks()
        script = fake_home / ".joy" / "bin" / "claude-state-hook.sh"
        mode = script.stat().st_mode
        assert mode & stat.S_IXUSR, "Script should be user-executable"
        assert mode & stat.S_IXGRP, "Script should be group-executable"
        assert mode & stat.S_IXOTH, "Script should be other-executable"

    def test_setup_hooks_script_content_contains_state_dir(self, fake_home):
        """The script content references the claude-states directory."""
        from joy.hooks import setup_hooks

        setup_hooks()
        script = fake_home / ".joy" / "bin" / "claude-state-hook.sh"
        content = script.read_text()
        assert "claude-states" in content

    def test_setup_hooks_script_content_has_shebang(self, fake_home):
        """The script starts with a bash shebang."""
        from joy.hooks import setup_hooks

        setup_hooks()
        script = fake_home / ".joy" / "bin" / "claude-state-hook.sh"
        content = script.read_text()
        assert content.startswith("#!/bin/bash"), f"Expected bash shebang, got: {content[:20]}"


# ---------------------------------------------------------------------------
# setup_hooks: settings.json merging
# ---------------------------------------------------------------------------


class TestSetupHooksSettings:
    def test_setup_hooks_merges_into_empty_settings(self, fake_home):
        """Fresh settings.json gets all 6 hook events."""
        from joy.hooks import HOOK_EVENTS, setup_hooks

        # Create empty settings.json
        settings_dir = fake_home / ".claude"
        settings_dir.mkdir(parents=True)
        settings_path = settings_dir / "settings.json"
        settings_path.write_text("{}")

        setup_hooks()

        data = json.loads(settings_path.read_text())
        assert "hooks" in data
        for event in HOOK_EVENTS:
            assert event in data["hooks"], f"Missing event: {event}"
            # Each event should have at least one matcher group with our hook
            groups = data["hooks"][event]
            assert isinstance(groups, list)
            assert len(groups) >= 1

    def test_setup_hooks_preserves_existing_hooks(self, fake_home):
        """Existing terminal-notifier hooks survive after setup_hooks()."""
        from joy.hooks import setup_hooks

        settings_dir = fake_home / ".claude"
        settings_dir.mkdir(parents=True)
        settings_path = settings_dir / "settings.json"
        existing = {
            "hooks": {
                "Stop": [
                    {
                        "matcher": "",
                        "hooks": [
                            {"type": "command", "command": "terminal-notifier -message \"Claude Code Finished\""}
                        ],
                    }
                ]
            }
        }
        settings_path.write_text(json.dumps(existing))

        setup_hooks()

        data = json.loads(settings_path.read_text())
        stop_hooks = data["hooks"]["Stop"]
        # Find the empty matcher group
        empty_group = next(g for g in stop_hooks if g["matcher"] == "")
        commands = [h["command"] for h in empty_group["hooks"]]
        assert any("terminal-notifier" in c for c in commands), (
            f"terminal-notifier hook lost after merge! Commands: {commands}"
        )

    def test_setup_hooks_idempotent(self, fake_home):
        """Running setup_hooks() twice produces identical settings.json."""
        from joy.hooks import setup_hooks

        settings_dir = fake_home / ".claude"
        settings_dir.mkdir(parents=True)
        (settings_dir / "settings.json").write_text("{}")

        setup_hooks()
        first = (settings_dir / "settings.json").read_text()

        setup_hooks()
        second = (settings_dir / "settings.json").read_text()

        assert first == second, "setup_hooks is not idempotent"

    def test_setup_hooks_creates_settings_if_missing(self, fake_home):
        """setup_hooks() creates ~/.claude/settings.json if it does not exist."""
        from joy.hooks import setup_hooks

        # Do NOT create ~/.claude dir -- setup_hooks should handle it
        setup_hooks()

        settings_path = fake_home / ".claude" / "settings.json"
        assert settings_path.exists(), "settings.json should be created if missing"

    def test_setup_hooks_creates_state_dir(self, fake_home):
        """setup_hooks() creates ~/.joy/claude-states/ directory."""
        from joy.hooks import setup_hooks

        setup_hooks()
        state_dir = fake_home / ".joy" / "claude-states"
        assert state_dir.is_dir(), f"Expected state dir at {state_dir}"


# ---------------------------------------------------------------------------
# HOOK_EVENTS constant
# ---------------------------------------------------------------------------


class TestHookEvents:
    def test_hook_events_has_six_entries(self):
        """HOOK_EVENTS contains exactly 6 event names."""
        from joy.hooks import HOOK_EVENTS

        assert len(HOOK_EVENTS) == 6

    def test_hook_events_contains_expected_names(self):
        """HOOK_EVENTS contains Stop, Notification, UserPromptSubmit, PreToolUse, SessionStart, SessionEnd."""
        from joy.hooks import HOOK_EVENTS

        expected = {"Stop", "Notification", "UserPromptSubmit", "PreToolUse", "SessionStart", "SessionEnd"}
        assert set(HOOK_EVENTS) == expected
