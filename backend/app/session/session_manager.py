"""
In-memory session store.

P6 should replace the storage backing (self._sessions dict) with a real DB
table without changing this class's public methods, so the rest of the
pipeline doesn't need to change.
"""
from __future__ import annotations

from backend.app.schemas import Intent, Location, SessionState, TimeWindow


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def get_or_create(self, session_id: str, user_id: str | None = None) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(session_id=session_id, user_id=user_id)
        return self._sessions[session_id]

    def update_after_plan(
        self,
        session_id: str,
        location: Location,
        time_window: TimeWindow,
        intent: Intent,
    ) -> None:
        session = self.get_or_create(session_id)
        session.last_location = location
        session.last_time_window = time_window
        session.last_intent = intent
