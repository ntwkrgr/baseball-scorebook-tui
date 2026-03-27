"""Scoreline widget — pinned scoreboard showing runs per inning for both teams."""

from __future__ import annotations

from rich.table import Table
from rich.text import Text
from textual.widget import Widget

from baseball_scorebook.models.constants import HalfCode
from baseball_scorebook.models.game import GameState, InningStats

_HEADER_STYLE = "bold cyan"
_TEAM_STYLE = "bold white"
_RUN_STYLE = "white"
_ZERO_STYLE = "dim white"
_ACTIVE_STYLE = "bold yellow on dark_green"
_TOTAL_STYLE = "bold yellow"
_EMPTY_DASH = "-"

# Minimum number of inning columns to always display.
_MIN_INNINGS = 9


def _run_cell(runs: int, is_active: bool) -> Text:
    """Render a runs integer with appropriate styling."""
    text = str(runs)
    if is_active:
        return Text(text, style=_ACTIVE_STYLE)
    if runs == 0:
        return Text(text, style=_ZERO_STYLE)
    return Text(text, style=_RUN_STYLE)


def _empty_cell(is_active: bool) -> Text:
    """Render a placeholder for an inning that has not been played yet."""
    if is_active:
        return Text(_EMPTY_DASH, style=_ACTIVE_STYLE)
    return Text(_EMPTY_DASH, style=_ZERO_STYLE)


def _collect_runs(
    state: GameState,
    half: HalfCode,
    max_inning: int,
) -> dict[int, int]:
    """Return a mapping of inning_number → runs for the given half."""
    result: dict[int, int] = {}
    for (inning_num, h), stats in state.inning_stats.items():
        if h is half:
            result[inning_num] = stats.runs
    return result


def _compute_totals(state: GameState) -> tuple[int, int, int, int]:
    """Return (away_runs, home_runs, away_hits, home_hits, away_errors, home_errors).

    Actually returns (away_runs, home_runs, away_hits+errors placeholder, home_hits+errors placeholder)
    as a 4-tuple: (away_r, home_r, away_hits, home_hits) — errors are
    collected separately below.
    """
    away_r = away_h = away_e = 0
    home_r = home_h = home_e = 0
    for (_, half), stats in state.inning_stats.items():
        if half is HalfCode.TOP:
            away_r += stats.runs
            away_h += stats.hits
            away_e += stats.errors
        else:
            home_r += stats.runs
            home_h += stats.hits
            home_e += stats.errors
    return away_r, away_h, away_e, home_r, home_h, home_e


def _build_empty_table(away_name: str, home_name: str) -> Table:
    """Return a placeholder scoreboard with no game data."""
    table = Table(
        show_header=True,
        header_style=_HEADER_STYLE,
        show_edge=True,
        box=None,
        padding=(0, 1),
    )
    table.add_column("Team", style=_TEAM_STYLE, width=12, justify="left")
    for i in range(1, _MIN_INNINGS + 1):
        table.add_column(str(i), style=_ZERO_STYLE, width=3, justify="right")
    for col in ("R", "H", "E"):
        table.add_column(col, style=_TOTAL_STYLE, width=3, justify="right")

    away_cells = [Text(away_name[:12], style=_TEAM_STYLE)]
    home_cells = [Text(home_name[:12], style=_TEAM_STYLE)]
    for _ in range(_MIN_INNINGS):
        away_cells.append(Text(_EMPTY_DASH, style=_ZERO_STYLE))
        home_cells.append(Text(_EMPTY_DASH, style=_ZERO_STYLE))
    for _ in range(3):
        away_cells.append(Text("0", style=_ZERO_STYLE))
        home_cells.append(Text("0", style=_ZERO_STYLE))

    table.add_row(*away_cells)
    table.add_row(*home_cells)
    return table


def _build_scoreline_table(
    state: GameState,
    away_name: str,
    home_name: str,
) -> Table:
    """Build the full scoreline table from a live game state."""
    # Determine the column count — at least 9, but more for extra innings.
    all_innings = {inning for (inning, _) in state.inning_stats}
    max_inning = max(all_innings, default=0)
    num_cols = max(max_inning, _MIN_INNINGS)

    active_inning = state.current_inning
    active_half = state.current_half

    away_runs = _collect_runs(state, HalfCode.TOP, num_cols)
    home_runs = _collect_runs(state, HalfCode.BOTTOM, num_cols)
    away_r, away_h, away_e, home_r, home_h, home_e = _compute_totals(state)

    table = Table(
        show_header=True,
        header_style=_HEADER_STYLE,
        show_edge=True,
        box=None,
        padding=(0, 1),
    )

    # Column definitions
    table.add_column("Team", style=_TEAM_STYLE, width=12, justify="left")
    for i in range(1, num_cols + 1):
        table.add_column(str(i), style=_RUN_STYLE, width=3, justify="right")
    for col in ("R", "H", "E"):
        table.add_column(col, style=_TOTAL_STYLE, width=3, justify="right")

    # Away row (TOP half)
    away_cells: list[Text] = [Text(away_name[:12], style=_TEAM_STYLE)]
    for inning in range(1, num_cols + 1):
        is_active = (inning == active_inning and active_half is HalfCode.TOP)
        if inning in away_runs:
            away_cells.append(_run_cell(away_runs[inning], is_active))
        elif inning < active_inning or (
            inning == active_inning and active_half is HalfCode.BOTTOM
        ):
            # Inning has been completed for away
            away_cells.append(_run_cell(0, is_active))
        else:
            away_cells.append(_empty_cell(is_active))
    away_cells.extend([
        Text(str(away_r), style=_TOTAL_STYLE),
        Text(str(away_h), style=_TOTAL_STYLE),
        Text(str(away_e), style=_TOTAL_STYLE),
    ])
    table.add_row(*away_cells)

    # Home row (BOTTOM half)
    home_cells: list[Text] = [Text(home_name[:12], style=_TEAM_STYLE)]
    for inning in range(1, num_cols + 1):
        is_active = (inning == active_inning and active_half is HalfCode.BOTTOM)
        if inning in home_runs:
            home_cells.append(_run_cell(home_runs[inning], is_active))
        elif inning < active_inning:
            # Full inning completed
            home_cells.append(_run_cell(0, is_active))
        else:
            home_cells.append(_empty_cell(is_active))
    home_cells.extend([
        Text(str(home_r), style=_TOTAL_STYLE),
        Text(str(home_h), style=_TOTAL_STYLE),
        Text(str(home_e), style=_TOTAL_STYLE),
    ])
    table.add_row(*home_cells)

    return table


class ScorelineWidget(Widget):
    """Pinned scoreboard showing runs per inning for both teams.

    Looks like a baseball scoreboard with team names, inning columns, and
    R/H/E totals.  The current inning column is highlighted.
    Extra-inning columns are added dynamically as the game progresses.
    """

    DEFAULT_CSS = """
    ScorelineWidget {
        width: 100%;
        height: 5;
        dock: bottom;
    }
    """

    def __init__(
        self,
        away_name: str = "Away",
        home_name: str = "Home",
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.away_name = away_name
        self.home_name = home_name
        self.state: GameState | None = None

    def render(self) -> Table:
        """Build the scoreline table for the current game state."""
        if self.state is None:
            return _build_empty_table(self.away_name, self.home_name)
        return _build_scoreline_table(self.state, self.away_name, self.home_name)

    def update_state(self, state: GameState) -> None:
        """Refresh the scoreboard from a new game state."""
        self.state = state
        self.refresh()
