"""Lineup row widget — one batter row in the scorecard grid."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label

from baseball_scorebook.models.at_bat import DiamondState
from baseball_scorebook.widgets.diamond import DiamondWidget

_LABEL_STYLE = "bold white"
_NUMBER_STYLE = "dim white"
_POSITION_STYLE = "yellow"

# Fixed column widths for the left identity cells.
_ORDER_WIDTH = 2
_NUMBER_WIDTH = 3
_NAME_WIDTH = 12
_POSITION_WIDTH = 3


def _pad(text: str, width: int) -> str:
    """Left-justify text in a fixed-width field, truncating if necessary."""
    return text[:width].ljust(width)


class LineupRowWidget(Widget):
    """One row in the scorecard showing a batter's number, name, position,
    and diamond cells for each inning they batted.

    The left side shows fixed identity columns:
        #order  #jersey  Name          Pos
        1       42       J. Smith      CF

    Diamond cells are added dynamically via add_diamond().
    """

    DEFAULT_CSS = """
    LineupRowWidget {
        height: 9;
        layout: horizontal;
        border-bottom: dashed $surface-lighten-2;
    }

    LineupRowWidget > .identity {
        width: 22;
        height: 9;
        padding: 0 1;
        content-align: left middle;
    }

    LineupRowWidget > DiamondWidget {
        width: 16;
        height: 9;
        margin: 0;
    }
    """

    def __init__(
        self,
        batting_order: int,
        player_name: str,
        player_number: int,
        position: str,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.batting_order = batting_order
        self.player_name = player_name
        self.player_number = player_number
        self.position = position
        # Keyed by inning number; populated by add_diamond().
        self._diamonds: dict[int, DiamondWidget] = {}

    def compose(self) -> ComposeResult:
        """Yield the fixed identity label."""
        yield Label(self._identity_text(), classes="identity")

    def _identity_text(self) -> str:
        """Build the fixed-width identity string for the left column."""
        order = _pad(str(self.batting_order), _ORDER_WIDTH)
        number = _pad(f"#{self.player_number}", _NUMBER_WIDTH)
        name = _pad(self.player_name, _NAME_WIDTH)
        pos = _pad(self.position, _POSITION_WIDTH)
        return f"{order} {number} {name} {pos}"

    def add_diamond(self, inning: int, state: DiamondState | None = None) -> DiamondWidget:
        """Append a DiamondWidget for the given inning and return it.

        If a diamond for this inning already exists, its state is updated
        and the existing widget is returned.
        """
        if inning in self._diamonds:
            widget = self._diamonds[inning]
            widget.diamond_state = state
            return widget

        widget = DiamondWidget()
        widget.diamond_state = state
        self._diamonds[inning] = widget
        self.mount(widget)
        return widget

    def update_diamond(self, inning: int, state: DiamondState | None) -> None:
        """Update the diamond state for a specific inning."""
        if inning in self._diamonds:
            self._diamonds[inning].diamond_state = state

    def update_identity(
        self,
        player_name: str,
        player_number: int,
        position: str,
    ) -> None:
        """Refresh the identity label (e.g. after a substitution)."""
        self.player_name = player_name
        self.player_number = player_number
        self.position = position
        label = self.query_one(".identity", Label)
        label.update(self._identity_text())
