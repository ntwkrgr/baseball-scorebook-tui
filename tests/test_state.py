"""Unit tests for game state derivation in engine/state.py."""
from __future__ import annotations

from baseball_scorebook.engine.event_store import EventStore
from baseball_scorebook.engine.state import check_game_over, derive_state
from baseball_scorebook.models.at_bat import BaseEvent
from baseball_scorebook.models.constants import (
    AdvanceType,
    BaseCode,
    BaserunnerType,
    HalfCode,
    ResultType,
)
from baseball_scorebook.models.events import (
    AtBatEvent,
    BaserunnerEvent,
    ErrorEvent,
    RunnerAdvanceEvent,
)
from baseball_scorebook.models.game import RunnerInfo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ground_out(
    inning: int = 1,
    half: HalfCode = HalfCode.TOP,
    batting_order: int = 1,
) -> AtBatEvent:
    return AtBatEvent(
        inning=inning,
        half=half,
        batting_order=batting_order,
        result_type=ResultType.GROUND_OUT,
        fielders="6-3",
        batter_reached=False,
        outs_on_play=1,
    )


def _single(
    inning: int = 1,
    half: HalfCode = HalfCode.TOP,
    batting_order: int = 1,
) -> AtBatEvent:
    return AtBatEvent(
        inning=inning,
        half=half,
        batting_order=batting_order,
        result_type=ResultType.SINGLE,
        batter_reached=True,
        outs_on_play=0,
        bases_reached=(
            BaseEvent(
                from_base=BaseCode.HOME,
                to_base=BaseCode.FIRST,
                how=AdvanceType.ON_HIT,
                earned=True,
                rbi=False,
            ),
        ),
    )


def _home_run(
    inning: int = 1,
    half: HalfCode = HalfCode.TOP,
    batting_order: int = 1,
) -> AtBatEvent:
    return AtBatEvent(
        inning=inning,
        half=half,
        batting_order=batting_order,
        result_type=ResultType.HOME_RUN,
        batter_reached=True,
        outs_on_play=0,
        bases_reached=(
            BaseEvent(
                from_base=BaseCode.HOME,
                to_base=BaseCode.HOME,
                how=AdvanceType.ON_HIT,
                earned=True,
                rbi=False,
            ),
        ),
    )


def _three_ground_outs(
    inning: int,
    half: HalfCode,
    start_batting_order: int = 1,
) -> list[AtBatEvent]:
    return [
        _ground_out(inning=inning, half=half, batting_order=start_batting_order + i)
        for i in range(3)
    ]


def _store_with(*events) -> EventStore:
    store = EventStore()
    for ev in events:
        store.append(ev)
    return store


# ---------------------------------------------------------------------------
# Empty store
# ---------------------------------------------------------------------------


def test_empty_store_returns_default_game_state():
    store = EventStore()
    state = derive_state(store)

    assert state.current_inning == 1
    assert state.current_half == HalfCode.TOP
    assert state.outs == 0
    assert state.runners == {}
    assert state.away_score == 0
    assert state.home_score == 0
    assert state.game_over is False


def test_empty_store_batter_index_initialized():
    store = EventStore()
    state = derive_state(store)

    assert state.current_batter_index[HalfCode.TOP] == 0
    assert state.current_batter_index[HalfCode.BOTTOM] == 0


# ---------------------------------------------------------------------------
# Single at-bat out
# ---------------------------------------------------------------------------


def test_single_ground_out_records_one_out():
    store = _store_with(_ground_out())
    state = derive_state(store)

    assert state.outs == 1


def test_single_ground_out_advances_batter_index():
    store = _store_with(_ground_out(half=HalfCode.TOP, batting_order=1))
    state = derive_state(store)

    assert state.current_batter_index[HalfCode.TOP] == 1


def test_single_ground_out_does_not_change_half():
    store = _store_with(_ground_out())
    state = derive_state(store)

    assert state.current_half == HalfCode.TOP
    assert state.current_inning == 1


