import os

DATA_DIRECTORY = os.path.join("C:", "music_player", "data")
MUSIC_DIR = os.path.join(DATA_DIRECTORY, "music")
DATABASE_FILE = os.path.join(DATA_DIRECTORY, "database.db")

WEBSERVER_IP = "0.0.0.0"
WEBSERVER_PORT = 80

YOUTUBE_DL_COMMAND = "C:/music_player/youtube-dl.exe"
FFMPEG_LOCATION = "C:/music_player/ffmpeg/bin/"

PREFERRED_AUDIO_OUTPUT_ORDER = ["vlc", "pygame"]

MAX_PARALLEL_DOWNLOADS = 1

SONGS_PER_PAGE = 10