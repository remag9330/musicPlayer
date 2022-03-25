from importlib import import_module
import logging
from typing import Optional

from speaker.abstract_speaker import AbstractSpeaker
from settings import PREFERRED_AUDIO_OUTPUT_ORDER

__speaker: Optional[AbstractSpeaker] = None

def speaker() -> AbstractSpeaker:
    global __speaker
    
    if not __speaker:
        for audio in PREFERRED_AUDIO_OUTPUT_ORDER:
            try:
                logging.info(f"Attempting to load {audio}_speaker...")
                lib = import_module(f"speaker.{audio}_speaker")
                if not isinstance(lib.speaker, AbstractSpeaker):
                    raise Exception("lib.speaker is not an AbstractSpeaker")

                logging.info(f"Using {audio}_speaker module")
                __speaker = lib.speaker
                break
            except:
                logging.exception(f"Could not load {audio}_speaker.py")

        if __speaker is None:
            raise Exception("Could not load any appropriate speakers")

    return __speaker