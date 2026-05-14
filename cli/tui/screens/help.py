from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Markdown

HELP_TEXT = """# srt2web TUI — Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Start / Stop pipeline |
| `S` | Save configuration |
| `L` | Toggle log panel |
| `C` | Focus config panel |
| `O` | Focus outputs panel |
| `M` | Open module detail |
| `R` | Refresh status |
| `?` | Show this help |
| `Q` | Quit |
| `Esc` | Back / Close panel |
| `Tab` | Cycle through panels |
| `↑` / `↓` | Scroll content |

> On macOS: `Cmd+Q` also quits the TUI.

## One-shot Commands

```
srt2web-tui status          # Show pipeline status
srt2web-tui start           # Start pipeline
srt2web-tui stop            # Stop pipeline
srt2web-tui config          # Show full configuration
srt2web-tui config get <key>   # Get a config value
srt2web-tui config set <k> <v> # Set a config value
srt2web-tui logs -f         # Follow logs
srt2web-tui logs --level ERROR  # Filter logs
srt2web-tui health          # System health
srt2web-tui tui             # Launch this TUI
```

## Module States

| Indicator | Meaning |
|-----------|---------|
| `●` green | Running |
| `●` yellow | Starting / Stopping |
| `●` red | Error |
| `⚠` orange | Degraded |
| `○` dim | Idle / Stopped |
| `—` gray | Disabled |

Press `Q` or `Esc` to close.
"""


class HelpScreen(Screen):
    BINDINGS = [("escape", "dismiss"), ("q", "dismiss")]

    def compose(self) -> ComposeResult:
        yield Markdown(HELP_TEXT)
