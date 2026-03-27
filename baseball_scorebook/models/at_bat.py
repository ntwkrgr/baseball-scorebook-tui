"""Data classes for individual at-bat records and diamond display state."""

from __future__ import annotations

from dataclasses import dataclass, field

from baseball_scorebook.models.constants import (
    AdvanceType,
    BaseCode,
    ResultType,
    RunnerFinalState,
    SegmentState,
)


@dataclass(frozen=True)
class BaseEvent:
    """
    One leg of a batter's (or runner's) journey around the bases.

    A complete plate appearance may produce multiple BaseEvents — one
    for each base-to-base transition the runner makes on that play.

    Attributes:
        from_base: Starting base for this leg.  HOME represents the
            batter's box before they reach first.
        to_base: Ending base for this leg.  HOME means the runner
            scored; OUT means the runner was retired.
        how: The mechanism by which the runner advanced (or was out).
        earned: True when the run (if scored) is earned for the
            purposes of the pitcher's ERA.
        rbi: True when this advancement produces an RBI credited to
            the batter.
    """

    from_base: BaseCode   # HOME (batter's box), FIRST, SECOND, THIRD
    to_base: BaseCode     # FIRST, SECOND, THIRD, HOME, or OUT
    how: AdvanceType
    earned: bool
    rbi: bool


@dataclass
class DiamondState:
    """
    Visual state of one at-bat cell's diamond widget.

    This is a *derived* display object rebuilt by the engine each time
    the event log is replayed.  It is intentionally mutable so that the
    rendering layer can update it in place without generating garbage.

    Attributes:
        result_type: The at-bat outcome (drives the label drawn inside
            the diamond).
        fielders: Fielder notation string for display (e.g. ``"6-3"``).
        segments: Mapping from a (from_base, to_base) pair to the
            rendering state of that base-path segment.  Only segments
            the runner traversed are present.
        final_base: The base where the runner's journey ended.
        final_state: Whether the runner ultimately scored, was left on
            base, or was put out.
        annotations: Short labels drawn alongside a segment, such as
            ``"SB"`` or ``"CS"``.
    """

    result_type: ResultType
    fielders: str
    segments: dict[tuple[BaseCode, BaseCode], SegmentState] = field(
        default_factory=dict
    )
    final_base: BaseCode = BaseCode.HOME
    final_state: RunnerFinalState = RunnerFinalState.RUNNING
    annotations: list[str] = field(default_factory=list)
