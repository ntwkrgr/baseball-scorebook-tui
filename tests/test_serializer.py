"""Unit tests for JSON serialization round-trips in storage/serializer.py."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from baseball_scorebook.engine.event_store import EventStore
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
from baseball_scorebook.models.events import (
    AtBatEvent,
    BaserunnerEvent,
    EditEvent,
    ErrorEvent,
    RunnerAdvanceEvent,
    SubstitutionEvent,
)
from baseball_scorebook.models.team import LineupSlot, Player, Team
from baseball_scorebook.storage.serializer import (
    _deserialize_event,
    _serialize_event,
    generate_filename,
    load_game,
    save_game,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_player(name: str = "Player One", number: int = 1, position: Position = Position.CF) -> Player:
    return Player(name=name, number=number, position=position)


def _make_lineup_slot(
    batting_order: int = 1,
    name: str = "Player One",
    number: int = 1,
    player_position: Position = Position.CF,
    slot_position: Position = Position.CF,
    entered_inning: int = 1,
) -> LineupSlot:
    return LineupSlot(
        batting_order=batting_order,
        player=_make_player(name=name, number=number, position=player_position),
        position=slot_position,
        entered_inning=entered_inning,
    )


def _make_team(name: str = "Test Team") -> Team:
    slots = tuple(
        _make_lineup_slot(
            batting_order=i,
            name=f"Player {i}",
            number=i,
            player_position=Position.CF,
            slot_position=Position.CF,
        )
        for i in range(1, 10)
    )
    return Team(name=name, lineup=slots)


def _make_at_bat_event(
    inning: int = 1,
    half: HalfCode = HalfCode.TOP,
    batting_order: int = 1,
    result_type: ResultType = ResultType.GROUND_OUT,
    batter_reached: bool = False,
    outs_on_play: int = 1,
    bases_reached: tuple[BaseEvent, ...] = (),
    fielders: str = "6-3",
    rbi_count: int = 0,
    notes: str = "",
) -> AtBatEvent:
    return AtBatEvent(
        inning=inning,
        half=half,
        batting_order=batting_order,
        result_type=result_type,
        fielders=fielders,
        batter_reached=batter_reached,
        outs_on_play=outs_on_play,
        bases_reached=bases_reached,
        rbi_count=rbi_count,
        notes=notes,
    )


def _make_single_event() -> AtBatEvent:
    return AtBatEvent(
        inning=1,
        half=HalfCode.TOP,
        batting_order=1,
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


def _save_and_load(
    away_team: Team,
    home_team: Team,
    store: EventStore,
    **kwargs,
) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "game.json"
        save_game(path, away_team, home_team, store, **kwargs)
        return load_game(path)


# ---------------------------------------------------------------------------
# Team serialization round-trip
# ---------------------------------------------------------------------------


def test_team_round_trip_name_preserved():
    team = _make_team("Springfield Isotopes")
    result = _save_and_load(team, _make_team("Other"), EventStore())

    assert result["away_team"].name == "Springfield Isotopes"


def test_team_round_trip_lineup_length_preserved():
    team = _make_team()
    result = _save_and_load(team, _make_team(), EventStore())

    assert len(result["away_team"].lineup) == 9


def test_team_round_trip_player_names_preserved():
    team = _make_team("Visitors")
    result = _save_and_load(team, _make_team(), EventStore())

    loaded_names = [slot.player.name for slot in result["away_team"].lineup]
    original_names = [slot.player.name for slot in team.lineup]
    assert loaded_names == original_names


def test_team_round_trip_batting_order_preserved():
    team = _make_team()
    result = _save_and_load(team, _make_team(), EventStore())

    for i, slot in enumerate(result["away_team"].lineup):
        assert slot.batting_order == i + 1


def test_team_round_trip_player_numbers_preserved():
    team = _make_team()
    result = _save_and_load(team, _make_team(), EventStore())

    for original, loaded in zip(team.lineup, result["away_team"].lineup):
        assert loaded.player.number == original.player.number


def test_team_round_trip_positions_preserved():
    team = _make_team()
    result = _save_and_load(team, _make_team(), EventStore())

    for original, loaded in zip(team.lineup, result["away_team"].lineup):
        assert loaded.player.position == original.player.position
        assert loaded.position == original.position


def test_team_round_trip_entered_inning_preserved():
    team = _make_team()
    result = _save_and_load(team, _make_team(), EventStore())

    for original, loaded in zip(team.lineup, result["away_team"].lineup):
        assert loaded.entered_inning == original.entered_inning


def test_both_teams_round_trip_correctly():
    away = _make_team("Away Team")
    home = _make_team("Home Team")
    result = _save_and_load(away, home, EventStore())

    assert result["away_team"].name == "Away Team"
    assert result["home_team"].name == "Home Team"


# ---------------------------------------------------------------------------
# AtBatEvent serialization round-trip
# ---------------------------------------------------------------------------


def test_at_bat_event_type_preserved():
    event = _make_at_bat_event()
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert isinstance(restored, AtBatEvent)


def test_at_bat_event_id_preserved():
    event = _make_at_bat_event()
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert restored.event_id == event.event_id


def test_at_bat_result_type_preserved():
    event = _make_at_bat_event(result_type=ResultType.STRIKEOUT)
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert restored.result_type == ResultType.STRIKEOUT


def test_at_bat_half_preserved():
    event = _make_at_bat_event(half=HalfCode.BOTTOM)
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert restored.half == HalfCode.BOTTOM


def test_at_bat_batter_reached_preserved():
    event = _make_single_event()
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert restored.batter_reached is True


def test_at_bat_outs_on_play_preserved():
    event = _make_at_bat_event(outs_on_play=2, result_type=ResultType.DOUBLE_PLAY)
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert restored.outs_on_play == 2


def test_at_bat_bases_reached_preserved():
    event = _make_single_event()
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert len(restored.bases_reached) == 1
    be = restored.bases_reached[0]
    assert be.from_base == BaseCode.HOME
    assert be.to_base == BaseCode.FIRST
    assert be.how == AdvanceType.ON_HIT
    assert be.earned is True
    assert be.rbi is False


def test_at_bat_rbi_count_preserved():
    event = _make_at_bat_event(rbi_count=2)
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert restored.rbi_count == 2


def test_at_bat_notes_preserved():
    event = _make_at_bat_event(notes="hit hard to left")
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert restored.notes == "hit hard to left"


def test_at_bat_fielders_preserved():
    event = _make_at_bat_event(fielders="5-4-3")
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert restored.fielders == "5-4-3"


def test_at_bat_empty_bases_reached():
    event = _make_at_bat_event()
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert restored.bases_reached == ()


# ---------------------------------------------------------------------------
# RunnerAdvanceEvent serialization round-trip
# ---------------------------------------------------------------------------


def test_runner_advance_event_type_preserved():
    event = RunnerAdvanceEvent(
        inning=2,
        half=HalfCode.BOTTOM,
        runner_batting_order=3,
        runner_at_bat_inning=2,
        from_base=BaseCode.SECOND,
        to_base=BaseCode.THIRD,
        how=AdvanceType.ON_HIT,
        earned=True,
        rbi_batter_order=4,
    )
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert isinstance(restored, RunnerAdvanceEvent)


def test_runner_advance_fields_preserved():
    event = RunnerAdvanceEvent(
        inning=2,
        half=HalfCode.BOTTOM,
        runner_batting_order=3,
        runner_at_bat_inning=2,
        from_base=BaseCode.SECOND,
        to_base=BaseCode.THIRD,
        how=AdvanceType.ON_HIT,
        earned=True,
        rbi_batter_order=4,
    )
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert restored.inning == 2
    assert restored.half == HalfCode.BOTTOM
    assert restored.runner_batting_order == 3
    assert restored.runner_at_bat_inning == 2
    assert restored.from_base == BaseCode.SECOND
    assert restored.to_base == BaseCode.THIRD
    assert restored.how == AdvanceType.ON_HIT
    assert restored.earned is True
    assert restored.rbi_batter_order == 4


def test_runner_advance_rbi_batter_order_none():
    event = RunnerAdvanceEvent(rbi_batter_order=None)
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert restored.rbi_batter_order is None


# ---------------------------------------------------------------------------
# BaserunnerEvent serialization round-trip
# ---------------------------------------------------------------------------


def test_baserunner_event_type_preserved():
    event = BaserunnerEvent(
        inning=3,
        half=HalfCode.TOP,
        runner_batting_order=2,
        runner_at_bat_inning=3,
        from_base=BaseCode.FIRST,
        to_base=BaseCode.SECOND,
        how=BaserunnerType.SB,
        fielders="",
        earned=True,
        outs_on_play=0,
    )
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert isinstance(restored, BaserunnerEvent)


def test_baserunner_event_fields_preserved():
    event = BaserunnerEvent(
        inning=3,
        half=HalfCode.TOP,
        runner_batting_order=2,
        runner_at_bat_inning=3,
        from_base=BaseCode.FIRST,
        to_base=BaseCode.SECOND,
        how=BaserunnerType.SB,
        fielders="",
        earned=True,
        outs_on_play=0,
    )
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert restored.inning == 3
    assert restored.runner_batting_order == 2
    assert restored.how == BaserunnerType.SB
    assert restored.from_base == BaseCode.FIRST
    assert restored.to_base == BaseCode.SECOND
    assert restored.outs_on_play == 0


def test_caught_stealing_event_round_trip():
    event = BaserunnerEvent(
        inning=1,
        half=HalfCode.TOP,
        runner_batting_order=1,
        runner_at_bat_inning=1,
        from_base=BaseCode.FIRST,
        to_base=BaseCode.OUT,
        how=BaserunnerType.CS,
        fielders="2-6",
        earned=False,
        outs_on_play=1,
    )
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert restored.to_base == BaseCode.OUT
    assert restored.how == BaserunnerType.CS
    assert restored.outs_on_play == 1
    assert restored.fielders == "2-6"


# ---------------------------------------------------------------------------
# SubstitutionEvent serialization round-trip
# ---------------------------------------------------------------------------


def test_substitution_event_type_preserved():
    event = SubstitutionEvent(
        inning=5,
        half=HalfCode.BOTTOM,
        team=HalfCode.BOTTOM,
        batting_order=4,
        leaving_name="Old Player",
        entering_name="New Player",
        entering_number=42,
        new_position=Position.LF,
        sub_type=SubType.PINCH_HIT,
    )
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert isinstance(restored, SubstitutionEvent)


def test_substitution_event_fields_preserved():
    event = SubstitutionEvent(
        inning=5,
        half=HalfCode.BOTTOM,
        team=HalfCode.BOTTOM,
        batting_order=4,
        leaving_name="Old Player",
        entering_name="New Player",
        entering_number=42,
        new_position=Position.LF,
        sub_type=SubType.PINCH_HIT,
    )
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert restored.inning == 5
    assert restored.leaving_name == "Old Player"
    assert restored.entering_name == "New Player"
    assert restored.entering_number == 42
    assert restored.new_position == Position.LF
    assert restored.sub_type == SubType.PINCH_HIT


# ---------------------------------------------------------------------------
# ErrorEvent serialization round-trip
# ---------------------------------------------------------------------------


def test_error_event_type_preserved():
    event = ErrorEvent(
        inning=2,
        half=HalfCode.TOP,
        fielder_position=Position.SS,
        fielder_name="Smith",
        notes="dropped routine popup",
    )
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert isinstance(restored, ErrorEvent)


def test_error_event_fields_preserved():
    event = ErrorEvent(
        inning=2,
        half=HalfCode.TOP,
        fielder_position=Position.SS,
        fielder_name="Smith",
        notes="dropped routine popup",
    )
    data = _serialize_event(event)
    restored = _deserialize_event(data)

    assert restored.inning == 2
    assert restored.half == HalfCode.TOP
    assert restored.fielder_position == Position.SS
    assert restored.fielder_name == "Smith"
    assert restored.notes == "dropped routine popup"


# ---------------------------------------------------------------------------
# EditEvent serialization round-trip
# ---------------------------------------------------------------------------


def test_edit_event_type_preserved():
    original = _make_at_bat_event(result_type=ResultType.GROUND_OUT)
    corrected = _make_at_bat_event(result_type=ResultType.SINGLE)
    edit = EditEvent(
        target_event_id=original.event_id,
        corrected_event=corrected,
        reason="wrong result",
    )
    data = _serialize_event(edit)
    restored = _deserialize_event(data)

    assert isinstance(restored, EditEvent)


def test_edit_event_fields_preserved():
    original = _make_at_bat_event(result_type=ResultType.GROUND_OUT)
    corrected = _make_at_bat_event(result_type=ResultType.SINGLE)
    edit = EditEvent(
        target_event_id=original.event_id,
        corrected_event=corrected,
        reason="scorer's correction",
    )
    data = _serialize_event(edit)
    restored = _deserialize_event(data)

    assert restored.target_event_id == original.event_id
    assert restored.reason == "scorer's correction"


def test_edit_event_nested_corrected_event_round_trip():
    original = _make_at_bat_event(result_type=ResultType.GROUND_OUT)
    corrected = _make_single_event()
    edit = EditEvent(
        target_event_id=original.event_id,
        corrected_event=corrected,
        reason="was actually a single",
    )
    data = _serialize_event(edit)
    restored = _deserialize_event(data)

    nested = restored.corrected_event
    assert isinstance(nested, AtBatEvent)
    assert nested.result_type == ResultType.SINGLE
    assert nested.batter_reached is True
    assert len(nested.bases_reached) == 1
    assert nested.bases_reached[0].to_base == BaseCode.FIRST


def test_edit_event_nested_event_id_preserved():
    original = _make_at_bat_event()
    corrected = _make_at_bat_event(result_type=ResultType.WALK)
    edit = EditEvent(
        target_event_id=original.event_id,
        corrected_event=corrected,
    )
    data = _serialize_event(edit)
    restored = _deserialize_event(data)

    assert restored.corrected_event.event_id == corrected.event_id


# ---------------------------------------------------------------------------
# Full save/load round-trip
# ---------------------------------------------------------------------------


def test_save_load_empty_store():
    away = _make_team("Away")
    home = _make_team("Home")
    store = EventStore()

    result = _save_and_load(away, home, store)

    assert len(result["store"]) == 0


def test_save_load_preserves_event_count():
    away = _make_team("Away")
    home = _make_team("Home")
    store = EventStore()
    for i in range(5):
        store.append(_make_at_bat_event(batting_order=i + 1))

    result = _save_and_load(away, home, store)

    assert len(result["store"]) == 5


def test_save_load_preserves_event_order():
    away = _make_team("Away")
    home = _make_team("Home")
    store = EventStore()
    events = [_make_at_bat_event(batting_order=i + 1) for i in range(3)]
    for ev in events:
        store.append(ev)

    result = _save_and_load(away, home, store)

    for original, loaded in zip(events, result["store"].events):
        assert loaded.event_id == original.event_id


def test_save_load_preserves_metadata():
    away = _make_team("Away")
    home = _make_team("Home")
    store = EventStore()

    result = _save_and_load(
        away,
        home,
        store,
        date="2025-07-04",
        stadium="Test Stadium",
        completed=True,
        notes="Game notes here",
    )

    assert result["date"] == "2025-07-04"
    assert result["stadium"] == "Test Stadium"
    assert result["completed"] is True
    assert result["notes"] == "Game notes here"


def test_save_load_mixed_event_types():
    away = _make_team("Away")
    home = _make_team("Home")
    store = EventStore()
    store.append(_make_single_event())
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
    store.append(BaserunnerEvent(
        inning=1,
        half=HalfCode.TOP,
        runner_batting_order=1,
        runner_at_bat_inning=1,
        from_base=BaseCode.SECOND,
        to_base=BaseCode.THIRD,
        how=BaserunnerType.SB,
        earned=True,
        outs_on_play=0,
    ))
    store.append(ErrorEvent(
        inning=1,
        half=HalfCode.TOP,
        fielder_position=Position.SS,
        fielder_name="Jones",
    ))

    result = _save_and_load(away, home, store)

    loaded_events = result["store"].events
    assert isinstance(loaded_events[0], AtBatEvent)
    assert isinstance(loaded_events[1], RunnerAdvanceEvent)
    assert isinstance(loaded_events[2], BaserunnerEvent)
    assert isinstance(loaded_events[3], ErrorEvent)


def test_save_load_edit_event_in_store():
    away = _make_team("Away")
    home = _make_team("Home")
    store = EventStore()
    original = _make_at_bat_event(result_type=ResultType.GROUND_OUT)
    corrected = _make_at_bat_event(result_type=ResultType.SINGLE)
    edit = EditEvent(
        target_event_id=original.event_id,
        corrected_event=corrected,
        reason="fix",
    )
    store.append(original)
    store.append(edit)

    result = _save_and_load(away, home, store)

    loaded_events = result["store"].events
    assert len(loaded_events) == 2
    assert isinstance(loaded_events[1], EditEvent)
    assert loaded_events[1].target_event_id == original.event_id


def test_save_load_effective_events_apply_edits():
    away = _make_team("Away")
    home = _make_team("Home")
    store = EventStore()
    original = _make_at_bat_event(result_type=ResultType.GROUND_OUT)
    corrected = _make_at_bat_event(result_type=ResultType.SINGLE)
    edit = EditEvent(
        target_event_id=original.event_id,
        corrected_event=corrected,
    )
    store.append(original)
    store.append(edit)

    result = _save_and_load(away, home, store)

    effective = result["store"].effective_events()
    assert len(effective) == 1
    assert effective[0].result_type == ResultType.SINGLE


def test_save_creates_parent_directories():
    away = _make_team()
    home = _make_team()
    with tempfile.TemporaryDirectory() as tmpdir:
        nested_path = Path(tmpdir) / "nested" / "dir" / "game.json"
        save_game(nested_path, away, home, EventStore())
        assert nested_path.exists()


def test_load_raises_file_not_found_for_missing_file():
    with pytest.raises(FileNotFoundError):
        load_game("/nonexistent/path/game.json")


def test_serialize_event_raises_type_error_for_unknown_type():
    unknown = object.__new__(type("UnknownEvent", (object,), {}))
    from baseball_scorebook.models.events import GameEvent
    unknown.__class__ = type("Unknown", (GameEvent,), {})

    # Create a raw GameEvent (not a recognized subclass)
    base = GameEvent()
    with pytest.raises(TypeError):
        _serialize_event(base)


def test_deserialize_event_raises_value_error_for_unknown_type():
    import pytest

    with pytest.raises(ValueError):
        _deserialize_event({
            "type": "not_a_real_event_type",
            "event_id": "abc123",
            "timestamp": "2025-01-01T00:00:00+00:00",
        })


# ---------------------------------------------------------------------------
# generate_filename
# ---------------------------------------------------------------------------


def test_generate_filename_with_explicit_date():
    name = generate_filename("Red Sox", "Yankees", "2025-07-04")
    assert name == "2025-07-04_Red-Sox-vs-Yankees.json"


def test_generate_filename_replaces_spaces_with_hyphens():
    name = generate_filename("Team A", "Team B", "2025-01-01")
    assert "Team-A" in name
    assert "Team-B" in name


def test_generate_filename_uses_today_when_date_empty():
    from datetime import date

    name = generate_filename("Away", "Home", "")
    today = str(date.today())
    assert name.startswith(today)


def test_generate_filename_ends_with_json():
    name = generate_filename("X", "Y", "2025-05-01")
    assert name.endswith(".json")


def test_generate_filename_format():
    name = generate_filename("Cubs", "Cardinals", "2025-04-15")
    assert name == "2025-04-15_Cubs-vs-Cardinals.json"
