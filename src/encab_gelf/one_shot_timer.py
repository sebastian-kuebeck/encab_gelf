from typing import Callable
from threading import Thread, Lock, Event


class TimerClosed(Exception):
    pass


class OneShotTimer(object):

    STARTING = 0
    IDLE = 1
    RUNNING = 2
    SKIP = 3
    SKIPPING = 4
    CLOSING = 5
    CLOSED = 6

    def _waitStarted(self):
        self._state_change.wait()
        with self._lock:
            self._state_change.clear()
            if self._state == self.STARTING:
                self._state = self.RUNNING
            else:
                raise TimerClosed()

    def _runTarget(self):
        self._state_change.wait(self._timeout)
        skip = False
        with self._lock:
            self._state_change.clear()
            if self._state == self.RUNNING:
                pass
            elif self._state == self.SKIP:
                skip = True
                self._state = self.SKIPPING
            else:
                raise TimerClosed()
        if not skip:
            self._target()

    def _setIdle(self):
        with self._lock:
            if self._state in (self.RUNNING, self.SKIPPING):
                self._state = self.IDLE
            else:
                raise TimerClosed()

    def _run(self):
        try:
            while True:
                self._waitStarted()
                self._runTarget()
                self._setIdle()
        except TimerClosed:
            self._state = self.CLOSED

    def __init__(self, timeout: float, target: Callable) -> None:
        self._timeout = timeout
        self._target = target
        self._state_change = Event()
        self._state = self.IDLE
        self._lock = Lock()

        def timer():
            self._run()

        self._thread = Thread(target=timer, name="timer", daemon=True)
        self._thread.start()

    def start(self):
        with self._lock:
            if self._state == self.IDLE:
                self._state = self.STARTING
                self._state_change.set()

    def clear(self):
        with self._lock:
            if self._state == self.IDLE:
                self._state = self.SKIP
                self._state_change.set()

    def close(self):
        with self._lock:
            if self._state not in (self.CLOSING, self.CLOSED):
                self._state == self.CLOSING
                self._state_change.set()
