"""
constants.py — Enums for the baseball scorebook TUI.

All enums are immutable by virtue of Python's enum machinery.
String enums inherit from (str, Enum) so they serialize cleanly to JSON
without extra conversion.
"""
from __future__ import annotations

from enum import Enum


class Position(str, Enum):
    """Defensive positions, numbered by traditional convention."""

    P = "1"
    C = "2"
    FIRST_BASE = "3"
    SECOND_BASE = "4"
    THIRD_BASE = "5"
    SS = "6"
    LF = "7"
    CF = "8"
    RF = "9"
    DH = "10"

    @property
    def display(self) -> str:
        """Short display label for the position."""
        _labels: dict[str, str] = {
            "1": "P",
            "2": "C",
            "3": "1B",
            "4": "2B",
            "5": "3B",
            "6": "SS",
            "7": "LF",
            "8": "CF",
            "9": "RF",
            "10": "DH",
        }
        return _labels[self.value]


class BaseCode(str, Enum):
    """Represents the five possible base states for a runner."""

    HOME = "HOME"
    FIRST = "FIRST"
    SECOND = "SECOND"
    THIRD = "THIRD"
    OUT = "OUT"


class HalfCode(str, Enum):
    """Which half of an inning."""

    TOP = "TOP"
    BOTTOM = "BOTTOM"


