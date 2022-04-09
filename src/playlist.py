from glob import glob
import logging
import os
from random import choice
import random
from typing import Union

from settings import MUSIC_DIR, PLAYLISTS_DIR
from song import DownloadState, NullSong, Song

class Playlist:
    def __init__(self, name: str) -> None:
        self.name = name
        self.shuffle = False

    def get_next(self) -> Song:
        raise NotImplementedError()

    def add_song(self, song: Song) -> None:
        raise NotImplementedError()

    @staticmethod
    def _song_name_from_path(path: str) -> str:
        return os.path.splitext(os.path.split(path)[1])[0]

    @staticmethod
    def _song_from_path(path: str) -> Song:
        name = Playlist._song_name_from_path(path)
        song = Song(name, path, DownloadState.Downloaded)
        return song

class AllAvailableCachedSongsPlaylist(Playlist):
    playlist_name = "All Downloaded Songs"

    def __init__(self) -> None:
        super().__init__(self.playlist_name)
        self.all_songs = set(glob(os.path.join(MUSIC_DIR, "*", "*.mp3")))

        if len(self.all_songs) == 0:
            # TODO Improve initial setup
            raise Exception("No songs found!")

    def get_next(self) -> Song:
        path = choice(tuple(self.all_songs))
        return self._song_from_path(path)

    def add_song(self, song: Song) -> None:
        self.all_songs.add(song.path)

    def remove_song(self, path: str) -> None:
        try:
            self.all_songs.remove(path)
        except KeyError:
            logging.exception(f"could not remove song from all_songs list, this might cause issues further down the line '{path}'")

    def all_available_songs(self) -> list[Song]:
        l = [self._song_from_path(s) for s in self.all_songs]
        l.sort(key=lambda s: s.name)
        return l

class FilePlaylist(Playlist):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.filename = os.path.join(PLAYLISTS_DIR, name)
        self.current_song_idx: int = -1 # Start just before first, `get_next()` will "prime" to the first item

        with open(self.filename, "r") as f:
            self.all_songs = f.readlines()
        
        self.all_songs = [s.strip() for s in self.all_songs if s.strip() != ""]

    def get_next(self) -> Song:
        if len(self.all_songs) == 0:
            logging.error(f"Read in an empty playlist: {self.filename}")
            return NullSong()

        if self.shuffle:
            self.current_song_idx = random.randint(0, len(self.all_songs) - 1)
        else:
            self.current_song_idx = (self.current_song_idx + 1) % len(self.all_songs)

        song_path = os.path.join(MUSIC_DIR, self.all_songs[self.current_song_idx])
        return self._song_from_path(song_path)

    def add_song(self, song: Union[Song, str]) -> None:
        full_path = song if isinstance(song, str) else song.path
        path = os.path.relpath(full_path, MUSIC_DIR)
        self.all_songs.append(path)

        with open(self.filename, "w") as f:
            f.writelines("\n".join(self.all_songs))

    @staticmethod
    def create_playlist(name: str, filenames: list[str]) -> Playlist:
        with open(os.path.join(PLAYLISTS_DIR, name), "w"):
            pass # Just create

        pl = FilePlaylist(name)

        for filename in filenames:
            pl.add_song(filename)

        return pl

    @staticmethod
    def all_available_playlist_names() -> list[str]:
        playlists = [AllAvailableCachedSongsPlaylist.playlist_name]

        try:
            playlists += os.listdir(PLAYLISTS_DIR)
        except FileNotFoundError:
            pass # Dir doesn't exist, do nothing
        except:
            logging.exception("Could not load playlists")

        return playlists