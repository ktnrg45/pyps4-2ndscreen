# -*- coding: utf-8 -*-
"""Client for PS4."""
import logging
import threading
import time

_LOGGER = logging.getLogger(__name__)


class PS4Client():
    """Client for handling background IO."""

    def __init__(self):
        """Init."""
        self.listeners = {}

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
        _LOGGER.debug("Starting listener @ %s", ps4._host)
        self.listeners[ps4].start()

    def stop_listener(self, ps4):
        """Stop a Listener."""
        if ps4 in self.listeners:
            self.listeners[ps4].stop.set()

    def remove_listener(self, ps4):
        """Stop and Remove a Listener."""
        self.stop_listener(ps4)
        self.listeners.pop(ps4)

    def _connect_ps4(self, ps4):
        """Try connecting ps4."""
        from .errors import NotReady

        if ps4 in self.listeners:
            if self.listeners[ps4].ps4.connected:
                _LOGGER.debug("PS4 @ %s already connected", ps4._host)
            else:
                active = self._get_active()
                if active is not None:
                    active.ps4.close()
                    try:
                        self.listeners[ps4].ps4.open()
                    except NotReady:
                        pass
                    else:
                        _LOGGER.warning("PS4 Connected @ %s", ps4._host)
                        self.listeners[ps4].connected.set()
        else:
            _LOGGER.error("Client has no PS4 Listeners")

    def schedule_task(self, ps4, task, connect=True):
        """Schedule socket task in thread."""
        self.listeners[ps4].block_status.set()
        # _task = {task: {}}

        if not connect:
            self.listeners[ps4].task_no_connect = task
        else:
            self._connect_ps4(ps4)
            if ps4.connected:
                # if args:
                #     _task[task][args] = args
                # if kwargs:
                #     _task[task][kwargs] = kwargs
                self.listeners[ps4].task = task

    def add_ps4(self, ps4):
        """Add PS4 to listeners."""
        if ps4 not in self.listeners:
            self.listeners[ps4] = Listener(client=self, ps4=ps4)

    def add_callback(self, ps4, callback):
        """Add Callback for listener."""
        assert callable(callback) is True, "Callback must be callable"
        if ps4 in self.listeners:
            self.listeners[ps4].callbacks.append(callback)

    def _get_active(self):
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
        self.interval = 3
        self.interval_keep_alive = 30
        self.last_poll = 0
        self.last_keep_alive = 0
        self.callbacks = []
        self.task = None
        self.task_no_connect = None

        self.stop = threading.Event()
        self.polling = threading.Event()
        self.waiting = threading.Event()
        self.block_status = threading.Event()
        self.connected = threading.Event()

    def run(self):
        """Run Listener."""
        if self.ps4.connected:
            self.connected.set()
        else:
            self.connected.clear()

        while not self.stop.is_set():
            if not self.block_status.is_set():
                self.schedule_status()
            elif not self.polling.is_set():
                self.schedule_task()

    def schedule_task(self):
        """Schedule a Task."""
        # if not self.task:
        #     task = self.task.keys()
        #     assert len(task) == 1, "Task dict should only have 1 key"

        #     if self.task[task]:
        #         for value in self.task.values():
        if self.task_no_connect is not None:
            self.task_no_connect()
        else:
            self.connected.wait()
            self.task()
        self.task = None
        self.task_no_connect = None
        self.block_status.clear()

    def schedule_status(self):
        """Schedule Status Update."""
        if self.waiting.is_set():
            if not self._should_poll(self.last_poll, self.interval):
                return
            self.waiting.clear()

        if not self.polling.is_set():
            if not self.waiting.is_set():
                self.polling.set()

                # Poll PS4 for Status
                self.ps4.get_status()

                # If connected send keep alive msg at intervals.
                if self.ps4.connected:
                    if self._should_poll(self.last_keep_alive,
                                         self.interval_keep_alive):
                        self.ps4.send_status()
                        self.last_keep_alive = time.time()

                self.last_poll = time.time()
                self.waiting.set()
                self.polling.clear()
                self._notify_callbacks()

    def _should_poll(self, last, interval):
        time_since = time.time() - last
        if time_since > interval:
            return True
        return False

    def _notify_callbacks(self):
        if self.callbacks:
            for callback in self.callbacks:
                callback()

    @property
    def is_connected(self):
        """Return True if connected with TCP."""
        return self.ps4.connected
