"""Main Textual App class and screen routing."""

from textual.app import App


class BaseballScorebookApp(App):
    """Baseball Scorebook TUI application."""

    TITLE = "Baseball Scorebook"

    def on_mount(self) -> None:
        """Push the home screen on startup."""
        from baseball_scorebook.screens.home import HomeScreen
        self.push_screen(HomeScreen())
