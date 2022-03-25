import base64
from enum import Enum, auto
import os
from typing import Optional

from mutagen.mp3 import MP3

from utils import hours_mins_secs_to_human_readable, secs_to_hours_mins_secs

class DownloadState(Enum):
	Downloading = auto()
	Downloaded = auto()
	Error = auto()


class Song:
	def __init__(self, name: str, path: str, downloading: DownloadState):
		self.name = name
		self.path = path
		self.downloading: DownloadState = downloading
		self.download_percentage = 0.0 if downloading == DownloadState.Downloading else 1.0

		self._cached_length_secs: Optional[float] = None

	@property
	def length_secs(self) -> float:
		if self._cached_length_secs is None:
			audio = MP3(self.path)
			self._cached_length_secs = audio.info.length

		return self._cached_length_secs

	@property
	def thumbnail_path(self) -> str:
		jpg = self.path.replace(".mp3", ".jpg")
		webp = self.path.replace(".mp3", ".webp")
		if os.path.isfile(webp):
			return webp
		
		return jpg

	def length_human_readable(self) -> str:
		return hours_mins_secs_to_human_readable(secs_to_hours_mins_secs(self.length_secs))

	def thumbnail_base64(self) -> str:
		try:
			with open(self.thumbnail_path, "rb") as f:
				data = f.read()
		except FileNotFoundError:
			with open("./static/questionMark.png", "rb") as f:
				data = f.read()

		b64 = base64.b64encode(data).decode("utf-8")

		return b64

	def set_download_percentage(self, val: float) -> None:
		self.download_percentage = val

class NullSong(Song):
	def __init__(self):
		super().__init__("<NULL>", "<NULL>", DownloadState.Downloaded)
		# Don't let the length_secs property try to read this non-existant file
		self._cached_length_secs = 0

	def thumbnail_base64(self) -> str:
		return ""

# pyright: reportMissingTypeStubs=false