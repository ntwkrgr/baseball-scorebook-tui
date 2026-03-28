"""FastAPI application and DTOs for the browser scorebook."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from baseball_scorebook.engine.state import derive_state
from baseball_scorebook.models.constants import (
    BaseCode,
    BaserunnerType,
    HalfCode,
    Position,
    ResultType,
    SubType,
)
from baseball_scorebook.models.team import LineupSlot, Player, Team
from baseball_scorebook.services.commands import (
    create_at_bat_events,
    create_baserunner_event,
    create_substitution_event,
    get_at_bat_defaults,
)
from baseball_scorebook.services.presentation import (
    build_game_snapshot,
    build_transition_summary,
)
from baseball_scorebook.storage.serializer import (
    generate_filename,
    get_default_save_dir,
    load_game,
    save_game,
)
from baseball_scorebook.web.sessions import SessionManager

STATIC_DIR = Path(__file__).resolve().parent / "static"


class LineupSlotPayload(BaseModel):
    battingOrder: int
    playerName: str
    playerNumber: int = 0
    position: str


class TeamPayload(BaseModel):
    name: str
    lineup: list[LineupSlotPayload]


class CreateGameRequest(BaseModel):
    awayTeam: TeamPayload
    homeTeam: TeamPayload


class AtBatDraftRequest(BaseModel):
    resultType: str = ResultType.GROUND_OUT.value


class RunnerAdvancePayload(BaseModel):
    fromBase: str
    toBase: str


class CommitAtBatRequest(BaseModel):
    resultType: str
    fielders: str = ""
    outsOnPlay: int | None = None
    batterReached: bool = False
    batterDestination: str | None = None
    runnerAdvances: list[RunnerAdvancePayload] = Field(default_factory=list)
    rbiCount: int = 0
    notes: str = ""


class CommitBaserunnerRequest(BaseModel):
    fromBase: str
    toBase: str
    how: str
    fielders: str = ""


class CommitSubstitutionRequest(BaseModel):
    team: str
    battingOrder: int
    enteringName: str
    enteringNumber: int = 0
    newPosition: str
    subType: str


class SaveGameRequest(BaseModel):
    filename: str | None = None


class LoadGameRequest(BaseModel):
    filename: str


def _payload_to_team(payload: TeamPayload) -> Team:
    lineup: list[LineupSlot] = []
    for slot in sorted(payload.lineup, key=lambda item: item.battingOrder):
        position = Position(slot.position)
        lineup.append(
            LineupSlot(
                batting_order=slot.battingOrder,
                player=Player(
                    name=slot.playerName.strip(),
                    number=slot.playerNumber,
                    position=position,
                ),
                position=position,
                entered_inning=1,
            )
        )
    return Team(name=payload.name.strip(), lineup=tuple(lineup))


def _transition_payload(session) -> dict[str, object]:
    return build_game_snapshot(
        session.session_id,
        session.away_team,
        session.home_team,
        session.store,
        pending_transition=session.pending_transition,
    )


def _update_transition(session, before_state, after_state) -> None:
    if (
        before_state.current_inning != after_state.current_inning
        or before_state.current_half != after_state.current_half
    ):
        session.pending_transition = build_transition_summary(
            after_state,
            session.away_team.name,
            session.home_team.name,
            before_state.current_inning,
            before_state.current_half,
        )


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(title="Baseball Scorebook")
    sessions = SessionManager()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/games/saved")
    def list_saved_games() -> dict[str, object]:
        save_dir = get_default_save_dir()
        return {
            "items": [
                {
                    "filename": path.name,
                    "stem": path.stem,
                }
                for path in sorted(save_dir.glob("*.json"), reverse=True)
            ]
        }

    @app.post("/api/games")
    def create_game(request: CreateGameRequest) -> dict[str, object]:
        away_team = _payload_to_team(request.awayTeam)
        home_team = _payload_to_team(request.homeTeam)
        session = sessions.create(away_team, home_team)
        return _transition_payload(session)

    @app.post("/api/games/load")
    def load_game_route(request: LoadGameRequest) -> dict[str, object]:
        path = get_default_save_dir() / request.filename
        if not path.exists():
            raise HTTPException(status_code=404, detail="Save file not found")
        data = load_game(path)
        session = sessions.create(data["away_team"], data["home_team"], data["store"])
        return _transition_payload(session)

    @app.get("/api/games/{session_id}")
    def get_game(session_id: str) -> dict[str, object]:
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return _transition_payload(session)

    @app.post("/api/games/{session_id}/drafts/at-bat")
    def get_at_bat_draft(session_id: str, request: AtBatDraftRequest) -> dict[str, object]:
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        state = derive_state(session.store)
        batting_team = session.away_team if state.current_half == HalfCode.TOP else session.home_team
        return get_at_bat_defaults(state, batting_team, ResultType(request.resultType))

    @app.post("/api/games/{session_id}/commands/at-bat")
    def commit_at_bat(session_id: str, request: CommitAtBatRequest) -> dict[str, object]:
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        before = derive_state(session.store)
        events = create_at_bat_events(
            before,
            result_type=ResultType(request.resultType),
            fielders=request.fielders,
            outs_on_play=request.outsOnPlay,
            batter_reached=request.batterReached,
            batter_destination=BaseCode(request.batterDestination) if request.batterDestination else None,
            runner_advances=[item.model_dump() for item in request.runnerAdvances],
            rbi_count=request.rbiCount,
            notes=request.notes,
        )
        for event in events:
            session.store.append(event)
        after = derive_state(session.store)
        _update_transition(session, before, after)
        return _transition_payload(session)

    @app.post("/api/games/{session_id}/commands/baserunner")
    def commit_baserunner(session_id: str, request: CommitBaserunnerRequest) -> dict[str, object]:
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        before = derive_state(session.store)
        event = create_baserunner_event(
            before,
            from_base=BaseCode(request.fromBase),
            to_base=BaseCode(request.toBase),
            how=BaserunnerType(request.how),
            fielders=request.fielders,
        )
        session.store.append(event)
        after = derive_state(session.store)
        _update_transition(session, before, after)
        return _transition_payload(session)

    @app.post("/api/games/{session_id}/commands/substitution")
    def commit_substitution(session_id: str, request: CommitSubstitutionRequest) -> dict[str, object]:
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        before = derive_state(session.store)
        event = create_substitution_event(
            before,
            session.away_team,
            session.home_team,
            team=HalfCode(request.team),
            batting_order=request.battingOrder,
            entering_name=request.enteringName,
            entering_number=request.enteringNumber,
            new_position=Position(request.newPosition),
            sub_type=SubType(request.subType),
        )
        session.store.append(event)
        after = derive_state(session.store)
        _update_transition(session, before, after)
        return _transition_payload(session)

    @app.post("/api/games/{session_id}/undo")
    def undo(session_id: str) -> dict[str, object]:
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        before = derive_state(session.store)
        if session.store.undo() is None:
            raise HTTPException(status_code=400, detail="Nothing to undo")
        session.pending_transition = None
        after = derive_state(session.store)
        _update_transition(session, before, after)
        return _transition_payload(session)

    @app.post("/api/games/{session_id}/redo")
    def redo(session_id: str) -> dict[str, object]:
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        before = derive_state(session.store)
        if session.store.redo() is None:
            raise HTTPException(status_code=400, detail="Nothing to redo")
        session.pending_transition = None
        after = derive_state(session.store)
        _update_transition(session, before, after)
        return _transition_payload(session)

    @app.post("/api/games/{session_id}/save")
    def save(session_id: str, request: SaveGameRequest) -> dict[str, object]:
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        filename = request.filename
        if not filename:
            filename = generate_filename(
                session.away_team.name,
                session.home_team.name,
                "",
            )
        path = get_default_save_dir() / filename
        save_game(path, session.away_team, session.home_team, session.store)
        return {"saved": True, "path": str(path), "filename": path.name}

    @app.post("/api/games/{session_id}/acknowledge-transition")
    def acknowledge_transition(session_id: str) -> dict[str, object]:
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        session.pending_transition = None
        return _transition_payload(session)

    if STATIC_DIR.exists():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

        @app.get("/{full_path:path}")
        def spa(full_path: str) -> FileResponse:
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not found")
            requested = STATIC_DIR / full_path
            if full_path and requested.exists() and requested.is_file():
                return FileResponse(requested)
            return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
