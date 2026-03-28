"""Pure helpers for command defaults and event construction."""

from __future__ import annotations

from dataclasses import asdict

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
    RunnerAdvanceEvent,
    SubstitutionEvent,
)
from baseball_scorebook.models.game import GameState, RunnerInfo
from baseball_scorebook.models.team import Team

_BASE_ORDER: dict[BaseCode, int] = {
    BaseCode.FIRST: 1,
    BaseCode.SECOND: 2,
    BaseCode.THIRD: 3,
    BaseCode.HOME: 4,
    BaseCode.OUT: 5,
}

_PATH_SEGMENTS: tuple[tuple[BaseCode, BaseCode], ...] = (
    (BaseCode.HOME, BaseCode.FIRST),
    (BaseCode.FIRST, BaseCode.SECOND),
    (BaseCode.SECOND, BaseCode.THIRD),
    (BaseCode.THIRD, BaseCode.HOME),
)


def lookup_player_name(batting_order: int, team: Team | None) -> str:
    """Return the player name for a given batting order slot, or ``#N``."""
    if team is None:
        return f"#{batting_order}"
    for slot in team.lineup:
        if slot.batting_order == batting_order:
            return slot.player.name
    return f"#{batting_order}"


def _auto_runner_destination(
    result_type: ResultType,
    from_base: BaseCode,
) -> BaseCode:
    """Compute the default destination for a runner given the result type."""
    if result_type in (ResultType.HOME_RUN, ResultType.TRIPLE):
        return BaseCode.HOME

    if result_type == ResultType.DOUBLE:
        if from_base in (BaseCode.SECOND, BaseCode.THIRD):
            return BaseCode.HOME
        if from_base == BaseCode.FIRST:
            return BaseCode.THIRD
        return from_base

    if result_type == ResultType.SINGLE:
        mapping: dict[BaseCode, BaseCode] = {
            BaseCode.FIRST: BaseCode.SECOND,
            BaseCode.SECOND: BaseCode.THIRD,
            BaseCode.THIRD: BaseCode.HOME,
        }
        return mapping.get(from_base, from_base)

    if result_type in (
        ResultType.WALK,
        ResultType.INTENTIONAL_WALK,
        ResultType.HIT_BY_PITCH,
    ):
        return from_base

    return from_base


def _compute_forced_advances(
    result_type: ResultType,
    runners: dict[BaseCode, RunnerInfo],
) -> dict[BaseCode, BaseCode]:
    """Return forced-advance mapping for walk/HBP results."""
    if result_type not in (
        ResultType.WALK,
        ResultType.INTENTIONAL_WALK,
        ResultType.HIT_BY_PITCH,
    ):
        return {}

    advances: dict[BaseCode, BaseCode] = {}
    if BaseCode.FIRST in runners:
        advances[BaseCode.FIRST] = BaseCode.SECOND
        if BaseCode.SECOND in runners:
            advances[BaseCode.SECOND] = BaseCode.THIRD
            if BaseCode.THIRD in runners:
                advances[BaseCode.THIRD] = BaseCode.HOME
    return advances


def advance_how_for_result(result_type: ResultType) -> AdvanceType:
    """Pick the most appropriate AdvanceType for runners on this result."""
    mapping: dict[ResultType, AdvanceType] = {
        ResultType.SINGLE: AdvanceType.ON_HIT,
        ResultType.DOUBLE: AdvanceType.ON_HIT,
        ResultType.TRIPLE: AdvanceType.ON_HIT,
        ResultType.HOME_RUN: AdvanceType.ON_HIT,
        ResultType.WALK: AdvanceType.ON_BB,
        ResultType.INTENTIONAL_WALK: AdvanceType.ON_BB,
        ResultType.HIT_BY_PITCH: AdvanceType.ON_HBP,
        ResultType.FIELDERS_CHOICE: AdvanceType.ON_FC,
        ResultType.REACHED_ON_ERROR: AdvanceType.ON_ERROR,
        ResultType.SAC_FLY: AdvanceType.ON_SAC,
        ResultType.SAC_BUNT: AdvanceType.ON_SAC,
        ResultType.CATCHERS_INTERFERENCE: AdvanceType.ON_CI,
    }
    return mapping.get(result_type, AdvanceType.ON_HIT)


def build_base_path(
    final_base: BaseCode,
    how: AdvanceType,
    *,
    earned: bool = True,
    rbi: bool = False,
) -> tuple[BaseEvent, ...]:
    """Return the base path from home to the requested final base."""
    if final_base in (BaseCode.OUT, BaseCode.HOME):
        limit = 4 if final_base == BaseCode.HOME else 0
    else:
        limit = _BASE_ORDER[final_base]

    if final_base == BaseCode.OUT:
        return ()

    result: list[BaseEvent] = []
    for index, (from_base, to_base) in enumerate(_PATH_SEGMENTS):
        if index + 1 > limit:
            break
        result.append(
            BaseEvent(
                from_base=from_base,
                to_base=to_base,
                how=how,
                earned=earned,
                rbi=rbi and to_base == BaseCode.HOME,
            )
        )
    return tuple(result)


def get_current_batter_order(state: GameState) -> int:
    """Return the current batter's 1-based lineup slot."""
    return state.current_batter_index[state.current_half] + 1