class ResultType(str, Enum):
    """
    All possible at-bat outcomes.

    Properties drive stat counting in the engine — no free-form text parsing
    is required.
    """

    SINGLE = "SINGLE"
    DOUBLE = "DOUBLE"
    TRIPLE = "TRIPLE"
    HOME_RUN = "HOME_RUN"
    WALK = "WALK"
    INTENTIONAL_WALK = "INTENTIONAL_WALK"
    HIT_BY_PITCH = "HIT_BY_PITCH"
    STRIKEOUT = "STRIKEOUT"
    STRIKEOUT_LOOKING = "STRIKEOUT_LOOKING"
    GROUND_OUT = "GROUND_OUT"
    FLY_OUT = "FLY_OUT"
    FOUL_OUT = "FOUL_OUT"
    LINE_OUT = "LINE_OUT"
    DOUBLE_PLAY = "DOUBLE_PLAY"
    TRIPLE_PLAY = "TRIPLE_PLAY"
    SAC_FLY = "SAC_FLY"
    SAC_BUNT = "SAC_BUNT"
    FIELDERS_CHOICE = "FIELDERS_CHOICE"
    REACHED_ON_ERROR = "REACHED_ON_ERROR"
    CATCHERS_INTERFERENCE = "CATCHERS_INTERFERENCE"

    # ------------------------------------------------------------------
    # Stat classification helpers
    # ------------------------------------------------------------------

    @property
    def counts_as_ab(self) -> bool:
        """
        True when the plate appearance counts as an official at-bat.

        Excludes: walks, intentional walks, HBP, sac fly, sac bunt,
        and catcher's interference (per official scoring rules).
        """
        _no_ab = {
            ResultType.WALK,
            ResultType.INTENTIONAL_WALK,
            ResultType.HIT_BY_PITCH,
            ResultType.SAC_FLY,
            ResultType.SAC_BUNT,
            ResultType.CATCHERS_INTERFERENCE,
        }
        return self not in _no_ab

    @property
    def counts_as_hit(self) -> bool:
        """True for base hits: single, double, triple, home run."""
        _hits = {
            ResultType.SINGLE,
            ResultType.DOUBLE,
            ResultType.TRIPLE,
            ResultType.HOME_RUN,
        }
        return self in _hits

    @property
    def counts_as_out(self) -> bool:
        """
        True when the result typically produces an out.

        Note: STRIKEOUT and STRIKEOUT_LOOKING are marked True here.
        When the batter reaches on a dropped third strike
        (AtBatEvent.batter_reached=True), the engine overrides
        outs_on_play to 0 — the strikeout still counts for pitching stats
        but does not register as a batting out in that edge case.
        """
        _outs = {
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
        return self in _outs

    @property
    def display(self) -> str:
        """Short scorecard notation for this result type."""
        _displays: dict[str, str] = {
            "SINGLE": "1B",
            "DOUBLE": "2B",
            "TRIPLE": "3B",
            "HOME_RUN": "HR",
            "WALK": "BB",
            "INTENTIONAL_WALK": "IBB",
            "HIT_BY_PITCH": "HBP",
            "STRIKEOUT": "K",
            "STRIKEOUT_LOOKING": "Kl",
            "GROUND_OUT": "GB",
            "FLY_OUT": "FB",
            "FOUL_OUT": "F",
            "LINE_OUT": "L",
            "DOUBLE_PLAY": "DP",
            "TRIPLE_PLAY": "TP",
            "SAC_FLY": "SF",
            "SAC_BUNT": "SAC",
            "FIELDERS_CHOICE": "FC",
            "REACHED_ON_ERROR": "E",
            "CATCHERS_INTERFERENCE": "CI",
        }
        return _displays[self.value]

    @property
    def default_outs(self) -> int:
        """
        Default number of outs recorded on this play.

        - 3 for triple play
        - 2 for double play
        - 1 for standard outs and strikeouts
        - 0 for reaches (hits, walks, HBP, FC, ROE, CI)
        """
        if self is ResultType.TRIPLE_PLAY:
            return 3
        if self is ResultType.DOUBLE_PLAY:
            return 2
        if self.counts_as_out:
            return 1
        return 0

    @property
    def batter_default_base(self) -> BaseCode | None:
        """
        The base the batter reaches by default on this result.

        Returns None for results where the batter is out.
        The engine may override this when batter_reached=True on strikeouts.
        """
        _base_map: dict[str, BaseCode] = {
            "SINGLE": BaseCode.FIRST,
            "WALK": BaseCode.FIRST,
            "INTENTIONAL_WALK": BaseCode.FIRST,
            "HIT_BY_PITCH": BaseCode.FIRST,
            "FIELDERS_CHOICE": BaseCode.FIRST,
            "REACHED_ON_ERROR": BaseCode.FIRST,
            "CATCHERS_INTERFERENCE": BaseCode.FIRST,
            "DOUBLE": BaseCode.SECOND,
            "TRIPLE": BaseCode.THIRD,
            "HOME_RUN": BaseCode.HOME,
        }
        return _base_map.get(self.value)


class AdvanceType(str, Enum):
    """How a runner moved (or was retired) between bases on a given play."""

    ON_HIT = "ON_HIT"
    ON_BB = "ON_BB"
    ON_HBP = "ON_HBP"
    ON_FC = "ON_FC"
    ON_ERROR = "ON_ERROR"
    ON_SAC = "ON_SAC"
    ON_WP = "ON_WP"
    ON_PB = "ON_PB"
    ON_THROW = "ON_THROW"
    ON_CI = "ON_CI"


class BaserunnerType(str, Enum):
    """Standalone baserunner events that occur outside a plate appearance."""

    SB = "SB"    # stolen base
    CS = "CS"    # caught stealing
    PO = "PO"    # pickoff
    WP = "WP"    # wild pitch
    PB = "PB"    # passed ball
    BK = "BK"    # balk
    OBR = "OBR"  # out on base running


class SubType(str, Enum):
    """Substitution categories."""

    PINCH_HIT = "PINCH_HIT"
    PINCH_RUN = "PINCH_RUN"
    DEFENSIVE = "DEFENSIVE"
    PITCHER_CHANGE = "PITCHER_CHANGE"


class SegmentState(str, Enum):
    """
    Visual state of one base-path segment on the per-at-bat diamond.

    Each segment connects two adjacent bases (e.g. HOME→FIRST).
    """

    DIM = "DIM"        # runner has not yet reached this segment
    LIT = "LIT"        # runner passed through this segment
    SCORED = "SCORED"  # this segment completed a run scoring


class RunnerFinalState(str, Enum):
    """Ultimate disposition of a runner at the end of a half-inning (or game)."""

    SCORED = "SCORED"          # crossed home plate
    LEFT_ON_BASE = "LEFT_ON_BASE"  # inning ended with runner still on base
    OUT = "OUT"                # put out before scoring
    RUNNING = "RUNNING"        # game still in progress; runner is on base