def test_two_ground_outs_records_two_outs():
    store = _store_with(
        _ground_out(batting_order=1),
        _ground_out(batting_order=2),
    )
    state = derive_state(store)

    assert state.outs == 2


# ---------------------------------------------------------------------------
# Three outs cause half-inning change
# ---------------------------------------------------------------------------


def test_three_outs_in_top_transitions_to_bottom():
    store = _store_with(*_three_ground_outs(inning=1, half=HalfCode.TOP))
    state = derive_state(store)

    assert state.current_half == HalfCode.BOTTOM
    assert state.current_inning == 1
    assert state.outs == 0


def test_three_outs_clears_runners():
    store = EventStore()
    store.append(_single(inning=1, half=HalfCode.TOP, batting_order=1))
    for i in range(3):
        store.append(_ground_out(inning=1, half=HalfCode.TOP, batting_order=i + 2))

    state = derive_state(store)

    assert state.runners == {}


def test_three_outs_resets_out_count():
    store = _store_with(*_three_ground_outs(inning=1, half=HalfCode.TOP))
    state = derive_state(store)

    assert state.outs == 0


# ---------------------------------------------------------------------------
# Full inning: top 3 outs + bottom 3 outs → inning 2
# ---------------------------------------------------------------------------


def test_full_inning_advances_to_inning_2():
    store = EventStore()
    for ev in _three_ground_outs(inning=1, half=HalfCode.TOP):
        store.append(ev)
    for ev in _three_ground_outs(inning=1, half=HalfCode.BOTTOM):
        store.append(ev)

    state = derive_state(store)

    assert state.current_inning == 2
    assert state.current_half == HalfCode.TOP
    assert state.outs == 0


def test_two_full_innings_reaches_inning_3():
    store = EventStore()
    for inning in range(1, 3):
        for half in (HalfCode.TOP, HalfCode.BOTTOM):
            for ev in _three_ground_outs(inning=inning, half=half):
                store.append(ev)

    state = derive_state(store)

    assert state.current_inning == 3
    assert state.current_half == HalfCode.TOP


# ---------------------------------------------------------------------------
# Runner on base — single
# ---------------------------------------------------------------------------


def test_single_places_runner_on_first():
    store = _store_with(_single(inning=1, half=HalfCode.TOP, batting_order=1))
    state = derive_state(store)

    assert BaseCode.FIRST in state.runners
    runner = state.runners[BaseCode.FIRST]
    assert runner.batting_order == 1
    assert runner.at_bat_inning == 1


def test_single_no_runners_on_second_or_third():
    store = _store_with(_single())
    state = derive_state(store)

    assert BaseCode.SECOND not in state.runners
    assert BaseCode.THIRD not in state.runners


def test_single_does_not_score():
    store = _store_with(_single())
    state = derive_state(store)

    assert state.away_score == 0
    assert state.home_score == 0


# ---------------------------------------------------------------------------
# Runner advance
# ---------------------------------------------------------------------------


def test_runner_advance_moves_runner_from_first_to_second():
    store = EventStore()
    store.append(_single(inning=1, half=HalfCode.TOP, batting_order=1))
    store.append(RunnerAdvanceEvent(
        inning=1,
        half=HalfCode.TOP,
        runner_batting_order=1,
        runner_at_bat_inning=1,
        from_base=BaseCode.FIRST,
        to_base=BaseCode.SECOND,
        how=AdvanceType.ON_HIT,
        earned=True,
    ))

    state = derive_state(store)

    assert BaseCode.FIRST not in state.runners
    assert BaseCode.SECOND in state.runners
    assert state.runners[BaseCode.SECOND].batting_order == 1


