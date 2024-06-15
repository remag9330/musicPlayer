import logging
import math
import queue
from pathlib import Path
from typing import Optional, Union

from mutex import Mutex
import ratings
from song import Song
from song_filename_generator import get_youtube_filename_from_cache
from song_queue import SongQueue
from commands import Command, PlayCommand, PauseCommand, QueueCommand, SkipCommand, VolumeCommand, ChangePlaylistCommand, CreatePlaylistFromUrlCommand, DeleteCommand
from speaker import speaker

from bottle import get, hook, post, run, template, static_file, request, response, redirect

from settings import WEBSERVER_IP, WEBSERVER_PORT, MUSIC_DIR, SONGS_PER_PAGE
from users import authenticate_user
from web_sessions import Sessions
from youtube_api import SearchResult, search_youtube

def start_webserver(event_queue: "queue.Queue[Command]", song_queue: Mutex[SongQueue]):
	try:
		logging.info("Background server thread starting up! Setting up routes")
		setup_routes(event_queue, song_queue)
		logging.info("Routes set up. Starting web server")
		run(host=WEBSERVER_IP, port=WEBSERVER_PORT, quiet=True, debug=True)
		logging.warning("Webserver finished - this shouldn't normally happen?")
	except:
		logging.exception("Error occurred while running web server")

