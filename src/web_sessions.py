import time
from typing import Optional
from datetime import datetime, timedelta, timezone

from database import database

class Sessions:
    __session_last_active: "dict[str, float]" = {}

    def create_session_for_user(self, user_id: int) -> str:
        self.expire_users_session(user_id)

        expires_at = (datetime.now(timezone.utc) + timedelta(days=90)).replace(microsecond=0).isoformat()
        return database.create_session(user_id, expires_at)

    def expire_session(self, session_id: str) -> None:
        database.remove_session(session_id)

    def expire_users_session(self, user_id: int) -> None:
        database.remove_users_session(user_id)

    def user_id_from_session(self, session_id: str) -> Optional[int]:
        session = database.get_session(session_id)
        return session.user_id if session else None
    
    def update_last_active(self, session_id: str) -> None:
        session = database.get_session(session_id)
        if session:
            self.__session_last_active[session.id] = time.time()
    
    def recently_active_users(self) -> "list[int]":
        active_sessions = database.get_active_sessions()
        result = []
        now = time.time()
        one_hour_in_seconds = 60 * 60

        for session in active_sessions:
            if now - self.__session_last_active.get(session.id, 0) < one_hour_in_seconds:
                result.append(session.user_id)
        return result
    
class Session:
    def __init__(self, user_id: int, session_id: str) -> None:
        self.user_id = user_id
        self.session_id = session_id
        self.last_active = time.time()