def test_runner_advance_removes_runner_from_source_base():
    store = EventStore()
    store.append(_single(inning=1, half=HalfCode.TOP, batting_order=1))
    store.append(RunnerAdvanceEvent(
        inning=1,
        half=HalfCode.TOP,
        runner_batting_order=1,
        runner_at_bat_inning=1,
        from_base=BaseCode.FIRST,
        to_base=BaseCode.SECOND,
        how=AdvanceType.ON_HIT,
        earned=True,
    ))

    state = derive_state(store)

    assert BaseCode.FIRST not in state.runners


# ---------------------------------------------------------------------------
# Run scored via RunnerAdvanceEvent
# ---------------------------------------------------------------------------


def test_runner_advance_to_home_scores_run():
    store = EventStore()
    store.append(_single(inning=1, half=HalfCode.TOP, batting_order=1))
    store.append(RunnerAdvanceEvent(
        inning=1,
        half=HalfCode.TOP,
        runner_batting_order=1,
        runner_at_bat_inning=1,
        from_base=BaseCode.FIRST,
        to_base=BaseCode.HOME,
        how=AdvanceType.ON_HIT,
        earned=True,
    ))

    state = derive_state(store)

    assert state.away_score == 1
    assert state.home_score == 0


def test_runner_advance_to_home_removes_runner():
    store = EventStore()
    store.append(_single(inning=1, half=HalfCode.TOP, batting_order=1))
    store.append(RunnerAdvanceEvent(
        inning=1,
        half=HalfCode.TOP,
        runner_batting_order=1,
        runner_at_bat_inning=1,
        from_base=BaseCode.FIRST,
        to_base=BaseCode.HOME,
        how=AdvanceType.ON_HIT,
        earned=True,
    ))

    state = derive_state(store)

    assert BaseCode.FIRST not in state.runners
    assert BaseCode.HOME not in state.runners


def test_bottom_half_run_increments_home_score():
    store = EventStore()
    store.append(_single(inning=1, half=HalfCode.BOTTOM, batting_order=1))
    store.append(RunnerAdvanceEvent(
        inning=1,
        half=HalfCode.BOTTOM,
        runner_batting_order=1,
        runner_at_bat_inning=1,
        from_base=BaseCode.FIRST,
        to_base=BaseCode.HOME,
        how=AdvanceType.ON_HIT,
        earned=True,
    ))

    state = derive_state(store)

    assert state.home_score == 1
    assert state.away_score == 0


# ---------------------------------------------------------------------------
# Home run
# ---------------------------------------------------------------------------


def test_home_run_scores_away_run_in_top_half():
    store = _store_with(_home_run(inning=1, half=HalfCode.TOP, batting_order=1))
    state = derive_state(store)

    assert state.away_score == 1
    assert state.home_score == 0


def test_home_run_batter_does_not_remain_on_base():
    store = _store_with(_home_run())
    state = derive_state(store)

    assert state.runners == {}


def test_home_run_in_bottom_increments_home_score():
    store = _store_with(_home_run(half=HalfCode.BOTTOM))
    state = derive_state(store)

    assert state.home_score == 1
    assert state.away_score == 0


def test_home_run_no_outs_recorded():
    store = _store_with(_home_run())
    state = derive_state(store)

    assert state.outs == 0


# ---------------------------------------------------------------------------
# Stolen base
# ---------------------------------------------------------------------------


def test_stolen_base_moves_runner_from_first_to_second():
    store = EventStore()
    store.append(_single(inning=1, half=HalfCode.TOP, batting_order=1))
    store.append(BaserunnerEvent(
        inning=1,
        half=HalfCode.TOP,
        runner_batting_order=1,
        runner_at_bat_inning=1,
        from_base=BaseCode.FIRST,
        to_base=BaseCode.SECOND,
        how=BaserunnerType.SB,
        earned=True,
        outs_on_play=0,
    ))

    state = derive_state(store)

    assert BaseCode.SECOND in state.runners
    assert BaseCode.FIRST not in state.runners
    assert state.outs == 0


