import logging
import os
import sys

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s:%(levelname)s:%(name)s:%(message)s"
)

if __name__ != "__main__":
    print("This should be run as a stand-alone script, not imported as a module")
    sys.exit()

from database import database
from migrationScripts.convertFilesToSqlite import migrate
from settings import DATA_DIRECTORY, MUSIC_DIR

users_dir = os.path.join(DATA_DIRECTORY, "users")
playlists_dir = os.path.join(DATA_DIRECTORY, "playlists")
migrate(database, users_dir, playlists_dir, MUSIC_DIR)