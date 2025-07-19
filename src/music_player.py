import pathlib
import shutil
import threading
import logging
import queue
from typing import Callable, Optional, TypeVar, Union
from typing_extensions import Never

from mutex import Mutex
from playlist import FilePlaylist, Playlist

from database import database
from song import DownloadState, Song
from commands import Command, CreatePlaylistFromUrlCommand, DownloadCommand, PlayCommand, PauseCommand, QueueCommand, SkipCommand, VolumeCommand, ChangePlaylistCommand, DeleteCommand
from song_filename_generator import get_name, get_video_id, get_youtube_playlist_id_from_url
from song_queue import SongQueue
from speaker import speaker
import youtube_dl as yt_dl
import youtube_api as yt_api
import settings

def start_music_player(event_queue: "queue.Queue[Command]", song_queue: Mutex[SongQueue]):
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
		song = database.get_song(cmd.song_id)

		if song is None:
			logging.warning(f"Could not find song {cmd.song_id} during queue command")
			return
		
		song = Song.from_db_song(song, DownloadState.Downloaded)

		with song_queue.acquire() as sq:
			if cmd.is_priority:
				sq.value.queue_song_priority(song)
			else:
				sq.value.queue_song(song)

	elif isinstance(cmd, DownloadCommand):
		song = background_download_song_if_necessary(cmd.url)

		with song_queue.acquire() as sq:
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
		song = database.get_song(cmd.song_id)
		if song is None:
			logging.warning(f"Song {cmd.song_id} could not be found")
			return
		
		database.remove_song(song.id)
		shutil.rmtree(pathlib.Path(song.path()).parent.absolute())
		shutil.rmtree(pathlib.Path(song.thumbnail_jpg()).parent.absolute())
		shutil.rmtree(pathlib.Path(song.thumbnail_webp()).parent.absolute())

	else:
		exhausted: Never = cmd
		raise Exception(f"Unknown command {exhausted}")

T = TypeVar("T")
def try_get(q: "queue.Queue[T]") -> Optional[T]:
	try:
		return q.get(timeout=1)
	except queue.Empty:
		return None

def background_download_song_if_necessary(url: str, song_name: Optional[str] = None, on_complete: Optional[Callable[[Song], None]] = None) -> Song:
	logging.info(f"Starting download process for {url}")
	vid_id = get_video_id(url)
	if vid_id is None:
		raise ValueError("Supplied URL was not a YT URL")
	
	existing_song = database.get_song_by_youtube_id(vid_id)

	if existing_song is not None:
		logging.info("Song exists, no need to download")
		return Song.from_db_song(existing_song, DownloadState.Downloaded)
	else:
		logging.info("Song does not exist, starting download")
		song_name = song_name or get_name(url)

		def on_complete_override(s: Song):
			id = database.add_song(song_name, vid_id, 0)
			new_song = database.get_song(id)
			assert new_song is not None

			s.id = id
			s.path = new_song.path()

			if on_complete: on_complete(s)

		s = Song(-1, song_name, "", DownloadState.Downloading)
		background_download_song(url, s, on_complete_override)
		return s

def background_download_song(url: str, s: Song, on_complete: Optional[Callable[[Song], None]] = None) -> None:
	t = threading.Thread(target=download_song, args=(url, s, on_complete), daemon=True)
	t.start()

__downloader_semaphore = threading.BoundedSemaphore(settings.MAX_PARALLEL_DOWNLOADS)

def download_song(url: str, s: Song, on_complete: Optional[Callable[[Song], None]] = None) -> None:
	attempts = 0

	while attempts < 2:
		attempts += 1

		try:
			logging.info("Waiting to acquire semaphore...")
			with __downloader_semaphore:
				logging.info("Semaphore acquired, starting download")
				yt_dl.download_audio(url, s.set_download_percentage)
				s.downloading = DownloadState.Downloaded
				if on_complete: on_complete(s)
				break
		except:
			logging.exception("Failed to download, setting .downloading to Error")
			if attempts >= 2:
				# Only set on final failure - otherwise it will get auto-removed from the queue
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
	
	completed_songs: "list[Union[Song, str]]" = [v.id for v in playlist_videos]
	downloads_remaining = len(playlist_videos)

	def on_song_complete(s: Song):
		new_song = database.get_song(s.id)
		assert new_song is not None, "Song should already exist"
		idx = completed_songs.index(new_song.youtube_id)
		completed_songs[idx] = s
		nonlocal downloads_remaining
		downloads_remaining -= 1

		if downloads_remaining == 0:
			assert all(isinstance(x, Song) for x in completed_songs), "Not all songs in completed list were songs?"
			pl = FilePlaylist.create_playlist(playlist_name, completed_songs) # type: ignore
			on_complete(pl)

	for vid in playlist_videos:
		vid_url = f"https://www.youtube.com/watch?v={vid.id}"
		background_download_song_if_necessary(vid_url, vid.name, on_song_complete)

# pyright: reportUnnecessaryIsInstance=false