def get_at_bat_defaults(
    state: GameState,
    batting_team: Team | None,
    result_type: ResultType,
) -> dict[str, object]:
    """Return the canonical default form values for an at-bat draft."""
    batter_order = get_current_batter_order(state)
    forced = _compute_forced_advances(result_type, state.runners)
    batter_default = result_type.batter_default_base
    is_strikeout = result_type in (
        ResultType.STRIKEOUT,
        ResultType.STRIKEOUT_LOOKING,
    )
    runner_defaults: list[dict[str, object]] = []
    for base, runner_info in sorted(
        state.runners.items(),
        key=lambda item: _BASE_ORDER[item[0]],
    ):
        runner_defaults.append(
            {
                "fromBase": base.value,
                "destination": forced.get(
                    base, _auto_runner_destination(result_type, base)
                ).value,
                "runnerBattingOrder": runner_info.batting_order,
                "runnerAtBatInning": runner_info.at_bat_inning,
                "runnerName": lookup_player_name(
                    runner_info.batting_order,
                    batting_team,
                ),
            }
        )

    return {
        "inning": state.current_inning,
        "half": state.current_half.value,
        "battingOrder": batter_order,
        "batterName": lookup_player_name(batter_order, batting_team),
        "resultType": result_type.value,
        "outsOnPlay": result_type.default_outs,
        "batterReachedVisible": is_strikeout,
        "batterReached": False,
        "batterDestination": batter_default.value if batter_default else None,
        "runnerDefaults": runner_defaults,
    }


def create_at_bat_events(
    state: GameState,
    *,
    result_type: ResultType,
    fielders: str = "",
    outs_on_play: int | None = None,
    batter_reached: bool = False,
    batter_destination: BaseCode | None = None,
    runner_advances: list[dict[str, str]] | None = None,
    rbi_count: int = 0,
    notes: str = "",
) -> list[object]:
    """Construct the canonical event list for one at-bat submission."""
    effective_outs = result_type.default_outs if outs_on_play is None else outs_on_play
    batter_order = get_current_batter_order(state)
    advance_how = advance_how_for_result(result_type)

    reaches_by_default = result_type.batter_default_base is not None
    batter_actually_reaches = reaches_by_default or batter_reached
    if result_type in (ResultType.STRIKEOUT, ResultType.STRIKEOUT_LOOKING) and batter_reached:
        effective_outs = 0

    final_batter_base = batter_destination
    if batter_actually_reaches and final_batter_base is None:
        final_batter_base = result_type.batter_default_base or BaseCode.FIRST

    bases_reached = ()
    if batter_actually_reaches and final_batter_base is not None:
        bases_reached = build_base_path(
            final_batter_base,
            advance_how,
            earned=True,
            rbi=rbi_count > 0,
        )

    at_bat = AtBatEvent(
        inning=state.current_inning,
        half=state.current_half,
        batting_order=batter_order,
        result_type=result_type,
        fielders=fielders.strip(),
        batter_reached=batter_actually_reaches,
        outs_on_play=effective_outs,
        bases_reached=bases_reached,
        rbi_count=max(rbi_count, 0),
        notes=notes.strip(),
    )

    runner_events: list[RunnerAdvanceEvent] = []
    requested_advances = runner_advances or []
    runner_map = {base.value: info for base, info in state.runners.items()}
    for advance in requested_advances:
        from_base_value = str(advance["fromBase"])
        to_base_value = str(advance["toBase"])
        runner_info = runner_map.get(from_base_value)
        if runner_info is None or from_base_value == to_base_value:
            continue
        to_base = BaseCode(to_base_value)
        runner_events.append(
            RunnerAdvanceEvent(
                inning=state.current_inning,
                half=state.current_half,
                runner_batting_order=runner_info.batting_order,
                runner_at_bat_inning=runner_info.at_bat_inning,
                from_base=BaseCode(from_base_value),
                to_base=to_base,
                how=advance_how,
                earned=True,
                rbi_batter_order=batter_order if to_base == BaseCode.HOME else None,
            )
        )

    return [at_bat, *runner_events]


def create_baserunner_event(
    state: GameState,
    *,
    from_base: BaseCode,
    to_base: BaseCode,
    how: BaserunnerType,
    fielders: str = "",
) -> BaserunnerEvent:
    """Construct a standalone baserunner event."""
    runner_info = state.runners[from_base]
    is_out = to_base == BaseCode.OUT
    return BaserunnerEvent(
        inning=state.current_inning,
        half=state.current_half,
        runner_batting_order=runner_info.batting_order,
        runner_at_bat_inning=runner_info.at_bat_inning,
        from_base=from_base,
        to_base=to_base,
        how=how,
        fielders=fielders.strip(),
        earned=True,
        outs_on_play=1 if is_out else 0,
    )


def create_substitution_event(
    state: GameState,
    away_team: Team | None,
    home_team: Team | None,
    *,
    team: HalfCode,
    batting_order: int,
    entering_name: str,
    entering_number: int,
    new_position: Position,
    sub_type: SubType,
) -> SubstitutionEvent:
    """Construct a substitution event using the selected lineup slot."""
    source_team = away_team if team == HalfCode.TOP else home_team
    leaving_name = lookup_player_name(batting_order, source_team)
    return SubstitutionEvent(
        inning=state.current_inning,
        half=state.current_half,
        team=team,
        batting_order=batting_order,
        leaving_name=leaving_name,
        entering_name=entering_name.strip(),
        entering_number=entering_number,
        new_position=new_position,
        sub_type=sub_type,
    )

