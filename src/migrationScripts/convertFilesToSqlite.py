import json
import os
import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database import Database

PASSWORD_SEPARATOR = ':'  # separator for hash, salt, and iterations

def migrate(db: "Database", USERS_DIR: str, PLAYLISTS_DIR: str, MUSIC_DIR: str):
    username_to_id = {}
    song_ext_id_to_db_id = {}

    # Import Users
    if os.path.exists(USERS_DIR):
        for user_file in os.listdir(USERS_DIR):
            username = os.path.splitext(user_file)[0]
            with open(os.path.join(USERS_DIR, user_file), 'r') as f:
                user_data = json.load(f)
                pwd = user_data['password']
                combined_hash = f"{pwd['hash']}{PASSWORD_SEPARATOR}{pwd['salt']}{PASSWORD_SEPARATOR}{pwd['iterations']}"
                user_id = db.add_user(username, combined_hash)
                username_to_id[username] = user_id
    else:
        print("No users dir found, skipping user import")

    # Import Songs
    if os.path.exists(MUSIC_DIR):
        for ext_song_id in os.listdir(MUSIC_DIR):
            song_dir = os.path.join(MUSIC_DIR, ext_song_id)
            if not os.path.isdir(song_dir):
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
                db.add_song(song_name, ext_song_id, start_time_ms)
                song_record = db.get_song(song_name)
                if song_record:
                    song_db_id = song_record[0]
                    song_ext_id_to_db_id[ext_song_id] = song_db_id

                    # Ratings
                    if user_ratings is not None:
                        for username, rating in user_ratings.items():
                            user_id = username_to_id.get(username)
                            if user_id is not None:
                                db.add_rating(user_id, song_db_id, rating)

            shutil.rmtree(song_dir)
    else:
        print("No music dir found, skipping song import")

    if os.path.exists(PLAYLISTS_DIR):
        # Import Playlists
        for playlist_file in os.listdir(PLAYLISTS_DIR):
            playlist_name = os.path.splitext(playlist_file)[0]
            playlist_path = os.path.join(PLAYLISTS_DIR, playlist_file)
            with open(playlist_path, 'r') as f:
                song_ids = [os.path.split(line.strip())[0] for line in f.readlines() if line.strip()]

            # Create playlist
            playlist_id = db.add_playlist(playlist_name)

            for ext_song_id in song_ids:
                song_id = song_ext_id_to_db_id.get(ext_song_id)
                if song_id:
                    db.add_song_to_playlist(song_id, playlist_id)
    else:
        print("No playlist dir found, skipping playlist import")
