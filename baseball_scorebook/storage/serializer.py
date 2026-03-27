"""
serializer.py — JSON serialization and deserialization for game data.

Saves and loads the full game state (teams, lineup, event log) to and from a
JSON file.  All enum values are stored as their string ``.value``; frozen
dataclasses are represented as plain dicts.  The event log is stored as an
array of typed dicts distinguished by a ``"type"`` field.

Format version: ``"1.0"``
"""
from __future__ import annotations

import json
from datetime import date as _date
from pathlib import Path
from typing import Any

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
    GameEvent,
    RunnerAdvanceEvent,
    SubstitutionEvent,
)
from baseball_scorebook.models.team import LineupSlot, Player, Team

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FORMAT_VERSION = "1.0"

_EVENT_TYPE_AT_BAT = "at_bat"
_EVENT_TYPE_RUNNER_ADVANCE = "runner_advance"
_EVENT_TYPE_BASERUNNER = "baserunner"
_EVENT_TYPE_SUBSTITUTION = "substitution"
_EVENT_TYPE_ERROR = "error"
_EVENT_TYPE_EDIT = "edit"


# ---------------------------------------------------------------------------
# Directory helpers
# ---------------------------------------------------------------------------


def get_default_save_dir() -> Path:
    """Return ``~/.baseball-scorebook/games/``, creating it if necessary."""
    path = Path.home() / ".baseball-scorebook" / "games"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_autosave_dir() -> Path:
    """Return ``~/.baseball-scorebook/autosave/``, creating it if necessary."""
    path = Path.home() / ".baseball-scorebook" / "autosave"
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_filename(away_name: str, home_name: str, date: str) -> str:
    """Return a filename in the form ``YYYY-MM-DD_Away-vs-Home.json``.

    Args:
        away_name: Display name of the away team.
        home_name: Display name of the home team.
        date: Date string in ``YYYY-MM-DD`` format.  When empty the current
            date is used.

    Returns:
        A filename string (not a full path).
    """
    effective_date = date if date else str(_date.today())
    safe_away = away_name.replace(" ", "-")
    safe_home = home_name.replace(" ", "-")
    return f"{effective_date}_{safe_away}-vs-{safe_home}.json"


# ---------------------------------------------------------------------------
# LineupSlot serialization
# ---------------------------------------------------------------------------


def _serialize_lineup_slot(slot: LineupSlot) -> dict[str, Any]:
    """Serialize a :class:`LineupSlot` to a JSON-compatible dict.

    Args:
        slot: The lineup slot to serialize.

    Returns:
        A plain dict with primitive and string values only.
    """
    return {
        "batting_order": slot.batting_order,
        "name": slot.player.name,
        "number": slot.player.number,
        "player_position": slot.player.position.value,
        "position": slot.position.value,
        "entered_inning": slot.entered_inning,
    }


def _deserialize_lineup_slot(data: dict[str, Any]) -> LineupSlot:
    """Deserialize a dict produced by :func:`_serialize_lineup_slot`.

    Args:
        data: Raw dict from JSON.

    Returns:
        A reconstructed :class:`LineupSlot`.

    Raises:
        KeyError: If a required field is missing.
        ValueError: If an enum value is unrecognized.
    """
    player = Player(
        name=data["name"],
        number=int(data["number"]),
        position=Position(data["player_position"]),
    )
    return LineupSlot(
        batting_order=int(data["batting_order"]),
        player=player,
        position=Position(data["position"]),
        entered_inning=int(data["entered_inning"]),
    )


# ---------------------------------------------------------------------------
# BaseEvent serialization
# ---------------------------------------------------------------------------


def _serialize_base_event(be: BaseEvent) -> dict[str, Any]:
    """Serialize a :class:`BaseEvent` to a JSON-compatible dict.

    Args:
        be: The base event to serialize.

    Returns:
        A plain dict with string enum values.
    """
    return {
        "from_base": be.from_base.value,
        "to_base": be.to_base.value,
        "how": be.how.value,
        "earned": be.earned,
        "rbi": be.rbi,
    }


def _deserialize_base_event(data: dict[str, Any]) -> BaseEvent:
    """Deserialize a dict produced by :func:`_serialize_base_event`.

    Args:
        data: Raw dict from JSON.

    Returns:
        A reconstructed :class:`BaseEvent`.

    Raises:
        KeyError: If a required field is missing.
        ValueError: If an enum value is unrecognized.
    """
    return BaseEvent(
        from_base=BaseCode(data["from_base"]),
        to_base=BaseCode(data["to_base"]),
        how=AdvanceType(data["how"]),
        earned=bool(data["earned"]),
        rbi=bool(data["rbi"]),
    )


# ---------------------------------------------------------------------------
# Event serialization
# ---------------------------------------------------------------------------


