"""In-memory session store for active web games."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from uuid import uuid4

from baseball_scorebook.engine.event_store import EventStore
from baseball_scorebook.models.team import Team


@dataclass
class GameSession:
    """One active browser scoring session."""

    session_id: str
    away_team: Team
    home_team: Team
    store: EventStore = field(default_factory=EventStore)
    pending_transition: dict[str, object] | None = None


class SessionManager:
    """Thread-safe in-memory session registry."""

    def __init__(self) -> None:
        self._sessions: dict[str, GameSession] = {}
        self._lock = Lock()

    def create(self, away_team: Team, home_team: Team, store: EventStore | None = None) -> GameSession:
        session = GameSession(
            session_id=str(uuid4()),
            away_team=away_team,
            home_team=home_team,
            store=store or EventStore(),
        )
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> GameSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def require(self, session_id: str) -> GameSession:
        session = self.get(session_id)
        if session is None:
            raise KeyError(session_id)
        return session

    def clear_transition(self, session_id: str) -> GameSession:
        session = self.require(session_id)
        session.pending_transition = None
        return session

