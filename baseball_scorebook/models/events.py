"""
Immutable event types for the append-only game event log.

All GameEvent subclasses are frozen dataclasses.  The full game state is
derived by replaying these events in order — nothing is mutated in place.
EditEvent allows corrections to be recorded without modifying history.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from baseball_scorebook.models.at_bat import BaseEvent
from baseball_scorebook.models.constants import (
    AdvanceType,
    BaseCode,
    BaserunnerType,
    HalfCode,
    Position,
    ResultType,
    SubType,
)


# ---------------------------------------------------------------------------
# Factory helpers (used as dataclass field defaults)
# ---------------------------------------------------------------------------


def _new_id() -> str:
    """Generate a new UUID string for an event identifier."""
    return str(uuid.uuid4())


def _now() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Base event
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GameEvent:
    """
    Root event class.

    All events are immutable and carry a unique identifier plus a UTC
    timestamp so the append-only log can be audited and replayed.

    Attributes:
        event_id: UUID identifying this specific event instance.
        timestamp: ISO 8601 UTC datetime string set at creation time.
    """

    event_id: str = field(default_factory=_new_id)
    timestamp: str = field(default_factory=_now)


# ---------------------------------------------------------------------------
# Plate-appearance events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AtBatEvent(GameEvent):
    """
    A completed plate appearance.

    Captures the full outcome of a single batter's trip to the plate,
    including how far the batter advanced and how many outs resulted.

    Attributes:
        inning: Inning number (1-based).
        half: TOP (away) or BOTTOM (home) half of the inning.
        batting_order: Lineup slot (1-9) for the batter.
        result_type: Structured outcome driving stat counting.
        fielders: Fielder notation string for display (e.g. ``"6-3"``).
            Empty string when not applicable.
        batter_reached: True when the batter safely reaches base,
            including on a dropped third strike (K+WP/PB).
        outs_on_play: Number of outs recorded on this play (0–3).
        bases_reached: Ordered legs of the batter's base journey.
            Uses a tuple to guarantee immutability.
        rbi_count: RBIs credited to the batter on this play.
        notes: Free-form scorekeeper annotation.
    """

    inning: int = 1
    half: HalfCode = HalfCode.TOP
    batting_order: int = 1
    result_type: ResultType = ResultType.GROUND_OUT
    fielders: str = ""
    batter_reached: bool = False
    outs_on_play: int = 1
    bases_reached: tuple[BaseEvent, ...] = ()
    rbi_count: int = 0
    notes: str = ""


@dataclass(frozen=True)
class RunnerAdvanceEvent(GameEvent):
    """
    A baserunner advances (or is put out) as a consequence of a plate appearance.

    Recorded separately from AtBatEvent so that each runner on base at the
    time of a plate appearance can have their individual diamond updated
    without embedding all runner movements inside a single event.

    Attributes:
        inning: Inning number of the plate appearance that caused this move.
        half: Half-inning of the causing plate appearance.
        runner_batting_order: Lineup slot of the runner being advanced.
        runner_at_bat_inning: Inning in which the runner originally reached
            base (used to locate their diamond cell on the scorecard).
        from_base: Base the runner occupied before this advance.
        to_base: Base the runner reached; HOME means scored, OUT means retired.
        how: Mechanism of advancement.
        earned: True when a resulting run is earned.
        rbi_batter_order: Lineup slot of the batter credited with the RBI,
            or None if no RBI is awarded.
    """

    inning: int = 1
    half: HalfCode = HalfCode.TOP
    runner_batting_order: int = 1
    runner_at_bat_inning: int = 1
    from_base: BaseCode = BaseCode.FIRST
    to_base: BaseCode = BaseCode.SECOND
    how: AdvanceType = AdvanceType.ON_HIT
    earned: bool = True
    rbi_batter_order: int | None = None


# ---------------------------------------------------------------------------
# Baserunner events (outside plate appearances)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BaserunnerEvent(GameEvent):
    """
    A baserunner event that occurs outside a plate appearance.

    Covers stolen bases, caught stealing, pickoffs, wild pitches, passed
    balls, balks, and outs on base running — anything that moves or removes
    a runner without the batter completing an at-bat.

    Attributes:
        inning: Inning number.
        half: Half-inning.
        runner_batting_order: Lineup slot of the runner.
        runner_at_bat_inning: Inning in which the runner originally reached
            base (scorecard cell lookup key).
        from_base: Base the runner started on.
        to_base: Base the runner reached; HOME means scored, OUT means retired.
        how: Type of baserunner event.
        fielders: Fielder notation for display (e.g. ``"2-6"`` for CS).
        earned: True when a resulting run is earned.
        outs_on_play: 0 or 1 (CS and pickoffs produce an out).
    """

    inning: int = 1
    half: HalfCode = HalfCode.TOP
    runner_batting_order: int = 1
    runner_at_bat_inning: int = 1
    from_base: BaseCode = BaseCode.FIRST
    to_base: BaseCode = BaseCode.SECOND
    how: BaserunnerType = BaserunnerType.SB
    fielders: str = ""
    earned: bool = True
    outs_on_play: int = 0


# ---------------------------------------------------------------------------
# Substitution events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubstitutionEvent(GameEvent):
    """
    A player substitution.

    Attributes:
        inning: Inning in which the substitution is made.
        half: Half-inning of the substitution.
        team: Which team is making the substitution (AWAY=TOP, HOME=BOTTOM).
        batting_order: Lineup slot being filled by the entering player.
        leaving_name: Display name of the departing player.
        entering_name: Display name of the entering player.
        entering_number: Jersey number of the entering player.
        new_position: Defensive position assigned to the entering player.
        sub_type: Category of substitution.
    """

    inning: int = 1
    half: HalfCode = HalfCode.TOP
    team: HalfCode = HalfCode.TOP  # AWAY=TOP, HOME=BOTTOM
    batting_order: int = 1
    leaving_name: str = ""
    entering_name: str = ""
    entering_number: int = 0
    new_position: Position = Position.P
    sub_type: SubType = SubType.PINCH_HIT


# ---------------------------------------------------------------------------
# Error events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ErrorEvent(GameEvent):
    """
    A fielding error committed on the defensive team.

    Errors are recorded as standalone events so they can be referenced
    when computing earned-run status for runners who reached via the error.

    Attributes:
        inning: Inning in which the error occurred.
        half: Half-inning of the error.
        fielder_position: Defensive position that committed the error.
        fielder_name: Name of the fielder for display.
        notes: Optional scorekeeper annotation.
    """

    inning: int = 1
    half: HalfCode = HalfCode.TOP
    fielder_position: Position = Position.SS
    fielder_name: str = ""
    notes: str = ""


# ---------------------------------------------------------------------------
# Correction / edit events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EditEvent(GameEvent):
    """
    An append-only correction to a previous event.

    The original event is retained in the log unchanged; the engine uses
    the corrected version whenever it encounters the target_event_id
    during replay.  This preserves a full audit trail of all changes.

    Attributes:
        target_event_id: ``event_id`` of the event being corrected.
        corrected_event: Replacement event (same type, updated data).
        reason: Optional note explaining why the correction was made.
    """

    target_event_id: str = ""
    corrected_event: GameEvent = field(default_factory=GameEvent)
    reason: str = ""
