import logging
import os
from typing import Optional
from urllib.parse import parse_qs, urlparse

import requests

import youtube_dl as ytdl
from utils import get_yt_api_key
import settings

def get_filename(url: str) -> str:
	if "youtube.com" in url.lower():
		name = try_get_youtube_filename_quick(url)
		if name is not None:
			return name

	if "youtu.be" in url.lower():
		vid_id = url.strip("/").split("/")[-1]
		name = try_get_filename_from_id(vid_id)
		if name is not None:
			return name

	logging.info("Attempting to get filename from YTDL")
	return ytdl.get_filename(url)


def try_get_youtube_filename_quick(url: str) -> Optional[str]:
	try:
		vid_id = get_youtube_video_id_from_url(url)
	except:
		logging.exception(f"Error while getting video ID from supposedly good youtube URL '{url}'")
		return None

	return try_get_filename_from_id(vid_id)

def try_get_filename_from_id(vid_id: str) -> Optional[str]:
	logging.info("Attempting to get filename from cached songs")
	cached = get_youtube_filename_from_cache(vid_id)
	if cached is not None:
		return cached

	logging.info("Attempting to get filename from YT API")
	cached = get_youtube_filename_from_api(vid_id)
	if cached is not None:
		return cached

def get_youtube_video_id_from_url(url: str) -> str:
	logging.info("Attempting to extract existing video's path")
	parsed = urlparse(url)
	vid_id = parse_qs(parsed.query)["v"][0]
	logging.debug(f"video id: {vid_id}")
	return vid_id

def get_youtube_filename_from_cache(vid_id: str) -> Optional[str]:
	try:
		curr_path = os.path.join(settings.MUSIC_DIR, vid_id)
		if not os.path.isdir(curr_path):
			logging.info(f"No directory for id {vid_id}, skipping filename from cache")
			return None

		files = [f for f in os.listdir(curr_path) if f.endswith(".mp3")]
		logging.debug(f"Files found: {len(files)}")
		if len(files) == 1:
			filename = files[0]
			result = os.path.join(curr_path, filename)
			logging.info(f"Found cached path: {result}")
			return result
	except:
		logging.exception("Could not get filename from cached songs")
	
	return None

def get_youtube_filename_from_api(vid_id: str) -> Optional[str]:
	try:
		api_key = get_yt_api_key()
		if api_key is None:
			logging.info("No API key supplied, supplying one can improve RPi performance")
			return None

		r = requests.get(
			f"https://www.googleapis.com/youtube/v3/videos?id={vid_id}&key={api_key}&part=snippet"
		)

		if not r.ok:
			logging.error(f"Error retrieving data from YT API: status_code: {r.status_code}, text: {r.text}")
			return None
		
		name = r.json()["items"][0]["snippet"]["title"]
		filename = os.path.join(settings.MUSIC_DIR, vid_id, name + ".mp3")
		logging.info(f"Found API path {filename}")
		return filename
	except:
		logging.exception("Error getting filename from YT API")
		
	return None