def _serialize_event(event: GameEvent) -> dict[str, Any]:
    """Convert a :class:`GameEvent` subclass to a JSON-serializable dict.

    A ``"type"`` discriminator field is always present so that
    :func:`_deserialize_event` can reconstruct the correct subclass.

    Args:
        event: Any supported :class:`GameEvent` subclass.

    Returns:
        A plain dict with only JSON-serializable values.

    Raises:
        TypeError: If *event* is not a recognized subclass.
    """
    base: dict[str, Any] = {
        "event_id": event.event_id,
        "timestamp": event.timestamp,
    }

    if isinstance(event, AtBatEvent):
        return {
            **base,
            "type": _EVENT_TYPE_AT_BAT,
            "inning": event.inning,
            "half": event.half.value,
            "batting_order": event.batting_order,
            "result_type": event.result_type.value,
            "fielders": event.fielders,
            "batter_reached": event.batter_reached,
            "outs_on_play": event.outs_on_play,
            "bases_reached": [_serialize_base_event(be) for be in event.bases_reached],
            "rbi_count": event.rbi_count,
            "notes": event.notes,
        }

    if isinstance(event, RunnerAdvanceEvent):
        return {
            **base,
            "type": _EVENT_TYPE_RUNNER_ADVANCE,
            "inning": event.inning,
            "half": event.half.value,
            "runner_batting_order": event.runner_batting_order,
            "runner_at_bat_inning": event.runner_at_bat_inning,
            "from_base": event.from_base.value,
            "to_base": event.to_base.value,
            "how": event.how.value,
            "earned": event.earned,
            "rbi_batter_order": event.rbi_batter_order,
        }

    if isinstance(event, BaserunnerEvent):
        return {
            **base,
            "type": _EVENT_TYPE_BASERUNNER,
            "inning": event.inning,
            "half": event.half.value,
            "runner_batting_order": event.runner_batting_order,
            "runner_at_bat_inning": event.runner_at_bat_inning,
            "from_base": event.from_base.value,
            "to_base": event.to_base.value,
            "how": event.how.value,
            "fielders": event.fielders,
            "earned": event.earned,
            "outs_on_play": event.outs_on_play,
        }

    if isinstance(event, SubstitutionEvent):
        return {
            **base,
            "type": _EVENT_TYPE_SUBSTITUTION,
            "inning": event.inning,
            "half": event.half.value,
            "team": event.team.value,
            "batting_order": event.batting_order,
            "leaving_name": event.leaving_name,
            "entering_name": event.entering_name,
            "entering_number": event.entering_number,
            "new_position": event.new_position.value,
            "sub_type": event.sub_type.value,
        }

    if isinstance(event, ErrorEvent):
        return {
            **base,
            "type": _EVENT_TYPE_ERROR,
            "inning": event.inning,
            "half": event.half.value,
            "fielder_position": event.fielder_position.value,
            "fielder_name": event.fielder_name,
            "notes": event.notes,
        }

    if isinstance(event, EditEvent):
        return {
            **base,
            "type": _EVENT_TYPE_EDIT,
            "target_event_id": event.target_event_id,
            "corrected_event": _serialize_event(event.corrected_event),
            "reason": event.reason,
        }

    raise TypeError(
        f"_serialize_event: unrecognized event type {type(event).__name__!r}"
    )


def _deserialize_event(data: dict[str, Any]) -> GameEvent:
    """Convert a dict produced by :func:`_serialize_event` back to a
    :class:`GameEvent` subclass.

    Args:
        data: Raw dict from JSON, must contain a ``"type"`` field.

    Returns:
        A reconstructed :class:`GameEvent` subclass instance.

    Raises:
        KeyError: If a required field is missing.
        ValueError: If ``"type"`` or an enum value is unrecognized.
    """
    event_type: str = data["type"]
    event_id: str = data["event_id"]
    timestamp: str = data["timestamp"]

    if event_type == _EVENT_TYPE_AT_BAT:
        bases_reached = tuple(
            _deserialize_base_event(be) for be in data["bases_reached"]
        )
        return AtBatEvent(
            event_id=event_id,
            timestamp=timestamp,
            inning=int(data["inning"]),
            half=HalfCode(data["half"]),
            batting_order=int(data["batting_order"]),
            result_type=ResultType(data["result_type"]),
            fielders=data["fielders"],
            batter_reached=bool(data["batter_reached"]),
            outs_on_play=int(data["outs_on_play"]),
            bases_reached=bases_reached,
            rbi_count=int(data["rbi_count"]),
            notes=data["notes"],
        )

    if event_type == _EVENT_TYPE_RUNNER_ADVANCE:
        rbi_raw = data["rbi_batter_order"]
        return RunnerAdvanceEvent(
            event_id=event_id,
            timestamp=timestamp,
            inning=int(data["inning"]),
            half=HalfCode(data["half"]),
            runner_batting_order=int(data["runner_batting_order"]),
            runner_at_bat_inning=int(data["runner_at_bat_inning"]),
            from_base=BaseCode(data["from_base"]),
            to_base=BaseCode(data["to_base"]),
            how=AdvanceType(data["how"]),
            earned=bool(data["earned"]),
            rbi_batter_order=int(rbi_raw) if rbi_raw is not None else None,
        )

    if event_type == _EVENT_TYPE_BASERUNNER:
        return BaserunnerEvent(
            event_id=event_id,
            timestamp=timestamp,
            inning=int(data["inning"]),
            half=HalfCode(data["half"]),
            runner_batting_order=int(data["runner_batting_order"]),
            runner_at_bat_inning=int(data["runner_at_bat_inning"]),
            from_base=BaseCode(data["from_base"]),
            to_base=BaseCode(data["to_base"]),
            how=BaserunnerType(data["how"]),
            fielders=data["fielders"],
            earned=bool(data["earned"]),
            outs_on_play=int(data["outs_on_play"]),
        )

    if event_type == _EVENT_TYPE_SUBSTITUTION:
        return SubstitutionEvent(
            event_id=event_id,
            timestamp=timestamp,
            inning=int(data["inning"]),
            half=HalfCode(data["half"]),
            team=HalfCode(data["team"]),
            batting_order=int(data["batting_order"]),
            leaving_name=data["leaving_name"],
            entering_name=data["entering_name"],
            entering_number=int(data["entering_number"]),
            new_position=Position(data["new_position"]),
            sub_type=SubType(data["sub_type"]),
        )

    if event_type == _EVENT_TYPE_ERROR:
        return ErrorEvent(
            event_id=event_id,
            timestamp=timestamp,
            inning=int(data["inning"]),
            half=HalfCode(data["half"]),
            fielder_position=Position(data["fielder_position"]),
            fielder_name=data["fielder_name"],
            notes=data["notes"],
        )

    if event_type == _EVENT_TYPE_EDIT:
        corrected = _deserialize_event(data["corrected_event"])
        return EditEvent(
            event_id=event_id,
            timestamp=timestamp,
            target_event_id=data["target_event_id"],
            corrected_event=corrected,
            reason=data["reason"],
        )

    raise ValueError(
        f"_deserialize_event: unrecognized event type {event_type!r}"
    )


