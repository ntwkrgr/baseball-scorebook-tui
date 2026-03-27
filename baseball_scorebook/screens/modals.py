"""modals.py — All modal dialogs for the game screen.

Each modal is a ModalScreen subclass that collects user input and returns
a result via self.dismiss().  Modals are kept focused: one purpose each,
minimal logic, no state mutation.

Modals defined here:
- AtBatModal          — record a plate appearance
- BaserunnerModal     — record a standalone baserunner event
- SubstitutionModal   — record a player substitution
- EndGameModal        — confirm ending the game
- HalfInningTransitionModal — display end-of-half summary
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Select, Static

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

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

_MODAL_CSS = """
.modal-box {
    background: $surface;
    border: thick $accent;
    width: 70;
    height: auto;
    padding: 1 2;
}

.modal-title {
    text-style: bold;
    color: $accent;
    margin-bottom: 1;
}

.field-row {
    height: auto;
    margin-bottom: 1;
}

.field-label {
    width: 22;
    height: 3;
    content-align: left middle;
}

.field-input {
    width: 1fr;
}

.button-row {
    height: 3;
    align: right middle;
    margin-top: 1;
}

.button-row Button {
    margin-left: 1;
}

.runner-section-title {
    text-style: bold;
    color: $text-muted;
    margin-top: 1;
    margin-bottom: 1;
}

.runner-row {
    height: auto;
    margin-bottom: 1;
}

.runner-label {
    width: 22;
    height: 3;
    content-align: left middle;
}
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_label(base: BaseCode) -> str:
    """Short human-readable label for a base."""
    _labels: dict[BaseCode, str] = {
        BaseCode.FIRST: "1st",
        BaseCode.SECOND: "2nd",
        BaseCode.THIRD: "3rd",
        BaseCode.HOME: "Home (scored)",
        BaseCode.OUT: "Out",
    }
    return _labels.get(base, base.value)


def _result_type_options() -> list[tuple[str, ResultType]]:
    """Sorted list of (label, value) for all ResultType values."""
    return [(rt.display + f" ({rt.value})", rt) for rt in ResultType]


def _position_options() -> list[tuple[str, Position]]:
    """List of (label, value) for all Position values."""
    return [(pos.display, pos) for pos in Position]


def _advance_destination_options() -> list[tuple[str, BaseCode]]:
    """Destination choices for a runner advance on a plate appearance."""
    return [
        (_base_label(BaseCode.FIRST), BaseCode.FIRST),
        (_base_label(BaseCode.SECOND), BaseCode.SECOND),
        (_base_label(BaseCode.THIRD), BaseCode.THIRD),
        (_base_label(BaseCode.HOME), BaseCode.HOME),
        (_base_label(BaseCode.OUT), BaseCode.OUT),
    ]


def _runner_destination_options() -> list[tuple[str, BaseCode]]:
    """Destination choices for a standalone baserunner event."""
    return [
        (_base_label(BaseCode.SECOND), BaseCode.SECOND),
        (_base_label(BaseCode.THIRD), BaseCode.THIRD),
        (_base_label(BaseCode.HOME), BaseCode.HOME),
        (_base_label(BaseCode.OUT), BaseCode.OUT),
    ]


