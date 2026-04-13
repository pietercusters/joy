---
phase: 06-models-config-store
reviewed: 2026-04-13T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/joy/models.py
  - tests/test_models.py
  - src/joy/store.py
  - tests/test_store.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-04-13
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed the pure data models (`models.py`), the TOML persistence layer (`store.py`), and both test files. The overall design is solid: atomic writes, graceful handling of missing files, and good separation between the model layer and I/O layer. Two bugs were found in `store.py` — a `KeyError` crash on malformed TOML and a missing `stacklevel` argument on a `warnings.warn` call — plus a maintainability issue with duplicated default values. Two minor info-level items in the test file round out the findings.

## Warnings

### WR-01: KeyError crash when TOML object entry is missing `value` field

**File:** `src/joy/store.py:62`
**Issue:** In `_toml_to_projects`, the `kind` field is validated with a `try/except ValueError` that emits a warning and skips the object on failure (lines 53-59). However the `value` field at line 62 is accessed via `obj["value"]` with no guard. If a TOML entry for an object is missing the `value` key (malformed file, hand-edited config, future schema evolution), this raises an uncaught `KeyError` from inside `load_projects`, crashing the entire load rather than skipping the bad object. The pattern established for `kind` should be applied consistently.

**Fix:**
```python
# Replace lines 60-68 with:
try:
    value = obj["value"]
except KeyError:
    warnings.warn(
        f"Object in project {name!r} is missing required 'value' field — skipping object",
        UserWarning,
        stacklevel=2,
    )
    continue
objects.append(
    ObjectItem(
        kind=kind,
        value=value,
        label=obj.get("label", ""),
        open_by_default=obj.get("open_by_default", False),
    )
)
```

### WR-02: Missing `stacklevel` in `warnings.warn` for unparseable date

**File:** `src/joy/store.py:78`
**Issue:** The `warnings.warn` call for an unparseable `created` date (lines 77-80) omits the `stacklevel` argument. The other `warnings.warn` call in the same function (line 55) correctly passes `stacklevel=2`. Without `stacklevel=2`, the warning points to the internal line inside `_toml_to_projects` instead of the public caller (`load_projects`), making it harder for users to locate the source of the warning.

**Fix:**
```python
warnings.warn(
    f"Cannot parse created date {created_raw!r} for project {name!r}, using today",
    UserWarning,
    stacklevel=2,  # add this
)
```

### WR-03: Default values duplicated between `Config` dataclass and `load_config`

**File:** `src/joy/store.py:109-117`
**Issue:** `load_config` hardcodes fallback default values in every `data.get(...)` call (e.g., `data.get("ide", "PyCharm")`, `data.get("refresh_interval", 30)`). These duplicate the defaults already declared on the `Config` dataclass (lines 92-102 of `models.py`). If a default is changed in `Config`, the `load_config` fallback silently stays out of sync, causing old config files missing that field to receive stale defaults.

**Fix:** Construct a `Config()` to get the defaults, then override only the fields present in the TOML:
```python
def load_config(*, path: Path = CONFIG_PATH) -> Config:
    """Load config from TOML file. Returns default Config if file missing."""
    if not path.exists():
        return Config()
    with open(path, "rb") as f:
        data = tomllib.load(f)
    defaults = Config()
    return Config(
        ide=data.get("ide", defaults.ide),
        editor=data.get("editor", defaults.editor),
        obsidian_vault=data.get("obsidian_vault", defaults.obsidian_vault),
        terminal=data.get("terminal", defaults.terminal),
        default_open_kinds=data.get("default_open_kinds", defaults.default_open_kinds),
        refresh_interval=data.get("refresh_interval", defaults.refresh_interval),
        branch_filter=data.get("branch_filter", defaults.branch_filter),
    )
```

## Info

### IN-01: Misleading test name for `detect_forge` boundary case

**File:** `tests/test_models.py:375`
**Issue:** `test_no_dot_com_substring` — the URL used in the test (`"https://notgithub.example.com/repo"`) actually does contain `.com` as a substring; the intent is to test that `github.com` is not present as a substring. The test logic is correct but the name misrepresents what boundary it exercises.

**Fix:** Rename to `test_non_github_non_gitlab_host` or `test_github_com_not_in_url` to accurately describe what is being asserted.

### IN-02: `Project.to_dict()` docstring says "TOML-compatible" but `created` is a `date` object, not a string

**File:** `src/joy/models.py:80-85`
**Issue:** `Project.to_dict()` returns `created` as a `datetime.date` object (not a string). This is correct for `tomli_w` (which supports TOML date literals) and round-trips cleanly, but the method is described as returning a "TOML-compatible dict." If the dict is ever passed to a JSON serializer or compared to a dict with a string `created` field, it will silently fail. The docstring is technically fine for the current usage but could mislead future callers.

**Fix:** Either note in the docstring that `created` is a `date` object (not a string), or convert it: `"created": self.created.isoformat()`. The latter is a more universally compatible representation — `tomllib` handles ISO 8601 date strings just as well as native date objects when loaded from TOML files.

---

_Reviewed: 2026-04-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
