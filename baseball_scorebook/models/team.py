"""Data classes representing teams, players, and lineup slots."""

from __future__ import annotations

from dataclasses import dataclass

from baseball_scorebook.models.constants import Position


@dataclass(frozen=True)
class Player:
    """
    An individual player with a name, jersey number, and primary
    defensive position.

    Immutable: player identity does not change mid-game; substitutions
    create new LineupSlot entries rather than mutating this record.
    """

    name: str
    number: int
    position: Position  # primary defensive position


@dataclass(frozen=True)
class LineupSlot:
    """
    One entry in a team's active batting order.

    A new LineupSlot is recorded whenever a substitution occurs so that
    the full batting-order history is preserved for the event log.

    Attributes:
        batting_order: Position in the order (1-9).
        player: The player occupying this slot.
        position: Defensive position for this appearance — may differ
            from player.position (e.g. a DH or a position-change after
            a substitution).
        entered_inning: Inning number when this slot became active.
            Starting lineup entries use 1.
    """

    batting_order: int   # 1-9
    player: Player
    position: Position   # may differ from player.position
    entered_inning: int  # inning when this slot became active


@dataclass(frozen=True)
class Team:
    """
    A team with a name and its current nine-slot batting order.

    ``lineup`` is a tuple (not a list) to enforce immutability: any
    roster change is expressed by deriving a new Team with a replacement
    tuple rather than mutating the existing one.

    Attributes:
        name: Display name for the team.
        lineup: Exactly nine active batting-order slots, ordered by
            batting_order (1 through 9).
    """

    name: str
    lineup: tuple[LineupSlot, ...]  # 9 active batting-order slots