def _auto_runner_destination(
    result_type: ResultType,
    from_base: BaseCode,
) -> BaseCode:
    """Compute the default destination for a runner given the result type.

    Logic follows PLAN.md §9.1:
    - HOME_RUN / TRIPLE: all runners score
    - DOUBLE: runners on 2B/3B score; runner on 1B goes to 3rd
    - SINGLE: each runner advances exactly one base
    - WALK / HBP / IBB: only forced runners advance (handled separately)
    - Outs: runners stay (return current base unchanged)
    """
    if result_type in (ResultType.HOME_RUN, ResultType.TRIPLE):
        return BaseCode.HOME

    if result_type == ResultType.DOUBLE:
        if from_base in (BaseCode.SECOND, BaseCode.THIRD):
            return BaseCode.HOME
        if from_base == BaseCode.FIRST:
            return BaseCode.THIRD
        return from_base

    if result_type == ResultType.SINGLE:
        _next: dict[BaseCode, BaseCode] = {
            BaseCode.FIRST: BaseCode.SECOND,
            BaseCode.SECOND: BaseCode.THIRD,
            BaseCode.THIRD: BaseCode.HOME,
        }
        return _next.get(from_base, from_base)

    # Walks/HBP: forced advances only — 1B→2B when batter goes to 1B,
    # 2B→3B if 1B also occupied, 3B→HOME if 1B+2B occupied.
    # The caller handles forced-advance logic; default is stay.
    if result_type in (
        ResultType.WALK,
        ResultType.INTENTIONAL_WALK,
        ResultType.HIT_BY_PITCH,
    ):
        return from_base

    # All outs and other results: runners stay
    return from_base


def _compute_forced_advances(
    result_type: ResultType,
    runners: dict[BaseCode, RunnerInfo],
) -> dict[BaseCode, BaseCode]:
    """Return forced-advance mapping for walk/HBP results.

    A runner is forced to advance only when every base between them and
    home is occupied (including the batter taking first base).

    Returns a dict mapping from_base → to_base for each forced runner.
    """
    if result_type not in (
        ResultType.WALK,
        ResultType.INTENTIONAL_WALK,
        ResultType.HIT_BY_PITCH,
    ):
        return {}

    advances: dict[BaseCode, BaseCode] = {}

    # Batter occupies 1st — force runner on 1st to 2nd if present
    if BaseCode.FIRST in runners:
        advances[BaseCode.FIRST] = BaseCode.SECOND
        # If 2nd is also occupied, force them to 3rd
        if BaseCode.SECOND in runners:
            advances[BaseCode.SECOND] = BaseCode.THIRD
            # If 3rd is also occupied, force them home
            if BaseCode.THIRD in runners:
                advances[BaseCode.THIRD] = BaseCode.HOME

    return advances