def test_stolen_base_runner_identity_preserved():
    store = EventStore()
    store.append(_single(inning=1, half=HalfCode.TOP, batting_order=3))
    store.append(BaserunnerEvent(
        inning=1,
        half=HalfCode.TOP,
        runner_batting_order=3,
        runner_at_bat_inning=1,
        from_base=BaseCode.FIRST,
        to_base=BaseCode.SECOND,
        how=BaserunnerType.SB,
        earned=True,
        outs_on_play=0,
    ))

    state = derive_state(store)

    assert state.runners[BaseCode.SECOND].batting_order == 3


# ---------------------------------------------------------------------------
# Caught stealing
# ---------------------------------------------------------------------------


def test_caught_stealing_adds_one_out():
    store = EventStore()
    store.append(_single(inning=1, half=HalfCode.TOP, batting_order=1))
    store.append(BaserunnerEvent(
        inning=1,
        half=HalfCode.TOP,
        runner_batting_order=1,
        runner_at_bat_inning=1,
        from_base=BaseCode.FIRST,
        to_base=BaseCode.OUT,
        how=BaserunnerType.CS,
        fielders="2-6",
        earned=True,
        outs_on_play=1,
    ))

    state = derive_state(store)

    assert state.outs == 1


def test_caught_stealing_removes_runner_from_base():
    store = EventStore()
    store.append(_single(inning=1, half=HalfCode.TOP, batting_order=1))
    store.append(BaserunnerEvent(
        inning=1,
        half=HalfCode.TOP,
        runner_batting_order=1,
        runner_at_bat_inning=1,
        from_base=BaseCode.FIRST,
        to_base=BaseCode.OUT,
        how=BaserunnerType.CS,
        earned=True,
        outs_on_play=1,
    ))

    state = derive_state(store)

    assert BaseCode.FIRST not in state.runners


def test_caught_stealing_third_out_triggers_half_inning_change():
    store = EventStore()
    store.append(_single(inning=1, half=HalfCode.TOP, batting_order=1))
    store.append(_ground_out(inning=1, half=HalfCode.TOP, batting_order=2))
    store.append(_ground_out(inning=1, half=HalfCode.TOP, batting_order=3))
    store.append(BaserunnerEvent(
        inning=1,
        half=HalfCode.TOP,
        runner_batting_order=1,
        runner_at_bat_inning=1,
        from_base=BaseCode.FIRST,
        to_base=BaseCode.OUT,
        how=BaserunnerType.CS,
        earned=True,
        outs_on_play=1,
    ))

    state = derive_state(store)

    assert state.current_half == HalfCode.BOTTOM
    assert state.outs == 0


# ---------------------------------------------------------------------------
# LOB calculation
# ---------------------------------------------------------------------------


def test_lob_counts_stranded_runners_after_third_out():
    store = EventStore()
    # Batter 1 singles to first.
    store.append(_single(inning=1, half=HalfCode.TOP, batting_order=1))
    # Advance batter 1 to second *before* batter 2 hits so both bases are
    # occupied simultaneously (the engine stores one runner per base).
    store.append(RunnerAdvanceEvent(
        inning=1,
        half=HalfCode.TOP,
        runner_batting_order=1,
        runner_at_bat_inning=1,
        from_base=BaseCode.FIRST,
        to_base=BaseCode.SECOND,
        how=AdvanceType.ON_HIT,
        earned=True,
    ))
    # Batter 2 singles to first — runners now on first and second.
    store.append(_single(inning=1, half=HalfCode.TOP, batting_order=2))
    # Record 3 outs to end the half-inning, stranding both runners.
    for i in range(3):
        store.append(_ground_out(inning=1, half=HalfCode.TOP, batting_order=i + 3))

    state = derive_state(store)

    inning_stats = state.inning_stats[(1, HalfCode.TOP)]
    assert inning_stats.left_on_base == 2


