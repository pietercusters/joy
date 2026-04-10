# Feature Landscape

**Domain:** Developer project artifact manager (keyboard-driven TUI)
**Researched:** 2026-04-10

## Table Stakes

Features users expect from a keyboard-driven developer TUI. Missing any of these makes the tool feel broken or amateur.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Instant startup (<300ms) | Developers launch this tool dozens of times a day. Textual demo apps start in ~250ms. Anything over 500ms feels sluggish and kills adoption. | Med | Use lazy imports (PEP 810 pattern), minimize import chain. Profile with `python -X importtime`. |
| Visible keyboard shortcuts | Every successful TUI (lazygit, taskwarrior-tui, terminal.shop) shows available keys in the footer or inline. Memory should never be required. | Low | Footer bar showing context-sensitive shortcuts for current view. Update on focus change. |
| Consistent key vocabulary | Power users expect the same key to mean the same thing everywhere: `a`=add, `d`=delete, `e`=edit, `q`=quit/back, `/`=search/filter, `?`=help. | Low | Define once, use everywhere. Lazygit and taskwarrior-tui both follow this pattern. |
| vim-style navigation (j/k) | Standard expectation for terminal power users. Also support arrow keys for casual users. | Low | j=down, k=up. Arrow keys as aliases. No need for h/l in a two-pane layout since Tab/Shift-Tab switches panes. |
| Confirmation on destructive actions | "Delete project X?" with specific naming, not generic "Are you sure?". Focus on Cancel by default. | Low | Use sparingly -- only for delete project, not for removing a single object. Overuse kills flow. |
| Immediate visual feedback on actions | When user presses `o` to open something, show a brief confirmation ("Opened in browser", "Copied to clipboard") in the status bar. | Low | Ephemeral status message, auto-clears after 2-3 seconds. No modal interruption. |
| Escape always goes back | ESC is the universal "undo my navigation" key. Users should never feel trapped. | Low | ESC returns to previous view/focus. From top-level, ESC or q quits. |
| Persistent state | Projects and their objects survive between sessions. Data stored in `~/.joy/`. | Med | TOML or JSON file(s). Load on startup, save on mutation. |
| Search/filter on project list | With 10+ projects, scrolling is painful. `/` to filter by name is expected (fzf trained this muscle memory). | Med | Fuzzy or substring match. Real-time filtering as user types. |
| Clean two-pane layout with clear focus indicator | Lazygit pattern: panels always visible, focused panel has a highlighted border. User always knows where they are. | Low | Bright border on focused pane, dim border on unfocused. Textual's CSS makes this straightforward. |

## Differentiators

Features that make joy stand out from generic project tools or ad-hoc shell scripts. These are not expected but create delight and stickiness.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| "Open All" with `O` | One keystroke opens the entire project context: IDE on worktree, browser tabs for MR/tickets, iTerm2 window for agents. No other TUI does this. This is joy's killer feature. | Med | Open objects marked as "open by default" in display order. Small delay between opens to avoid race conditions with OS handlers. |
| Per-object type icons (Nerd Font) | Visual scanning is 10x faster with icons. A git branch icon, a browser icon, a note icon -- the eye finds what it needs before reading text. | Low | Nerd Font glyphs: branch=``, MR=``, ticket=``, note=``, file=``, worktree=``, URL=``, thread=``, agents=``. Graceful fallback to text labels if Nerd Fonts not installed. |
| Smart clipboard feedback | When copying a branch name, show what was copied in the status bar. Developer knows it worked without Cmd-V to verify. | Low | "Copied: feature/my-branch" in status bar for 3 seconds. |
| Spacebar toggle for "open by default" set | Visual indicator (filled/empty circle or checkbox) next to each object showing whether it's in the `O` set. Spacebar to toggle. Immediately visible, immediately actionable. | Low | Similar to taskwarrior-tui's mark/unmark with `v`. Visual state change should be instant. |
| Project-as-context philosophy | Not just a bookmark manager. Each project is a complete developer context: everything needed to resume work on a codebase in one keystroke. | -- | This is the framing, not a feature. But it drives what objects are offered and how `O` works. |
| Object ordering by drag or manual reorder | `O` opens in display order. Letting users reorder objects controls the activation sequence. | Med | `J`/`K` (shift+j/k) to move selected object up/down. Similar to lazygit's interactive rebase reordering. |
| Quick-add from clipboard | Detect URL or branch name in clipboard and pre-fill the type and value when adding a new object. | Med | Reduces friction for the most common workflow: copy URL from browser, switch to joy, press `a`, it's already there. |

