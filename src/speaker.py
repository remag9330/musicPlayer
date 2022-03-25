import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide" # Stop pygame printing things on import

from mutex import Mutex

import pygame

pygame.mixer.init()
music = Mutex(pygame.mixer.music)

class Speaker:
    def load(self, filename: str):
        with music.acquire() as m:
            m.value.load(filename)

    def play(self):
        with music.acquire() as m:
            m.value.play()

    def pause(self):
        with music.acquire() as m:
            m.value.pause()

    def unpause(self):
        with music.acquire() as m:
            m.value.unpause()

    def get_busy(self) -> bool:
        with music.acquire() as m:
            return m.value.get_busy()

    def get_pos(self) -> int:
        with music.acquire() as m:
            return m.value.get_pos()

    def get_volume(self) -> float:
        with music.acquire() as m:
            return m.value.get_volume()

    def set_volume(self, volume: float):
        with music.acquire() as m:
            m.value.set_volume(min(1.0, max(0.0, volume)))

speaker = Speaker()