# ---------------------------------------------------------------------------
# Team serialization helpers
# ---------------------------------------------------------------------------


def _serialize_team(team: Team) -> dict[str, Any]:
    """Serialize a :class:`Team` to a JSON-compatible dict.

    Args:
        team: The team to serialize.

    Returns:
        A plain dict containing the team name and its starting lineup.
    """
    return {
        "name": team.name,
        "starting_lineup": [_serialize_lineup_slot(slot) for slot in team.lineup],
    }


def _deserialize_team(data: dict[str, Any]) -> Team:
    """Deserialize a dict produced by :func:`_serialize_team`.

    Args:
        data: Raw dict from JSON.

    Returns:
        A reconstructed :class:`Team`.

    Raises:
        KeyError: If a required field is missing.
    """
    slots = tuple(
        _deserialize_lineup_slot(slot_data)
        for slot_data in data["starting_lineup"]
    )
    return Team(name=data["name"], lineup=slots)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def save_game(
    path: str | Path,
    away_team: Team,
    home_team: Team,
    store: EventStore,
    *,
    date: str = "",
    stadium: str = "",
    completed: bool = False,
    notes: str = "",
) -> None:
    """Serialize a game to a JSON file at *path*.

    All parent directories are created automatically if they do not exist.

    Args:
        path: Destination file path.
        away_team: The visiting team.
        home_team: The home team.
        store: The :class:`EventStore` whose full append log is saved.
        date: Optional game date string (``YYYY-MM-DD``).
        stadium: Optional stadium name.
        completed: Whether the game has finished.
        notes: Optional free-form scorekeeper notes.

    Raises:
        OSError: If the file cannot be written.
    """
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "version": _FORMAT_VERSION,
        "date": date,
        "stadium": stadium,
        "away": _serialize_team(away_team),
        "home": _serialize_team(home_team),
        "events": [_serialize_event(event) for event in store.events],
        "completed": completed,
        "notes": notes,
    }

    dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_game(path: str | Path) -> dict[str, Any]:
    """Deserialize a game from a JSON file.

    Args:
        path: Path to the JSON file created by :func:`save_game`.

    Returns:
        A dict with the following keys:

        - ``away_team`` (:class:`Team`)
        - ``home_team`` (:class:`Team`)
        - ``store`` (:class:`EventStore`)
        - ``date`` (str)
        - ``stadium`` (str)
        - ``completed`` (bool)
        - ``notes`` (str)

    Raises:
        FileNotFoundError: If *path* does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
        KeyError: If a required field is absent from the file.
        ValueError: If an enum value or event type is unrecognized.
    """
    src = Path(path)
    raw = json.loads(src.read_text(encoding="utf-8"))

    away_team = _deserialize_team(raw["away"])
    home_team = _deserialize_team(raw["home"])

    store = EventStore()
    for event_data in raw["events"]:
        store.append(_deserialize_event(event_data))

    return {
        "away_team": away_team,
        "home_team": home_team,
        "store": store,
        "date": raw.get("date", ""),
        "stadium": raw.get("stadium", ""),
        "completed": bool(raw.get("completed", False)),
        "notes": raw.get("notes", ""),
    }
