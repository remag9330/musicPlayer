import queue
import time

from mutex import Mutex
from song_queue import SongQueue
from commands import Command, PlayCommand, PauseCommand, QueueCommand, SkipCommand, VolumeDownCommand, VolumeUpCommand
from speaker import speaker

from bottle import get, post, run, template, static_file, request, response, redirect

from settings import WEBSERVER_IP, WEBSERVER_PORT

def start_webserver(event_queue: queue.Queue[Command], song_queue: Mutex[SongQueue]):
	@get("/")
	def index():
		with song_queue.acquire() as sq:
			current_volume = round(speaker.get_volume() * 100 / 10) * 10 # Round to nearest 10
			return template("index", song_queue=sq.value, current_volume=current_volume)

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
		dir = request.params["direction"]
		if dir == "up":
			event_queue.put_nowait(VolumeUpCommand())
		elif dir == "down":
			event_queue.put_nowait(VolumeDownCommand())
		else:
			response.status = 400
			error_message = f"No such volume direction '{dir}'. Must be either 'up' or 'down'"
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

	@get("/stream")
	def stream():
		response.set_header("Content-Type", "text/event-stream")

		for i in range(5):
			yield f'event: test\ndata: {{"value": {i}}}\n\n'
			time.sleep(2)

	run(host=WEBSERVER_IP, port=WEBSERVER_PORT, quiet=True, debug=True)
	
# pyright: reportGeneralTypeIssues=false, reportMissingTypeStubs=false, reportUnusedFunction=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportUnknownMemberType=false