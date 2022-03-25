import pathlib
import threading
import logging
import queue
from typing import Optional, TypeVar
from typing_extensions import Never

from mutex import Mutex

from song import DownloadState, Song
from commands import Command, PlayCommand, PauseCommand, QueueCommand, SkipCommand, VolumeDownCommand, VolumeUpCommand
from song_queue import SongQueue
from speaker import speaker
from youtube_dl import download_audio, get_filename

def start_music_player(event_queue: queue.Queue[Command], song_queue: Mutex[SongQueue]):
	while True:
		cmd = try_get(event_queue)

		if cmd is not None:
			process_cmd(song_queue, cmd)

		with song_queue.acquire() as sq:
			if sq.value.current_song_finished():
				sq.value.next_song()

def process_cmd(song_queue: Mutex[SongQueue], cmd: Command) -> None:
	logging.info(f"Processing cmd: '{cmd}'")

	if isinstance(cmd, PlayCommand):
		with song_queue.acquire() as sq:
			sq.value.play()

	elif isinstance(cmd, PauseCommand):
		with song_queue.acquire() as sq:
			sq.value.pause()

	elif isinstance(cmd, QueueCommand):
		song = background_download_song_if_necessary(cmd.url)

		with song_queue.acquire() as sq:
			if cmd.is_priority:
				sq.value.queue_song_priority(song)
			else:
				sq.value.queue_song(song)

	elif isinstance(cmd, SkipCommand):
		with song_queue.acquire() as sq:
			sq.value.next_song()

	elif isinstance(cmd, VolumeUpCommand):
		speaker().set_volume(speaker().get_volume() + 0.1)

	elif isinstance(cmd, VolumeDownCommand):
		speaker().set_volume(speaker().get_volume() - 0.1)

	else:
		exhausted: Never = cmd
		raise Exception(f"Unknown command {exhausted}")

T = TypeVar("T")
def try_get(q: queue.Queue[T]) -> Optional[T]:
	try:
		return q.get(timeout=1)
	except queue.Empty:
		return None

def background_download_song_if_necessary(url: str) -> Song:
	filename = get_filename(url)
	pathname = pathlib.Path(filename)

	if pathname.is_file():
		logging.info("Song exists, no need to download")
		return Song(pathname.stem, filename, DownloadState.Downloaded)
	else:
		logging.info("Song does not exist, starting download")
		s = Song(pathname.stem, filename, DownloadState.Downloading)
		background_download_song(url, s)
		return s

def background_download_song(url: str, s: Song) -> None:
	t = threading.Thread(target=download_song, args=(url, s), daemon=True)
	t.start()

def download_song(url: str, s: Song) -> None:
	try:
		download_audio(url, s.set_download_percentage)
		s.downloading = DownloadState.Downloaded
	except:
		logging.exception("Failed to download, setting .downloading to Error")
		s.downloading = DownloadState.Error

# pyright: reportUnnecessaryIsInstance=false