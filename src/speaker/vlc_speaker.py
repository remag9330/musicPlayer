import time
import logging
        
from typing import Optional, Tuple
from .abstract_speaker import AbstractSpeaker

from settings import TARGET_INTEGRATED_LOUDNESS
from mutex import Mutex

from vlc import MediaPlayer

class VlcSpeaker(AbstractSpeaker):
    def __init__(self) -> None:
        self.__track: Mutex[Optional[MediaPlayer]] = Mutex(None)
        self.__volume: float = 1.0
        self.__track_integrated_loudness: float = TARGET_INTEGRATED_LOUDNESS
        self.__current_playing_filename: str = ""

        self.__pause_state: Optional[Tuple[int, str]] = None

    def load(self, filename: str, integrated_loudness: float) -> None:
        with self.__track.acquire() as track:
            if track.value:
                track.value.release()

            track.replace_value(MediaPlayer(filename))
            self.__current_playing_filename = filename
            self.__track_integrated_loudness = integrated_loudness

    def play(self) -> None:
        self.__pause_state = None

        with self.__track.acquire() as track:
            if track.value:
                track.value.play()
                # MediaPlayer.is_playing() will return False _immediately_ after .play(), so we need
                # to wait a split second so we don't end up changing songs after returning from here.
                attempts = 0
                while attempts < 5 and not track.value.is_playing():
                    attempts += 1
                    time.sleep(0.1)

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
            self.load(filename, self.__track_integrated_loudness)
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

    def set_pos(self, ms: int) -> None:
        with self.__track.acquire() as track:
            if track.value:
                track.value.set_time(ms)

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
            base_volume = int(self.__volume * 100)
            # true_volume = base_volume
            true_volume = normalised_volume(
                self.__track_integrated_loudness,
                TARGET_INTEGRATED_LOUDNESS,
                base_volume)
            logging.info(f"Setting song volume to {true_volume}")
            track.audio_set_volume(true_volume)

                
    def volume_min_max_step(self) -> Tuple[float, float, float]:
        return (0.0, 2.0, 0.1)

def normalised_volume(measured_lufs, target_lufs, base_volume):
    """
    measured_lufs: float, integrated loudness of file
    target_lufs: float, desired LUFS (e.g., -14)
    base_volume: int, user/system setting (0-200 in VLC scale)
    """
    diff_db = target_lufs - measured_lufs
    factor = 10 ** (diff_db / 20)    # dB -> linear
    normalised = base_volume * factor
    # clamp to VLC's 0-200
    return max(0, min(int(round(normalised)), 200))

speaker = VlcSpeaker()

# pyright: reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false