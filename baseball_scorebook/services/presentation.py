"""Build browser-friendly view snapshots from the game engine."""

from __future__ import annotations

from dataclasses import replace

from baseball_scorebook.engine.state import check_game_over, derive_state
from baseball_scorebook.models.at_bat import DiamondState
from baseball_scorebook.models.constants import (
    BaseCode,
    BaserunnerType,
    HalfCode,
    Position,
    RunnerFinalState,
    SegmentState,
)
from baseball_scorebook.models.events import (
    AtBatEvent,
    BaserunnerEvent,
    ErrorEvent,
    GameEvent,
    RunnerAdvanceEvent,
    SubstitutionEvent,
)
from baseball_scorebook.models.game import GameState, InningStats
from baseball_scorebook.models.team import LineupSlot, Player, Team

_BASE_ORDER: dict[BaseCode, int] = {
    BaseCode.FIRST: 1,
    BaseCode.SECOND: 2,
    BaseCode.THIRD: 3,
    BaseCode.HOME: 4,
    BaseCode.OUT: 5,
}

_POSITION_ORDER: tuple[Position, ...] = (
    Position.P,
    Position.C,
    Position.FIRST_BASE,
    Position.SECOND_BASE,
    Position.THIRD_BASE,
    Position.SS,
    Position.LF,
    Position.CF,
    Position.RF,
)

_HALF_LABELS: dict[HalfCode, str] = {
    HalfCode.TOP: "TOP",
    HalfCode.BOTTOM: "BOT",
}


def _base_sequence(final_base: BaseCode) -> tuple[tuple[BaseCode, BaseCode], ...]:
    mapping: dict[BaseCode, tuple[tuple[BaseCode, BaseCode], ...]] = {
        BaseCode.FIRST: ((BaseCode.HOME, BaseCode.FIRST),),
        BaseCode.SECOND: (
            (BaseCode.HOME, BaseCode.FIRST),
            (BaseCode.FIRST, BaseCode.SECOND),
        ),
        BaseCode.THIRD: (
            (BaseCode.HOME, BaseCode.FIRST),
            (BaseCode.FIRST, BaseCode.SECOND),
            (BaseCode.SECOND, BaseCode.THIRD),
        ),
        BaseCode.HOME: (
            (BaseCode.HOME, BaseCode.FIRST),
            (BaseCode.FIRST, BaseCode.SECOND),
            (BaseCode.SECOND, BaseCode.THIRD),
            (BaseCode.THIRD, BaseCode.HOME),
        ),
    }
    return mapping.get(final_base, ())


def _half_label(half: HalfCode) -> str:
    return _HALF_LABELS[half]


def _inning_prefix(inning: int, half: HalfCode) -> str:
    return f"{inning:>2}{_half_label(half)}"


def format_game_log_event(event: GameEvent) -> str:
    """Format one event as a browser play-by-play line."""
    if isinstance(event, AtBatEvent):
        prefix = _inning_prefix(event.inning, event.half)
        fielders = f" {event.fielders}" if event.fielders else ""
        rbi = f"  {event.rbi_count} RBI" if event.rbi_count > 0 else ""
        notes = f"  [{event.notes}]" if event.notes else ""
        return f"{prefix}  #{event.batting_order}{fielders} {event.result_type.display}{rbi}{notes}"
    if isinstance(event, RunnerAdvanceEvent):
        prefix = _inning_prefix(event.inning, event.half)
        return (
            f"{prefix}  Runner #{event.runner_batting_order}: "
            f"{event.from_base.value}\u2192{event.to_base.value}"
        )
    if isinstance(event, BaserunnerEvent):
        prefix = _inning_prefix(event.inning, event.half)
        fielders = f" ({event.fielders})" if event.fielders else ""
        return (
            f"{prefix}  #{event.runner_batting_order} {event.how.value}{fielders}: "
            f"{event.from_base.value}\u2192{event.to_base.value}"
        )
    if isinstance(event, SubstitutionEvent):
        prefix = _inning_prefix(event.inning, event.half)
        return (
            f"{prefix}  SUB ({event.sub_type.value}): "
            f"#{event.entering_number} {event.entering_name} for {event.leaving_name}"
        )
    return ""


def _team_to_dict(team: Team) -> dict[str, object]:
    return {
        "name": team.name,
        "lineup": [
            {
                "battingOrder": slot.batting_order,
                "playerName": slot.player.name,
                "playerNumber": slot.player.number,
                "position": slot.position.display,
                "enteredInning": slot.entered_inning,
            }
            for slot in sorted(team.lineup, key=lambda item: item.batting_order)
        ],
    }