def test_lob_zero_when_no_runners_stranded():
    store = _store_with(*_three_ground_outs(inning=1, half=HalfCode.TOP))
    state = derive_state(store)

    inning_stats = state.inning_stats.get((1, HalfCode.TOP))
    assert inning_stats is not None
    assert inning_stats.left_on_base == 0


def test_lob_one_runner_stranded():
    store = EventStore()
    store.append(_single(inning=1, half=HalfCode.TOP, batting_order=1))
    for i in range(3):
        store.append(_ground_out(inning=1, half=HalfCode.TOP, batting_order=i + 2))

    state = derive_state(store)

    inning_stats = state.inning_stats[(1, HalfCode.TOP)]
    assert inning_stats.left_on_base == 1


# ---------------------------------------------------------------------------
# Error event
# ---------------------------------------------------------------------------


def test_error_increments_error_count():
    store = _store_with(ErrorEvent(
        inning=1,
        half=HalfCode.TOP,
        fielder_position=__import__(
            "baseball_scorebook.models.constants", fromlist=["Position"]
        ).Position.SS,
        fielder_name="Jones",
    ))
    state = derive_state(store)

    inning_stats = state.inning_stats[(1, HalfCode.TOP)]
    assert inning_stats.errors == 1


def test_multiple_errors_accumulate():
    from baseball_scorebook.models.constants import Position

    store = EventStore()
    store.append(ErrorEvent(inning=1, half=HalfCode.TOP, fielder_position=Position.SS))
    store.append(ErrorEvent(inning=1, half=HalfCode.TOP, fielder_position=Position.FIRST_BASE))

    state = derive_state(store)

    inning_stats = state.inning_stats[(1, HalfCode.TOP)]
    assert inning_stats.errors == 2


def test_error_in_different_half_counted_separately():
    from baseball_scorebook.models.constants import Position

    store = EventStore()
    store.append(ErrorEvent(inning=1, half=HalfCode.TOP, fielder_position=Position.CF))
    store.append(ErrorEvent(inning=1, half=HalfCode.BOTTOM, fielder_position=Position.SS))

    state = derive_state(store)

    top_stats = state.inning_stats[(1, HalfCode.TOP)]
    bottom_stats = state.inning_stats[(1, HalfCode.BOTTOM)]
    assert top_stats.errors == 1
    assert bottom_stats.errors == 1


# ---------------------------------------------------------------------------
# Hit counting
# ---------------------------------------------------------------------------


def test_hit_increments_inning_hits():
    store = _store_with(_single(inning=1, half=HalfCode.TOP, batting_order=1))
    state = derive_state(store)

    inning_stats = state.inning_stats[(1, HalfCode.TOP)]
    assert inning_stats.hits == 1


def test_ground_out_does_not_count_as_hit():
    store = _store_with(_ground_out())
    state = derive_state(store)

    inning_stats = state.inning_stats.get((1, HalfCode.TOP))
    assert inning_stats is not None
    assert inning_stats.hits == 0


def test_multiple_hits_accumulate():
    store = EventStore()
    for i in range(3):
        store.append(_single(batting_order=i + 1))

    state = derive_state(store)

    inning_stats = state.inning_stats[(1, HalfCode.TOP)]
    assert inning_stats.hits == 3


# ---------------------------------------------------------------------------
# Game over detection
# ---------------------------------------------------------------------------


def _simulate_n_full_innings(store: EventStore, n: int) -> None:
    """Append 3 ground outs for each half of n innings."""
    for inning in range(1, n + 1):
        for half in (HalfCode.TOP, HalfCode.BOTTOM):
            for order in range(1, 4):
                store.append(_ground_out(inning=inning, half=half, batting_order=order))


def test_game_over_false_before_9_innings():
    store = EventStore()
    _simulate_n_full_innings(store, 8)
    state = derive_state(store)

    assert check_game_over(state) is False