def setup_routes(event_queue: "queue.Queue[Command]", song_queue: Mutex[SongQueue]):
	sessions = Sessions()
	with song_queue.acquire() as sq:
		sq.value.default_all_playlist.whos_listening = lambda: sessions.recently_active_users()

	def _get_username() -> Optional[str]:
		return sessions.user_from_session(request.get_cookie("authSession", ""))
	
	@hook("before_request")
	def update_last_accessed() -> None:
		username = _get_username()
		if username:
			sessions.update_last_active(username)

	@get("/")
	def index():
		username = _get_username()

		with song_queue.acquire() as sq:
			current_volume = speaker().get_volume()
			vol_min_max_step = speaker().volume_min_max_step()

			rating = ratings.get_song_rating(sq.value.currently_playing.song, username)
			
			return template("index",
				song_queue=sq.value,
				current_volume=current_volume,
				vol_min_max_step=vol_min_max_step,
				username=username,
				rating=rating
			)

	@get("/static/<filename:path>")
	def static(filename: str):
		return static_file(filename, root="./static/")

	@post("/play")
	def play():
		event_queue.put_nowait(PlayCommand())
		return redirect("/")

	@post("/pause")
	def pause():
		event_queue.put_nowait(PauseCommand())
		return redirect("/")

	@post("/volume")
	def volume():
		vol = ""

		try:
			vol = request.params["volume"]
			if not isinstance(vol, str):
				raise Exception(f"Unknown type for vol")

			vol = float(vol)
			event_queue.put_nowait(VolumeCommand(vol))
		except:
			logging.exception("Bad input for volume endpoint")
			response.status = 400
			error_message = f"Volume parameter not specified or invalid. Ensure it's a number. vol='{vol}'"
			return template("error", error_message=error_message)
			
		return redirect("/")

	@post("/queue")
	def queue():
		url: str = request.params["url"]

		try:
			is_priority: bool = request.params["priority"] != ""
		except KeyError:
			is_priority: bool = False

		event_queue.put_nowait(QueueCommand(url, is_priority))
		return redirect("/")

	@post("/skip")
	def skip():
		event_queue.put_nowait(SkipCommand())
		return redirect("/")

	@post("/playlist")
	def playlist():
		playlist_name = ""
		shuffle = False

		try:
			playlist_name = request.forms.playlist
			if not isinstance(playlist_name, str):
				raise Exception("Unknown type for playlist")

			try:
				shuffle: bool = request.params["shuffle"] != ""
			except KeyError:
				shuffle: bool = False

			event_queue.put_nowait(ChangePlaylistCommand(playlist_name, shuffle))
		except:
			logging.exception("Bad input for playlist endpoint")
			response.status = 400
			error_message = f"Playlist parameters not specified or invalid: playlist='{playlist_name}', shuffle='{shuffle}'"
			return template("error", error_message=error_message)

		return redirect("/")

	@post("/createPlaylist")
	def createPlaylist():
		url = ""

		try:
			url = request.params["url"]
			if not isinstance(url, str):
				raise Exception("Unknown type for url")

			event_queue.put_nowait(CreatePlaylistFromUrlCommand(url))
		except:
			logging.exception("Bad input for create playlist endpoint")
			response.status = 400
			error_message = f"Create playlist parameters not specified or invalid: url='{url}'"
			return template("error", error_message=error_message)

		return redirect("/")

		
	def _search_terms() -> str:
		search_terms = ""
		try:
			search_terms = request.query.search or request.forms.search
			if not isinstance(search_terms, str):
				raise Exception("Unknown type for search_terms")
		except:
			logging.exception("Could not get search terms")

		return search_terms or ""

	def _page() -> int:
		page = 1

		try:
			page_str = request.query.page or request.forms.page
			if not isinstance(page_str, str):
				raise Exception("Unknown type for page")
			
			page = int(page_str or "1")
		except:
			logging.exception("Could not get page number")

		return page

	def _force_search_youtube() -> bool:
		force_search_youtube = ""
		try:
			force_search_youtube = request.query.forceSearchYoutube or request.forms.forceSearchYoutube
			if not isinstance(force_search_youtube, str):
				raise Exception("Unknown type for force_search_youtube")
		except:
			logging.exception("Could not get search terms")

		return (force_search_youtube or "false") != "false"

	@get("/songs")
	def songs():
		search_terms = _search_terms()
		logging.info(f"search_terms = {search_terms}")

		page = _page()
		logging.info(f"page = {page}")
		if page < 1:
			logging.info("Page is below 1, clamping to 1")
			page = 1

		force_search_youtube = _force_search_youtube()
		logging.info(f"force_search_youtube = {force_search_youtube}")

		songs_per_page = SONGS_PER_PAGE

		songs: list[Union[Song, SearchResult]] = []
		youtube_searched = False

		with song_queue.acquire() as sq:
			songs = sq.value.default_all_playlist.all_available_songs()

		if search_terms:
			for term in search_terms.split():
				songs = [s for s in songs if term.lower() in s.path.lower()]

			# If we didn't find any songs (or it's been requested), also perform a search via the YouTube API
			if len(songs) == 0 or force_search_youtube:
				results = search_youtube(search_terms, "video") or []
				youtube_searched = True

				with song_queue.acquire() as sq:
					song_from_path = sq.value.default_all_playlist.song_from_path

					for result in results:
						# We check if the song's already been downloaded by checking if the file's already on disk
						path = get_youtube_filename_from_cache(result.video_id)
						existing_song = song_from_path(path) if path is not None else None

						# Make sure to not double up on any results that may already be retrieved earlier
						if existing_song is not None:
							if existing_song not in songs:
								songs.append(existing_song)
						else:
							songs.append(result)

				# Sort the songs so already-downloaded songs appear first
				songs.sort(key=lambda s: not isinstance(s, Song))


		total_pages = math.ceil(len(songs) / songs_per_page)
		if page > total_pages:
			page = total_pages
			logging.info(f"Page is above max ({total_pages}), clamping to max")
		
		start = (page - 1) * songs_per_page
		end = start + songs_per_page
		songs = songs[start:end]

		return template("songs", songs=songs, search=search_terms, youtube_searched=youtube_searched, current_page=page, total_pages=total_pages)

	@post("/songs/play")
	def songs_play():
		song_id = ""

		try:
			song_id = request.forms.id
			if not isinstance(song_id, str):
				raise Exception("Unknown type for song id")

			music_dir = Path(MUSIC_DIR)
			suggested_song_path = Path(song_id)
			if not music_dir in suggested_song_path.parents:
				raise Exception("Invalid song id")

			event_queue.put_nowait(QueueCommand("", False, song_id))
		except:
			logging.exception("Bad input for play song")
			response.status = 400
			error_message = f"Play song parameters not specified or invalid: id='{song_id}'"
			return template("error", error_message=error_message)

		search = _search_terms()
		return redirect(f"/songs?search={search}")

	@post("/songs/delete")
	def songs_delete():
		song_id = ""

		try:
			song_id = request.forms.id
			if not isinstance(song_id, str):
				raise Exception("Unknown type for song id")

			music_dir = Path(MUSIC_DIR)
			suggested_song_path = Path(song_id)
			if not music_dir in suggested_song_path.parents:
				raise Exception("Invalid song id")

			event_queue.put_nowait(DeleteCommand(song_id))
		except:
			logging.exception("Bad input for delete song")
			response.status = 400
			error_message = f"Delete song parameters not specified or invalid: id='{song_id}'"
			return template("error", error_message=error_message)

		search = _search_terms()
		return redirect(f"/songs?search={search}")

	@get("/login")
	def login_page():
		try:
			error = request.params["error"] or ""
		except KeyError:
			error = ""

		error_message = None
		if error == "invalidUsernameOrPassword":
			error_message = "The username or password was incorrect"

		return template("login", error_message=error_message)

	@post("/login")
	def login():
		try:
			username = str(request.forms.username)
			password = str(request.forms.password)
		except:
			logging.exception("Bad input for login")
			response.status = 400
			error_message = f"Login parameters not specified or invalid"
			return template("error", error_message=error_message)
		
		logging.info(f"attempting login for {username}")
		
		error = authenticate_user(username, password)
		if error:
			return redirect(f"/login?error={error}")
			
		session = sessions.create_session_for_user(username)
		response.set_cookie("authSession", session, max_age=90*24*60*60, httponly=True, samesite="strict")

		return redirect("/")
	

	@post("/rateSong")
	def rate_song():
		username = _get_username()
		if username is None:
			logging.info("Unauthenticated user in rateSong, exiting")
			response.status = 403
			return redirect("/")

		try:
			song_name = request.forms.song_name
			rating = int(request.forms.rating)
		except:
			logging.exception("Bad input for login")
			response.status = 400
			error_message = f"Login parameters not specified or invalid"
			return template("error", error_message=error_message)
		
		with song_queue.acquire() as sq:
			if sq.value.currently_playing.song.name != song_name:
				logging.warn("song name not current song, skipping user rating")

			ratings.rate_song(sq.value.currently_playing.song, username, rating)

		logging.info(f"{username} {song_name} {rating}")
		return redirect("/")

# pyright: reportGeneralTypeIssues=false, reportMissingTypeStubs=false, reportUnusedFunction=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportUnknownMemberType=false