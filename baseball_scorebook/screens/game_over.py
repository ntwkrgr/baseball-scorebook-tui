"""
game_over.py — Final game summary screen with save options.

Displays the final score, winner, and per-team R/H/E totals.
Offers buttons to save the game, start a new game, or quit.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Center, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from baseball_scorebook.engine.event_store import EventStore
from baseball_scorebook.engine.state import derive_state
from baseball_scorebook.models.constants import HalfCode
from baseball_scorebook.models.team import Team
from baseball_scorebook.storage.serializer import (
    generate_filename,
    get_default_save_dir,
    save_game,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AWAY_HALF = HalfCode.TOP     # away team bats in the top half
_HOME_HALF = HalfCode.BOTTOM  # home team bats in the bottom half


def _sum_stat(inning_stats: dict, half: HalfCode, attr: str) -> int:
    """Sum one stat field across all half-innings matching *half*.

    Args:
        inning_stats: The ``GameState.inning_stats`` dict keyed by
            ``(inning_number, HalfCode)``.
        half: The half to aggregate (TOP for away batting stats,
            BOTTOM for home batting stats).
        attr: Attribute name on ``InningStats`` (e.g. ``"hits"``).

    Returns:
        Integer total across all matching half-inning entries.
    """
    return sum(
        getattr(stats, attr)
        for (_, h), stats in inning_stats.items()
        if h == half
    )


# ---------------------------------------------------------------------------
# Screen
# ---------------------------------------------------------------------------


class GameOverScreen(Screen):
    """Final game summary screen with save options."""

    BINDINGS = [
        ("s", "save", "Save"),
        ("q", "quit", "Quit"),
    ]

    DEFAULT_CSS = """
    GameOverScreen {
        align: center middle;
    }

    #game-over-container {
        width: 60;
        height: auto;
        border: double $accent;
        padding: 2 4;
        background: $surface;
    }

    #game-over-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        width: 100%;
    }

    #final-score {
        text-align: center;
        text-style: bold;
        margin: 1 0;
        width: 100%;
    }

    #winner-text {
        text-align: center;
        text-style: italic;
        margin-bottom: 1;
        width: 100%;
    }

    #game-summary {
        margin: 1 0;
        width: 100%;
    }

    #button-row {
        height: auto;
        align: center middle;
        margin-top: 2;
    }

    Button {
        margin: 0 2;
    }
    """

    def __init__(
        self,
        away_team: Team | None = None,
        home_team: Team | None = None,
        store: EventStore | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._away_team = away_team
        self._home_team = home_team
        self._store = store if store is not None else EventStore()

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()

        state = derive_state(self._store)
        away_name = self._away_team.name if self._away_team else "Away"
        home_name = self._home_team.name if self._home_team else "Home"

        winner_text = _determine_winner(away_name, home_name, state)
        summary = _build_summary(away_name, home_name, state)

        with Center():
            with Vertical(id="game-over-container"):
                yield Static("Game Over", id="game-over-title")
                yield Static(
                    f"{away_name} {state.away_score}  —  {home_name} {state.home_score}",
                    id="final-score",
                )
                yield Static(winner_text, id="winner-text")
                yield Static(summary, id="game-summary")
                with Horizontal(id="button-row"):
                    yield Button("Save Game", variant="primary", id="save-btn")
                    yield Button("New Game", variant="default", id="new-btn")
                    yield Button("Quit", variant="error", id="quit-btn")

        yield Footer()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self.action_save()
        elif event.button.id == "new-btn":
            self._go_to_new_game()
        elif event.button.id == "quit-btn":
            self.action_quit()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_save(self) -> None:
        """Save the game to the default save directory."""
        away_name = self._away_team.name if self._away_team else "Away"
        home_name = self._home_team.name if self._home_team else "Home"

        save_dir = get_default_save_dir()
        filename = generate_filename(away_name, home_name, date="")
        path = save_dir / filename

        if self._away_team is None or self._home_team is None:
            self.notify("Cannot save: team data is missing.", severity="error")
            return

        save_game(
            path,
            self._away_team,
            self._home_team,
            self._store,
            completed=True,
        )
        self.notify(f"Game saved to {path}", severity="information")

    def action_quit(self) -> None:
        """Exit the application."""
        self.app.exit()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _go_to_new_game(self) -> None:
        """Pop this screen and navigate to the home screen."""
        self.app.pop_screen()
        from baseball_scorebook.screens.home import HomeScreen  # noqa: PLC0415

        self.app.push_screen(HomeScreen())


# ---------------------------------------------------------------------------
# Pure helpers (module-level, easily testable)
# ---------------------------------------------------------------------------


def _determine_winner(away_name: str, home_name: str, state) -> str:
    """Return a human-readable winner string given the final scores.

    Args:
        away_name: Display name for the away team.
        home_name: Display name for the home team.
        state: Derived ``GameState`` with ``away_score`` and ``home_score``.

    Returns:
        A string such as ``"Away Win!"``, ``"Home Win!"``, or
        ``"Tied Game"``.
    """
    if state.away_score > state.home_score:
        return f"{away_name} Win!"
    if state.home_score > state.away_score:
        return f"{home_name} Win!"
    return "Tied Game"


def _build_summary(away_name: str, home_name: str, state) -> str:
    """Build the R/H/E summary lines for both teams.

    Hits are credited to the batting team (away bats TOP, home bats
    BOTTOM).  Errors are charged to the *fielding* team, so errors
    recorded in the TOP half (while away bats) are home-team errors,
    and errors in the BOTTOM half are away-team errors.

    Args:
        away_name: Display name for the away team.
        home_name: Display name for the home team.
        state: Derived ``GameState`` with ``inning_stats``.

    Returns:
        A two-line string with R/H/E totals for each team.
    """
    inning_stats = state.inning_stats

    away_hits = _sum_stat(inning_stats, _AWAY_HALF, "hits")
    home_hits = _sum_stat(inning_stats, _HOME_HALF, "hits")

    # Errors committed by the away team occur while home team bats (BOTTOM).
    # Errors committed by the home team occur while away team bats (TOP).
    away_errors = _sum_stat(inning_stats, _HOME_HALF, "errors")
    home_errors = _sum_stat(inning_stats, _AWAY_HALF, "errors")

    away_line = f"{away_name}: {state.away_score}R  {away_hits}H  {away_errors}E"
    home_line = f"{home_name}: {state.home_score}R  {home_hits}H  {home_errors}E"
    return f"\n{away_line}\n{home_line}"
