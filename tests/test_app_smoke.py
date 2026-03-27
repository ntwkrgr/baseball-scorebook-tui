"""Smoke test: verify the app starts and screens work."""
from __future__ import annotations

import pytest

from baseball_scorebook.app import BaseballScorebookApp


@pytest.mark.asyncio
async def test_app_starts() -> None:
    """The app should boot without crashing."""
    app = BaseballScorebookApp()
    async with app.run_test() as pilot:
        assert pilot.app.screen is not None


@pytest.mark.asyncio
async def test_new_game_pushes_lineup_editor() -> None:
    """Pressing New Game should push the lineup editor screen."""
    app = BaseballScorebookApp()
    async with app.run_test() as pilot:
        await pilot.click("#new-game")
        from baseball_scorebook.screens.lineup_editor import LineupEditorScreen
        assert isinstance(pilot.app.screen, LineupEditorScreen)
