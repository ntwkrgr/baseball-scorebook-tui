"""Inning totals widget — R/H/E/LOB summary row below the scorecard."""

from __future__ import annotations

from rich.table import Table
from rich.text import Text
from textual.widget import Widget

from baseball_scorebook.models.constants import HalfCode
from baseball_scorebook.models.game import GameState, InningStats

_HEADER_STYLE = "bold cyan"
_LABEL_STYLE = "bold white"
_VALUE_STYLE = "white"
_TOTAL_STYLE = "bold yellow"
_ZERO_STYLE = "dim white"
_EMPTY_DASH = "—"


def _stat_cell(value: int) -> Text:
    """Render a stat integer, dimming zeros for readability."""
    if value == 0:
        return Text(str(value), style=_ZERO_STYLE)
    return Text(str(value), style=_VALUE_STYLE)


def _total_cell(value: int) -> Text:
    """Render a totals column value in highlighted style."""
    return Text(str(value), style=_TOTAL_STYLE)


def _collect_innings(
    state: GameState,
    half: HalfCode,
) -> tuple[list[int], list[InningStats]]:
    """Return sorted inning numbers and their stats for the given half.

    Innings are sorted numerically so extra innings appear in order.
    """
    pairs = [
        (inning_num, stats)
        for (inning_num, h), stats in state.inning_stats.items()
        if h is half
    ]
    pairs.sort(key=lambda p: p[0])
    innings = [p[0] for p in pairs]
    stats = [p[1] for p in pairs]
    return innings, stats


def _build_table(
    innings: list[int],
    stats: list[InningStats],
) -> Table:
    """Construct the Rich Table for the given innings and stats."""
    table = Table(
        show_header=True,
        header_style=_HEADER_STYLE,
        show_edge=True,
        box=None,
        padding=(0, 1),
    )

    # Row-label column
    table.add_column("", style=_LABEL_STYLE, width=5, justify="right")

    # One column per inning
    for inning_num in innings:
        table.add_column(str(inning_num), style=_VALUE_STYLE, width=3, justify="right")

    # Totals column
    table.add_column("TOT", style=_TOTAL_STYLE, width=5, justify="right")

    # Build one row per stat category.
    categories: list[tuple[str, str]] = [
        ("R", "runs"),
        ("H", "hits"),
        ("E", "errors"),
        ("LOB", "left_on_base"),
    ]

    for label, attr in categories:
        cells: list[Text] = [Text(label, style=_LABEL_STYLE)]
        total = 0
        for stat in stats:
            value = getattr(stat, attr)
            total += value
            cells.append(_stat_cell(value))
        cells.append(_total_cell(total))
        table.add_row(*cells)

    return table


def _build_empty_table(half: HalfCode) -> Table:
    """Return a placeholder table when no game state is available."""
    table = Table(
        show_header=True,
        header_style=_HEADER_STYLE,
        show_edge=True,
        box=None,
        padding=(0, 1),
    )
    half_label = "TOP" if half is HalfCode.TOP else "BOT"
    table.add_column("", style=_LABEL_STYLE, width=5, justify="right")
    table.add_column(f"({half_label})", style=_ZERO_STYLE, width=12, justify="left")
    table.add_column("TOT", style=_TOTAL_STYLE, width=5, justify="right")

    for label in ("R", "H", "E", "LOB"):
        table.add_row(
            Text(label, style=_LABEL_STYLE),
            Text(_EMPTY_DASH, style=_ZERO_STYLE),
            Text("0", style=_ZERO_STYLE),
        )
    return table


class InningTotalsWidget(Widget):
    """R/H/E/LOB summary row below the scorecard.

    Shows per-inning breakdown and cumulative totals for one half-inning
    perspective (TOP = away batting, BOTTOM = home batting).
    """

    DEFAULT_CSS = """
    InningTotalsWidget {
        width: 100%;
        height: auto;
    }
    """

    def __init__(self, half: HalfCode = HalfCode.TOP, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.half = half
        self.state: GameState | None = None

    def render(self) -> Table:
        """Build table with rows: R, H, E, LOB and a column per inning."""
        if self.state is None:
            return _build_empty_table(self.half)

        innings, stats = _collect_innings(self.state, self.half)

        if not innings:
            return _build_empty_table(self.half)

        return _build_table(innings, stats)

    def update_state(self, state: GameState) -> None:
        """Refresh the widget with a new game state."""
        self.state = state
        self.refresh()