## Anti-Features

Things to deliberately NOT build. Each would make joy worse, slower, or more confusing.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Mouse interaction | joy is keyboard-driven by design. Adding mouse support creates two interaction paradigms to maintain and test. It dilutes the keyboard-first identity. | Ignore mouse events entirely in v1. Textual supports disabling mouse. |
| Plugin/extension system | Adds massive complexity for a personal tool. The abstraction cost is high and the user base (one person) doesn't justify it. | Keep object types as a simple enum. Add new types by editing code directly. |
| Inline editing of object values | Combining list and edit in the same view is a known TUI anti-pattern (Jens Roemer). It creates ambiguity about whether keystrokes navigate or edit. | Open a separate edit overlay/modal. Clear mode distinction. |
| Hundreds of keybindings | Tig's ~100 keybindings are cited as a TUI anti-pattern. Users stop discovering features. Joy has a small, focused feature set. | Keep total keybindings under 25. Every key should be discoverable from the footer or `?` help. |
| Fancy animations and transitions | Gratuitous animation (sliding panels, fade effects) feels jarring in a terminal. Will Mcgugan (Textual creator) specifically warns against decorative animation. | Only use animation for genuinely useful feedback: smooth scrolling, brief highlight on state change. |
| Auto-sync or cloud features | Adds network dependency, latency, error states, auth flows. Completely unnecessary for local-first personal tooling. | Files live in `~/.joy/`. User can symlink or git-manage that directory if they want sync. |
| Multi-window or tabbed interface | More than two panes creates cognitive overhead. K9s and lazygit succeed with fixed, predictable layouts. | Stick to the two-pane layout. Use overlays/modals for create/edit forms. Return to the two-pane view after. |
| Undo/redo system | Complex to implement correctly for heterogeneous operations (OS calls, clipboard, file opens). The data mutations are simple enough that confirmation dialogs suffice. | Confirmation on delete. No undo needed for opens/copies (they're idempotent). |
| Configurable keybindings | Premature complexity. The default keybindings follow universal TUI conventions (vim-style, mnemonic letters). Customization adds config surface area for marginal benefit. | Ship opinionated defaults. Revisit only if multiple users request specific changes. |
| Rich project templates | Pre-configured project types ("Python project", "Go project") with default objects. Feels helpful but creates maintenance burden and assumes workflows. | One generic project type. User adds whatever objects they need. The pre-defined object types provide enough structure. |

## UX Patterns from Successful TUIs

### Navigation Conventions (adopted from lazygit, taskwarrior-tui, k9s)

| Key | Action | Source |
|-----|--------|--------|
| `j` / `Down` | Move selection down | Universal TUI standard |
| `k` / `Up` | Move selection up | Universal TUI standard |
| `g` | Jump to top of list | vim convention, taskwarrior-tui |
| `G` | Jump to bottom of list | vim convention, taskwarrior-tui |
| `Tab` / `Shift-Tab` | Switch focus between panes | lazygit uses number keys, but Tab is more discoverable for a two-pane layout |
| `Enter` | Activate / confirm / open detail | Universal |
| `Esc` | Go back / close overlay / cancel | Universal TUI convention |
| `q` | Quit application (from top level) | lazygit, k9s, taskwarrior-tui |
| `/` | Filter/search | fzf, lazygit, k9s, vim |
| `?` | Show help | lazygit, taskwarrior-tui |

### Action Conventions (mnemonic, consistent across views)

| Key | Action | Rationale |
|-----|--------|-----------|
| `o` | Open/activate selected object | "open" -- the primary action |
| `O` | Open all "default" objects | Shift variant = bulk action |
| `a` | Add new object/project | "add" -- Jens Roemer pattern, taskwarrior-tui |
| `e` | Edit selected item | "edit" |
| `d` / `Delete` | Delete selected item | "delete" -- taskwarrior-tui uses `x`, but `d` is more mnemonic |
| `Space` | Toggle "open by default" flag | Lazygit uses space for stage/unstage toggle |
| `J` / `K` | Reorder selected object up/down | Shift+movement = rearrange (lazygit rebase pattern) |

### Visual Patterns Worth Adopting

**Persistent layout, never rearranging.** Lazygit keeps all panels visible at all times. The layout never changes based on what you're doing. This creates spatial memory -- users learn where to look. Joy should keep the two-pane layout fixed; overlays for forms, never layout changes.

**Highlighted active panel border.** The focused pane gets a bright/colored border; unfocused panes get dim borders. This is how lazygit, k9s, and gitui all indicate focus. Textual CSS: `border: solid $accent;` vs `border: solid $surface;`.

**Footer key hints that change with context.** Show 5-8 most relevant keys for the current view in a footer bar. When focus moves to a different pane or an overlay opens, the footer updates. This is the single most important discoverability mechanism -- lazygit and taskwarrior-tui both do this.

**Inline status messages instead of modals.** When an action completes ("Copied to clipboard", "Opened in PyCharm"), show a brief message in the footer/status area. It disappears after 2-3 seconds. Never interrupt workflow with a modal for non-destructive confirmations.

**Icons as type indicators, not decoration.** Each object type gets one icon, displayed consistently in the same position (left of the object name). Icons serve as scannable type markers, not visual flair. Use Nerd Font glyphs with ASCII fallback.

**Dimmed secondary information.** Object values (URLs, paths) should be dimmer than object names/types. This creates visual hierarchy: type + name pops, value is available but doesn't compete for attention.

**Selected item highlight.** The currently selected item gets a distinct background color (not just a cursor character). This is standard in all modern TUIs and Textual provides it out of the box with ListView/DataTable.

### Performance Patterns

**Lazy imports for fast startup.** PEP 810 pattern: only import Textual and heavy dependencies when actually needed. Can cut startup from 200ms to 50ms. Profile with `python -X importtime`.

**Batch OS operations in `O` (open all).** When opening multiple objects, introduce a small delay (50-100ms) between subprocess calls. macOS URL handlers and AppleScript can choke on rapid-fire invocations. Sequential with micro-delays feels instant to the user but is reliable.

**Immutable data objects for caching.** Will Mcgugan recommends frozen dataclasses and NamedTuples for TUI state. They're hashable (cacheable), thread-safe, and easier to reason about.

## Feature Dependencies

```
Core TUI Layout --> Project List --> Project Detail Pane
Project Detail Pane --> Object Display (with types & icons)
Object Display --> Object Activation (`o` single, `O` all)
Object Activation --> Type-specific handlers (clipboard, browser, editor, iTerm2, etc.)
Project CRUD --> Persistent Storage (~/.joy/ data files)
Persistent Storage --> Settings Screen (global config)
"Open by default" toggle --> `O` bulk open feature
Object Reordering --> `O` respects display order
Search/Filter --> Project list grows beyond ~5 items
```

## MVP Recommendation

Prioritize in this order:

1. **Two-pane layout with navigation** -- the shell of the app; without this nothing else works
2. **Persistent storage (create/read projects and objects)** -- data must survive restarts
3. **Object activation (`o`)** -- the core value proposition: open things with one key
4. **"Open All" (`O`)** -- the killer differentiator; ship it in MVP, not as a follow-up
5. **Footer key hints** -- discoverability makes or breaks first-time experience
6. **Search/filter on project list** -- becomes critical as soon as there are 5+ projects

Defer:
- **Settings screen**: Use a config file directly for v1. A TUI settings screen is nice-to-have.
- **Object reordering (J/K)**: Useful but not blocking. Default order (creation order) works initially.
- **Quick-add from clipboard**: Delightful but can be added after core loop is solid.
- **Nerd Font icon fallback detection**: Ship with Nerd Font icons, document the font requirement. Fallback is a polish item.

## Sources

- Jens Roemer, "TUI Design" (2025): https://jensroemer.com/writing/tui-design/
- Lazygit UX analysis: https://www.bwplotka.dev/2025/lazygit/
- Will Mcgugan, "7 Things I've Learned Building a Modern TUI Framework": https://www.textualize.io/blog/7-things-ive-learned-building-a-modern-tui-framework/
- Taskwarrior-TUI keybindings: https://kdheepak.com/taskwarrior-tui/keybindings/
- ThePrimeagen tmux-sessionizer (project switching workflow): https://github.com/ThePrimeagen/tmux-sessionizer
- Nerd Fonts (icon set): https://www.nerdfonts.com/
- PEP 810 lazy imports: https://peps.python.org/pep-0810/
- Textual themes and CSS: https://textual.textualize.io/guide/design/
- Hugo van Kemenade lazy imports benchmark (3x startup improvement): https://hugovk.dev/blog/2025/lazy-imports/
