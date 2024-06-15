import time
from typing import Optional
import uuid

class Sessions:
    __session_id_to_session: "dict[str, Session]" = {}
    __username_to_session: "dict[str, Session]" = {}

    def create_session_for_user(self, username: str) -> str:
        self.expire_users_session(username)

        session_id = str(uuid.uuid4())
        session = Session(username, session_id)

        self.__username_to_session[username] = session
        self.__session_id_to_session[session_id] = session
        
        return session.session_id

    def expire_session(self, session_id: str) -> None:
        session = self.__session_id_to_session.pop(session_id, None)
        if session:
            self.__username_to_session.pop(session.username, None)

    def expire_users_session(self, username: str) -> None:
        session = self.__username_to_session.pop(username, None)
        if session:
            self.__session_id_to_session.pop(session.session_id, None)

    def user_from_session(self, session_id: str) -> Optional[str]:
        session = self.__session_id_to_session.get(session_id, None)
        return session.username if session else None
    
    def update_last_active(self, username: str) -> None:
        session = self.__username_to_session.get(username, None)
        if session:
            session.update_last_active()
    
    def recently_active_users(self) -> "list[str]":
        result = []
        now = time.time()
        one_hour_in_seconds = 60 * 60

        for user in self.__username_to_session:
            session = self.__username_to_session[user]
            if now - session.last_active < one_hour_in_seconds:
                result.append(user)
        return result
    
class Session:
    def __init__(self, username: str, session_id: str) -> None:
        self.username = username
        self.session_id = session_id
        self.last_active = time.time()

    def update_last_active(self) -> None:
        self.last_active = time.time()