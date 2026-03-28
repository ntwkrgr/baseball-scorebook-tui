"""Lineup editor screen — pre-game entry of both teams' starting lineups.

The user fills in away team first (name, 9 players with number and position),
then presses Continue to move on to the home team.  After both lineups are
accepted the GameScreen is pushed.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static

from baseball_scorebook.models.constants import Position
from baseball_scorebook.models.team import LineupSlot, Player, Team

# (label, value) tuples consumed by Select widgets.
_POSITION_CHOICES: list[tuple[str, str]] = [
    (p.display, p.value) for p in Position
]

_SLOT_COUNT = 9


class LineupEditorScreen(Screen):
    """Pre-game lineup entry: away team first, then home team."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
    ]

    DEFAULT_CSS = """
    LineupEditorScreen {
        layout: vertical;
    }

    #team-label {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin: 1;
        width: 100%;
    }

    #team-name-row {
        height: auto;
        align: center middle;
        margin-bottom: 1;
    }

    #team-name-input {
        width: 30;
    }

    .lineup-grid {
        grid-size: 4;
        grid-columns: 4 20 8 12;
        grid-rows: auto;
        padding: 0 2;
        height: auto;
    }

    .lineup-grid Label {
        padding: 0 1;
    }

    .lineup-grid Input {
        width: 100%;
    }

    #button-row {
        height: auto;
        align: center middle;
        margin: 1;
    }

    Button {
        margin: 0 2;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._editing_away = True
        self._away_team: Team | None = None

    def compose(self) -> ComposeResult:
        yield Header()

        label_text = self._current_team_label()
        yield Static(label_text, id="team-label")

        with Horizontal(id="team-name-row"):
            yield Label("Team Name: ")
            yield Input(placeholder="Team name", id="team-name-input")

        with Grid(classes="lineup-grid"):
            yield Label("#", classes="header")
            yield Label("Player Name", classes="header")
            yield Label("Number", classes="header")
            yield Label("Position", classes="header")

            for i in range(1, _SLOT_COUNT + 1):
                yield Label(str(i))
                yield Input(placeholder=f"Player {i} name", id=f"name-{i}")
                # select_on_focus=False: avoid full selection after Tab — otherwise
                # each digit replaces the previous instead of appending.
                yield Input(
                    placeholder="#",
                    id=f"number-{i}",
                    type="integer",
                    select_on_focus=False,
                )
                yield Select(
                    _POSITION_CHOICES,
                    id=f"pos-{i}",
                    prompt="Pos",
                )

        with Horizontal(id="button-row"):
            yield Button("Continue", variant="primary", id="continue-btn")
            yield Button("Cancel", variant="default", id="cancel-btn")

        yield Footer()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.app.pop_screen()
        elif event.button.id == "continue-btn":
            self._handle_continue()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_go_back(self) -> None:
        if not self._editing_away:
            self._editing_away = True
            self._clear_fields()
            self.query_one("#team-label", Static).update(
                self._current_team_label()
            )
        else:
            self.app.pop_screen()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _current_team_label(self) -> str:
        return "Enter Away Team Lineup" if self._editing_away else "Enter Home Team Lineup"

    def _handle_continue(self) -> None:
        team = self._build_team()
        if team is None:
            self.notify("Please fill in all fields", severity="warning")
            return

        if self._editing_away:
            self._away_team = team
            self._editing_away = False
            self._clear_fields()
            self.query_one("#team-label", Static).update(
                self._current_team_label()
            )
        else:
            self._start_game(home_team=team)

    def _build_team(self) -> Team | None:
        """Read form fields and return a Team, or None if any field is invalid."""
        team_name = self.query_one("#team-name-input", Input).value.strip()
        if not team_name:
            return None

        slots: list[LineupSlot] = []
        for i in range(1, _SLOT_COUNT + 1):
            name_val = self.query_one(f"#name-{i}", Input).value.strip()
            if not name_val:
                return None

            number_raw = self.query_one(f"#number-{i}", Input).value.strip()
            try:
                number = int(number_raw) if number_raw else 0
            except ValueError:
                number = 0

            pos_select = self.query_one(f"#pos-{i}", Select)
            pos_val = pos_select.value
            if pos_val is Select.BLANK:
                return None

            position = Position(str(pos_val))
            player = Player(name=name_val, number=number, position=position)
            slots.append(
                LineupSlot(
                    batting_order=i,
                    player=player,
                    position=position,
                    entered_inning=1,
                )
            )

        return Team(name=team_name, lineup=tuple(slots))

    def _clear_fields(self) -> None:
        """Reset all form fields to empty / blank."""
        self.query_one("#team-name-input", Input).value = ""
        for i in range(1, _SLOT_COUNT + 1):
            self.query_one(f"#name-{i}", Input).value = ""
            self.query_one(f"#number-{i}", Input).value = ""
            self.query_one(f"#pos-{i}", Select).value = Select.BLANK

    def _start_game(self, home_team: Team) -> None:
        """Replace this screen with GameScreen (do not pop then push).

        ``pop_screen`` schedules async teardown; an immediate ``push_screen``
        can overlap that work and race Header composition (crash on mount).
        ``switch_screen`` performs one atomic replace of the stack top.
        """
        from baseball_scorebook.screens.game import GameScreen

        away_team = self._away_team
        self.app.switch_screen(
            GameScreen(away_team=away_team, home_team=home_team)
        )
