"""Centralized Nerd Font icon constants shared across joy widgets."""

# MR/CI status icons (migrated from worktree_pane.py)
ICON_MR_OPEN    = "\uea64"   # nf-cod-git_pull_request
ICON_MR_DRAFT   = "\uebdb"   # nf-cod-git_pull_request_draft
ICON_MR_CLOSED  = "\uea65"   # nf-cod-git_pull_request_closed
ICON_CI_PASS    = "\uf00c"   # nf-fa-check
ICON_CI_FAIL    = "\uf00d"   # nf-fa-times
ICON_CI_PENDING = "\uf192"   # nf-fa-dot_circle_o

# Review status icons (MR pane)
ICON_REVIEW_APPROVED  = "\uf00c"   # reuse check mark (same as CI_PASS)
ICON_REVIEW_CHANGES   = "\uf12a"   # nf-fa-exclamation
ICON_REVIEW_PENDING   = "\uf192"   # reuse dot circle (same as CI_PENDING)

# Branch/worktree status icons (migrated from worktree_pane.py)
ICON_BRANCH      = "\ue0a0"        # nf-pl-branch
ICON_DIRTY       = "\uf111"        # nf-fa-circle
ICON_NO_UPSTREAM = "\U000f0be1"    # nf-md-cloud_off

# Object-presence ribbon icons (sourced from PRESET_ICONS in object_row.py)
ICON_TICKET   = "\uf0ea"   # nf-fa-clipboard
ICON_THREAD   = "\uf086"   # nf-fa-comment
ICON_NOTE     = "\uf040"   # nf-fa-pencil
ICON_WORKTREE = "\uf07b"   # nf-fa-folder
ICON_TERMINAL = "\uf120"   # nf-fa-terminal
