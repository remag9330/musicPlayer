from typing import Optional, Union

class PlayCommand: pass

class PauseCommand: pass

class QueueCommand:
	def __init__(self, song_id: int, is_priority: bool = False, filename: Optional[str] = None):
		self.song_id = song_id
		self.is_priority = is_priority

class DownloadCommand:
	def __init__(self, url: str):
		self.url = url

class SkipCommand: pass

class VolumeCommand:
	def __init__(self, volume: float) -> None:
		self.volume = volume

class ChangePlaylistCommand:
	def __init__(self, name: str, shuffle: bool) -> None:
		self.name = name
		self.shuffle = shuffle

class CreatePlaylistFromUrlCommand:
	def __init__(self, url: str) -> None:
		self.url = url

class DeleteCommand:
	def __init__(self, song_id: int) -> None:
		self.song_id = song_id

Command = Union[
	PlayCommand,
	PauseCommand,
	QueueCommand,
	DownloadCommand,
	SkipCommand,
	VolumeCommand,
	ChangePlaylistCommand,
	CreatePlaylistFromUrlCommand,
	DeleteCommand
]