import logging

from playing_song import NullPlayingSong, PlayingSong
from playlist import AllAvailableCachedSongsPlaylist, FilePlaylist, Playlist
from song import DownloadState, Song
from database import database

MAX_RECENTLY_PLAYED_SONGS = 100


class SongQueue:
	def __init__(self):
		self.up_next: list[Song] = []
		self.currently_playing: PlayingSong = NullPlayingSong()
		self.recently_played: list[Song] = []

		self.default_all_playlist = AllAvailableCachedSongsPlaylist()
		self.playlist: Playlist = self.default_all_playlist

	def queue_song(self, song: Song) -> None:
		self.up_next.append(song)

	def queue_song_priority(self, song: Song) -> None:
		self.up_next.insert(0, song)

	def play(self) -> None:
		self.currently_playing.play()

	def pause(self) -> None:
		self.currently_playing.pause()

	def current_song_finished(self) -> bool:
		return self.currently_playing.is_finished()

	def next_song(self):
		song = self._extract_next_song_from_up_next()
		self._copy_currently_playing_to_recently_played()

		self.currently_playing = PlayingSong(song)
		self.currently_playing.play()
		self.currently_playing.skip_to_overridden_start()

	def _copy_currently_playing_to_recently_played(self):
		self.recently_played.append(self.currently_playing.song)
		self.recently_played = self.recently_played[-MAX_RECENTLY_PLAYED_SONGS:]

	def _extract_next_song_from_up_next(self):
		self._clear_errored_downloads()
		
		logging.info(f"Finding next song in queue of {len(self.up_next)} song(s)")
		for song in self.up_next:
			if song.downloading == DownloadState.Downloaded:
				logging.info(f"Found song available to play: {song.name} ({song.path})")
				self.up_next.remove(song)
				break
		else:
			song = None

		if song is None:
			logging.info("No songs queued/ready, getting next song from playlist")
			song = self._random_available_song()
			logging.info(f"Selected song is {song.name}")

		return song

	def _random_available_song(self) -> Song:
		return self.playlist.get_next()

	def _clear_errored_downloads(self) -> None:
		errored_songs = [s for s in self.up_next if s.downloading == DownloadState.Error]
		if len(errored_songs) == 0:
			return

		logging.info(f"Removing {len(errored_songs)} song(s) that errored downloading")
		for to_remove in errored_songs:
			logging.debug(f"Removing {to_remove.name} (failed to download)")
			self.up_next.remove(to_remove)

	def change_playlist(self, id: int, shuffle: bool) -> None:
		if id != self.playlist.id:
			if id == self.default_all_playlist.id:
				logging.info(f"Changing playlist back to default all song playlist")
				self.playlist = self.default_all_playlist
			else:
				logging.info(f"Changing playlist to {id}")
				pl = database.get_playlist(id)
				if pl is None:
					logging.warning("Unknown playlist selected")
					return
				self.playlist = FilePlaylist(pl.id, pl.name)

		logging.info(f"Setting playlists shuffle state to {shuffle}")
		self.playlist.shuffle = shuffle