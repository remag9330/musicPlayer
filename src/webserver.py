import logging
import math
import queue
from typing import NoReturn, Optional, Union

from database import database
from mutex import Mutex
from song import DownloadState, Song
from song_queue import SongQueue
from commands import Command, PlayCommand, PauseCommand, QueueCommand, SkipCommand, VolumeCommand, ChangePlaylistCommand, CreatePlaylistFromUrlCommand, DeleteCommand
from speaker import speaker

from bottle import get, hook, post, run, template, static_file, request, response, redirect
from settings import WEBSERVER_IP, WEBSERVER_PORT, SONGS_PER_PAGE
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

	def _get_session_id():
		return request.get_cookie("authSession", "")

	def _get_user():
		session_id = _get_session_id()
		if session_id is None: return None
		user_id = sessions.user_id_from_session(session_id)
		if user_id is None: return None
		return database.get_user(user_id)
	
	def _get_str_param(name: str) -> Optional[str]:
		param = request.query.get(name) or request.forms.get(name) # type: ignore Bad typings on the .get(...)
		if not (param is None or isinstance(param, str)):
			raise Exception(f"Unknown type for {name}")
		return param
	
	def _get_int_param(name: str) -> Optional[int]:
		param = _get_str_param(name)
		try:
			return int(param) if param else None
		except:
			logging.exception(f"Could not parse param '{name}' with value '{param}'")
			raise
	
	def _get_float_param(name: str) -> Optional[float]:
		param = _get_str_param(name)
		try:
			return float(param) if param else None
		except:
			logging.exception(f"Could not parse param '{name}' with value '{param}'")
			raise
	
	def _get_bool_param(name: str) -> bool:
		try:
			return (_get_str_param(name) or "") != ""
		except KeyError:
			return False
	
	def _throw_bad_param(name: str) -> NoReturn:
		raise ValueError(f"Invalid param {name}")
	
	@hook("before_request")
	def update_last_accessed() -> None:
		session_id = _get_session_id()
		if session_id is not None:
			sessions.update_last_active(session_id)

	@get("/")
	def index():
		user = _get_user()
		logging.info(user.name if user else "<>")

		with song_queue.acquire() as sq:
			current_volume = speaker().get_volume()
			vol_min_max_step = speaker().volume_min_max_step()

			rating = database.get_rating_for_song(user.id, sq.value.currently_playing.song.id) if user else 0
			
			return template("index",
				song_queue=sq.value,
				current_volume=current_volume,
				vol_min_max_step=vol_min_max_step,
				username=user.name if user else None,
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
			vol = _get_float_param("volume")
			if vol is None: _throw_bad_param("volume")
			event_queue.put_nowait(VolumeCommand(vol))
		except:
			logging.exception("Bad input for volume endpoint")
			response.status = 400
			error_message = f"Volume parameter not specified or invalid. Ensure it's a number. vol='{vol}'"
			return template("error", error_message=error_message)
			
		return redirect("/")

	@post("/queue")
	def queue():
		id = ""

		try:
			id = _get_int_param("id") or _throw_bad_param("id")
			is_priority = _get_bool_param("priority")

			event_queue.put_nowait(QueueCommand(id, is_priority))
		except:
			logging.exception("Bad input for queue endpoint")
			response.status = 400
			error_message = f"ID parameter not specified or invalid. Ensure it's a number. id='{id}'"
			return template("error", error_message=error_message)

		return redirect("/")

	@post("/skip")
	def skip():
		event_queue.put_nowait(SkipCommand())
		return redirect("/")

	@post("/playlist")
	def playlist():
		playlist_id = ""
		shuffle = False

		try:
			playlist_id = _get_int_param("playlist_id") or _throw_bad_param("playlist_id")
			shuffle = _get_bool_param("shuffle")

			event_queue.put_nowait(ChangePlaylistCommand(playlist_id, shuffle))
		except:
			logging.exception("Bad input for playlist endpoint")
			response.status = 400
			error_message = f"Playlist parameters not specified or invalid: playlist='{playlist_id}', shuffle='{shuffle}'"
			return template("error", error_message=error_message)

		return redirect("/")

	@post("/createPlaylist")
	def createPlaylist():
		url = ""

		try:
			url = _get_str_param("url") or _throw_bad_param("url")

			event_queue.put_nowait(CreatePlaylistFromUrlCommand(url))
		except:
			logging.exception("Bad input for create playlist endpoint")
			response.status = 400
			error_message = f"Create playlist parameters not specified or invalid: url='{url}'"
			return template("error", error_message=error_message)

		return redirect("/")

		
	def _search_terms() -> str:
		try:
			return _get_str_param("search") or ""
		except:
			logging.exception("Could not get search terms")
			return ""

	def _page() -> int:
		try:
			return _get_int_param("page") or 1
		except:
			logging.exception("Could not get page number")
			return 1

	def _force_search_youtube() -> bool:
		try:
			return _get_str_param("forceSearchYoutube") == "true"
		except:
			logging.exception("Could not get search terms")
			return False

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

		if search_terms:
			db_songs = database.search_songs(search_terms)
		else:
			db_songs = database.get_songs()

		songs: list[Union[Song, SearchResult]] = [Song.from_db_song(s, DownloadState.Downloaded) for s in db_songs]
		song_count = len(songs)

		start = (page - 1) * SONGS_PER_PAGE
		end = start + SONGS_PER_PAGE
		
		youtube_searched = False

		# If we didn't find any songs (or it's been requested), also perform a search via the YouTube API
		if search_terms and (len(songs) == 0 or force_search_youtube):
			results = search_youtube(search_terms, "video") or []
			youtube_searched = True

			for result in results:
				existing_song_db = database.get_song_by_youtube_id(result.video_id)

				# Make sure to not double up on any results that may already be retrieved earlier
				if existing_song_db is not None:
					existing_song = next((x for x in songs if isinstance(x, Song) and x.id == existing_song_db.id), None)
					if existing_song is None:
						songs.append(Song.from_db_song(existing_song_db, DownloadState.Downloaded))
				else:
					songs.append(result)

			# Sort the songs so already-downloaded songs appear first
			songs.sort(key=lambda s: not isinstance(s, Song))

		total_pages = math.ceil(song_count / SONGS_PER_PAGE)
		if page > total_pages:
			page = total_pages
			logging.info(f"Page is above max ({total_pages}), clamping to max")
		
		songs = songs[start:end]

		return template("songs", songs=songs, search=search_terms, youtube_searched=youtube_searched, current_page=page, total_pages=total_pages)

	@post("/songs/play")
	def songs_play():
		song_id = ""

		try:
			song_id = _get_int_param("id") or _throw_bad_param("id")
			
			if database.get_song(song_id) is None:
				raise Exception("Invalid song id")

			event_queue.put_nowait(QueueCommand(song_id, False))
		except:
			logging.exception("Bad input for play song")
			response.status = 400
			error_message = f"Play song parameters not specified or invalid: id='{song_id}'"
			return template("error", error_message=error_message)

		search = _search_terms()
		page = _page()
		return redirect(f"/songs?search={search}&page={page}")

	@post("/songs/delete")
	def songs_delete():
		song_id = ""

		try:
			song_id = _get_int_param("id") or _throw_bad_param("id")
			
			if database.get_song(song_id) is None:
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
		error = _get_str_param("error") or ""

		error_message = None
		if error == "invalidUsernameOrPassword":
			error_message = "The username or password was incorrect"

		return template("login", error_message=error_message)

	@post("/login")
	def login():
		try:
			username = _get_str_param("username") or _throw_bad_param("username")
			password = _get_str_param("password") or _throw_bad_param("password")
		except:
			logging.exception("Bad input for login")
			response.status = 400
			error_message = f"Login parameters not specified or invalid"
			return template("error", error_message=error_message)
		
		logging.info(f"attempting login for {username}")
		
		result = authenticate_user(username, password)
		if isinstance(result, str):
			return redirect(f"/login?error={result}")
			
		session = sessions.create_session_for_user(result)
		response.set_cookie("authSession", session, max_age=90*24*60*60, httponly=True, samesite="strict")

		return redirect("/")
	

	@post("/rateSong")
	def rate_song():
		user = _get_user()
		if user is None:
			logging.info("Unauthenticated user in rateSong, exiting")
			response.status = 403
			return redirect("/")

		try:
			song_id = _get_int_param("song_id") or _throw_bad_param("song_id")
			rating = _get_int_param("rating") or _throw_bad_param("rating")
			
			if database.get_song(song_id) is None:
				raise Exception("Invalid song id")
		except:
			logging.exception("Bad input for login")
			response.status = 400
			error_message = f"Login parameters not specified or invalid"
			return template("error", error_message=error_message)
		
		with song_queue.acquire() as sq:
			if sq.value.currently_playing.song.id != song_id:
				logging.warning("song name not current song, skipping user rating")

		database.add_rating(user.id, song_id, rating)

		logging.info(f"user '{user.id}' rated song '{song_id}' a {rating}/5")
		return redirect("/")

# pyright: reportGeneralTypeIssues=false, reportMissingTypeStubs=false, reportUnusedFunction=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportUnknownMemberType=false