def _apply_substitutions(
    away_team: Team,
    home_team: Team,
    events: tuple[GameEvent, ...],
) -> tuple[Team, Team]:
    away_slots = list(away_team.lineup)
    home_slots = list(home_team.lineup)
    for event in events:
        if not isinstance(event, SubstitutionEvent):
            continue
        target = away_slots if event.team == HalfCode.TOP else home_slots
        replacement = LineupSlot(
            batting_order=event.batting_order,
            player=Player(
                name=event.entering_name,
                number=event.entering_number,
                position=event.new_position,
            ),
            position=event.new_position,
            entered_inning=event.inning,
        )
        for index, slot in enumerate(target):
            if slot.batting_order == event.batting_order:
                target[index] = replacement
                break
    return (
        Team(name=away_team.name, lineup=tuple(sorted(away_slots, key=lambda item: item.batting_order))),
        Team(name=home_team.name, lineup=tuple(sorted(home_slots, key=lambda item: item.batting_order))),
    )


def _build_defense(team: Team) -> list[dict[str, object]]:
    position_map: dict[Position, LineupSlot] = {}
    for slot in team.lineup:
        existing = position_map.get(slot.position)
        if existing is None or slot.entered_inning > existing.entered_inning:
            position_map[slot.position] = slot
    result: list[dict[str, object]] = []
    for position in _POSITION_ORDER:
        slot = position_map.get(position)
        result.append(
            {
                "number": position.value,
                "position": position.display,
                "playerName": slot.player.name if slot else "—",
                "playerNumber": slot.player.number if slot else None,
            }
        )
    return result


def _make_cell(event: AtBatEvent) -> dict[str, object]:
    if event.batter_reached:
        final_base = (
            event.bases_reached[-1].to_base
            if event.bases_reached
            else (event.result_type.batter_default_base or BaseCode.FIRST)
        )
        final_state = (
            RunnerFinalState.SCORED
            if final_base == BaseCode.HOME
            else RunnerFinalState.RUNNING
        )
    else:
        final_base = BaseCode.HOME
        final_state = RunnerFinalState.OUT

    segments: list[dict[str, str]] = []
    if event.bases_reached:
        for base_event in event.bases_reached:
            segments.append(
                {
                    "fromBase": base_event.from_base.value,
                    "toBase": base_event.to_base.value,
                    "state": (
                        SegmentState.SCORED.value
                        if base_event.to_base == BaseCode.HOME
                        else SegmentState.LIT.value
                    ),
                }
            )
    elif event.batter_reached:
        for from_base, to_base in _base_sequence(final_base):
            segments.append(
                {
                    "fromBase": from_base.value,
                    "toBase": to_base.value,
                    "state": (
                        SegmentState.SCORED.value
                        if to_base == BaseCode.HOME
                        else SegmentState.LIT.value
                    ),
                }
            )

    return {
        "key": f"{event.half.value}-{event.batting_order}-{event.inning}",
        "inning": event.inning,
        "battingOrder": event.batting_order,
        "half": event.half.value,
        "resultType": event.result_type.value,
        "resultDisplay": event.result_type.display,
        "fielders": event.fielders,
        "annotations": [],
        "segments": segments,
        "finalBase": final_base.value,
        "finalState": final_state.value,
        "notes": event.notes,
    }


def _update_final(cell: dict[str, object], to_base: BaseCode, *, out_from_base: BaseCode | None = None) -> None:
    if to_base == BaseCode.HOME:
        cell["finalBase"] = BaseCode.HOME.value
        cell["finalState"] = RunnerFinalState.SCORED.value
        return
    if to_base == BaseCode.OUT:
        cell["finalBase"] = (out_from_base or BaseCode.HOME).value
        cell["finalState"] = RunnerFinalState.OUT.value
        return
    cell["finalBase"] = to_base.value
    cell["finalState"] = RunnerFinalState.RUNNING.value


def _mark_left_on_base(runners: dict[BaseCode, tuple[HalfCode, int, int]], cells: dict[tuple[HalfCode, int, int], dict[str, object]]) -> None:
    for base, key in runners.items():
        cell = cells.get(key)
        if cell is None:
            continue
        cell["finalBase"] = base.value
        cell["finalState"] = RunnerFinalState.LEFT_ON_BASE.value


