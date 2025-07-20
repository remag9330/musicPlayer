from typing import Callable

from song import DownloadState, NullSong, Song
from database import database

class Playlist:
    def __init__(self, id: int, name: str) -> None:
        self.id = id
        self.name = name
        self.shuffle = False

    def get_next(self) -> Song:
        raise NotImplementedError()

class AllAvailableCachedSongsPlaylist(Playlist):
    playlist_name = "All Downloaded Songs"
    playlist_id = -1

    def __init__(self) -> None:
        super().__init__(self.playlist_id, self.playlist_name)
        self.whos_listening: Callable[[], list[int]] = lambda: []

    def get_next(self) -> Song:
        whos_listening = self.whos_listening()
        song = database.get_random_song_rated_not_low_by_users(whos_listening)
        return Song.from_db_song(song, DownloadState.Downloaded) if song else NullSong()

class FilePlaylist(Playlist):
    def __init__(self, id: int, name: str) -> None:
        super().__init__(id, name)
        self.current_song_idx: int = -1 # Start just before first, `get_next()` will "prime" to the first item

    def get_next(self) -> Song:
        if self.shuffle:
            song = database.get_random_playlist_song(self.id)
        else:
            [song, looped] = database.get_next_playlist_song(self.id, self.current_song_idx)
            self.current_song_idx = 0 if looped else self.current_song_idx + 1
        return Song.from_db_song(song, DownloadState.Downloaded) if song else NullSong()

    def add_song(self, song: Song) -> None:
        database.add_song_to_playlist(song.id, self.id)

    @staticmethod
    def create_playlist(name: str, songs: "list[Song]") -> Playlist:
        id = database.add_playlist(name)
        for song in songs:
            database.add_song_to_playlist(song.id, id)

        return FilePlaylist(id, name)

    @staticmethod
    def all_available_playlists() -> "list[Playlist]":
        playlists: list[Playlist] = [AllAvailableCachedSongsPlaylist()]
        playlists += [FilePlaylist(p.id, p.name) for p in database.get_all_playlists()]
        return playlists