from enum import Enum, auto
from typing import Optional, Tuple

from song import NullSong, Song
from speaker import speaker

from utils import hours_mins_secs_to_human_readable, secs_to_hours_mins_secs

class PlayingState(Enum):
	NotStarted = auto()
	Playing = auto()
	Paused = auto()


class PlayingSong:
	def __init__(self, song: Song):
		self.song = song
		self.playing_state = PlayingState.NotStarted
		self.load()

	def load(self):
		speaker.load(self.song.path)

	def play(self):
		if self.playing_state == PlayingState.NotStarted:
			speaker.play()
		elif self.playing_state == PlayingState.Paused:
			speaker.unpause()

		self.playing_state = PlayingState.Playing

	def pause(self):
		if self.playing_state != PlayingState.Playing:
			return

		self.playing_state = PlayingState.Paused
		speaker.pause()
	
	def is_finished(self) -> bool:
		return self.playing_state == PlayingState.Playing and not speaker.get_busy()
	
	def current_elapsed_time_secs(self) -> Optional[float]:
		pos = speaker.get_pos()
		if pos == -1:
			return None
		
		return pos / 1000

	def current_elapsed_time_hours_mins_secs(self) -> Optional[Tuple[int, int, int]]:
		total_secs = self.current_elapsed_time_secs()
		if total_secs is None:
			return None

		total_secs = round(total_secs)
		return secs_to_hours_mins_secs(total_secs)

	def current_elapsed_time_human_readable(self) -> str:
		elapsed = self.current_elapsed_time_hours_mins_secs()
		if elapsed is None:
			return "0:00"

		return hours_mins_secs_to_human_readable(elapsed)


	def current_elapsed_time_percent(self) -> Optional[float]:
		elapsed = self.current_elapsed_time_secs()
		if elapsed is None:
			return None

		if self.song.length_secs == 0:
			return 1

		return elapsed / self.song.length_secs


class NullPlayingSong(PlayingSong):
	def __init__(self):
		super().__init__(NullSong())

	def load(self):
		pass
	
	def play(self):
		pass

	def pause(self):
		pass

	def is_finished(self) -> bool:
		return True

	def current_elapsed_time_secs(self) -> Optional[float]:
		return 0