def _build_scorecards(
    away_team: Team,
    home_team: Team,
    events: tuple[GameEvent, ...],
) -> dict[str, dict[str, object]]:
    cells: dict[tuple[HalfCode, int, int], dict[str, object]] = {}
    active_runners: dict[BaseCode, tuple[HalfCode, int, int]] = {}
    outs = 0

    for event in events:
        if isinstance(event, AtBatEvent):
            key = (event.half, event.batting_order, event.inning)
            cell = _make_cell(event)
            cells[key] = cell
            if event.batter_reached:
                final_base = BaseCode(cell["finalBase"])
                if final_base not in (BaseCode.HOME, BaseCode.OUT):
                    active_runners[final_base] = key
            outs += event.outs_on_play
            if outs >= 3:
                _mark_left_on_base(active_runners, cells)
                active_runners.clear()
                outs = 0
            continue

        if isinstance(event, RunnerAdvanceEvent):
            key = active_runners.pop(
                event.from_base,
                (event.half, event.runner_batting_order, event.runner_at_bat_inning),
            )
            cell = cells.get(key)
            if cell is None:
                continue
            segments = list(cell["segments"])
            segments.append(
                {
                    "fromBase": event.from_base.value,
                    "toBase": event.to_base.value,
                    "state": (
                        SegmentState.SCORED.value
                        if event.to_base == BaseCode.HOME
                        else SegmentState.LIT.value
                    ),
                }
            )
            cell["segments"] = segments
            _update_final(cell, event.to_base, out_from_base=event.from_base)
            if event.to_base not in (BaseCode.HOME, BaseCode.OUT):
                active_runners[event.to_base] = key
            if event.to_base == BaseCode.OUT:
                outs += 1
                if outs >= 3:
                    _mark_left_on_base(active_runners, cells)
                    active_runners.clear()
                    outs = 0
            continue

        if isinstance(event, BaserunnerEvent):
            key = active_runners.pop(
                event.from_base,
                (event.half, event.runner_batting_order, event.runner_at_bat_inning),
            )
            cell = cells.get(key)
            if cell is None:
                continue
            segments = list(cell["segments"])
            segments.append(
                {
                    "fromBase": event.from_base.value,
                    "toBase": event.to_base.value,
                    "state": (
                        SegmentState.SCORED.value
                        if event.to_base == BaseCode.HOME
                        else SegmentState.LIT.value
                    ),
                }
            )
            cell["segments"] = segments
            annotations = list(cell["annotations"])
            label = event.how.value
            if event.fielders:
                label = f"{label} {event.fielders}"
            annotations.append(label)
            cell["annotations"] = annotations[-3:]
            _update_final(cell, event.to_base, out_from_base=event.from_base)
            if event.to_base not in (BaseCode.HOME, BaseCode.OUT):
                active_runners[event.to_base] = key
            if event.to_base == BaseCode.OUT:
                outs += event.outs_on_play
                if outs >= 3:
                    _mark_left_on_base(active_runners, cells)
                    active_runners.clear()
                    outs = 0

    def build_team_card(team: Team, half: HalfCode) -> dict[str, object]:
        innings = sorted({inning for (cell_half, _, inning) in cells if cell_half == half})
        if not innings:
            innings = list(range(1, 10))
        else:
            innings = list(range(1, max(max(innings), 9) + 1))
        rows: list[dict[str, object]] = []
        for slot in sorted(team.lineup, key=lambda item: item.batting_order):
            row_cells: list[dict[str, object] | None] = []
            for inning in innings:
                row_cells.append(cells.get((half, slot.batting_order, inning)))
            rows.append(
                {
                    "battingOrder": slot.batting_order,
                    "playerName": slot.player.name,
                    "playerNumber": slot.player.number,
                    "position": slot.position.display,
                    "cells": row_cells,
                }
            )
        return {
            "teamName": team.name,
            "innings": innings,
            "rows": rows,
        }

    return {
        "away": build_team_card(away_team, HalfCode.TOP),
        "home": build_team_card(home_team, HalfCode.BOTTOM),
    }


def _build_scoreline(state: GameState, away_name: str, home_name: str) -> dict[str, object]:
    innings = sorted({inning for (inning, _) in state.inning_stats})
    inning_list = list(range(1, max(max(innings, default=0), 9) + 1))

    def runs_for(half: HalfCode) -> list[int | None]:
        result: list[int | None] = []
        for inning in inning_list:
            stats = state.inning_stats.get((inning, half))
            if stats is not None:
                result.append(stats.runs)
            elif inning < state.current_inning or (
                inning == state.current_inning and state.current_half == HalfCode.BOTTOM and half == HalfCode.TOP
            ):
                result.append(0)
            elif inning < state.current_inning and half == HalfCode.BOTTOM:
                result.append(0)
            else:
                result.append(None)
        return result

    away_hits = away_errors = home_hits = home_errors = 0
    for (_, half), stats in state.inning_stats.items():
        if half == HalfCode.TOP:
            away_hits += stats.hits
            away_errors += stats.errors
        else:
            home_hits += stats.hits
            home_errors += stats.errors

    return {
        "innings": inning_list,
        "awayName": away_name,
        "homeName": home_name,
        "awayRunsByInning": runs_for(HalfCode.TOP),
        "homeRunsByInning": runs_for(HalfCode.BOTTOM),
        "totals": {
            "away": {"R": state.away_score, "H": away_hits, "E": away_errors},
            "home": {"R": state.home_score, "H": home_hits, "E": home_errors},
        },
        "active": {
            "inning": state.current_inning,
            "half": state.current_half.value,
        },
    }


