"""
State derivation engine for the baseball scorebook.

Replays all effective events from an EventStore to produce a GameState.
The engine never persists state directly; every call to derive_state
replays from scratch, making the system trivially correct after edits.

Design notes
------------
- ``derive_state`` is the only public entry point.
- ``_apply_*`` helpers are pure-mutation helpers that update GameState
  in place during replay.  Because derive_state always starts from a
  fresh GameState(), the mutation is safe and unobservable to callers.
- ``check_game_over`` is a pure predicate; it does *not* set
  ``state.game_over``.  The UI calls it after each event and decides
  whether to prompt the user to end the game.
"""

from __future__ import annotations

from baseball_scorebook.models.constants import BaseCode, HalfCode
from baseball_scorebook.models.events import (
    AtBatEvent,
    BaserunnerEvent,
    ErrorEvent,
    GameEvent,
    RunnerAdvanceEvent,
    SubstitutionEvent,
)
from baseball_scorebook.models.game import GameState, InningStats, RunnerInfo
from baseball_scorebook.engine.event_store import EventStore


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def derive_state(store: EventStore) -> GameState:
    """Derive the full GameState by replaying all effective events.

    Starts from a clean GameState and applies each event returned by
    ``store.effective_events()`` in order.  EditEvent corrections are
    already resolved by the store; the engine only sees the logical
    sequence.

    Args:
        store: The EventStore whose effective events will be replayed.

    Returns:
        A fully populated GameState reflecting every effective event.
    """
    state = GameState()
    for event in store.effective_events():
        _apply_event(state, event)
    return state


# ---------------------------------------------------------------------------
# Event dispatch
# ---------------------------------------------------------------------------


def _apply_event(state: GameState, event: GameEvent) -> None:
    """Dispatch a single event to its type-specific handler.

    Unknown event types are silently ignored so that new event kinds
    added in the future do not crash older replay logic.

    Args:
        state: Mutable game state accumulator.
        event: The event to apply.
    """
    if isinstance(event, AtBatEvent):
        _apply_at_bat(state, event)
    elif isinstance(event, RunnerAdvanceEvent):
        _apply_runner_advance(state, event)
    elif isinstance(event, BaserunnerEvent):
        _apply_baserunner(state, event)
    elif isinstance(event, SubstitutionEvent):
        pass  # Substitutions affect lineup display only, not game state.
    elif isinstance(event, ErrorEvent):
        _apply_error(state, event)


# ---------------------------------------------------------------------------
# Per-event handlers
# ---------------------------------------------------------------------------


def _apply_at_bat(state: GameState, event: AtBatEvent) -> None:
    """Process a completed plate appearance.

    Handles:
    - Hit counting for the half-inning stats.
    - Out recording, including the dropped-third-strike override where
      the strikeout is *not* an out even though result_type is
      STRIKEOUT/STRIKEOUT_LOOKING.
    - Placing the batter on the appropriate base when batter_reached is
      True, or recording a home run.
    - Advancing the batting-order index for the relevant lineup slot.
    - Triggering a half-inning transition when 3 outs accumulate.

    Args:
        state: Mutable game state accumulator.
        event: The plate-appearance event to apply.
    """
    stats = _get_inning_stats(state, event.inning, event.half)

    if event.result_type.counts_as_hit:
        stats.hits += 1

    # outs_on_play already accounts for the dropped-third-strike case
    # (outs_on_play == 0 when batter_reached=True on a strikeout).
    state.outs += event.outs_on_play

    if event.batter_reached:
        _place_batter(state, event)

    # Advance the lineup cursor for this half regardless of outcome.
    _advance_batter_index(state, event.half)

    _check_half_inning_change(state)


def _place_batter(state: GameState, event: AtBatEvent) -> None:
    """Place a batter who reached base onto the appropriate base.

    Uses ``bases_reached`` to determine the batter's final base.  When
    the batter reached home (e.g. inside-the-park home run or HOME_RUN
    with no separate runner advance), a run is scored immediately.

    Args:
        state: Mutable game state accumulator.
        event: The at-bat event for the batter who reached.
    """
    if not event.bases_reached:
        # Fallback: use the result type's default base.
        default_base = event.result_type.batter_default_base
        if default_base is None:
            return
        final_base = default_base
    else:
        final_base = event.bases_reached[-1].to_base

    if final_base == BaseCode.HOME:
        _score_run(state, event.inning, event.half, earned=True)
    elif final_base != BaseCode.OUT:
        state.runners[final_base] = RunnerInfo(
            batting_order=event.batting_order,
            at_bat_inning=event.inning,
        )


def _apply_runner_advance(state: GameState, event: RunnerAdvanceEvent) -> None:
    """Process a runner advance that is a consequence of a plate appearance.

    Removes the runner from their starting base, then either scores a
    run, records an out, or places the runner on the destination base.

    Args:
        state: Mutable game state accumulator.
        event: The runner-advance event to apply.
    """
    state.runners.pop(event.from_base, None)

    if event.to_base == BaseCode.HOME:
        _score_run(state, event.inning, event.half, earned=event.earned)
    elif event.to_base == BaseCode.OUT:
        state.outs += 1
        _check_half_inning_change(state)
    else:
        state.runners[event.to_base] = RunnerInfo(
            batting_order=event.runner_batting_order,
            at_bat_inning=event.runner_at_bat_inning,
        )


