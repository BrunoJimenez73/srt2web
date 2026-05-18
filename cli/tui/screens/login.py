from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Input, Label


class LoginScreen(Screen[Any]):
    def compose(self) -> ComposeResult:
        yield Label("Authentication Required", classes="title")
        yield Input(placeholder="Username", id="username")
        yield Input(placeholder="Password", password=True, id="password")
        yield Button("Login", variant="primary", id="login-btn")
        yield Button("Skip (read-only)", id="skip-btn")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login-btn":
            username = self.query_one("#username", Input).value
            password = self.query_one("#password", Input).value
            try:
                api = getattr(self.app, "api", None)
                if api is None:
                    self.notify("API client not available", severity="error")
                    return
                token = await api.login(username, password)
                if token:
                    api.token = token
                    ws = getattr(self.app, "ws", None)
                    if ws is not None:
                        ws.token = token
                    self.dismiss(True)
                else:
                    self.notify("Login failed", severity="error")
            except Exception as e:
                self.notify(f"Login error: {e}", severity="error")
        elif event.button.id == "skip-btn":
            self.dismiss(False)
