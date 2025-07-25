import logging
from subprocess import CalledProcessError, Popen, check_output, PIPE, STDOUT
import os
from typing import Any, Callable, Optional, Union

from settings import MUSIC_DIR, YOUTUBE_DL_COMMAND, FFMPEG_LOCATION

YOUTUBE_DL = YOUTUBE_DL_COMMAND

OUT_PATH = os.path.join(MUSIC_DIR, "%(id)s.%(ext)s")

def download_audio(url: str, progress_callback: Optional[Callable[[float], None]]=None) -> None:
	logging.info(f"Starting download of '{url}'")

	p = Popen([
		YOUTUBE_DL,
		url,
		"--newline",
		"--no-playlist",
		"--extract-audio",
		"--audio-format", "mp3",
		"--write-thumbnail",
		"--ffmpeg-location", FFMPEG_LOCATION,
		"-o", OUT_PATH
	], universal_newlines=True, stdout=PIPE, stderr=STDOUT, preexec_fn=_preexec_fn())

	if p.stdout is None:
		raise Exception()

	for line in iter(p.stdout.readline, ""):
		if progress_callback is not None and "[download]" in line and "%" in line:
			download_percent = _parse_download_progress(line)
			progress_callback(download_percent)
			
		logging.debug("YTDL output: " + line.strip())

	p.wait(2)

	if p.returncode != 0:
		logging.error(f"return code is non-zero: {p.returncode}")
		raise CalledProcessError(p.returncode, p.args)

	logging.info(f"Download of '{url}' complete")

def _parse_download_progress(line: str) -> float:
	try:
		value = line.replace("[download]", "").split("% of")[0].strip()
		return float(value)
	except ValueError:
		logging.exception(f"Error parsing progress, returning 0 '{line}'")
		return 0.0

def get_title(url: str) -> str:
	logging.info(f"Starting title retrieval for '{url}'")

	out = check_output([
		YOUTUBE_DL,
		url,
		"--no-playlist",
		"--skip-download",
		"--get-title"
	], preexec_fn=_preexec_fn())

	title = out.decode("utf-8").strip()
	
	logging.info(f"Title '{title}' retrieved for '{url}'")
	return title

def get_id(url: str) -> str:
	logging.info(f"Starting id retrieval for '{url}'")

	out = check_output([
		YOUTUBE_DL,
		url,
		"--no-playlist",
		"--skip-download",
		"--get-id"
	], preexec_fn=_preexec_fn())

	id = out.decode("utf-8").strip()

	logging.info(f"Id '{id}' retrieved for '{url}'")
	return id

def get_filename(url: str) -> str:
	logging.info(f"Starting filename retrieval for '{url}'")
	
	out = check_output([
		YOUTUBE_DL,
		url,
		"--no-playlist",
		"--skip-download",
		"--get-filename",
		"-o", OUT_PATH
	], preexec_fn=_preexec_fn())
	
	p = out.decode("utf-8").strip()
	base = os.path.splitext(p)[0]
	filename = base + ".mp3"
	
	logging.info(f"Filename '{filename}' retrieved for '{url}'")
	return filename

def _preexec_fn() -> Union[None, Callable[[], Any]]:
	if hasattr(os, "nice"):
		return lambda: os.nice(10)
	else:
		return None