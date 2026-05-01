import logging
import os
import sys

if __name__ != "__main__":
    print("This should be run as a stand-alone script, not imported as a module")
    sys.exit()

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s:%(levelname)s:%(name)s:%(message)s"
)

requested_migrator = sys.argv[1] if len(sys.argv) > 1 else None
if requested_migrator is None:
    print("No migrator specified - exiting")
    print("Usage: python migrator.py <migrator_name>")
    print("Available migrators:")
    print("  convertFilesToSqlite - Convert from old file-based storage to new SQLite database")
    print("  normaliseAudio - Run loudness normalisation on all existing audio files (useful if TARGET_INTEGRATED_LOUDNESS is changed)")

    sys.exit()

if requested_migrator == "convertFilesToSqlite":
    from database import database
    from migrationScripts.convertFilesToSqlite import migrate
    from settings import DATA_DIRECTORY, MUSIC_DIR

    users_dir = os.path.join(DATA_DIRECTORY, "users")
    playlists_dir = os.path.join(DATA_DIRECTORY, "playlists")
    migrate(database, users_dir, playlists_dir, MUSIC_DIR)

elif requested_migrator == "normaliseAudio":
    from database import database
    from ffmpeg import normalise_loudness

    all_songs = database.get_songs()
    
    for i, song in enumerate(all_songs):
        logging.info(f"Normalising {i + 1}/{len(all_songs)} {song.youtube_id} ({song.name})...")
        real_path = song.path()
        orig_path = real_path + ".original"

        if not (os.path.exists(real_path) or os.path.exists(orig_path)):
            logging.warning(f"Neither {real_path} nor {orig_path} exist - skipping this file")
            continue

        if not os.path.exists(orig_path):
            logging.info(f"File {orig_path} does not exist, moving existing to {real_path}...")
            os.rename(real_path, orig_path)

        try:
            logging.info(f"Removing existing file at {real_path} (if it exists)...")
            os.remove(real_path)
            logging.info(f"Removed existing file at {real_path}")
        except FileNotFoundError:
            logging.info(f"No existing file at {real_path} to remove, continuing...")

        logging.info(f"Normalising loudness for {orig_path} and saving to {real_path}...")
        normalise_loudness(orig_path, real_path)
        logging.info(f"Finished normalising loudness for {orig_path}")

    logging.info("All done!")

else:
    logging.error(f"Unknown migrator '{requested_migrator}' - exiting")
    sys.exit()