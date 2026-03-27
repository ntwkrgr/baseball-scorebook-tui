"""
Derived game state and inning statistics.

GameState is computed by replaying the event log; it is never stored
directly.  InningStats accumulates per-half-inning totals for display
in the scorecard's R/H/E/LOB row.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from baseball_scorebook.models.constants import BaseCode, HalfCode


@dataclass(frozen=True)
class RunnerInfo:
    """
    Identifies a runner currently occupying a base.

    Attributes:
        batting_order: Lineup slot (1-9) of the runner.  Used to look up
            the runner's identity and batting history.
        at_bat_inning: The inning in which this runner originally reached
            base.  Combined with batting_order this uniquely locates the
            scorecard diamond cell that displays the runner's journey.
    """

    batting_order: int
    at_bat_inning: int


@dataclass
class InningStats:
    """
    Accumulated statistics for a single half-inning.

    Used to populate the R/H/E/LOB summary row on the scorecard.
    Mutable because the engine increments these fields as events are
    replayed.

    Attributes:
        runs: Runs scored in this half-inning.
        hits: Base hits recorded in this half-inning.
        errors: Fielding errors committed in this half-inning.
        left_on_base: Runners still on base when the third out was made.
    """

    runs: int = 0
    hits: int = 0
    errors: int = 0
    left_on_base: int = 0


@dataclass
class GameState:
    """
    Full derived state of the game at a given point in the event log.

    Computed by replaying all events from the beginning; never persisted
    directly.  Mutable so that the engine can update it incrementally
    during replay without allocating a new object on every event.

    Attributes:
        current_inning: Active inning number (1-based).
        current_half: Active half-inning (TOP = away, BOTTOM = home).
        current_batter_index: Per-half mapping of the 0-based lineup
            index for the next batter (wraps at 8 → 0).
        outs: Outs recorded in the current half-inning (0-2; 3 triggers
            a half-inning change).
        runners: Mapping from base to the runner currently occupying it.
            Only populated entries are present (no null placeholders).
        away_score: Total runs scored by the away team.
        home_score: Total runs scored by the home team.
        game_over: True once the game has been officially ended.
        inning_stats: Per-half-inning stat totals keyed by
            (inning_number, HalfCode).
    """

    current_inning: int = 1
    current_half: HalfCode = HalfCode.TOP
    current_batter_index: dict[HalfCode, int] = field(
        default_factory=lambda: {HalfCode.TOP: 0, HalfCode.BOTTOM: 0}
    )
    outs: int = 0
    runners: dict[BaseCode, RunnerInfo] = field(default_factory=dict)
    away_score: int = 0
    home_score: int = 0
    game_over: bool = False
    inning_stats: dict[tuple[int, HalfCode], InningStats] = field(
        default_factory=dict
    )
