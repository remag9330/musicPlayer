import queue
import time

from mutex import Mutex
from song_queue import SongQueue
from commands import Command, PlayCommand, PauseCommand, QueueCommand, SkipCommand

from bottle import get, post, run, template, static_file, request, response, redirect

from settings import WEBSERVER_IP, WEBSERVER_PORT

def start_webserver(event_queue: queue.Queue[Command], song_queue: Mutex[SongQueue]):
	@get("/")
	def index():
		with song_queue.acquire() as sq:
			return template("index", song_queue=sq.value)

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

	run(host=WEBSERVER_IP, port=WEBSERVER_PORT, quiet=True)
	
# pyright: reportGeneralTypeIssues=false, reportMissingTypeStubs=false, reportUnusedFunction=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportUnknownMemberType=false