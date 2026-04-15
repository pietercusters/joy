# Quick Task 260415-qqx: iTerm2 Python API Research

**Researched:** 2026-04-15
**Domain:** iterm2 Python package — session create, rename, close
**Confidence:** HIGH (verified from installed package source at `.venv/lib/python3.14/site-packages/iterm2/`)

---

## Package Version

`iterm2 2.15` — installed at `.venv/lib/python3.14/site-packages/iterm2/` [VERIFIED: `_version.py`]

---

## 1. Create Session

### Method

`Window.async_create_tab()` is the correct call. [VERIFIED: `window.py:303`]

```python
tab = await window.async_create_tab(
    profile=None,    # None = default profile
    command=None,    # None = profile default shell
    index=None,      # None = append at end
)
```

`tab` is an `iterm2.Tab` or `None` (if session closed immediately).

### Getting the session from the tab

`tab.sessions` returns a list of `Session` objects (split panes). A freshly created tab has exactly one session.

```python
session = tab.sessions[0]  # safe for a fresh tab with no splits
```

Alternatively: `tab.current_session` returns the active session in the tab (same object for a single-pane tab).

### Setting the name after creation

Use `session.async_set_name(name)`. [VERIFIED: `session.py:871`]

```python
await session.async_set_name("my-session-name")
```

This calls `iterm2.set_name` via the RPC layer — equivalent to editing the session name in "Edit Session" in iTerm2. This sets the persistent tab title.

**Do NOT use** `session.async_set_variable("user.name", name)` for this purpose — `async_set_variable` is for user-defined custom variables (must begin with `"user."`), not for the session display name.

### Getting the front window

`app.current_window` returns the frontmost terminal window (`app.current_terminal_window` is a deprecated alias for the same property). [VERIFIED: `app.py:436,447`]

```python
window = app.current_window   # preferred
# window = app.current_terminal_window  # deprecated alias, still works
```

### Full create_session pattern

```python
async def _create(connection):
    nonlocal result
    app = await iterm2.async_get_app(connection)
    window = app.current_window
    if window is None:
        return  # iTerm2 has no open windows — caller handles None
    tab = await window.async_create_tab()
    if tab is None:
        return
    session = tab.sessions[0]
    await session.async_set_name(name)
    result = session.session_id
```

---

## 2. Rename Session

### Method

`session.async_set_name(new_name)` — same method used after creation. [VERIFIED: `session.py:871`]

```python
async def _rename(connection):
    nonlocal success
    app = await iterm2.async_get_app(connection)
    session = app.get_session_by_id(session_id)
    if session:
        await session.async_set_name(new_name)
        success = True
```

### What `session.name` is

`session.name` is populated from `session.title` in the protobuf, which is the tab title as shown in the iTerm2 UI. [VERIFIED: `session.py:240,244`] This is what `async_set_name` modifies.

---

## 3. Close Session

### Method

`session.async_close(force=False)` [VERIFIED: `session.py:710`]

- `force=False` — graceful close; iTerm2 will prompt the user if the session has a running process (standard "close" behavior).
- `force=True` — skips the confirmation prompt; kills immediately.

```python
await session.async_close(force=False)   # graceful
await session.async_close(force=True)    # force kill
```

### Exceptions

Raises `iterm2.rpc.RPCException` when the status code is not `OK`. The exception message is the string name of the status enum (e.g. `"INVALID_SESSION"`, `"REQUEST_MALFORMED"`). [VERIFIED: `session.py:723`]

There is no separate "busy/refused to close" exception type — any non-OK response becomes an `RPCException` with a string description. Wrap the graceful call in try/except and fall through to force-close on failure.

### Full close_session pattern

```python
async def _close(connection):
    nonlocal success
    app = await iterm2.async_get_app(connection)
    session = app.get_session_by_id(session_id)
    if session is None:
        return  # session already gone — treat as success
    await session.async_close(force=force)
    success = True
```

---

## 4. Wrapper Functions for terminal_sessions.py

All three follow the same established pattern from `activate_session`: lazy imports, `Connection().run_until_complete(..., retry=False)`, catch-all except, return bool (or str for create).

### create_session(name) -> str | None

```python
def create_session(name: str) -> str | None:
    """Create a new iTerm2 tab in the front window and set its name.

    Returns the new session_id on success, or None on failure.
    """
    import iterm2
    from iterm2.connection import Connection

    result: str | None = None

    async def _create(connection):
        nonlocal result
        app = await iterm2.async_get_app(connection)
        window = app.current_window
        if window is None:
            return
        tab = await window.async_create_tab()
        if tab is None:
            return
        session = tab.sessions[0]
        await session.async_set_name(name)
        result = session.session_id

    try:
        Connection().run_until_complete(_create, retry=False)
    except Exception:
        pass
    return result
```

### rename_session(session_id, new_name) -> bool

```python
def rename_session(session_id: str, new_name: str) -> bool:
    import iterm2
    from iterm2.connection import Connection

    success = False

    async def _rename(connection):
        nonlocal success
        app = await iterm2.async_get_app(connection)
        session = app.get_session_by_id(session_id)
        if session:
            await session.async_set_name(new_name)
            success = True

    try:
        Connection().run_until_complete(_rename, retry=False)
    except Exception:
        pass
    return success
```

### close_session(session_id, force=False) -> bool

```python
def close_session(session_id: str, force: bool = False) -> bool:
    import iterm2
    from iterm2.connection import Connection

    success = False

    async def _close(connection):
        nonlocal success
        app = await iterm2.async_get_app(connection)
        session = app.get_session_by_id(session_id)
        if session is None:
            success = True  # already gone
            return
        await session.async_close(force=force)
        success = True

    try:
        Connection().run_until_complete(_close, retry=False)
    except Exception:
        pass
    return success
```

---

## 5. Key API Facts Summary

| Question | Answer | Source |
|----------|--------|--------|
| Create tab in front window | `app.current_window.async_create_tab()` | `window.py:303` |
| Get session from new tab | `tab.sessions[0]` or `tab.current_session` | `tab.py:111,151` |
| Set session name | `session.async_set_name(name)` | `session.py:871` |
| Rename existing session | same: `session.async_set_name(new_name)` | `session.py:871` |
| Close graceful | `session.async_close(force=False)` | `session.py:710` |
| Close force | `session.async_close(force=True)` | `session.py:710` |
| Exception type | `iterm2.rpc.RPCException` | `rpc.py:16` |
| `current_terminal_window` | deprecated alias for `current_window` | `app.py:447` |
| `async_set_variable("user.name", ...)` | NOT for session title — user custom vars only | `session.py:643` |
| Package version | 2.15 | `_version.py` |

---

## Sources

- [VERIFIED] `/Users/pieter/Github/joy/.venv/lib/python3.14/site-packages/iterm2/session.py` — `async_set_name`, `async_close`, `async_set_variable`
- [VERIFIED] `/Users/pieter/Github/joy/.venv/lib/python3.14/site-packages/iterm2/window.py` — `async_create_tab`
- [VERIFIED] `/Users/pieter/Github/joy/.venv/lib/python3.14/site-packages/iterm2/app.py` — `current_window`, `current_terminal_window`
- [VERIFIED] `/Users/pieter/Github/joy/.venv/lib/python3.14/site-packages/iterm2/tab.py` — `sessions`, `current_session`
- [VERIFIED] `/Users/pieter/Github/joy/.venv/lib/python3.14/site-packages/iterm2/_version.py` — version 2.15
