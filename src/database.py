from collections import namedtuple
import sqlite3
from typing import Optional, List, Tuple, Union, NamedTuple
import os

import settings

class User(NamedTuple):
    id: int
    name: str
    password_hash: str

class Song(NamedTuple):
    id: int
    name: str
    youtube_id: str
    start_time_ms: Optional[int]

    def path(self) -> str:
        return os.path.join(settings.MUSIC_DIR, self.youtube_id + ".mp3")

    def thumbnail_jpg(self) -> str:
        return os.path.join(settings.MUSIC_DIR, self.youtube_id + ".jpg")
    
    def thumbnail_webp(self) -> str:
        return os.path.join(settings.MUSIC_DIR, self.youtube_id + ".webp")

class Playlist(NamedTuple):
    id: int
    name: str

class Database:
    _expected_metadata_version = 1

    def __init__(self):
        self.db_name = settings.DATABASE_FILE
        self._initialize_schema()

        metadata_version = self._get_metadata_version()
        if metadata_version != self._expected_metadata_version:
            raise RuntimeError(f"The DB metadata version {metadata_version} was not the same as the expected one {self._expected_metadata_version}. This may mean that you have upgraded without running migration scripts, or you've downgraded beyond a DB schema change")

    def _initialize_schema(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Metadata (
                    version INTEGER PRIMARY KEY,
                )
            ''')

            cursor.execute('INSERT INTO Metadata (version) VALUES (1)')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Songs (
                    song_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    song_name TEXT NOT NULL,
                    youtube_id TEXT NOT NULL,
                    start_time_ms INTEGER DEFAULT 0,
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Ratings (
                    user_id INTEGER,
                    song_id INTEGER,
                    rating INTEGER CHECK(rating >= 0 AND rating <= 5),
                    PRIMARY KEY (user_id, song_id),
                    FOREIGN KEY (user_id) REFERENCES Users(user_id),
                    FOREIGN KEY (song_id) REFERENCES Songs(song_id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Playlists (
                    playlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS PlaylistSongs (
                    playlist_song_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    song_id INTEGER NOT NULL,
                    playlist_id INTEGER NOT NULL,
                    idx INTEGER NOT NULL,
                    FOREIGN KEY (song_id) REFERENCES Songs(song_id),
                    FOREIGN KEY (playlist_id) REFERENCES Playlists(playlist_id)
                )
            ''')
            conn.commit()

    def add_user(self, username: str, password_hash: str) -> int:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Users (username, password_hash) VALUES (?, ?)", (username, password_hash))
            conn.commit()
            return self._last_row_id(cursor)

    def add_song(self, song_name: str, youtube_id: str, start_time_ms: int = 0) -> int:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Songs (song_name, youtube_id, start_time_ms)
                VALUES (?, ?, ?)
            """, (song_name, youtube_id, start_time_ms))
            conn.commit()
            return self._last_row_id(cursor)

    def add_rating(self, user_id: int, song_id: int, rating: int) -> int:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Ratings (user_id, song_id, rating)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, song_id) DO UPDATE SET rating = excluded.rating
            """, (user_id, song_id, rating))
            conn.commit()
            return self._last_row_id(cursor)

    def add_playlist(self, playlist_name: str) -> int:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Playlists (name) VALUES (?)", (playlist_name,))
            conn.commit()
            return self._last_row_id(cursor)
        
    def add_song_to_playlist(self, song_id: int, playlist_id: int) -> int:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
        
            cursor.execute("""
                SELECT COALESCE(MAX(idx), -1) + 1
                FROM PlaylistSongs
                WHERE playlist_id = ?
            """, (playlist_id,))
            
            next_idx = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO PlaylistSongs (song_id, playlist_id, idx)
                VALUES (?, ?, ?)
            """, (song_id, playlist_id, next_idx))

            conn.commit()
            return self._last_row_id(cursor)

    def get_user(self, name_or_id: Union[str, int]) -> Optional[User]:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            if isinstance(name_or_id, int):
                cursor.execute("SELECT * FROM Users WHERE user_id = ?", (name_or_id,))
            else:
                cursor.execute("SELECT * FROM Users WHERE username = ?", (name_or_id,))
            return User(*cursor.fetchone())

    def get_song(self, id_or_name: Union[str, int]) -> Optional[Song]:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            if isinstance(id_or_name, int):
                cursor.execute("SELECT * FROM Songs WHERE song_id = ?", (id_or_name,))
            else:
                cursor.execute("SELECT * FROM Songs WHERE song_name = ?", (id_or_name,))
            return Song(*cursor.fetchone())
        
    def get_total_song_count(self) -> int:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM Songs")
            result = cursor.fetchone()
            return int(result[0]) if result else 0
    
    def get_songs(self) -> "list[Song]":
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Songs")
            songs = cursor.fetchall()
            return [Song(*song) for song in songs]
        
    def get_song_by_youtube_id(self, yt_id: str) -> Optional[Song]:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Songs WHERE youtube_id = ?", (yt_id,))
            result = cursor.fetchone()
            return Song(*result) if result else None
        
    def search_songs(self, query: str) -> "list[Song]":
        words = query.lower().split()

        if not words:
            return []

        conditions = " AND ".join([f"LOWER(song_name) LIKE ?" for _ in words])
        parameters = [f"%{word}%" for word in words]

        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT * FROM Songs
                WHERE {conditions}
            """, parameters)

            all_songs = cursor.fetchall()
            return [Song(*song) for song in all_songs]

    def get_rating_for_song(self, user_id: int, song_id: int) -> Optional[int]:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT rating FROM Ratings WHERE user_id = ? AND song_id = ?", (user_id, song_id))
            result = cursor.fetchone()
            return result[0] if result else None

    def get_ratings_for_song(self, song_id: int) -> List[int]:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT rating FROM Ratings WHERE song_id = ?", (song_id,))
            return cursor.fetchall()
        
    def get_random_song_rated_high_by_users(self, user_ids: List[int]) -> Optional[Song]:
        if not user_ids:
            return None

        placeholders = ','.join('?' for _ in user_ids)
        query = f'''
            SELECT s.*
            FROM Songs s
            JOIN Ratings r ON s.song_id = r.song_id
            WHERE r.rating > 3 AND r.user_id IN ({placeholders})
            GROUP BY s.song_id
            ORDER BY RANDOM()
            LIMIT 1
        '''

        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(query, user_ids)
            return Song(*cursor.fetchone())
        
    def get_playlist(self, playlist_id: Union[int, str]) -> Optional[Playlist]:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            if isinstance(playlist_id, int):
                cursor.execute("SELECT * FROM Playlists WHERE playlist_id = ?", (playlist_id,))
            else:
                cursor.execute("SELECT * FROM Playlists WHERE playlist_id = ?", (playlist_id,))
            playlist = cursor.fetchall()
            return Playlist(*playlist) if playlist else None
        
    def get_all_playlists(self) -> List[Playlist]:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Playlists")
            playlists = cursor.fetchall()
            return [Playlist(*playlist) for playlist in playlists]
        
    def get_next_playlist_song(self, playlist_id: int, current_idx: int) -> Tuple[Optional[Song], bool]:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT s.*
                FROM PlaylistSongs ps
                JOIN Songs s ON ps.song_id = s.song_id
                WHERE ps.playlist_id = ?
                AND ps.idx = ?
            """, (playlist_id, current_idx + 1))
            
            result = cursor.fetchone()

            back_to_start = result is None
            if back_to_start:
                cursor.execute("""
                    SELECT s.*
                    FROM PlaylistSongs ps
                    JOIN Songs s ON ps.song_id = s.song_id
                    WHERE ps.playlist_id = ?
                    AND ps.idx = 0
                """, (playlist_id,))

            song = Song(*result) if result else None
            return (song, back_to_start)
        
    def remove_song(self, song_id: int):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Songs WHERE song_id = ?", (song_id,))
            cursor.execute("DELETE FROM Ratings WHERE song_id = ?", (song_id,))
            cursor.execute("DELETE FROM PlaylistSongs WHERE song_id = ?", (song_id,))
            conn.commit()

    def _last_row_id(self, cursor) -> int:
        if cursor.lastrowid is not None:
            return cursor.lastrowid
        else:
            raise ValueError("No last row ID found.")
        
    def _get_metadata_version(self) -> int:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM Metadata")
            result = cursor.fetchone()
            return int(result[0]) if result else 0

database = Database()