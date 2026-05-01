import logging
import subprocess

from settings import FFMPEG_LOCATION, TARGET_INTEGRATED_LOUDNESS

def normalise_loudness(input_path: str, output_path: str) -> None:
    cmd = [
        FFMPEG_LOCATION + "ffmpeg.exe",
        "-hide_banner",
        "-loglevel", "info",
        "-i", input_path,
        "-af", "loudnorm=I=" + str(TARGET_INTEGRATED_LOUDNESS) + ":LRA=11:TP=-1.5:print_format=json",
        output_path
    ]

    logging.debug(f"Running ffmpeg with command: {' '.join(cmd)}")

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    logging.debug(f"ffmpeg return code: {result.returncode}")
    logging.debug("ffmpeg output: " + result.stderr)