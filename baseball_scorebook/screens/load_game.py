"""Load game modal — lets users pick a previously saved game file.

Lists all ``.json`` files in the default save directory, sorted newest first.
Selecting an entry and pressing Open reconstructs the game and navigates to
the GameScreen.
"""
from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView, Static


class LoadGameModal(ModalScreen):
    """Modal dialog for loading a saved game."""

    DEFAULT_CSS = """
    LoadGameModal {
        align: center middle;
    }

    #load-dialog {
        width: 60;
        height: 20;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }

    #load-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        width: 100%;
    }

    ListView {
        height: 1fr;
        margin-bottom: 1;
    }

    #load-buttons {
        height: auto;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="load-dialog"):
            yield Static("Load a Saved Game", id="load-title")
            yield ListView(id="game-list")
            with Horizontal(id="load-buttons"):
                yield Button("Open", variant="primary", id="open-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_mount(self) -> None:
        self._populate_game_list()

    def _populate_game_list(self) -> None:
        from baseball_scorebook.storage.serializer import get_default_save_dir

        save_dir = get_default_save_dir()
        game_list = self.query_one("#game-list", ListView)
        game_files = sorted(save_dir.glob("*.json"), reverse=True)

        if not game_files:
            game_list.append(ListItem(Label("No saved games found")))
            return

        for f in game_files:
            item = ListItem(Label(f.stem))
            item.name = str(f)
            game_list.append(item)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.app.pop_screen()
        elif event.button.id == "open-btn":
            self._open_highlighted()

    def _open_highlighted(self) -> None:
        game_list = self.query_one("#game-list", ListView)
        highlighted = game_list.highlighted_child

        if highlighted is None or not highlighted.name:
            self.notify("Select a game to open", severity="warning")
            return

        self._load_selected(Path(highlighted.name))

    def _load_selected(self, path: Path) -> None:
        from baseball_scorebook.storage.serializer import load_game

        try:
            data = load_game(path)
        except Exception as exc:
            self.notify(f"Error loading game: {exc}", severity="error")
            return

        self.app.pop_screen()

        from baseball_scorebook.screens.game import GameScreen

        self.app.push_screen(
            GameScreen(
                away_team=data["away_team"],
                home_team=data["home_team"],
                store=data["store"],
            )
        )
