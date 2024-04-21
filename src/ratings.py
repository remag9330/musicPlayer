import json
from pathlib import Path
from typing import Optional

from song import Song

def rate_song(song: Song, username: str, rating: int) -> None:
    ratings = get_song_ratings(song)
    ratings[username] = rating
    save_song_ratings(song, ratings)

def get_song_rating(song: Song, username: str) -> Optional[int]:
    ratings = get_song_ratings(song)
    return ratings.get(username, None)

def ratings_file_path(song: Song) -> str:
    path = Path(song.path)
    return path.parent / "user_ratings.json"

def get_song_ratings(song: Song) -> "dict[str, int]":
    ratings_file = ratings_file_path(song)

    try:
        with open(ratings_file) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    
def save_song_ratings(song: Song, ratings: "dict[str, int]") -> None:
    ratings_file = ratings_file_path(song)
    with open(ratings_file, "w") as f:
        json.dump(ratings, f)