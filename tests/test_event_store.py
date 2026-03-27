"""Unit tests for EventStore append-only event log with undo/redo support."""
from __future__ import annotations

from baseball_scorebook.engine.event_store import EventStore
from baseball_scorebook.models.at_bat import BaseEvent
from baseball_scorebook.models.constants import AdvanceType, BaseCode, HalfCode, ResultType
from baseball_scorebook.models.events import (
    AtBatEvent,
    EditEvent,
    GameEvent,
    RunnerAdvanceEvent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_at_bat(
    inning: int = 1,
    half: HalfCode = HalfCode.TOP,
    batting_order: int = 1,
    result_type: ResultType = ResultType.GROUND_OUT,
) -> AtBatEvent:
    return AtBatEvent(
        inning=inning,
        half=half,
        batting_order=batting_order,
        result_type=result_type,
        batter_reached=False,
        outs_on_play=1,
    )


def _make_single(
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


def _make_runner_advance(
    inning: int = 1,
    half: HalfCode = HalfCode.TOP,
    runner_batting_order: int = 1,
    from_base: BaseCode = BaseCode.FIRST,
    to_base: BaseCode = BaseCode.SECOND,
) -> RunnerAdvanceEvent:
    return RunnerAdvanceEvent(
        inning=inning,
        half=half,
        runner_batting_order=runner_batting_order,
        runner_at_bat_inning=inning,
        from_base=from_base,
        to_base=to_base,
        how=AdvanceType.ON_HIT,
        earned=True,
    )


def _populated_store(count: int = 3) -> EventStore:
    store = EventStore()
    for i in range(count):
        store.append(_make_at_bat(batting_order=i + 1))
    return store


# ---------------------------------------------------------------------------
# append / events
# ---------------------------------------------------------------------------


def test_new_store_is_empty():
    store = EventStore()
    assert store.events == ()


def test_append_single_event():
    store = EventStore()
    event = _make_at_bat()
    store.append(event)
    assert len(store.events) == 1
    assert store.events[0] is event


def test_append_preserves_order():
    store = EventStore()
    events = [_make_at_bat(batting_order=i + 1) for i in range(5)]
    for ev in events:
        store.append(ev)
    for i, ev in enumerate(events):
        assert store.events[i] is ev


def test_events_returns_immutable_tuple():
    store = _populated_store(2)
    result = store.events
    assert isinstance(result, tuple)


def test_events_snapshot_does_not_change_after_append():
    store = _populated_store(2)
    snapshot = store.events
    store.append(_make_at_bat(batting_order=3))
    assert len(snapshot) == 2  # original snapshot unchanged


# ---------------------------------------------------------------------------
# undo
# ---------------------------------------------------------------------------


def test_undo_removes_last_event():
    store = _populated_store(3)
    last = store.events[-1]
    removed = store.undo()
    assert removed is last
    assert len(store.events) == 2


def test_undo_returns_none_on_empty_store():
    store = EventStore()
    assert store.undo() is None


def test_undo_sequential():
    store = _populated_store(3)
    events = list(store.events)
    store.undo()
    store.undo()
    assert len(store.events) == 1
    assert store.events[0] is events[0]


def test_undo_all_events_leaves_empty_store():
    store = _populated_store(3)
    store.undo()
    store.undo()
    store.undo()
    assert store.events == ()


def test_undo_on_already_empty_store_returns_none():
    store = _populated_store(2)
    store.undo()
    store.undo()
    result = store.undo()
    assert result is None


# ---------------------------------------------------------------------------
# redo
# ---------------------------------------------------------------------------


def test_redo_reappends_undone_event():
    store = _populated_store(2)
    removed = store.undo()
    reappended = store.redo()
    assert reappended is removed
    assert len(store.events) == 2


def test_redo_returns_none_on_empty_redo_stack():
    store = _populated_store(2)
    assert store.redo() is None


def test_redo_multiple_events_in_order():
    store = _populated_store(3)
    original_events = list(store.events)
    store.undo()
    store.undo()
    store.undo()
    store.redo()
    store.redo()
    store.redo()
    assert list(store.events) == original_events


def test_redo_stack_exhausted_after_all_redos():
    store = _populated_store(2)
    store.undo()
    store.undo()
    store.redo()
    store.redo()
    assert store.redo() is None


# ---------------------------------------------------------------------------
# append clears redo stack
# ---------------------------------------------------------------------------


def test_append_after_undo_clears_redo_stack():
    store = _populated_store(2)
    store.undo()
    store.append(_make_at_bat(batting_order=99))
    assert store.redo() is None


def test_append_after_undo_adds_new_event_not_undone_event():
    store = _populated_store(2)
    store.undo()
    new_event = _make_at_bat(batting_order=99)
    store.append(new_event)
    assert store.events[-1] is new_event
    assert len(store.events) == 2


def test_redo_impossible_after_new_append():
    store = _populated_store(3)
    store.undo()
    store.undo()
    store.append(_make_at_bat(batting_order=50))
    assert store.redo() is None


# ---------------------------------------------------------------------------
# effective_events — no EditEvents present
# ---------------------------------------------------------------------------


def test_effective_events_equals_events_when_no_edits():
    store = _populated_store(3)
    assert store.effective_events() == store.events


def test_effective_events_empty_store():
    store = EventStore()
    assert store.effective_events() == ()


# ---------------------------------------------------------------------------
# effective_events — EditEvent correction
# ---------------------------------------------------------------------------


def test_edit_event_replaces_target_in_effective_events():
    store = EventStore()
    original = _make_at_bat(batting_order=1, result_type=ResultType.GROUND_OUT)
    store.append(original)

    corrected = AtBatEvent(
        event_id=original.event_id,
        timestamp=original.timestamp,
        inning=1,
        half=HalfCode.TOP,
        batting_order=1,
        result_type=ResultType.SINGLE,
        batter_reached=True,
        outs_on_play=0,
    )
    edit = EditEvent(
        target_event_id=original.event_id,
        corrected_event=corrected,
        reason="scorer correction",
    )
    store.append(edit)

    effective = store.effective_events()
    assert len(effective) == 1
    assert effective[0] is corrected


def test_edit_event_excluded_from_effective_events():
    store = EventStore()
    original = _make_at_bat(batting_order=1)
    store.append(original)

    corrected = _make_at_bat(batting_order=1, result_type=ResultType.WALK)
    edit = EditEvent(
        target_event_id=original.event_id,
        corrected_event=corrected,
    )
    store.append(edit)

    effective = store.effective_events()
    assert not any(isinstance(e, EditEvent) for e in effective)


def test_edit_event_raw_log_still_contains_original_and_edit():
    store = EventStore()
    original = _make_at_bat()
    store.append(original)

    corrected = _make_at_bat(result_type=ResultType.STRIKEOUT)
    edit = EditEvent(
        target_event_id=original.event_id,
        corrected_event=corrected,
    )
    store.append(edit)

    raw = store.events
    assert len(raw) == 2
    assert raw[0] is original
    assert raw[1] is edit


def test_multiple_edit_events_last_one_wins():
    store = EventStore()
    original = _make_at_bat(batting_order=1, result_type=ResultType.GROUND_OUT)
    store.append(original)

    first_correction = _make_at_bat(batting_order=1, result_type=ResultType.SINGLE)
    second_correction = _make_at_bat(batting_order=1, result_type=ResultType.DOUBLE)

    store.append(EditEvent(
        target_event_id=original.event_id,
        corrected_event=first_correction,
        reason="first attempt",
    ))
    store.append(EditEvent(
        target_event_id=original.event_id,
        corrected_event=second_correction,
        reason="second attempt wins",
    ))

    effective = store.effective_events()
    assert len(effective) == 1
    assert effective[0] is second_correction


def test_three_edit_events_last_one_wins():
    store = EventStore()
    original = _make_at_bat(result_type=ResultType.GROUND_OUT)
    store.append(original)

    corrections = [
        _make_at_bat(result_type=ResultType.SINGLE),
        _make_at_bat(result_type=ResultType.DOUBLE),
        _make_at_bat(result_type=ResultType.TRIPLE),
    ]
    for c in corrections:
        store.append(EditEvent(target_event_id=original.event_id, corrected_event=c))

    effective = store.effective_events()
    assert effective[0] is corrections[-1]


def test_edit_event_does_not_affect_other_events():
    store = EventStore()
    event_a = _make_at_bat(batting_order=1)
    event_b = _make_at_bat(batting_order=2)
    event_c = _make_at_bat(batting_order=3)
    store.append(event_a)
    store.append(event_b)
    store.append(event_c)

    corrected_b = _make_at_bat(batting_order=2, result_type=ResultType.WALK)
    store.append(EditEvent(target_event_id=event_b.event_id, corrected_event=corrected_b))

    effective = store.effective_events()
    assert len(effective) == 3
    assert effective[0] is event_a
    assert effective[1] is corrected_b
    assert effective[2] is event_c


def test_effective_events_with_edit_event_targeting_nonexistent_id():
    store = EventStore()
    real_event = _make_at_bat(batting_order=1)
    store.append(real_event)

    phantom_target = "00000000-0000-0000-0000-000000000000"
    orphan_correction = _make_at_bat(batting_order=9)
    store.append(EditEvent(
        target_event_id=phantom_target,
        corrected_event=orphan_correction,
    ))

    effective = store.effective_events()
    assert len(effective) == 1
    assert effective[0] is real_event


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


def test_clear_empties_events():
    store = _populated_store(3)
    store.clear()
    assert store.events == ()


def test_clear_empties_redo_stack():
    store = _populated_store(3)
    store.undo()
    store.clear()
    assert store.redo() is None


def test_clear_on_empty_store_is_safe():
    store = EventStore()
    store.clear()
    assert store.events == ()


def test_clear_then_append_works():
    store = _populated_store(3)
    store.clear()
    new_event = _make_at_bat()
    store.append(new_event)
    assert len(store.events) == 1
    assert store.events[0] is new_event


# ---------------------------------------------------------------------------
# __len__ and __bool__
# ---------------------------------------------------------------------------


def test_len_empty_store():
    assert len(EventStore()) == 0


def test_len_after_appends():
    store = _populated_store(5)
    assert len(store) == 5


def test_len_after_undo():
    store = _populated_store(3)
    store.undo()
    assert len(store) == 2


def test_len_after_redo():
    store = _populated_store(3)
    store.undo()
    store.redo()
    assert len(store) == 3


def test_bool_false_when_empty():
    assert not EventStore()


def test_bool_true_after_append():
    store = EventStore()
    store.append(_make_at_bat())
    assert bool(store) is True


def test_bool_false_after_clear():
    store = _populated_store(3)
    store.clear()
    assert not store


def test_bool_false_after_all_undos():
    store = _populated_store(2)
    store.undo()
    store.undo()
    assert not store
