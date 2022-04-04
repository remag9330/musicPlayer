import time
        
from typing import Optional, Tuple
from .abstract_speaker import AbstractSpeaker

from mutex import Mutex

from vlc import MediaPlayer

class VlcSpeaker(AbstractSpeaker):
    def __init__(self) -> None:
        self.__track: Mutex[Optional[MediaPlayer]] = Mutex(None)
        self.__volume: float = 1.0

    def load(self, filename: str) -> None:
        with self.__track.acquire() as track:
            if track.value:
                track.value.release()

            track.replace_value(MediaPlayer(filename))

    def play(self) -> None:
        with self.__track.acquire() as track:
            if track.value:
                track.value.play()
                # MediaPlayer.is_playing() will return False _immediately_ after .play(), so we need
                # to wait a split second so we don't end up changing songs after returning from here.
                time.sleep(0.5)

        self._update_track_volume()

    def pause(self) -> None:
        with self.__track.acquire() as track:
            if track.value:
                track.value.pause()

    def unpause(self) -> None:
        self.play()

    def get_busy(self) -> bool:
        with self.__track.acquire() as track:
            if track.value:
                return track.value.is_playing() == 1
            else:
                return False

    def get_pos(self) -> int:
        with self.__track.acquire() as track:
            if track.value:
                return track.value.get_time()
            else:
                return 0

    def get_volume(self) -> float:
        return self.__volume   

    def set_volume(self, volume: float) -> None:
        self.__volume = volume
        self._update_track_volume()

    def _update_track_volume(self) -> None:
        with self.__track.acquire() as track:
            if track.value and track.value.is_playing():
                track.value.audio_set_volume(int(self.__volume * 100))
                
    def volume_min_max_step(self) -> Tuple[float, float, float]:
        return (0.0, 2.0, 0.1)

speaker = VlcSpeaker()

# pyright: reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false