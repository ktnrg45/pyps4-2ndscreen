# -*- coding: utf-8 -*-
"""Client for PS4."""
import logging
import threading
import time
import queue

_LOGGER = logging.getLogger(__name__)

DEFAULT_INTERVAL = 3
DEFAULT_INTERVAL_KEEP_ALIVE = 30


def _should_poll(last, interval):
    """Poll timer."""
    time_since = time.time() - last
    if time_since > interval:
        return True
    return False


class PS4Client():
    """Client for handling background IO."""

    def __init__(self):
        """Init."""
        self.listeners = {}
        self.started = []

    def start_all(self):
        """Start all listeners."""
        if self.listeners:
            for listener in self.listeners:
                listener.start()

    def stop_all(self):
        """Stop all Listeners."""
        if self.listeners:
            for listener in self.listeners:
                listener.stop.set()

    def remove_all(self):
        """Remove all listeners."""
        self.stop_all()
        self.listeners = {}

    def start_listener(self, ps4):
        """Start listener thread."""
        _LOGGER.debug("Starting listener @ %s", ps4._host)  # noqa: pylint: disable=protected-access
        self.started.append(self.listeners[ps4])
        self.listeners[ps4].start()

    def stop_listener(self, ps4):
        """Stop a Listener."""
        if ps4 in self.listeners:
            self.listeners[ps4].stop.set()
            self.started.remove(self.listeners[ps4])

    def remove_listener(self, ps4):
        """Stop and Remove a Listener."""
        self.stop_listener(ps4)
        self.listeners.pop(ps4)

    def schedule_task(self, ps4, task, *args):
        """Schedule socket task in thread."""
        active = self.get_active()
        if active is not None:
            if active.ps4 != ps4:
                active.ps4.close()
        if not ps4.msg_sending:
            listener = self.listeners[ps4]
            if args:
                task = (task, *args)
            listener.queue.put(task)
        else:
            _LOGGER.info("PS4 already has a task in progress")

    def add_ps4(self, ps4):
        """Add PS4 to listeners."""
        if ps4 not in self.listeners:
            self.listeners[ps4] = Listener(client=self, ps4=ps4)
        else:
            _LOGGER.warning("Listener already exists")

    def add_callback(self, ps4, callback):
        """Add Callback for listener."""
        assert callable(callback) is True, "Callback must be callable"
        if ps4 in self.listeners:
            self.listeners[ps4].callbacks.append(callback)

    def get_active(self):
        """Return logged in PS4."""
        for listener in self.listeners.values():
            if listener.ps4.connected:
                return listener
        return None


class Listener(threading.Thread):
    """Listener per PS4 to handle sockets."""

    def __init__(self, client, ps4):
        """Init."""
        super().__init__()
        self.client = client
        self.ps4 = ps4
        self.interval = DEFAULT_INTERVAL
        self.interval_keep_alive = DEFAULT_INTERVAL_KEEP_ALIVE
        self.last_poll = 0
        self.last_keep_alive = 0
        self.callbacks = []
        self.running = False
        self._status = None
        self.queue = queue.Queue()

        self.stop = threading.Event()
        self.block = threading.Event()

    def run(self):
        """Run Listener."""
        while not self.stop.is_set():
            self.running = True
            while not self.queue.empty():
                if not self.block.is_set():
                    # Block queue.
                    self.block.set()
                    item = self.queue.get()

                    # If args are passed in.
                    if isinstance(item, tuple):
                        args = item[1:]
                        item = item[0]
                        result = item(*args)
                    else:
                        result = item()

                    if item == self.ps4.get_status:
                        self._check_status(result)
                        self.last_poll = time.time()
                    elif item == self.ps4.send_status:
                        self.last_keep_alive = time.time()

                    # Reset intervals for status.
                    else:
                        self.last_poll = time.time()
                        self.last_keep_alive = time.time()

                    # Unblock queue.
                    self.block.clear()

            # Call when queue is empty.
            # Queue status update.
            if _should_poll(self.last_poll, self.interval):
                self.queue.put(self.ps4.get_status, False)

            # Queue Keep Alive.
            if self.ps4.connected:
                if _should_poll(self.last_keep_alive,
                                self.interval_keep_alive):
                    self.queue.put(self.ps4.send_status, False)

        # If stopping.
        self.queue.join()
        self.running = False
        _LOGGER.debug("Stopping Listener @ %s", self.ps4._host)   # noqa: pylint: disable=protected-access

    def _notify_callbacks(self):
        """Call all callbacks."""
        if self.callbacks:
            for callback in self.callbacks:
                callback()

    def _check_status(self, status):
        if status != self._status:
            _LOGGER.debug(
                "PS4 @ %s: Status changed to %s", self.ps4._host, status)  # noqa: pylint: disable=protected-access
            self._status = status
            self._notify_callbacks()
