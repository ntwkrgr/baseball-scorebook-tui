"""Home screen — first screen shown on launch.

Users can start a new game or load a previously saved one.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Center, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static


class HomeScreen(Screen):
    """Home screen — start new game or load an existing game."""

    BINDINGS = [
        ("n", "new_game", "New Game"),
        ("l", "load_game", "Load Game"),
        ("q", "quit", "Quit"),
    ]

    DEFAULT_CSS = """
    HomeScreen {
        align: center middle;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 2;
        width: 100%;
    }

    #subtitle {
        text-align: center;
        color: $text-muted;
        margin-bottom: 2;
        width: 100%;
    }

    #button-container {
        width: auto;
        height: auto;
        align: center middle;
    }

    Button {
        margin: 1 2;
        min-width: 20;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Center():
            with Vertical(id="main-container"):
                yield Static("Baseball Scorebook", id="title")
                yield Static("A terminal-based baseball scorebook", id="subtitle")
                with Horizontal(id="button-container"):
                    yield Button("New Game", variant="primary", id="new-game")
                    yield Button("Load Game", variant="default", id="load-game")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new-game":
            self.action_new_game()
        elif event.button.id == "load-game":
            self.action_load_game()

    def action_new_game(self) -> None:
        from baseball_scorebook.screens.lineup_editor import LineupEditorScreen

        self.app.push_screen(LineupEditorScreen())

    def action_load_game(self) -> None:
        """Open the load game dialog."""
        from baseball_scorebook.screens.load_game import LoadGameModal

        self.app.push_screen(LoadGameModal())

    def action_quit(self) -> None:
        self.app.exit()
