"""Unit tests for ResultType enum properties in constants.py."""
from __future__ import annotations

import pytest

from baseball_scorebook.models.constants import BaseCode, ResultType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALL_RESULT_TYPES = list(ResultType)

_COUNTS_AS_AB_TRUE = {
    ResultType.SINGLE,
    ResultType.DOUBLE,
    ResultType.TRIPLE,
    ResultType.HOME_RUN,
    ResultType.STRIKEOUT,
    ResultType.STRIKEOUT_LOOKING,
    ResultType.GROUND_OUT,
    ResultType.FLY_OUT,
    ResultType.FOUL_OUT,
    ResultType.LINE_OUT,
    ResultType.DOUBLE_PLAY,
    ResultType.TRIPLE_PLAY,
    ResultType.FIELDERS_CHOICE,
    ResultType.REACHED_ON_ERROR,
}

_COUNTS_AS_AB_FALSE = {
    ResultType.WALK,
    ResultType.INTENTIONAL_WALK,
    ResultType.HIT_BY_PITCH,
    ResultType.SAC_FLY,
    ResultType.SAC_BUNT,
    ResultType.CATCHERS_INTERFERENCE,
}

_COUNTS_AS_HIT_TRUE = {
    ResultType.SINGLE,
    ResultType.DOUBLE,
    ResultType.TRIPLE,
    ResultType.HOME_RUN,
}

_COUNTS_AS_OUT_TRUE = {
    ResultType.STRIKEOUT,
    ResultType.STRIKEOUT_LOOKING,
    ResultType.GROUND_OUT,
    ResultType.FLY_OUT,
    ResultType.FOUL_OUT,
    ResultType.LINE_OUT,
    ResultType.DOUBLE_PLAY,
    ResultType.TRIPLE_PLAY,
    ResultType.SAC_FLY,
    ResultType.SAC_BUNT,
}

_EXPECTED_DISPLAYS = {
    ResultType.SINGLE: "1B",
    ResultType.DOUBLE: "2B",
    ResultType.TRIPLE: "3B",
    ResultType.HOME_RUN: "HR",
    ResultType.WALK: "BB",
    ResultType.INTENTIONAL_WALK: "IBB",
    ResultType.HIT_BY_PITCH: "HBP",
    ResultType.STRIKEOUT: "K",
    ResultType.STRIKEOUT_LOOKING: "Kl",
    ResultType.GROUND_OUT: "GB",
    ResultType.FLY_OUT: "FB",
    ResultType.FOUL_OUT: "F",
    ResultType.LINE_OUT: "L",
    ResultType.DOUBLE_PLAY: "DP",
    ResultType.TRIPLE_PLAY: "TP",
    ResultType.SAC_FLY: "SF",
    ResultType.SAC_BUNT: "SAC",
    ResultType.FIELDERS_CHOICE: "FC",
    ResultType.REACHED_ON_ERROR: "E",
    ResultType.CATCHERS_INTERFERENCE: "CI",
}

_EXPECTED_DEFAULT_OUTS = {
    ResultType.SINGLE: 0,
    ResultType.DOUBLE: 0,
    ResultType.TRIPLE: 0,
    ResultType.HOME_RUN: 0,
    ResultType.WALK: 0,
    ResultType.INTENTIONAL_WALK: 0,
    ResultType.HIT_BY_PITCH: 0,
    ResultType.FIELDERS_CHOICE: 0,
    ResultType.REACHED_ON_ERROR: 0,
    ResultType.CATCHERS_INTERFERENCE: 0,
    ResultType.STRIKEOUT: 1,
    ResultType.STRIKEOUT_LOOKING: 1,
    ResultType.GROUND_OUT: 1,
    ResultType.FLY_OUT: 1,
    ResultType.FOUL_OUT: 1,
    ResultType.LINE_OUT: 1,
    ResultType.SAC_FLY: 1,
    ResultType.SAC_BUNT: 1,
    ResultType.DOUBLE_PLAY: 2,
    ResultType.TRIPLE_PLAY: 3,
}

