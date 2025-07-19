import logging
from typing import Dict, List, Literal, Optional, Union

import requests

from utils import get_yt_api_key

JsonValue = Union[Dict[str, "JsonValue"], List["JsonValue"], int, str, bool, None]

YOUTUBE_URL = "https://www.googleapis.com/youtube/v3"

def create_url(resource: str, params: "dict[str, Optional[str]]") -> str:
    api_key = get_yt_api_key()
    if api_key is None:
        raise Exception("No API key supplied, supplying one can improve RPi performance")

    params["key"] = api_key
    query_params = "&".join(f"{k}={v}" for (k, v) in params.items() if v is not None)
    return f"{YOUTUBE_URL}/{resource}?{query_params}"

def get(resource: str, params: "dict[str, Optional[str]]") -> Optional[JsonValue]:
    url = create_url(resource, params)
    r = requests.get(url)

    if not r.ok:
        raise Exception(f"Error retrieving data from YT API - " +
            f"resource: '{resource}', status_code: '{r.status_code}', text: '{r.text}', params: '{params}'")

    return r.json()

def traverse_json(json: JsonValue, path: "list[Union[str, int]]") -> JsonValue:
    originalJson = json

    for p in path:
        if isinstance(p, str) and isinstance(json, dict):
            json = json[p] if p in json else None
        elif isinstance(p, int) and isinstance(json, list):
            json = json[p] if 0 <= p < len(json) else None
        else:
            logging.error(f"Invalid JSON path '{path}' for JSON object '{originalJson}'")
            return None
    
    return json

def get_video_name(vid_id: str) -> Optional[str]:
    try:        
        json = get("videos", {"id": vid_id, "part": "snippet"})
        name = traverse_json(json, ["items", 0, "snippet", "title"])
        assert isinstance(name, str)
        
        return name
    except:
        logging.exception("Error getting video name from YT API")
        
    return None

def get_playlist_name(playlist_id: str) -> Optional[str]:
    try:
        json = get("playlists", {"part": "snippet", "id": playlist_id})
        name = traverse_json(json, ["items", 0, "snippet", "title"])
        assert isinstance(name, str)
        
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

def get_playlist_videos(playlist_id: str) -> Optional["list[Video]"]:
    try:
        results: list[Video] = []
        nextPageToken = None

        while True:
            json = get("playlistItems",
                {"part": "snippet", "maxResults": "50", "playlistId": playlist_id, "pageToken": nextPageToken}
            )

            nextPageToken = traverse_json(json, ["nextPageToken"])
            assert nextPageToken is None or isinstance(nextPageToken, str)

            items = traverse_json(json, ["items"])
            assert isinstance(items, list)
            
            for i in items:
                id = traverse_json(i, ["snippet", "resourceId", "videoId"])
                assert isinstance(id, str)

                name = traverse_json(i, ["snippet", "title"])
                assert isinstance(name, str)

                video = Video(id, name)
                results.append(video)

            if not nextPageToken:
                break
        
        return results
    except:
        logging.exception("Error getting playlist items from YT API")

    return None

class SearchResult:
    def __init__(self, video_id: str, title: str, description: str, thumbnail: str, published_at: str, channel_title: str) -> None:
        self.video_id = video_id
        self.title = title
        self.description = description
        self.thumbnail = thumbnail
        self.published_at = published_at
        self.channel_title = channel_title

    def __str__(self) -> str:
        return f"{self.title} ({self.video_id})"
        
def search_youtube(search_query: str, result_type: Literal["video", "playlist"]) -> Optional["list[SearchResult]"]:
    try:
        results: list[SearchResult] = []

        json = get("search", {"part": "snippet", "q": search_query, "type": result_type})
        items = traverse_json(json, ["items"])
        assert isinstance(items, list)

        for item in items:
            vid_id = traverse_json(item, ["id", "videoId"])
            assert isinstance(vid_id, str)

            title = traverse_json(item, ["snippet", "title"])
            assert isinstance(title, str)

            desc = traverse_json(item, ["snippet", "description"])
            assert isinstance(desc, str)
            
            thumbnails = traverse_json(item, ["snippet", "thumbnails"])
            assert isinstance(thumbnails, dict)
            
            thumbnail = None
            for key in ["high", "medium", "default"]:
                if key in thumbnails:
                    thumbnail = traverse_json(thumbnails, [key, "url"])
            assert isinstance(thumbnail, str)
            
            published_at = traverse_json(item, ["snippet", "publishedAt"])
            assert isinstance(published_at, str)
            
            channel_title = traverse_json(item, ["snippet", "channelTitle"])
            assert isinstance(channel_title, str)

            results.append(SearchResult(vid_id, title, desc, thumbnail, published_at, channel_title))
        
        return results
    except:
        logging.exception("Error searching via YT API")

    return None
