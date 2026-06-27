"""Shared constants for the CLI/TUI package."""

# Pipeline state → Rich style color mapping.
# Used by header, status_bar, module_grid, and status command.
# Keep in sync: any new pipeline state must appear here.
STATE_STYLE: dict[str, str] = {
    "running": "green",
    "starting": "yellow",
    "stopping": "yellow",
    "stopped": "white",
    "error": "red",
    "idle": "dim white",
    "processing": "green",
    "initializing": "blue",
    "degraded": "orange1",
    "disabled": "dim",
}
