import time
from typing import Optional
import uuid

class Sessions:
    __session_id_to_session: "dict[str, Session]" = {}
    __user_id_to_session: "dict[int, Session]" = {}

    def create_session_for_user(self, user_id: int) -> str:
        self.expire_users_session(user_id)

        session_id = str(uuid.uuid4())
        session = Session(user_id, session_id)

        self.__user_id_to_session[user_id] = session
        self.__session_id_to_session[session_id] = session
        
        return session.session_id

    def expire_session(self, session_id: str) -> None:
        session = self.__session_id_to_session.pop(session_id, None)
        if session:
            self.__user_id_to_session.pop(session.user_id, None)

    def expire_users_session(self, user_id: int) -> None:
        session = self.__user_id_to_session.pop(user_id, None)
        if session:
            self.__session_id_to_session.pop(session.session_id, None)

    def user_id_from_session(self, session_id: str) -> Optional[int]:
        session = self.__session_id_to_session.get(session_id, None)
        return session.user_id if session else None
    
    def update_last_active(self, user_id: int) -> None:
        session = self.__user_id_to_session.get(user_id, None)
        if session:
            session.update_last_active()
    
    def recently_active_users(self) -> "list[int]":
        result = []
        now = time.time()
        one_hour_in_seconds = 60 * 60

        for user in self.__user_id_to_session:
            session = self.__user_id_to_session[user]
            if now - session.last_active < one_hour_in_seconds:
                result.append(user)
        return result
    
class Session:
    def __init__(self, user_id: int, session_id: str) -> None:
        self.user_id = user_id
        self.session_id = session_id
        self.last_active = time.time()

    def update_last_active(self) -> None:
        self.last_active = time.time()