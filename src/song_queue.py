from glob import glob
from random import choice
import logging
import os

from playing_song import NullPlayingSong, PlayingSong
from settings import MUSIC_DIR
from song import DownloadState, Song

MAX_RECENTLY_PLAYED_SONGS = 100


class SongQueue:
	def __init__(self):
		self.up_next: list[Song] = []
		self.currently_playing: PlayingSong = NullPlayingSong()
		self.recently_played: list[Song] = []

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

		# TODO remove at some point when _random_available_song is properly implemented
		self.currently_playing = PlayingSong(song)
		self.currently_playing.play()

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
			logging.info("No songs queued, getting random available song")
			song = self._random_available_song()

		return song

	def _random_available_song(self) -> Song:
		# TODO maybe cache this and update every half hour or when something new is queued?
		all_songs = glob(os.path.join(MUSIC_DIR, "*", "*.mp3"))
		if len(all_songs) == 0:
			# TODO Improve initial setup
			raise Exception("No songs found!")

		path = choice(all_songs)
		name = os.path.splitext(os.path.split(path)[1])[0]

		song = Song(name, path, DownloadState.Downloaded)
		return song

	def _clear_errored_downloads(self) -> None:
		errored_songs = [s for s in self.up_next if s.downloading == DownloadState.Error]
		if len(errored_songs) == 0:
			return

		logging.info(f"Removing {len(errored_songs)} song(s) that errored downloading")
		for to_remove in errored_songs:
			logging.debug(f"Removing {to_remove.name} (failed to download)")
			self.up_next.remove(to_remove)