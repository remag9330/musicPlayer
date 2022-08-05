import time
import logging
        
from typing import Optional, Tuple
from .abstract_speaker import AbstractSpeaker

from mutex import Mutex

from vlc import MediaPlayer

class VlcSpeaker(AbstractSpeaker):
    def __init__(self) -> None:
        self.__track: Mutex[Optional[MediaPlayer]] = Mutex(None)
        self.__volume: float = 1.0
        self.__current_playing_filename: str = ""

        self.__pause_state: Optional[Tuple[int, str]] = None

    def load(self, filename: str) -> None:
        with self.__track.acquire() as track:
            if track.value:
                track.value.release()

            track.replace_value(MediaPlayer(filename))
            self.__current_playing_filename = filename

    def play(self) -> None:
        self.__pause_state = None

        with self.__track.acquire() as track:
            if track.value:
                track.value.play()
                # MediaPlayer.is_playing() will return False _immediately_ after .play(), so we need
                # to wait a split second so we don't end up changing songs after returning from here.
                time.sleep(0.5)

            self._update_track_volume_locked(track.value)

    def pause(self) -> None:
        with self.__track.acquire() as track:
            if track.value:
                self.__pause_state = (
                    self.get_pos_locked(track.value),
                    self.__current_playing_filename
                )
                
                track.value.release()
                track.replace_value(None)

    def unpause(self) -> None:
        if self.__pause_state:
            # We'll set __pause_state back to None during self.play()
            [start_time, filename] = self.__pause_state
            self.load(filename)
            self.play()
            self.set_pos(start_time)
        else:
            logging.warn("Attempting to unpause but there's no pause state to resume from")
            self.play()

    def get_busy(self) -> bool:
        with self.__track.acquire() as track:
            return bool(track.value) and track.value.is_playing() == 1

    def get_pos(self) -> int:
        if self.__pause_state:
            # Short circuit here to avoid grabbing lock if possible, but should still check this in lock too
            return self.__pause_state[0]

        with self.__track.acquire() as track:
            return self.get_pos_locked(track.value)

    def get_pos_locked(self, track: Optional[MediaPlayer]) -> int:
        if self.__pause_state:
            return self.__pause_state[0]
        elif track:
            return track.get_time()
        else:
            return 0

    def set_pos(self, pos: int) -> None:
        with self.__track.acquire() as track:
            if track.value:
                track.value.set_time(pos)

    def get_volume(self) -> float:
        return self.__volume   

    def set_volume(self, volume: float) -> None:
        self.__volume = volume
        self._update_track_volume()

    def _update_track_volume(self) -> None:
        with self.__track.acquire() as track:
            self._update_track_volume_locked(track.value)

    def _update_track_volume_locked(self, track: Optional[MediaPlayer]) -> None:
        if track and track.is_playing():
            track.audio_set_volume(int(self.__volume * 100))

                
    def volume_min_max_step(self) -> Tuple[float, float, float]:
        return (0.0, 2.0, 0.1)

speaker = VlcSpeaker()

# pyright: reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false