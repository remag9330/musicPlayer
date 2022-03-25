from types import TracebackType
from typing import Optional, Type, TypeVar, Generic
from threading import Lock
from typing_extensions import Self

T = TypeVar("T")
U = TypeVar("U")

class Mutex(Generic[T]):
    class MutexGuard(Generic[U]):
        def __init__(self, mutex: "Mutex[U]") -> None:
            self.mutex = mutex

        @property
        def value(self) -> U:
            return self.mutex._value
            
        def replace_value(self, value: U):
            self.mutex._value = value

        def __enter__(self) -> Self:
            self.mutex._lock.acquire()
            return self

        def __exit__(self,
            exc_type: Optional[Type[BaseException]],
            exc: Optional[BaseException],
            traceback: Optional[TracebackType]
        ) -> None:
            self.mutex._lock.release()

    def __init__(self, initial_value: T) -> None:
        self._lock = Lock()
        self._value = initial_value

    def acquire(self) -> "MutexGuard[T]":
        return Mutex.MutexGuard(self)