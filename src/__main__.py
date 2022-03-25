import logging
import os
import sys
import threading
import queue

from mutex import Mutex

from song_queue import SongQueue
from commands import Command
from music_player import start_music_player
from webserver import start_webserver


def main():
	logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
	logging.info("Music player is starting up")

	os.chdir(os.path.dirname(os.path.abspath(__file__)))

	event_queue: queue.Queue[Command] = queue.Queue(-1)
	song_queue = Mutex(SongQueue())

	ws_thread = threading.Thread(
		target=start_webserver,
		args=(event_queue, song_queue),
		daemon=True
	)

	logging.info("Starting webserver daemon thread")
	ws_thread.start()

	logging.info("Starting music player")
	start_music_player(event_queue, song_queue)

if __name__ == "__main__":
	main()