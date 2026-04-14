---
date: "2026-04-14 00:00"
promoted: false
---

Phase 12 / TerminalPane: Claude idle vs active detection is unsolved. Current approach (foreground_process not in _SHELL_PROCESSES → busy) doesn't work — Claude is always running as a process whether it's asking for user input or actively executing an agent task. The distinction is application-level state, not detectable from ps/jobName alone. Need a different signal: e.g. iTerm2 badge text set by Claude, a socket/file that Claude writes to indicate state, CPU usage sampling, or iTerm2 "current command" variable if Claude updates the tab title differently when busy. Defer to a future session.
