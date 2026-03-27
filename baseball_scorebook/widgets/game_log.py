"""Game log widget — scrollable play-by-play log from the event store."""

from __future__ import annotations

from textual.widgets import RichLog

from baseball_scorebook.models.constants import HalfCode
from baseball_scorebook.models.events import (
    AtBatEvent,
    BaserunnerEvent,
    GameEvent,
    RunnerAdvanceEvent,
    SubstitutionEvent,
)

_HALF_LABELS: dict[HalfCode, str] = {
    HalfCode.TOP: "TOP",
    HalfCode.BOTTOM: "BOT",
}


def _half_label(half: HalfCode) -> str:
    """Return the short half-inning label."""
    return _HALF_LABELS.get(half, half.value)


def _inning_prefix(inning: int, half: HalfCode) -> str:
    """Build the inning/half prefix used at the start of each log line."""
    return f"{inning:>2}{_half_label(half)}"


def _format_at_bat(event: AtBatEvent) -> str:
    """Format a plate appearance event as a play-by-play line."""
    prefix = _inning_prefix(event.inning, event.half)
    result = event.result_type.display
    fielders = f" {event.fielders}" if event.fielders else ""
    rbi = f"  {event.rbi_count} RBI" if event.rbi_count > 0 else ""
    notes = f"  [{event.notes}]" if event.notes else ""
    return f"  {prefix}  #{event.batting_order}{fielders} {result}{rbi}{notes}"


def _format_runner_advance(event: RunnerAdvanceEvent) -> str:
    """Format a runner advance event as a play-by-play line."""
    prefix = _inning_prefix(event.inning, event.half)
    from_label = event.from_base.value
    to_label = event.to_base.value
    return f"  {prefix}  Runner #{event.runner_batting_order}: {from_label}\u2192{to_label}"


def _format_baserunner(event: BaserunnerEvent) -> str:
    """Format a standalone baserunner event (SB, CS, WP, etc.) as a line."""
    prefix = _inning_prefix(event.inning, event.half)
    how = event.how.value
    from_label = event.from_base.value
    to_label = event.to_base.value
    fielders = f" ({event.fielders})" if event.fielders else ""
    return f"  {prefix}  #{event.runner_batting_order} {how}{fielders}: {from_label}\u2192{to_label}"


def _format_substitution(event: SubstitutionEvent) -> str:
    """Format a substitution event as a play-by-play line."""
    prefix = _inning_prefix(event.inning, event.half)
    sub_type = event.sub_type.value
    return (
        f"  {prefix}  SUB ({sub_type}): #{event.entering_number} "
        f"{event.entering_name} for {event.leaving_name}"
    )


def _format_event(event: GameEvent) -> str:
    """Format a single event as a play-by-play text line.

    Returns an empty string for event types that do not produce
    visible log output (e.g. EditEvent, ErrorEvent).
    """
    if isinstance(event, AtBatEvent):
        return _format_at_bat(event)
    if isinstance(event, RunnerAdvanceEvent):
        return _format_runner_advance(event)
    if isinstance(event, BaserunnerEvent):
        return _format_baserunner(event)
    if isinstance(event, SubstitutionEvent):
        return _format_substitution(event)
    return ""


class GameLogWidget(RichLog):
    """Scrollable play-by-play log generated from the event store.

    Shows text descriptions of each event in chronological order.
    Call update_from_events() to rebuild the log from a new event sequence.
    """

    DEFAULT_CSS = """
    GameLogWidget {
        width: 100%;
        height: 100%;
        border: solid green;
    }
    """

    def update_from_events(self, events: tuple[GameEvent, ...]) -> None:
        """Regenerate the log from the given event sequence.

        Clears the existing content and writes a line for every event
        that produces displayable output.
        """
        self.clear()
        for event in events:
            line = _format_event(event)
            if line:
                self.write(line)
