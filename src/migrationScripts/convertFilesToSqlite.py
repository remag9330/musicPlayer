import json
import os
import shutil
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from database import Database

PASSWORD_SEPARATOR = ':'  # separator for hash, salt, and iterations

def migrate(db: "Database", USERS_DIR: str, PLAYLISTS_DIR: str, MUSIC_DIR: str):
    logging.info("Starting migration, let's go!")

    username_to_id = {}
    song_ext_id_to_db_id = {}

    if os.path.exists(USERS_DIR):
        logging.info("Importing users...")
        for user_file in os.listdir(USERS_DIR):
            username = os.path.splitext(user_file)[0]

            with open(os.path.join(USERS_DIR, user_file), 'r') as f:
                user_data = json.load(f)
                pwd = user_data['password']
                combined_hash = f"{pwd['hash']}{PASSWORD_SEPARATOR}{pwd['salt']}{PASSWORD_SEPARATOR}{pwd['iterations']}"
                user_id = db.add_user(username, combined_hash)
                username_to_id[username] = user_id
            
            logging.info(f"Imported user {username} with id {user_id}")

        logging.info("Finished importing users")
    else:
        logging.info("No users dir found, skipping user import")

    if os.path.exists(MUSIC_DIR):
        logging.info("Importing songs...")
        for ext_song_id in os.listdir(MUSIC_DIR):
            song_dir = os.path.join(MUSIC_DIR, ext_song_id)
            if not os.path.isdir(song_dir):
                logging.warning(f"Skipping {ext_song_id} - not a directory")
                continue

            song_name = None
            user_ratings = None
            start_time_ms = 0

            for file in os.listdir(song_dir):
                full_path = os.path.join(song_dir, file)
                if file.endswith('.mp3'):
                    song_name = file[:-4]
                    new_song_path = os.path.join(MUSIC_DIR, f"{ext_song_id}.mp3")
                    shutil.move(full_path, new_song_path)
                elif file.endswith('.jpg') or file.endswith('.webp'):
                    new_thumb_path = os.path.join(MUSIC_DIR, f"{ext_song_id}{os.path.splitext(file)[1]}")
                    shutil.move(full_path, new_thumb_path)
                elif file == 'settings.json':
                    with open(full_path) as f:
                        settings = json.load(f)
                        start_time_ms = settings.get('start_time_ms', 0)
                elif file == 'user_ratings.json':
                    with open(full_path) as f:
                        user_ratings = json.load(f)

            if song_name:
                song_db_id = db.add_song(song_name, ext_song_id, start_time_ms)
                song_ext_id_to_db_id[ext_song_id] = song_db_id

                logging.info(f"Imported song {song_name} ({ext_song_id}) with id {song_db_id}")

                # Ratings
                if user_ratings is not None:
                    count = 0
                    for username, rating in user_ratings.items():
                        count += 1
                        user_id = username_to_id.get(username)
                        if user_id is not None:
                            db.add_rating(user_id, song_db_id, rating)

                    logging.info(f"Adding {count} found ratings to songs")
                else:
                    logging.info("No ratings found for this song")
            else:
                logging.warning(f"Skipping {ext_song_id} - couldn't find song name")

            shutil.rmtree(song_dir)

        logging.info("Finished importing songs")
    else:
        logging.info("No music dir found, skipping song import")

    if os.path.exists(PLAYLISTS_DIR):
        logging.info("Importing playlists...")
        for playlist_file in os.listdir(PLAYLISTS_DIR):
            playlist_name = os.path.splitext(playlist_file)[0]
            playlist_path = os.path.join(PLAYLISTS_DIR, playlist_file)
            with open(playlist_path, 'r') as f:
                song_ids = [os.path.split(line.strip())[0] for line in f.readlines() if line.strip()]

            # Create playlist
            playlist_id = db.add_playlist(playlist_name)

            count = 0
            for ext_song_id in song_ids:
                song_id = song_ext_id_to_db_id.get(ext_song_id)
                if song_id:
                    count += 1
                    db.add_song_to_playlist(song_id, playlist_id)
                else:
                    logging.warning(f"Could not find {ext_song_id} to add to playlist")

            logging.info(f"Imported playlist {playlist_name} with id {playlist_id} and it's {count if count == len(song_ids) else f'{count}/{len(song_ids)}'} songs")
    else:
        logging.info("No playlist dir found, skipping playlist import")

    logging.info("Alrighty, I think we're done! Take a look and make sure nothing's broken/lost/etc")