def _build_inning_totals(state: GameState, half: HalfCode) -> dict[str, object]:
    innings = sorted(inning for (inning, h) in state.inning_stats if h == half)
    rows: dict[str, list[int]] = {"R": [], "H": [], "E": [], "LOB": []}
    totals = {"R": 0, "H": 0, "E": 0, "LOB": 0}
    for inning in innings:
        stats = state.inning_stats[(inning, half)]
        rows["R"].append(stats.runs)
        rows["H"].append(stats.hits)
        rows["E"].append(stats.errors)
        rows["LOB"].append(stats.left_on_base)
        totals["R"] += stats.runs
        totals["H"] += stats.hits
        totals["E"] += stats.errors
        totals["LOB"] += stats.left_on_base
    return {"innings": innings, "rows": rows, "totals": totals}


def build_transition_summary(
    state: GameState,
    away_name: str,
    home_name: str,
    completed_inning: int,
    completed_half: HalfCode,
) -> dict[str, object]:
    """Build the payload shown in the half-inning transition overlay."""
    stats = state.inning_stats.get((completed_inning, completed_half), InningStats())
    return {
        "completedInning": completed_inning,
        "completedHalf": completed_half.value,
        "battingTeam": away_name if completed_half == HalfCode.TOP else home_name,
        "stats": {
            "R": stats.runs,
            "H": stats.hits,
            "E": stats.errors,
            "LOB": stats.left_on_base,
        },
        "score": {
            "away": state.away_score,
            "home": state.home_score,
            "awayName": away_name,
            "homeName": home_name,
        },
    }


def build_game_snapshot(
    session_id: str,
    away_team: Team,
    home_team: Team,
    store,
    *,
    pending_transition: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the canonical snapshot returned to the browser."""
    effective_events = store.effective_events()
    state = derive_state(store)
    live_away, live_home = _apply_substitutions(away_team, home_team, effective_events)
    active_team = live_away if state.current_half == HalfCode.TOP else live_home
    current_batter_order = state.current_batter_index[state.current_half] + 1
    current_batter_name = next(
        (
            slot.player.name
            for slot in active_team.lineup
            if slot.batting_order == current_batter_order
        ),
        f"#{current_batter_order}",
    )

    return {
        "sessionId": session_id,
        "teams": {
            "away": _team_to_dict(live_away),
            "home": _team_to_dict(live_home),
        },
        "rawEventCount": len(store.events),
        "effectiveEventCount": len(effective_events),
        "state": {
            "currentInning": state.current_inning,
            "currentHalf": state.current_half.value,
            "outs": state.outs,
            "awayScore": state.away_score,
            "homeScore": state.home_score,
            "runners": [
                {
                    "base": base.value,
                    "battingOrder": info.batting_order,
                    "atBatInning": info.at_bat_inning,
                }
                for base, info in sorted(
                    state.runners.items(),
                    key=lambda item: _BASE_ORDER[item[0]],
                )
            ],
            "currentBatter": {
                "battingOrder": current_batter_order,
                "name": current_batter_name,
            },
            "statusLine": (
                f"Inning {state.current_inning} "
                f"{'TOP' if state.current_half == HalfCode.TOP else 'BOT'}"
                f"  |  Outs {state.outs}"
                f"  |  {live_away.name} {state.away_score} - {live_home.name} {state.home_score}"
            ),
        },
        "scoreline": _build_scoreline(state, live_away.name, live_home.name),
        "inningTotals": {
            "away": _build_inning_totals(state, HalfCode.TOP),
            "home": _build_inning_totals(state, HalfCode.BOTTOM),
        },
        "scorecards": _build_scorecards(live_away, live_home, effective_events),
        "defense": {
            "away": _build_defense(live_away),
            "home": _build_defense(live_home),
        },
        "gameLog": [
            {
                "id": getattr(event, "event_id", str(index)),
                "text": line,
            }
            for index, event in enumerate(effective_events)
            if (line := format_game_log_event(event))
        ],
        "gameOver": check_game_over(state),
        "pendingTransition": pending_transition,
    }

