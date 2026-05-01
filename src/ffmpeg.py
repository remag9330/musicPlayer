import logging
import subprocess
import platform

from settings import FFMPEG_LOCATION, TARGET_INTEGRATED_LOUDNESS

EXE_NAME = "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"

def normalise_loudness(input_path: str, output_path: str) -> None:
    cmd = [
        FFMPEG_LOCATION + EXE_NAME,
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