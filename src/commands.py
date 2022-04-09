from typing import Optional, Union

class PlayCommand: pass

class PauseCommand: pass

class QueueCommand:
	def __init__(self, url: str, is_priority: bool = False, filename: Optional[str] = None):
		self.url = url
		self.is_priority = is_priority
		self.filename = filename

class SkipCommand: pass

class VolumeCommand:
	def __init__(self, volume: int) -> None:
		self.volume = volume

class ChangePlaylistCommand:
	def __init__(self, name: str, shuffle: bool) -> None:
		self.name = name
		self.shuffle = shuffle

class CreatePlaylistFromUrlCommand:
	def __init__(self, url: str) -> None:
		self.url = url

class DeleteCommand:
	def __init__(self, path: str) -> None:
		self.path = path

Command = Union[
	PlayCommand,
	PauseCommand,
	QueueCommand,
	SkipCommand,
	VolumeCommand,
	ChangePlaylistCommand,
	CreatePlaylistFromUrlCommand,
	DeleteCommand
]