def test_game_over_false_at_9th_inning_top_when_tied():
    store = EventStore()
    _simulate_n_full_innings(store, 9)
    # After 9 full innings with no scoring, scores are tied
    state = derive_state(store)

    # Scores are equal (0-0), so game is not over
    assert check_game_over(state) is False


def test_game_over_true_after_9_full_innings_away_leads():
    store = EventStore()
    # Away team scores a home run in the top of inning 1 (0 outs on HR).
    # Then 3 ground outs are needed to retire the side (HR doesn't count as an out).
    store.append(_home_run(inning=1, half=HalfCode.TOP, batting_order=1))
    for order in range(2, 5):
        store.append(_ground_out(inning=1, half=HalfCode.TOP, batting_order=order))
    # Bottom of inning 1: 3 outs
    for order in range(1, 4):
        store.append(_ground_out(inning=1, half=HalfCode.BOTTOM, batting_order=order))
    # Innings 2–9 scoreless
    for inning in range(2, 10):
        for half in (HalfCode.TOP, HalfCode.BOTTOM):
            for order in range(1, 4):
                store.append(_ground_out(inning=inning, half=half, batting_order=order))

    state = derive_state(store)

    # After 9 complete innings the engine advances to top of the 10th.
    assert state.current_inning == 10
    assert state.current_half == HalfCode.TOP
    assert state.away_score == 1
    assert state.home_score == 0
    assert check_game_over(state) is True


def test_game_over_walkoff_home_leads_in_bottom_9th():
    store = EventStore()
    # Complete 8.5 innings with no scoring
    _simulate_n_full_innings(store, 8)
    # Top of 9th: 3 outs
    for order in range(1, 4):
        store.append(_ground_out(inning=9, half=HalfCode.TOP, batting_order=order))
    # Bottom of 9th: home team scores (walk-off)
    store.append(_home_run(inning=9, half=HalfCode.BOTTOM, batting_order=1))

    state = derive_state(store)

    # Still in bottom of 9th (walk-off, game not ended by outs)
    assert state.current_half == HalfCode.BOTTOM
    assert state.current_inning == 9
    assert state.home_score == 1
    assert state.away_score == 0
    assert check_game_over(state) is True


def test_game_over_false_bottom_9th_home_team_trailing():
    store = EventStore()
    # Away team scores in top of 9th
    for inning in range(1, 9):
        for half in (HalfCode.TOP, HalfCode.BOTTOM):
            for order in range(1, 4):
                store.append(_ground_out(inning=inning, half=half, batting_order=order))
    store.append(_home_run(inning=9, half=HalfCode.TOP, batting_order=1))
    for order in range(2, 4):
        store.append(_ground_out(inning=9, half=HalfCode.TOP, batting_order=order))
    # Bottom of 9th starts — home team is trailing
    store.append(_ground_out(inning=9, half=HalfCode.BOTTOM, batting_order=1))

    state = derive_state(store)

    assert state.current_half == HalfCode.BOTTOM
    assert state.away_score > state.home_score
    assert check_game_over(state) is False


def test_game_over_false_in_bottom_9th_when_home_tied():
    store = EventStore()
    _simulate_n_full_innings(store, 8)
    for order in range(1, 4):
        store.append(_ground_out(inning=9, half=HalfCode.TOP, batting_order=order))
    # Home team at bat, no score yet → tied
    store.append(_ground_out(inning=9, half=HalfCode.BOTTOM, batting_order=1))

    state = derive_state(store)

    assert state.current_half == HalfCode.BOTTOM
    assert state.home_score == state.away_score
    assert check_game_over(state) is False


def test_check_game_over_is_pure_does_not_set_game_over():
    store = EventStore()
    _simulate_n_full_innings(store, 8)
    for order in range(1, 4):
        store.append(_ground_out(inning=9, half=HalfCode.TOP, batting_order=order))
    store.append(_home_run(inning=9, half=HalfCode.BOTTOM, batting_order=1))

    state = derive_state(store)
    check_game_over(state)  # must not modify state

    assert state.game_over is False