def _advance_how_for_result(result_type: ResultType) -> AdvanceType:
    """Pick the most appropriate AdvanceType for runners scoring on this result."""
    _map: dict[ResultType, AdvanceType] = {
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
    return _map.get(result_type, AdvanceType.ON_HIT)


def _lookup_player_name(
    batting_order: int,
    team: Team | None,
) -> str:
    """Return the player name for a given batting order slot, or '#N'."""
    if team is None:
        return f"#{batting_order}"
    for slot in team.lineup:
        if slot.batting_order == batting_order:
            return slot.player.name
    return f"#{batting_order}"


# ---------------------------------------------------------------------------
# AtBatModal
# ---------------------------------------------------------------------------


class AtBatModal(ModalScreen[list | None]):
    """Record a plate appearance.

    Returns a list of GameEvent objects (AtBatEvent + RunnerAdvanceEvents)
    via self.dismiss(), or None if cancelled.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+enter", "submit", "OK"),
    ]

    DEFAULT_CSS = (
        _MODAL_CSS
        + """
    AtBatModal {
        align: center middle;
    }
    """
    )

    def __init__(
        self,
        state: GameState,
        away_team: Team | None = None,
        home_team: Team | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._state = state
        self._away_team = away_team
        self._home_team = home_team

    # --- helpers ---

    def _batting_team(self) -> Team | None:
        if self._state.current_half == HalfCode.TOP:
            return self._away_team
        return self._home_team

    def _current_batter_order(self) -> int:
        idx = self._state.current_batter_index[self._state.current_half]
        return idx + 1

    def _runner_select_id(self, base: BaseCode) -> str:
        return f"runner-dest-{base.value}"

    # --- compose ---

    def compose(self) -> ComposeResult:
        batter_order = self._current_batter_order()
        batter_name = _lookup_player_name(batter_order, self._batting_team())
        title = (
            f"New At-Bat — #{batter_order} {batter_name} "
            f"({'TOP' if self._state.current_half == HalfCode.TOP else 'BOT'} "
            f"{self._state.current_inning})"
        )

        with Vertical(classes="modal-box", id="atbat-box"):
            yield Static(title, classes="modal-title")

            # Result type
            with Horizontal(classes="field-row"):
                yield Label("Result:", classes="field-label")
                yield Select(
                    _result_type_options(),
                    value=ResultType.GROUND_OUT,
                    id="result-type",
                    classes="field-input",
                )

            # Fielders
            with Horizontal(classes="field-row"):
                yield Label("Fielders:", classes="field-label")
                yield Input(placeholder="e.g. 6-3", id="fielders", classes="field-input")

            # Outs on play
            with Horizontal(classes="field-row"):
                yield Label("Outs on play:", classes="field-label")
                yield Select(
                    [("0", 0), ("1", 1), ("2", 2), ("3", 3)],
                    value=1,
                    id="outs-on-play",
                    classes="field-input",
                )

            # Batter reached (for strikeouts — dropped 3rd strike)
            with Horizontal(classes="field-row", id="batter-reached-row"):
                yield Label("Batter reached:", classes="field-label")
                yield Checkbox("(dropped 3rd strike)", id="batter-reached")

            # RBI count
            with Horizontal(classes="field-row"):
                yield Label("RBI:", classes="field-label")
                yield Input(value="0", id="rbi-count", classes="field-input")

            # Notes
            with Horizontal(classes="field-row"):
                yield Label("Notes:", classes="field-label")
                yield Input(placeholder="optional", id="notes", classes="field-input")

            # Runner advances section
            if self._state.runners:
                yield Static("Runner Advances", classes="runner-section-title")
                for base, runner_info in sorted(
                    self._state.runners.items(),
                    key=lambda x: x[0].value,
                ):
                    runner_name = _lookup_player_name(
                        runner_info.batting_order, self._batting_team()
                    )
                    label_text = f"{_base_label(base)}: #{runner_info.batting_order} {runner_name}"
                    with Horizontal(classes="runner-row"):
                        yield Label(label_text, classes="runner-label")
                        yield Select(
                            _advance_destination_options(),
                            value=base,
                            id=self._runner_select_id(base),
                            classes="field-input",
                        )

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("OK", variant="primary", id="ok-btn")

    def on_mount(self) -> None:
        self._sync_result_type_defaults()

    def _sync_result_type_defaults(self) -> None:
        """Update outs and batter-reached visibility when result type changes."""
        result_select = self.query_one("#result-type", Select)
        if result_select.value is Select.BLANK:
            return
        result_type: ResultType = result_select.value  # type: ignore[assignment]

        # Auto-set outs on play
        outs_select = self.query_one("#outs-on-play", Select)
        outs_select.value = result_type.default_outs

        # Show batter-reached only for strikeout types
        batter_row = self.query_one("#batter-reached-row")
        is_strikeout = result_type in (
            ResultType.STRIKEOUT,
            ResultType.STRIKEOUT_LOOKING,
        )
        batter_row.display = is_strikeout

        # Update runner auto-destinations
        self._update_runner_defaults(result_type)

    def _update_runner_defaults(self, result_type: ResultType) -> None:
        """Auto-populate runner advance selects based on result type."""
        forced = _compute_forced_advances(result_type, self._state.runners)
        for base in self._state.runners:
            dest = forced.get(base, _auto_runner_destination(result_type, base))
            sel_id = self._runner_select_id(base)
            try:
                sel = self.query_one(f"#{sel_id}", Select)
                sel.value = dest
            except Exception:
                pass

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "result-type":
            self._sync_result_type_defaults()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok-btn":
            self.action_submit()
        elif event.button.id == "cancel-btn":
            self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_submit(self) -> None:
        events = self._build_events()
        self.dismiss(events)

    def _build_events(self) -> list:
        """Construct AtBatEvent + RunnerAdvanceEvents from form values."""
        result_select = self.query_one("#result-type", Select)
        if result_select.value is Select.BLANK:
            return []
        result_type: ResultType = result_select.value  # type: ignore[assignment]

        outs_select = self.query_one("#outs-on-play", Select)
        outs_on_play = int(outs_select.value) if outs_select.value is not Select.BLANK else result_type.default_outs

        fielders = self.query_one("#fielders", Input).value.strip()
        notes = self.query_one("#notes", Input).value.strip()

        rbi_raw = self.query_one("#rbi-count", Input).value.strip()
        try:
            rbi_count = int(rbi_raw)
        except ValueError:
            rbi_count = 0

        batter_reached_checkbox = self.query_one("#batter-reached", Checkbox)
        is_strikeout = result_type in (ResultType.STRIKEOUT, ResultType.STRIKEOUT_LOOKING)
        batter_reached_override = is_strikeout and batter_reached_checkbox.value

        # Determine whether batter reaches base
        batter_reaches = (
            result_type.batter_default_base is not None or batter_reached_override
        )
        # For strikeouts with dropped 3rd, override outs to 0
        if batter_reached_override:
            outs_on_play = 0

        batter_order = self._current_batter_order()
        inning = self._state.current_inning
        half = self._state.current_half

        at_bat = AtBatEvent(
            inning=inning,
            half=half,
            batting_order=batter_order,
            result_type=result_type,
            fielders=fielders,
            batter_reached=batter_reaches,
            outs_on_play=outs_on_play,
            bases_reached=(),
            rbi_count=rbi_count,
            notes=notes,
        )

        advance_events = self._build_runner_advance_events(
            inning, half, result_type, batter_order
        )

        return [at_bat, *advance_events]

    def _build_runner_advance_events(
        self,
        inning: int,
        half: HalfCode,
        result_type: ResultType,
        batter_order: int,
    ) -> list[RunnerAdvanceEvent]:
        """Build RunnerAdvanceEvent for each runner that moved."""
        events: list[RunnerAdvanceEvent] = []
        advance_how = _advance_how_for_result(result_type)

        for base, runner_info in self._state.runners.items():
            sel_id = self._runner_select_id(base)
            try:
                sel = self.query_one(f"#{sel_id}", Select)
                dest = sel.value
            except Exception:
                dest = base

            if dest is Select.BLANK or dest == base:
                continue

            events.append(
                RunnerAdvanceEvent(
                    inning=inning,
                    half=half,
                    runner_batting_order=runner_info.batting_order,
                    runner_at_bat_inning=runner_info.at_bat_inning,
                    from_base=base,
                    to_base=dest,  # type: ignore[arg-type]
                    how=advance_how,
                    earned=True,
                    rbi_batter_order=batter_order if dest == BaseCode.HOME else None,
                )
            )

        return events


# ---------------------------------------------------------------------------
# BaserunnerModal
# ---------------------------------------------------------------------------


class BaserunnerModal(ModalScreen[BaserunnerEvent | None]):
    """Record a standalone baserunner event (SB, CS, WP, PB, BK, OBR).

    Returns a BaserunnerEvent or None.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = (
        _MODAL_CSS
        + """
    BaserunnerModal {
        align: center middle;
    }
    """
    )

    def __init__(self, state: GameState, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._state = state

    def _runner_options(self) -> list[tuple[str, BaseCode]]:
        return [
            (
                f"{_base_label(base)} — #{info.batting_order}",
                base,
            )
            for base, info in sorted(
                self._state.runners.items(), key=lambda x: x[0].value
            )
        ]

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Static("Baserunner Event", classes="modal-title")

            with Horizontal(classes="field-row"):
                yield Label("Runner:", classes="field-label")
                yield Select(
                    self._runner_options(),
                    id="runner-base",
                    classes="field-input",
                )

            with Horizontal(classes="field-row"):
                yield Label("Destination:", classes="field-label")
                yield Select(
                    _runner_destination_options(),
                    value=BaseCode.SECOND,
                    id="runner-dest",
                    classes="field-input",
                )

            with Horizontal(classes="field-row"):
                yield Label("How:", classes="field-label")
                yield Select(
                    [(brt.value, brt) for brt in BaserunnerType],
                    value=BaserunnerType.SB,
                    id="how",
                    classes="field-input",
                )

            with Horizontal(classes="field-row"):
                yield Label("Fielders:", classes="field-label")
                yield Input(placeholder="e.g. 2-6", id="fielders", classes="field-input")

            with Horizontal(classes="field-row"):
                yield Label("Out on play:", classes="field-label")
                yield Checkbox("", id="is-out")

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("OK", variant="primary", id="ok-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok-btn":
            self._submit()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _submit(self) -> None:
        runner_base_sel = self.query_one("#runner-base", Select)
        dest_sel = self.query_one("#runner-dest", Select)
        how_sel = self.query_one("#how", Select)

        if runner_base_sel.value is Select.BLANK:
            self.dismiss(None)
            return
        if dest_sel.value is Select.BLANK:
            self.dismiss(None)
            return
        if how_sel.value is Select.BLANK:
            self.dismiss(None)
            return

        from_base: BaseCode = runner_base_sel.value  # type: ignore[assignment]
        to_base: BaseCode = dest_sel.value  # type: ignore[assignment]
        how: BaserunnerType = how_sel.value  # type: ignore[assignment]

        runner_info = self._state.runners.get(from_base)
        if runner_info is None:
            self.dismiss(None)
            return

        fielders = self.query_one("#fielders", Input).value.strip()
        is_out = self.query_one("#is-out", Checkbox).value
        outs_on_play = 1 if is_out else 0

        effective_to = BaseCode.OUT if is_out else to_base

        event = BaserunnerEvent(
            inning=self._state.current_inning,
            half=self._state.current_half,
            runner_batting_order=runner_info.batting_order,
            runner_at_bat_inning=runner_info.at_bat_inning,
            from_base=from_base,
            to_base=effective_to,
            how=how,
            fielders=fielders,
            earned=True,
            outs_on_play=outs_on_play,
        )
        self.dismiss(event)


# ---------------------------------------------------------------------------
# SubstitutionModal
# ---------------------------------------------------------------------------


class SubstitutionModal(ModalScreen[SubstitutionEvent | None]):
    """Record a player substitution.

    Returns a SubstitutionEvent or None.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = (
        _MODAL_CSS
        + """
    SubstitutionModal {
        align: center middle;
    }
    """
    )

    def __init__(
        self,
        state: GameState,
        away_team: Team | None = None,
        home_team: Team | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._state = state
        self._away_team = away_team
        self._home_team = home_team

    def _team_options(self) -> list[tuple[str, HalfCode]]:
        away_name = self._away_team.name if self._away_team else "Away"
        home_name = self._home_team.name if self._home_team else "Home"
        return [
            (f"Away — {away_name}", HalfCode.TOP),
            (f"Home — {home_name}", HalfCode.BOTTOM),
        ]

    def _lineup_options(self, team: Team | None) -> list[tuple[str, int]]:
        if team is None:
            return [(str(i), i) for i in range(1, 10)]
        return [
            (f"{slot.batting_order}. #{slot.player.number} {slot.player.name}", slot.batting_order)
            for slot in sorted(team.lineup, key=lambda s: s.batting_order)
        ]

    def _get_team(self, half: HalfCode) -> Team | None:
        return self._away_team if half == HalfCode.TOP else self._home_team

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Static("Substitution", classes="modal-title")

            with Horizontal(classes="field-row"):
                yield Label("Team:", classes="field-label")
                yield Select(
                    self._team_options(),
                    value=self._state.current_half,
                    id="team-select",
                    classes="field-input",
                )

            with Horizontal(classes="field-row"):
                yield Label("Sub type:", classes="field-label")
                yield Select(
                    [(st.value.replace("_", " ").title(), st) for st in SubType],
                    value=SubType.PINCH_HIT,
                    id="sub-type",
                    classes="field-input",
                )

            with Horizontal(classes="field-row"):
                yield Label("Lineup slot:", classes="field-label")
                default_team = self._get_team(self._state.current_half)
                yield Select(
                    self._lineup_options(default_team),
                    id="lineup-slot",
                    classes="field-input",
                )

            with Horizontal(classes="field-row"):
                yield Label("Leaving player:", classes="field-label")
                yield Static("—", id="leaving-name", classes="field-input")

            with Horizontal(classes="field-row"):
                yield Label("Entering name:", classes="field-label")
                yield Input(placeholder="Player name", id="entering-name", classes="field-input")

            with Horizontal(classes="field-row"):
                yield Label("Entering number:", classes="field-label")
                yield Input(placeholder="Jersey #", id="entering-number", classes="field-input")

            with Horizontal(classes="field-row"):
                yield Label("New position:", classes="field-label")
                yield Select(
                    _position_options(),
                    value=Position.P,
                    id="new-position",
                    classes="field-input",
                )

            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("OK", variant="primary", id="ok-btn")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id in ("team-select", "lineup-slot"):
            self._update_leaving_name()

    def _update_leaving_name(self) -> None:
        """Auto-fill the leaving player name from the selected slot."""
        team_sel = self.query_one("#team-select", Select)
        slot_sel = self.query_one("#lineup-slot", Select)

        if team_sel.value is Select.BLANK or slot_sel.value is Select.BLANK:
            return

        half: HalfCode = team_sel.value  # type: ignore[assignment]
        order: int = slot_sel.value  # type: ignore[assignment]
        team = self._get_team(half)
        name = _lookup_player_name(order, team)
        self.query_one("#leaving-name", Static).update(name)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok-btn":
            self._submit()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _submit(self) -> None:
        team_sel = self.query_one("#team-select", Select)
        sub_type_sel = self.query_one("#sub-type", Select)
        slot_sel = self.query_one("#lineup-slot", Select)
        pos_sel = self.query_one("#new-position", Select)

        for sel in (team_sel, sub_type_sel, slot_sel, pos_sel):
            if sel.value is Select.BLANK:
                self.dismiss(None)
                return

        team_half: HalfCode = team_sel.value  # type: ignore[assignment]
        sub_type: SubType = sub_type_sel.value  # type: ignore[assignment]
        batting_order: int = slot_sel.value  # type: ignore[assignment]
        new_position: Position = pos_sel.value  # type: ignore[assignment]

        leaving_name = self.query_one("#leaving-name", Static).renderable
        entering_name = self.query_one("#entering-name", Input).value.strip()
        entering_number_raw = self.query_one("#entering-number", Input).value.strip()

        try:
            entering_number = int(entering_number_raw)
        except ValueError:
            entering_number = 0

        if not entering_name:
            self.dismiss(None)
            return

        sub_event = SubstitutionEvent(
            inning=self._state.current_inning,
            half=self._state.current_half,
            team=team_half,
            batting_order=batting_order,
            leaving_name=str(leaving_name),
            entering_name=entering_name,
            entering_number=entering_number,
            new_position=new_position,
            sub_type=sub_type,
        )
        self.dismiss(sub_event)


# ---------------------------------------------------------------------------
# EndGameModal
# ---------------------------------------------------------------------------


class EndGameModal(ModalScreen[bool]):
    """Confirm ending the game.

    Returns True if the user confirms, False if they choose to continue.
    """

    BINDINGS = [
        Binding("y", "confirm", "Yes — End Game"),
        Binding("n", "continue_game", "No — Continue"),
        Binding("escape", "continue_game", "Cancel"),
    ]

    DEFAULT_CSS = """
    EndGameModal {
        align: center middle;
    }

    #end-game-box {
        background: $surface;
        border: thick $error;
        width: 50;
        height: auto;
        padding: 1 2;
    }

    #end-game-title {
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }

    #score-display {
        margin-bottom: 1;
    }

    .end-button-row {
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    .end-button-row Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        state: GameState,
        away_team: Team | None = None,
        home_team: Team | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._state = state
        self._away_team = away_team
        self._home_team = home_team

    def compose(self) -> ComposeResult:
        away_name = self._away_team.name if self._away_team else "Away"
        home_name = self._home_team.name if self._home_team else "Home"
        score_line = (
            f"{away_name} {self._state.away_score} — "
            f"{home_name} {self._state.home_score}"
        )

        with Vertical(id="end-game-box"):
            yield Static("End Game?", id="end-game-title")
            yield Static(score_line, id="score-display")
            yield Static(
                "Press Y to end the game or N to continue scoring.",
            )
            with Horizontal(classes="end-button-row"):
                yield Button("Yes — End Game (Y)", variant="error", id="yes-btn")
                yield Button("No — Continue (N)", variant="default", id="no-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes-btn":
            self.action_confirm()
        elif event.button.id == "no-btn":
            self.action_continue_game()

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_continue_game(self) -> None:
        self.dismiss(False)


# ---------------------------------------------------------------------------
# HalfInningTransitionModal
# ---------------------------------------------------------------------------


class HalfInningTransitionModal(ModalScreen[None]):
    """Display end-of-half-inning summary before starting the next half.

    Shows R/H/E/LOB for the half just completed and the current score.
    Press Enter or Space to continue.
    """

    BINDINGS = [
        Binding("enter", "continue_game", "Continue"),
        Binding("space", "continue_game", "Continue"),
        Binding("escape", "continue_game", "Continue"),
    ]

    DEFAULT_CSS = """
    HalfInningTransitionModal {
        align: center middle;
    }

    #transition-box {
        background: $surface;
        border: thick $primary;
        width: 50;
        height: auto;
        padding: 1 2;
    }

    #transition-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .transition-stat-row {
        height: 1;
        margin-bottom: 0;
    }

    #continue-hint {
        margin-top: 1;
        color: $text-muted;
        text-align: center;
    }
    """

    def __init__(
        self,
        state: GameState,
        completed_inning: int,
        completed_half: HalfCode,
        away_team: Team | None = None,
        home_team: Team | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._state = state
        self._completed_inning = completed_inning
        self._completed_half = completed_half
        self._away_team = away_team
        self._home_team = home_team

    def compose(self) -> ComposeResult:
        half_label = "TOP" if self._completed_half == HalfCode.TOP else "BOT"
        title = f"End of {half_label} {self._completed_inning}"

        key = (self._completed_inning, self._completed_half)
        stats = self._state.inning_stats.get(key)
        runs = stats.runs if stats else 0
        hits = stats.hits if stats else 0
        errors = stats.errors if stats else 0
        lob = stats.left_on_base if stats else 0

        away_name = self._away_team.name if self._away_team else "Away"
        home_name = self._home_team.name if self._home_team else "Home"
        score_line = (
            f"{away_name} {self._state.away_score} — "
            f"{home_name} {self._state.home_score}"
        )

        with Vertical(id="transition-box"):
            yield Static(title, id="transition-title")
            yield Static(score_line)
            yield Static("")
            yield Static(f"R: {runs}   H: {hits}   E: {errors}   LOB: {lob}")
            yield Static("")
            yield Static("Press Enter to continue.", id="continue-hint")
            yield Button("Continue (Enter)", variant="primary", id="continue-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "continue-btn":
            self.action_continue_game()

    def action_continue_game(self) -> None:
        self.dismiss(None)
