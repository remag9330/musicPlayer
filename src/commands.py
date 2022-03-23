from typing import Union

class PlayCommand: pass

class PauseCommand: pass

class QueueCommand:
	def __init__(self, url: str, is_priority: bool = False):
		self.url = url
		self.is_priority = is_priority

class SkipCommand: pass

Command = Union[PlayCommand, PauseCommand, QueueCommand, SkipCommand]