import os
import pathlib
import threading
import logging
import queue
from urllib.parse import urlparse, parse_qs
from typing import Optional, TypeVar
from typing_extensions import Never

from mutex import Mutex

from song import DownloadState, Song
from commands import Command, PlayCommand, PauseCommand, QueueCommand, SkipCommand, VolumeCommand
from song_queue import SongQueue
from speaker import speaker
from youtube_dl import download_audio, get_filename
import settings

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

	elif isinstance(cmd, VolumeCommand):
		speaker().set_volume(cmd.volume)

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
	filename = try_get_filename(url)
	pathname = pathlib.Path(filename)

	if pathname.is_file():
		logging.info("Song exists, no need to download")
		return Song(pathname.stem, filename, DownloadState.Downloaded)
	else:
		logging.info("Song does not exist, starting download")
		s = Song(pathname.stem, filename, DownloadState.Downloading)
		background_download_song(url, s)
		return s

def try_get_filename(url: str) -> str:
	import pdb; pdb.set_trace()
	if "youtube.com" in url.lower():
		try:
			logging.info("Attempting to extract existing video's path")
			parsed = urlparse(url)
			vid_id = parse_qs(parsed.query)["v"][0]
			logging.debug(f"video id: {vid_id}")

			curr_path = os.path.join(settings.MUSIC_DIR, vid_id)
			files = [f for f in os.listdir(curr_path) if f.endswith(".mp3")]
			logging.debug(f"Files found: {len(files)}")
			if len(files) == 1:
				filename = files[0]
				result = os.path.join(curr_path, filename)
				logging.info(f"Found cached path: {result}")
				return result
		except:
			logging.exception("Could not specifically parse youtube path, falling back to ytdl")

	return get_filename(url)

def background_download_song(url: str, s: Song) -> None:
	t = threading.Thread(target=download_song, args=(url, s), daemon=True)
	t.start()

__downloader_semaphore = threading.BoundedSemaphore(settings.MAX_PARALLEL_DOWNLOADS)

def download_song(url: str, s: Song) -> None:
	try:
		logging.info("Waiting to acquire semaphore...")
		with __downloader_semaphore:
			logging.info("Semaphore acquired, starting download")
			download_audio(url, s.set_download_percentage)
			s.downloading = DownloadState.Downloaded
	except:
		logging.exception("Failed to download, setting .downloading to Error")
		s.downloading = DownloadState.Error

# pyright: reportUnnecessaryIsInstance=false