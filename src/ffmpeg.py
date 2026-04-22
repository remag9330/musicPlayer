import json
import logging
import subprocess

from typing import NamedTuple

from settings import FFMPEG_LOCATION, TARGET_INTEGRATED_LOUDNESS

class LoudnessInfo(NamedTuple):
    integrated_loudness: float
    true_peak: float

def get_loudness_info(song_path: str) -> LoudnessInfo:
    cmd = [
        FFMPEG_LOCATION + "ffmpeg.exe",
        "-hide_banner",
        "-loglevel", "info",
        "-i", song_path,
        "-af", "loudnorm=I=" + str(TARGET_INTEGRATED_LOUDNESS) + ":LRA=11:TP=-1.5:print_format=json",
        "-f", "null",
        "-"
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    out = result.stderr

    start = out.find("{")
    end = out.rfind("}")

    if start == -1 or end == -1:
        raise RuntimeError("Failed to parse ffmpeg output")
    
    logging.info(out[start:end + 1])

    data = json.loads(out[start:end + 1])

    return LoudnessInfo(
        float(data["input_i"]),
        float(data["input_tp"])
    )