_EXPECTED_BATTER_DEFAULT_BASE = {
    ResultType.SINGLE: BaseCode.FIRST,
    ResultType.WALK: BaseCode.FIRST,
    ResultType.INTENTIONAL_WALK: BaseCode.FIRST,
    ResultType.HIT_BY_PITCH: BaseCode.FIRST,
    ResultType.FIELDERS_CHOICE: BaseCode.FIRST,
    ResultType.REACHED_ON_ERROR: BaseCode.FIRST,
    ResultType.CATCHERS_INTERFERENCE: BaseCode.FIRST,
    ResultType.DOUBLE: BaseCode.SECOND,
    ResultType.TRIPLE: BaseCode.THIRD,
    ResultType.HOME_RUN: BaseCode.HOME,
    # Outs return None
    ResultType.STRIKEOUT: None,
    ResultType.STRIKEOUT_LOOKING: None,
    ResultType.GROUND_OUT: None,
    ResultType.FLY_OUT: None,
    ResultType.FOUL_OUT: None,
    ResultType.LINE_OUT: None,
    ResultType.DOUBLE_PLAY: None,
    ResultType.TRIPLE_PLAY: None,
    ResultType.SAC_FLY: None,
    ResultType.SAC_BUNT: None,
}


# ---------------------------------------------------------------------------
# counts_as_ab
# ---------------------------------------------------------------------------


def test_counts_as_ab_true_for_hits_and_standard_outs():
    for rt in _COUNTS_AS_AB_TRUE:
        assert rt.counts_as_ab is True, f"{rt} should count as AB"


def test_counts_as_ab_false_for_walks_hbp_sac_ci():
    for rt in _COUNTS_AS_AB_FALSE:
        assert rt.counts_as_ab is False, f"{rt} should NOT count as AB"


def test_counts_as_ab_covers_all_result_types():
    covered = _COUNTS_AS_AB_TRUE | _COUNTS_AS_AB_FALSE
    assert covered == set(_ALL_RESULT_TYPES)


@pytest.mark.parametrize("rt", list(_COUNTS_AS_AB_TRUE))
def test_counts_as_ab_true_parametrized(rt):
    assert rt.counts_as_ab is True


@pytest.mark.parametrize("rt", list(_COUNTS_AS_AB_FALSE))
def test_counts_as_ab_false_parametrized(rt):
    assert rt.counts_as_ab is False


# ---------------------------------------------------------------------------
# counts_as_hit
# ---------------------------------------------------------------------------


def test_counts_as_hit_true_only_for_base_hits():
    for rt in _COUNTS_AS_HIT_TRUE:
        assert rt.counts_as_hit is True, f"{rt} should count as hit"


def test_counts_as_hit_false_for_all_non_hits():
    non_hits = set(_ALL_RESULT_TYPES) - _COUNTS_AS_HIT_TRUE
    for rt in non_hits:
        assert rt.counts_as_hit is False, f"{rt} should NOT count as hit"


def test_counts_as_hit_exactly_four_results():
    hit_types = [rt for rt in _ALL_RESULT_TYPES if rt.counts_as_hit]
    assert len(hit_types) == 4


@pytest.mark.parametrize("rt", list(_COUNTS_AS_HIT_TRUE))
def test_counts_as_hit_true_parametrized(rt):
    assert rt.counts_as_hit is True


def test_walk_does_not_count_as_hit():
    assert ResultType.WALK.counts_as_hit is False


def test_fielders_choice_does_not_count_as_hit():
    assert ResultType.FIELDERS_CHOICE.counts_as_hit is False


# ---------------------------------------------------------------------------
# counts_as_out
# ---------------------------------------------------------------------------


def test_counts_as_out_true_for_standard_outs():
    for rt in _COUNTS_AS_OUT_TRUE:
        assert rt.counts_as_out is True, f"{rt} should count as out"


def test_counts_as_out_false_for_all_reaches():
    non_outs = set(_ALL_RESULT_TYPES) - _COUNTS_AS_OUT_TRUE
    for rt in non_outs:
        assert rt.counts_as_out is False, f"{rt} should NOT count as out"


@pytest.mark.parametrize("rt", list(_COUNTS_AS_OUT_TRUE))
def test_counts_as_out_true_parametrized(rt):
    assert rt.counts_as_out is True


def test_sac_fly_counts_as_out():
    assert ResultType.SAC_FLY.counts_as_out is True


def test_sac_bunt_counts_as_out():
    assert ResultType.SAC_BUNT.counts_as_out is True


def test_reached_on_error_does_not_count_as_out():
    assert ResultType.REACHED_ON_ERROR.counts_as_out is False


def test_fielders_choice_does_not_count_as_out():
    assert ResultType.FIELDERS_CHOICE.counts_as_out is False


def test_catchers_interference_does_not_count_as_out():
    assert ResultType.CATCHERS_INTERFERENCE.counts_as_out is False


# ---------------------------------------------------------------------------
# display
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rt,expected", list(_EXPECTED_DISPLAYS.items()))
def test_display_value(rt, expected):
    assert rt.display == expected


def test_display_covers_all_result_types():
    assert set(_EXPECTED_DISPLAYS.keys()) == set(_ALL_RESULT_TYPES)


