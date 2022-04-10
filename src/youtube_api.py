import logging
from typing import Optional

import requests

from utils import get_yt_api_key

def get_video_name(vid_id: str) -> Optional[str]:
    try:
        api_key = get_yt_api_key()
        if api_key is None:
            logging.info("No API key supplied, supplying one can improve RPi performance")
            return None

        r = requests.get(
            f"https://www.googleapis.com/youtube/v3/videos?id={vid_id}&part=snippet&key={api_key}"
        )

        if not r.ok:
            logging.error(f"Error retrieving data from YT API: status_code: {r.status_code}, text: {r.text}")
            return None
        
        name = r.json()["items"][0]["snippet"]["title"]
        return name
    except:
        logging.exception("Error getting video name from YT API")
        
    return None

def get_playlist_name(playlist_id: str) -> Optional[str]:
    try:
        api_key = get_yt_api_key()
        if api_key is None:
            logging.info("No API key supplied, supplying one can improve RPi performance")
            return None

        r = requests.get(
            f"https://www.googleapis.com/youtube/v3/playlists?part=snippet&id={playlist_id}&key={api_key}"
        )

        if not r.ok:
            logging.error(f"Error retrieving data from YT API: status_code: {r.status_code}, text: {r.text}")
            return None
        
        name = r.json()["items"][0]["snippet"]["title"]
        return name
    except:
        logging.exception("Error getting playlist name from YT API")

    return None

class Video:
    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name

    def __str__(self) -> str:
        return f"{self.name} ({self.id})"

def get_playlist_videos(playlist_id: str) -> Optional[list[Video]]:
    try:
        api_key = get_yt_api_key()
        if api_key is None:
            logging.info("No API key supplied, supplying one can improve RPi performance")
            return None

        results: list[Video] = []
        nextPageToken = None

        while True:
            url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&playlistId={playlist_id}&key={api_key}"
            if nextPageToken:
                url += f"&pageToken={nextPageToken}"

            r = requests.get(url)

            if not r.ok:
                logging.error(f"Error retrieving data from YT API: status_code: {r.status_code}, text: {r.text}")
                return None

            json = r.json()
            nextPageToken = json["nextPageToken"] if "nextPageToken" in json else None
            results += [Video(i["snippet"]["resourceId"]["videoId"], i["snippet"]["title"]) for i in json["items"]]

            if not nextPageToken:
                break
        
        return results
    except:
        logging.exception("Error getting playlist items from YT API")

    return None