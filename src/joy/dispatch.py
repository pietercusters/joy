"""Per-kind dispatch configuration for keystroke actions.

Each PresetKind declares exactly one behavior for each of the four states:
  exists_openable      — kind has a real value and can be opened
  exists_not_openable  — kind has a real value but it is copied, not opened
  missing_auto_create  — kind has no value; one can be created without user input
  missing_needs_input  — kind has no value; user must supply one

Only one of (exists_openable, exists_not_openable) should be True per kind.
Only one of (missing_auto_create, missing_needs_input) should be True per kind;
both may be False if missing is not actionable.

The action strings are method names on JoyApp (without "action_" prefix) that will
be called by the generic dispatcher. The dispatcher resolves which state applies and
calls the appropriate app method.
"""
from __future__ import annotations

from dataclasses import dataclass

from joy.models import PresetKind


@dataclass(frozen=True)
class KindConfig:
    """Dispatch contract for a single PresetKind."""

    exists_openable: bool       # True → call app._do_open_global(item)
    exists_not_openable: bool   # True → call app._copy_value_bg(value, kind)
    missing_auto_create: bool   # True → call app._auto_create_kind(kind, project)
    missing_needs_input: bool   # True → call app._prompt_for_kind(kind, project)
    missing_notify: str = ""    # toast when no value and no create/prompt action


# Table-driven dispatch: add/change a kind's behavior here only.
DISPATCH: dict[PresetKind, KindConfig] = {
    PresetKind.MR:        KindConfig(exists_openable=True,  exists_not_openable=False, missing_auto_create=False, missing_needs_input=True,  missing_notify=""),
    PresetKind.BRANCH:    KindConfig(exists_openable=False, exists_not_openable=True,  missing_auto_create=False, missing_needs_input=True,  missing_notify=""),
    PresetKind.TICKET:    KindConfig(exists_openable=True,  exists_not_openable=False, missing_auto_create=False, missing_needs_input=True,  missing_notify=""),
    PresetKind.NOTE:      KindConfig(exists_openable=True,  exists_not_openable=False, missing_auto_create=False, missing_needs_input=True,  missing_notify=""),
    PresetKind.THREAD:    KindConfig(exists_openable=True,  exists_not_openable=False, missing_auto_create=False, missing_needs_input=True,  missing_notify=""),
    PresetKind.FILE:      KindConfig(exists_openable=True,  exists_not_openable=False, missing_auto_create=False, missing_needs_input=True,  missing_notify=""),
    PresetKind.URL:       KindConfig(exists_openable=True,  exists_not_openable=False, missing_auto_create=False, missing_needs_input=True,  missing_notify=""),
    PresetKind.WORKTREE:  KindConfig(exists_openable=True,  exists_not_openable=False, missing_auto_create=False, missing_needs_input=False, missing_notify="No worktree found"),
    PresetKind.TERMINALS: KindConfig(exists_openable=True,  exists_not_openable=False, missing_auto_create=True,  missing_needs_input=False, missing_notify=""),
    PresetKind.REPO:      KindConfig(exists_openable=False, exists_not_openable=True,  missing_auto_create=False, missing_needs_input=False, missing_notify="No repo assigned \u2014 press R to assign one"),
}
