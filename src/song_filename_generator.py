import logging
from typing import Optional
from urllib.parse import parse_qs, urlparse

import youtube_dl as yt_dl
import youtube_api as yt_api

def get_name(url: str) -> str:
	logging.info("Attempting to get the video name via the YT API")
	vid_id = get_video_id(url)
	if vid_id is not None:
		name = try_get_name_from_id(vid_id)
		if name is not None:
			return name

	logging.info("Attempting to get filename from YTDL")
	return yt_dl.get_filename(url)

def get_video_id(url: str) -> Optional[str]:
	if "youtube.com" in url.lower():
		return get_youtube_video_id_from_url(url)
	if "youtu.be" in url.lower():
		return url.strip("/").split("/")[-1]
	
	return None

def try_get_youtube_name_quick(url: str) -> Optional[str]:
	try:
		vid_id = get_youtube_video_id_from_url(url)
	except:
		logging.exception(f"Error while getting video ID from supposedly good youtube URL '{url}'")
		return None

	return try_get_name_from_id(vid_id)

def try_get_name_from_id(vid_id: str) -> Optional[str]:
	logging.info(f"Attempting to get name from YT API for {vid_id}")
	result = yt_api.get_video_name(vid_id)
	logging.info(f"Name for {vid_id} is {result}")
	return result

def get_youtube_video_id_from_url(url: str) -> str:
	logging.info("Attempting to extract existing video's path")
	parsed = urlparse(url)
	vid_id = parse_qs(parsed.query)["v"][0]
	logging.debug(f"video id: {vid_id}")
	return vid_id

def get_youtube_playlist_id_from_url(url: str) -> Optional[str]:
	logging.info(f"Attempting to extract playlist id from {url}")
	try:
		parsed = urlparse(url)
		playlist_id = parse_qs(parsed.query)["list"][0]
		logging.debug(f"video id: {playlist_id}")
		return playlist_id
	except:
		logging.exception("Could not get playlist ID")
		return None
