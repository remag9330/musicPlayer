import pathlib
import shutil
import threading
import logging
import queue
from typing import Callable, Optional, TypeVar
from typing_extensions import Never

from mutex import Mutex
from playlist import FilePlaylist, Playlist

from song import DownloadState, Song
from commands import Command, CreatePlaylistFromUrlCommand, PlayCommand, PauseCommand, QueueCommand, SkipCommand, VolumeCommand, ChangePlaylistCommand, DeleteCommand
from song_filename_generator import get_filename, get_youtube_filename, get_youtube_playlist_id_from_url
from song_queue import SongQueue
from speaker import speaker
import youtube_dl as yt_dl
import youtube_api as yt_api
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
		song = background_download_song_if_necessary(cmd.url, cmd.filename)

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

	elif isinstance(cmd, ChangePlaylistCommand):
		with song_queue.acquire() as sq:
			sq.value.change_playlist(cmd.name, cmd.shuffle)

	elif isinstance(cmd, CreatePlaylistFromUrlCommand):
		def on_complete(playlist: Playlist) -> None:
			with song_queue.acquire() as sq:
				sq.value.change_playlist(playlist.name, False)

		background_download_playlist(cmd.url, on_complete)

	elif isinstance(cmd, DeleteCommand):
		with song_queue.acquire() as sq:
			sq.value.default_all_playlist.remove_song(cmd.path)
			shutil.rmtree(pathlib.Path(cmd.path).parent.absolute())

	else:
		exhausted: Never = cmd
		raise Exception(f"Unknown command {exhausted}")

T = TypeVar("T")
def try_get(q: queue.Queue[T]) -> Optional[T]:
	try:
		return q.get(timeout=1)
	except queue.Empty:
		return None

def background_download_song_if_necessary(url: str, song_filename: Optional[str] = None) -> Song:
	logging.info(f"Starting download process for {url}")
	filename = song_filename or get_filename(url)
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

__downloader_semaphore = threading.BoundedSemaphore(settings.MAX_PARALLEL_DOWNLOADS)

def download_song(url: str, s: Song) -> None:
	try:
		logging.info("Waiting to acquire semaphore...")
		with __downloader_semaphore:
			logging.info("Semaphore acquired, starting download")
			yt_dl.download_audio(url, s.set_download_percentage)
			s.downloading = DownloadState.Downloaded
	except:
		logging.exception("Failed to download, setting .downloading to Error")
		s.downloading = DownloadState.Error



def background_download_playlist(url: str, on_complete: Callable[[Playlist], None]) -> None:
	logging.info(f"Starting playlist download for {url}")
	
	playlist_id = get_youtube_playlist_id_from_url(url)
	logging.debug(f"playlist_id = {playlist_id}")
	if playlist_id is None:
		logging.warning("No playlist id found - exiting")
		return

	playlist_name = yt_api.get_playlist_name(playlist_id)
	logging.debug(f"playlist_name = {playlist_name}")
	if playlist_name is None:
		logging.warning("No playlist name found - exiting")
		return
	
	playlist_videos = yt_api.get_playlist_videos(playlist_id)
	logging.debug(f"playlist_videos = {playlist_videos}")
	if playlist_videos is None:
		logging.warning("No playlist videos found - exiting")
		return

	filenames: list[str] = []
	for vid in playlist_videos:
		vid_url = f"https://www.youtube.com/watch?v={vid.id}"
		filename = get_youtube_filename(vid.id, vid.name)
		filenames.append(filename)
		background_download_song_if_necessary(vid_url, filename)

	FilePlaylist.create_playlist(playlist_name, filenames)

# pyright: reportUnnecessaryIsInstance=false