def _apply_baserunner(state: GameState, event: BaserunnerEvent) -> None:
    """Process a standalone baserunner event (SB, CS, WP, PB, BK, OBR).

    These events move or retire a runner outside of a plate appearance.
    The logic mirrors runner_advance: remove from source, then score,
    out, or reposition.

    Args:
        state: Mutable game state accumulator.
        event: The baserunner event to apply.
    """
    state.runners.pop(event.from_base, None)

    if event.to_base == BaseCode.HOME:
        _score_run(state, event.inning, event.half, earned=event.earned)
    elif event.to_base == BaseCode.OUT:
        state.outs += event.outs_on_play
        _check_half_inning_change(state)
    else:
        state.runners[event.to_base] = RunnerInfo(
            batting_order=event.runner_batting_order,
            at_bat_inning=event.runner_at_bat_inning,
        )


def _apply_error(state: GameState, event: ErrorEvent) -> None:
    """Increment the error count for the relevant half-inning.

    Args:
        state: Mutable game state accumulator.
        event: The error event to apply.
    """
    stats = _get_inning_stats(state, event.inning, event.half)
    stats.errors += 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_inning_stats(
    state: GameState, inning: int, half: HalfCode
) -> InningStats:
    """Return the InningStats for the given half-inning, creating it if absent.

    Args:
        state: Mutable game state accumulator.
        inning: Inning number (1-based).
        half: TOP or BOTTOM half of the inning.

    Returns:
        The InningStats object for the requested half-inning.
    """
    key = (inning, half)
    if key not in state.inning_stats:
        state.inning_stats[key] = InningStats()
    return state.inning_stats[key]


def _advance_batter_index(state: GameState, half: HalfCode) -> None:
    """Move the lineup cursor forward by one slot, wrapping at 9.

    Args:
        state: Mutable game state accumulator.
        half: The half-inning whose lineup cursor should advance.
    """
    state.current_batter_index[half] = (
        state.current_batter_index[half] + 1
    ) % 9


def _score_run(
    state: GameState, inning: int, half: HalfCode, *, earned: bool
) -> None:
    """Record a run scored for the batting team in the given half-inning.

    Updates both the cumulative team score and the per-half-inning run
    total.  The ``earned`` flag is accepted for completeness (it affects
    pitching stats downstream) but is not yet tracked on InningStats.

    Args:
        state: Mutable game state accumulator.
        inning: Inning number the run is scored in.
        half: TOP (away team scores) or BOTTOM (home team scores).
        earned: Whether the run is earned for ERA purposes.
    """
    if half == HalfCode.TOP:
        state.away_score += 1
    else:
        state.home_score += 1

    stats = _get_inning_stats(state, inning, half)
    stats.runs += 1


def _check_half_inning_change(state: GameState) -> None:
    """Transition to the next half-inning when 3 outs have been recorded.

    Before clearing runners, computes the left-on-base count for the
    current half-inning.  Then resets runners and outs and advances the
    inning/half cursor.

    This function is a no-op when fewer than 3 outs have accumulated.

    Args:
        state: Mutable game state accumulator.
    """
    if state.outs < 3:
        return

    stats = _get_inning_stats(state, state.current_inning, state.current_half)
    stats.left_on_base = len(state.runners)

    state.runners.clear()
    state.outs = 0

    if state.current_half == HalfCode.TOP:
        state.current_half = HalfCode.BOTTOM
    else:
        state.current_half = HalfCode.TOP
        state.current_inning += 1


# ---------------------------------------------------------------------------
# Game-over detection
# ---------------------------------------------------------------------------


def check_game_over(state: GameState) -> bool:
    """Return True when the game should be considered over.

    This is a pure predicate and does *not* set ``state.game_over``.
    The UI is responsible for calling this after each event and deciding
    whether to prompt the user to confirm the game has ended.

    Ending conditions:
    - Walk-off: home team leads in the middle of the bottom of the 9th+.
    - Regulation end: after the bottom of the 9th completes with the
      home team leading (we are now positioned at the top of the 10th).
    - Extra innings: any completed inning past the 9th where one team
      leads after the bottom half has been played (positioned at the
      top of the next inning).

    Args:
        state: The current derived game state.

    Returns:
        True if game-ending conditions have been met, False otherwise.
    """
    if state.current_inning < 9:
        return False

    # Walk-off: home team leads with the bottom half still in progress.
    if (
        state.current_half == HalfCode.BOTTOM
        and state.current_inning >= 9
        and state.home_score > state.away_score
    ):
        return True

    # After the bottom of the 9th (or later) completes, we are now in
    # the top of the next inning.  If either team leads, the game is
    # over — the trailing team has had its chance.
    if (
        state.current_half == HalfCode.TOP
        and state.current_inning >= 10
        and state.away_score != state.home_score
    ):
        return True

    return False