def test_display_values_are_unique():
    values = list(_EXPECTED_DISPLAYS.values())
    assert len(values) == len(set(values))


def test_display_single():
    assert ResultType.SINGLE.display == "1B"


def test_display_double_play():
    assert ResultType.DOUBLE_PLAY.display == "DP"


def test_display_strikeout_looking():
    assert ResultType.STRIKEOUT_LOOKING.display == "Kl"


# ---------------------------------------------------------------------------
# default_outs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rt,expected", list(_EXPECTED_DEFAULT_OUTS.items()))
def test_default_outs(rt, expected):
    assert rt.default_outs == expected, f"{rt}.default_outs expected {expected}"


def test_default_outs_triple_play_is_3():
    assert ResultType.TRIPLE_PLAY.default_outs == 3


def test_default_outs_double_play_is_2():
    assert ResultType.DOUBLE_PLAY.default_outs == 2


def test_default_outs_standard_out_is_1():
    for rt in [
        ResultType.STRIKEOUT,
        ResultType.STRIKEOUT_LOOKING,
        ResultType.GROUND_OUT,
        ResultType.FLY_OUT,
        ResultType.FOUL_OUT,
        ResultType.LINE_OUT,
        ResultType.SAC_FLY,
        ResultType.SAC_BUNT,
    ]:
        assert rt.default_outs == 1, f"{rt}.default_outs should be 1"


def test_default_outs_reaches_are_0():
    for rt in [
        ResultType.SINGLE,
        ResultType.DOUBLE,
        ResultType.TRIPLE,
        ResultType.HOME_RUN,
        ResultType.WALK,
        ResultType.INTENTIONAL_WALK,
        ResultType.HIT_BY_PITCH,
        ResultType.FIELDERS_CHOICE,
        ResultType.REACHED_ON_ERROR,
        ResultType.CATCHERS_INTERFERENCE,
    ]:
        assert rt.default_outs == 0, f"{rt}.default_outs should be 0"


def test_default_outs_covers_all_result_types():
    assert set(_EXPECTED_DEFAULT_OUTS.keys()) == set(_ALL_RESULT_TYPES)


# ---------------------------------------------------------------------------
# batter_default_base
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rt,expected", list(_EXPECTED_BATTER_DEFAULT_BASE.items()))
def test_batter_default_base(rt, expected):
    assert rt.batter_default_base == expected, (
        f"{rt}.batter_default_base expected {expected}"
    )


def test_batter_default_base_covers_all_result_types():
    assert set(_EXPECTED_BATTER_DEFAULT_BASE.keys()) == set(_ALL_RESULT_TYPES)


def test_batter_default_base_single_is_first():
    assert ResultType.SINGLE.batter_default_base == BaseCode.FIRST


def test_batter_default_base_double_is_second():
    assert ResultType.DOUBLE.batter_default_base == BaseCode.SECOND


def test_batter_default_base_triple_is_third():
    assert ResultType.TRIPLE.batter_default_base == BaseCode.THIRD


def test_batter_default_base_home_run_is_home():
    assert ResultType.HOME_RUN.batter_default_base == BaseCode.HOME


def test_batter_default_base_walk_is_first():
    assert ResultType.WALK.batter_default_base == BaseCode.FIRST


def test_batter_default_base_ibb_is_first():
    assert ResultType.INTENTIONAL_WALK.batter_default_base == BaseCode.FIRST


def test_batter_default_base_hbp_is_first():
    assert ResultType.HIT_BY_PITCH.batter_default_base == BaseCode.FIRST


def test_batter_default_base_fc_is_first():
    assert ResultType.FIELDERS_CHOICE.batter_default_base == BaseCode.FIRST


def test_batter_default_base_roe_is_first():
    assert ResultType.REACHED_ON_ERROR.batter_default_base == BaseCode.FIRST


def test_batter_default_base_ci_is_first():
    assert ResultType.CATCHERS_INTERFERENCE.batter_default_base == BaseCode.FIRST


def test_batter_default_base_strikeout_is_none():
    assert ResultType.STRIKEOUT.batter_default_base is None


def test_batter_default_base_ground_out_is_none():
    assert ResultType.GROUND_OUT.batter_default_base is None


def test_batter_default_base_sac_fly_is_none():
    assert ResultType.SAC_FLY.batter_default_base is None


def test_batter_default_base_double_play_is_none():
    assert ResultType.DOUBLE_PLAY.batter_default_base is None


def test_batter_default_base_triple_play_is_none():
    assert ResultType.TRIPLE_PLAY.batter_default_base is None
