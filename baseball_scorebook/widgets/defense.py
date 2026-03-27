"""Defense widget — 9-position defensive alignment for a team."""

from __future__ import annotations

from rich.table import Table
from rich.text import Text
from textual.widget import Widget

from baseball_scorebook.models.constants import Position
from baseball_scorebook.models.team import LineupSlot, Team

# Canonical defensive position ordering for display.
_POSITION_ORDER: tuple[Position, ...] = (
    Position.P,
    Position.C,
    Position.FIRST_BASE,
    Position.SECOND_BASE,
    Position.THIRD_BASE,
    Position.SS,
    Position.LF,
    Position.CF,
    Position.RF,
)

_HEADER_STYLE = "bold cyan"
_PITCHER_STYLE = "bold yellow"
_NORMAL_STYLE = "white"
_MISSING_STYLE = "dim white"
_MISSING_PLAYER = "—"


def _build_position_map(team: Team) -> dict[Position, LineupSlot]:
    """Build a mapping from defensive position to the active lineup slot.

    When multiple slots share a position, the one with the highest
    entered_inning (most recent) takes precedence.
    """
    result: dict[Position, LineupSlot] = {}
    for slot in team.lineup:
        existing = result.get(slot.position)
        if existing is None or slot.entered_inning > existing.entered_inning:
            result[slot.position] = slot
    return result


def _make_table() -> Table:
    """Create a new Rich Table with the standard column structure."""
    table = Table(
        show_header=True,
        header_style=_HEADER_STYLE,
        show_edge=True,
        box=None,
        padding=(0, 1),
    )
    table.add_column("#", style="dim white", width=3, justify="right")
    table.add_column("Pos", style="bold white", width=4, justify="left")
    table.add_column("Player", style="white", min_width=16, justify="left")
    return table


def _render_empty_table() -> Table:
    """Return a table indicating no team data is available."""
    table = _make_table()
    for pos in _POSITION_ORDER:
        table.add_row(
            pos.value,
            pos.display,
            Text(_MISSING_PLAYER, style=_MISSING_STYLE),
        )
    return table


def _render_team_table(team: Team) -> Table:
    """Render the full defensive alignment table for a team."""
    table = _make_table()
    position_map = _build_position_map(team)

    for pos in _POSITION_ORDER:
        slot = position_map.get(pos)
        is_pitcher = pos is Position.P

        if slot is None:
            row_style = _PITCHER_STYLE if is_pitcher else _MISSING_STYLE
            player_cell = Text(_MISSING_PLAYER, style=row_style)
        else:
            row_style = _PITCHER_STYLE if is_pitcher else _NORMAL_STYLE
            player_text = f"#{slot.player.number}  {slot.player.name}"
            player_cell = Text(player_text, style=row_style)

        table.add_row(
            Text(pos.value, style=row_style),
            Text(pos.display, style=row_style),
            player_cell,
        )

    return table


class DefenseWidget(Widget):
    """Shows the 9-position defensive alignment for a team.

    Lists position number, abbreviation, and player name.
    The pitcher row is highlighted in yellow.
    """

    DEFAULT_CSS = """
    DefenseWidget {
        width: 40;
        height: auto;
    }
    """

    def __init__(self, team: Team | None = None, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.team = team

    def render(self) -> Table:
        """Build a Rich Table with columns: #, Pos, Player."""
        if self.team is None:
            return _render_empty_table()
        return _render_team_table(self.team)

    def update_team(self, team: Team) -> None:
        """Replace the displayed team and trigger a re-render."""
        self.team = team
        self.refresh()
