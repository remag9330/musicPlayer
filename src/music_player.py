import pathlib
import threading
import time
import logging
import queue
from typing import Optional, TypeVar

from mutex import Mutex

from song import DownloadState, Song
from commands import Command, PlayCommand, PauseCommand, QueueCommand
from song_queue import SongQueue
from youtube_dl import download_audio, get_filename

def start_music_player(event_queue: queue.Queue[Command], song_queue: Mutex[SongQueue]):
	while True:
		cmd = try_get_no_wait(event_queue)

		if cmd is not None:
			process_cmd(song_queue, cmd)

		with song_queue.acquire() as sq:
			if sq.value.current_song_finished():
				sq.value.next_song()

		time.sleep(1)

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

	else: # SkipCommand
		with song_queue.acquire() as sq:
			sq.value.next_song()

T = TypeVar("T")
def try_get_no_wait(q: queue.Queue[T]) -> Optional[T]:
	try:
		return q.get_nowait()
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
