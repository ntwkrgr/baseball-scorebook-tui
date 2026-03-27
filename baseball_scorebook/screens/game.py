"""game.py — Main game scoring screen.

The heart of the app: users score a live game here.  The screen shows
batting and defensive views for both teams via tabs, a live scoreline
at the bottom, and an optional game log panel.
"""
from __future__ import annotations

from datetime import date as _date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, TabbedContent, TabPane

from baseball_scorebook.engine.event_store import EventStore
from baseball_scorebook.engine.state import check_game_over, derive_state
from baseball_scorebook.models.constants import HalfCode
from baseball_scorebook.models.events import BaserunnerEvent, SubstitutionEvent
from baseball_scorebook.models.game import GameState
from baseball_scorebook.models.team import Team
from baseball_scorebook.storage.serializer import (
    generate_filename,
    get_default_save_dir,
    save_game,
)
from baseball_scorebook.widgets.defense import DefenseWidget
from baseball_scorebook.widgets.game_log import GameLogWidget
from baseball_scorebook.widgets.inning_totals import InningTotalsWidget
from baseball_scorebook.widgets.scorecard import ScorecardWidget
from baseball_scorebook.widgets.scoreline import ScorelineWidget


class GameScreen(Screen):
    """Main game scoring screen with tabs for away and home teams."""

    BINDINGS = [
        Binding("n", "new_at_bat", "New AB", show=True),
        Binding("r", "runner_event", "Runner", show=True),
        Binding("s", "substitution", "Sub", show=True),
        Binding("g", "end_game", "End Game", show=True),
        Binding("l", "toggle_log", "Log", show=True),
        Binding("t", "switch_tab", "Switch Tab"),
        Binding("ctrl+s", "save_game", "Save"),
        Binding("ctrl+z", "undo", "Undo"),
        Binding("ctrl+y", "redo", "Redo"),
        Binding("q", "quit_game", "Quit"),
    ]

    DEFAULT_CSS = """
    GameScreen {
        layout: vertical;
    }

    #game-status {
        height: 1;
        text-align: center;
        background: $accent;
        color: $text;
        text-style: bold;
        width: 100%;
    }

    #main-content {
        height: 1fr;
    }

    .team-view {
        layout: horizontal;
        height: 1fr;
    }

    .scorecard-panel {
        width: 2fr;
        height: 100%;
    }

    .defense-panel {
        width: 1fr;
        height: 100%;
        border-left: solid $accent;
    }

    #game-log-panel {
        display: none;
        height: 15;
        dock: bottom;
        border-top: solid green;
    }

    #game-log-panel.visible {
        display: block;
    }
    """

    def __init__(
        self,
        away_team: Team | None = None,
        home_team: Team | None = None,
        store: EventStore | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.away_team = away_team
        self.home_team = home_team
        self.store = store or EventStore()
        self._log_visible = False
        self._prev_inning = 1
        self._prev_half = HalfCode.TOP

    # ------------------------------------------------------------------
    # Composition
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(self._status_text(), id="game-status")

        with TabbedContent(id="main-content"):
            away_label = f"AWAY: {self.away_team.name if self.away_team else 'Away'}"
            with TabPane(away_label, id="away-tab"):
                with Horizontal(classes="team-view"):
                    with Vertical(classes="scorecard-panel"):
                        yield ScorecardWidget(team=self.away_team, id="away-scorecard")
                        yield InningTotalsWidget(half=HalfCode.TOP, id="away-totals")
                    yield DefenseWidget(team=self.home_team, id="home-defense")

            home_label = f"HOME: {self.home_team.name if self.home_team else 'Home'}"
            with TabPane(home_label, id="home-tab"):
                with Horizontal(classes="team-view"):
                    with Vertical(classes="scorecard-panel"):
                        yield ScorecardWidget(team=self.home_team, id="home-scorecard")
                        yield InningTotalsWidget(half=HalfCode.BOTTOM, id="home-totals")
                    yield DefenseWidget(team=self.away_team, id="away-defense")

        yield ScorelineWidget(
            away_name=self.away_team.name if self.away_team else "Away",
            home_name=self.home_team.name if self.home_team else "Home",
            id="scoreline",
        )
        yield GameLogWidget(id="game-log-panel")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_state()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _away_name(self) -> str:
        return self.away_team.name if self.away_team else "Away"

    def _home_name(self) -> str:
        return self.home_team.name if self.home_team else "Home"

    def _status_text(self) -> str:
        state = derive_state(self.store)
        half_label = "TOP" if state.current_half == HalfCode.TOP else "BOT"
        return (
            f"Inning: {state.current_inning} {half_label}"
            f"  |  Outs: {state.outs}"
            f"  |  {self._away_name()} {state.away_score}"
            f" \u2014 {self._home_name()} {state.home_score}"
        )

    def _refresh_state(self) -> None:
        """Rebuild all widgets from the current event log."""
        state = derive_state(self.store)

        self.query_one("#game-status", Static).update(self._status_text())

        self.query_one("#scoreline", ScorelineWidget).update_state(state)
        self.query_one("#away-totals", InningTotalsWidget).update_state(state)
        self.query_one("#home-totals", InningTotalsWidget).update_state(state)

        if self._log_visible:
            log = self.query_one("#game-log-panel", GameLogWidget)
            log.update_from_events(self.store.effective_events())

        # Detect half-inning transition
        half_changed = (
            state.current_inning != self._prev_inning
            or state.current_half != self._prev_half
        )
        if half_changed and (self._prev_inning != 1 or self._prev_half != HalfCode.TOP or len(self.store) > 0):
            completed_inning = self._prev_inning
            completed_half = self._prev_half
            self._prev_inning = state.current_inning
            self._prev_half = state.current_half
            # Auto-switch tab to the batting team
            self._auto_switch_tab(state)
            # Show transition overlay (if not game over)
            if not check_game_over(state):
                self._show_transition(state, completed_inning, completed_half)
                return
        else:
            self._prev_inning = state.current_inning
            self._prev_half = state.current_half

        if check_game_over(state):
            self._prompt_end_game(state)

    def _auto_switch_tab(self, state: GameState) -> None:
        """Switch to the tab for the currently batting team."""
        tabs = self.query_one("#main-content", TabbedContent)
        target = "away-tab" if state.current_half == HalfCode.TOP else "home-tab"
        if tabs.active != target:
            tabs.active = target

    def _show_transition(
        self, state: GameState, completed_inning: int, completed_half: HalfCode
    ) -> None:
        from baseball_scorebook.screens.modals import HalfInningTransitionModal

        self.app.push_screen(
            HalfInningTransitionModal(
                state=state,
                completed_inning=completed_inning,
                completed_half=completed_half,
                away_team=self.away_team,
                home_team=self.home_team,
            ),
        )

    def _prompt_end_game(self, state: GameState) -> None:
        from baseball_scorebook.screens.modals import EndGameModal

        self.app.push_screen(
            EndGameModal(state=state, away_team=self.away_team, home_team=self.home_team),
            self._on_end_game_response,
        )

    def _on_end_game_response(self, ended: bool) -> None:
        if ended:
            from baseball_scorebook.screens.game_over import GameOverScreen

            self.app.switch_screen(
                GameOverScreen(
                    away_team=self.away_team,
                    home_team=self.home_team,
                    store=self.store,
                )
            )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_new_at_bat(self) -> None:
        from baseball_scorebook.screens.modals import AtBatModal

        state = derive_state(self.store)
        self.app.push_screen(
            AtBatModal(state=state, away_team=self.away_team, home_team=self.home_team),
            self._on_at_bat_result,
        )

    def _on_at_bat_result(self, events: list | None) -> None:
        if events:
            for event in events:
                self.store.append(event)
            self._refresh_state()

    def action_runner_event(self) -> None:
        from baseball_scorebook.screens.modals import BaserunnerModal

        state = derive_state(self.store)
        if not state.runners:
            self.notify("No runners on base", severity="warning")
            return
        self.app.push_screen(
            BaserunnerModal(state=state),
            self._on_baserunner_result,
        )

    def _on_baserunner_result(self, event: BaserunnerEvent | None) -> None:
        if event:
            self.store.append(event)
            self._refresh_state()

    def action_substitution(self) -> None:
        from baseball_scorebook.screens.modals import SubstitutionModal

        state = derive_state(self.store)
        self.app.push_screen(
            SubstitutionModal(
                state=state,
                away_team=self.away_team,
                home_team=self.home_team,
            ),
            self._on_substitution_result,
        )

    def _on_substitution_result(self, event: SubstitutionEvent | None) -> None:
        if event:
            self.store.append(event)
            self._refresh_state()

    def action_end_game(self) -> None:
        state = derive_state(self.store)
        self._prompt_end_game(state)

    def action_toggle_log(self) -> None:
        log = self.query_one("#game-log-panel", GameLogWidget)
        self._log_visible = not self._log_visible
        log.toggle_class("visible")
        if self._log_visible:
            log.update_from_events(self.store.effective_events())

    def action_switch_tab(self) -> None:
        tabs = self.query_one("#main-content", TabbedContent)
        if tabs.active == "away-tab":
            tabs.active = "home-tab"
        else:
            tabs.active = "away-tab"

    def action_save_game(self) -> None:
        save_dir = get_default_save_dir()
        today = str(_date.today())
        filename = generate_filename(self._away_name(), self._home_name(), today)
        path = save_dir / filename
        save_game(path, self.away_team, self.home_team, self.store)
        self.notify(f"Game saved to {path}", severity="information")

    def action_undo(self) -> None:
        event = self.store.undo()
        if event:
            self._refresh_state()
            self.notify("Undone", severity="information")
        else:
            self.notify("Nothing to undo", severity="warning")

    def action_redo(self) -> None:
        event = self.store.redo()
        if event:
            self._refresh_state()
            self.notify("Redone", severity="information")
        else:
            self.notify("Nothing to redo", severity="warning")

    def action_quit_game(self) -> None:
        self.app.exit()
