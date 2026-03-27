"""Scorecard widget — full team scorecard grid of lineup rows."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label

from baseball_scorebook.models.at_bat import DiamondState
from baseball_scorebook.models.team import Team
from baseball_scorebook.widgets.lineup_row import LineupRowWidget


class ScorecardWidget(Widget):
    """Full team scorecard grid: up to 9 lineup rows × dynamic inning columns.

    Shows the batting lineup with diamond cells for each at-bat.  Rows are
    keyed by batting_order (1-9).  Inning columns grow dynamically as
    add_at_bat() is called.
    """

    DEFAULT_CSS = """
    ScorecardWidget {
        height: 100%;
        width: 100%;
        overflow-y: auto;
        overflow-x: auto;
    }

    ScorecardWidget > .team-header {
        height: 1;
        width: 100%;
        background: $primary-darken-2;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }
    """

    def __init__(self, team: Team | None = None, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.team = team
        # batting_order (1-9) → LineupRowWidget
        self._rows: dict[int, LineupRowWidget] = {}

    def compose(self) -> ComposeResult:
        """Yield the header label then one row per lineup slot."""
        team_name = self.team.name if self.team else "Team"
        yield Label(team_name, classes="team-header")

        if self.team is None:
            return

        for slot in self.team.lineup:
            row = LineupRowWidget(
                batting_order=slot.batting_order,
                player_name=slot.player.name,
                player_number=slot.player.number,
                position=slot.position.display,
                id=f"row-order-{slot.batting_order}",
            )
            self._rows[slot.batting_order] = row
            yield row

    def _ensure_row(self, batting_order: int) -> LineupRowWidget:
        """Return the row for batting_order, creating it if needed."""
        if batting_order in self._rows:
            return self._rows[batting_order]

        row = LineupRowWidget(
            batting_order=batting_order,
            player_name="Unknown",
            player_number=0,
            position="?",
            id=f"row-order-{batting_order}",
        )
        self._rows[batting_order] = row
        self.mount(row)
        return row

    def add_at_bat(
        self,
        batting_order: int,
        inning: int,
        state: DiamondState | None = None,
    ) -> None:
        """Add or update the diamond cell for a specific batter and inning."""
        row = self._ensure_row(batting_order)
        row.add_diamond(inning, state)

    def update_at_bat(
        self,
        batting_order: int,
        inning: int,
        state: DiamondState | None,
    ) -> None:
        """Update an existing diamond cell's state."""
        if batting_order in self._rows:
            self._rows[batting_order].update_diamond(inning, state)

    def update_team(self, team: Team) -> None:
        """Swap in a new team, rebuilding all rows.

        Existing diamond states are lost; callers should re-populate
        at-bats after calling this method.
        """
        self.team = team
        self._rows.clear()
        self.remove_children()
        # Re-compose is triggered by Textual's reactive machinery when
        # remove_children + mount sequence is used.
        team_name = team.name
        self.mount(Label(team_name, classes="team-header"))
        for slot in team.lineup:
            row = LineupRowWidget(
                batting_order=slot.batting_order,
                player_name=slot.player.name,
                player_number=slot.player.number,
                position=slot.position.display,
                id=f"row-order-{slot.batting_order}",
            )
            self._rows[slot.batting_order] = row
            self.mount(row)
