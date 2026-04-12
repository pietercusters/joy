# joy

Keyboard-driven Python TUI for managing coding project artifacts. See all your branches, MRs, tickets, worktrees, notes, and more for the active project -- and open any of them with a single keystroke.

## Installation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv tool install git+https://github.com/pietercusters/joy
```

After installation, `joy` is available globally on your PATH.

Verify the installation:

```bash
joy --version
```

## First-Run Setup

On first launch, joy creates `~/.joy/` with two files:

- `~/.joy/config.toml` -- global settings (IDE, editor, Obsidian vault path, terminal, default open kinds)
- `~/.joy/projects.toml` -- your project data

Edit `~/.joy/config.toml` to configure your tools, or press `s` inside joy to open the Settings screen:

```toml
ide = "PyCharm"
editor = "Sublime Text"
obsidian_vault = ""
terminal = "iTerm2"
default_open_kinds = ["worktree", "agents"]
```

| Setting | Used By | Example Values |
|---------|---------|----------------|
| `ide` | Worktree objects (opens path in IDE) | "PyCharm", "VSCode", "Cursor" |
| `editor` | File objects (opens file in editor) | "Sublime Text", "vim", "code" |
| `obsidian_vault` | Note objects (opens in Obsidian) | "/Users/you/vault" |
| `terminal` | Agents objects (creates/focuses terminal window) | "iTerm2" |
| `default_open_kinds` | Pre-marks these types as "open by default" on new projects | Any combination of preset kinds |

## Usage

Launch the TUI:

```bash
joy
```

### Layout

Two-pane interface: project list on the left, object detail on the right.

### Key Bindings

#### Global (any pane)

| Key | Action |
|-----|--------|
| `q` | Quit |
| `O` | Open all default objects for current project |
| `n` | Create new project |
| `s` | Open settings |

#### Project List (left pane)

| Key | Action |
|-----|--------|
| `j` / `k` / Up / Down | Navigate projects |
| `Enter` | Select project (focus detail pane) |
| `D` / `Delete` | Delete project |
| `/` | Filter projects by name |

#### Detail Pane (right pane)

| Key | Action |
|-----|--------|
| `j` / `k` / Up / Down | Navigate objects |
| `o` | Open highlighted object |
| `Space` | Toggle "open by default" |
| `a` | Add new object |
| `e` | Edit highlighted object |
| `d` | Delete highlighted object |
| `Escape` | Return to project list |

### Object Types

Each object has a preset kind that determines its activation behavior:

| Preset | Action | Example |
|--------|--------|---------|
| `mr` | Opens URL in browser | GitLab/GitHub merge request URL |
| `branch` | Copies to clipboard | `feature/my-branch` |
| `ticket` | Opens in Notion desktop app | Notion page URL |
| `thread` | Opens in Slack desktop app | Slack thread URL |
| `file` | Opens in configured editor | `/path/to/file.py` |
| `note` | Opens in Obsidian | `my-note.md` |
| `worktree` | Opens in configured IDE | `/path/to/worktree` |
| `agents` | Creates/focuses terminal window | `my-project-agents` |
| `url` | Opens URL in browser | Any URL |

## Platform

macOS only. Relies on:
- `open` command for URL schemes
- `pbcopy` for clipboard
- `osascript` for iTerm2 integration
- Obsidian, Notion, and Slack desktop apps for deep linking

## License

MIT
