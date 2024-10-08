from typing import Tuple


class AbstractSpeaker:
    def load(self, filename: str) -> None:
        raise NotImplementedError()

    def play(self) -> None:
        raise NotImplementedError()

    def pause(self) -> None:
        raise NotImplementedError()

    def unpause(self) -> None:
        raise NotImplementedError()

    def get_busy(self) -> bool:
        raise NotImplementedError()

    def get_pos(self) -> int:
        raise NotImplementedError()

    def set_pos(self, ms: int):
        raise NotImplementedError()

    def get_volume(self) -> float:
        raise NotImplementedError()

    def set_volume(self, volume: float) -> None:
        raise NotImplementedError()

    def volume_min_max_step(self) -> Tuple[float, float, float]:
        raise NotImplementedError()