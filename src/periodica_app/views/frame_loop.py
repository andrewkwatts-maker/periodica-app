"""Start / stop / pause a per-frame callback.

Pure Python: the scheduler is injected (Kivy's ``Clock`` by default, imported
lazily), so the lifecycle logic is unit-tested headless with a fake clock.

States::

    stopped --start()--> running --pause()--> paused --resume()--> running
       ^                    |                   |
       +------stop()--------+-------stop()------+

``start`` and ``resume`` are idempotent, ``pause`` only acts on a running
loop, and ``resume`` only restarts a loop that ``pause`` stopped -- so a
screen that was left (``stop``) is not revived by an app-level resume.
"""
from __future__ import annotations

from typing import Callable, Protocol


class _Event(Protocol):
    def cancel(self) -> None: ...


class Scheduler(Protocol):
    def schedule_interval(self, callback: Callable[[float], None], timeout: float) -> _Event: ...


class FrameLoop:
    def __init__(self, on_frame: Callable[[float], None], fps: float = 60.0,
                 scheduler: Scheduler | None = None):
        if fps <= 0:
            raise ValueError("fps must be positive")
        self._on_frame = on_frame
        self.interval = 1.0 / float(fps)
        self._scheduler = scheduler
        self._event: _Event | None = None
        self._paused = False
        self.frames = 0

    @property
    def running(self) -> bool:
        return self._event is not None

    @property
    def paused(self) -> bool:
        return self._paused

    def _clock(self) -> Scheduler:
        if self._scheduler is None:
            from kivy.clock import Clock

            self._scheduler = Clock
        return self._scheduler

    def start(self) -> None:
        self._paused = False
        if self._event is None:
            self._event = self._clock().schedule_interval(self._tick, self.interval)

    def stop(self) -> None:
        self._paused = False
        self._cancel()

    def pause(self) -> None:
        if self._event is not None:
            self._cancel()
            self._paused = True

    def resume(self) -> None:
        if self._paused:
            self.start()

    def _cancel(self) -> None:
        if self._event is not None:
            self._event.cancel()
            self._event = None

    def _tick(self, dt: float) -> None:
        self.frames += 1
        self._on_frame(dt)
