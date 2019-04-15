# -*- coding: utf-8 -*-
"""Methods for PS4 Object."""
from __future__ import print_function
from threading import Timer
import json
import logging
import time

from .connection import Connection
from .ddp import get_status, launch, wakeup
from .errors import NotReady, UnknownButton, LoginFailed, DataNotFound
from .media_art import get_ps_store_data as ps_data, search_all as _search_all
from .media_art import COUNTRIES, DEPRECATED_REGIONS

_LOGGER = logging.getLogger(__name__)


def open_credential_file(filename):
    """Open credential file."""
    return json.load(open(filename))


def delay(seconds):
    """Delay in seconds."""
    start_time = time.time()
    while time.time() - start_time < seconds:
        pass


class StatusTimer():
    """Status Thread Class."""

    def __init__(self, seconds, target):
        """Init."""
        self._should_continue = False
        self.is_running = False
        self.seconds = seconds
        self.target = target
        self.thread = None

    def _handle_target(self):
        self.is_running = True
        self.target()
        self.is_running = False
        self._start_timer()

    def _start_timer(self):
        """Restart Timer."""
        if self._should_continue:
            self.thread = Timer(self.seconds, self._handle_target)
            self.thread.start()

    def start(self):
        """Start Timer."""
        if not self._should_continue and not self.is_running:
            self._should_continue = True
            self._start_timer()

    def cancel(self):
        """Cancel Timer."""
        if self.thread is not None:
            self._should_continue = False
            self.thread.cancel()


class Ps4():   # noqa: pylint: disable=too-many-instance-attributes
    """The PS4 object."""

    STATUS_OK = 200
    STATUS_STANDBY = 620

    def __init__(self, host, credential=None, credentials_file=None,
                 broadcast=False):
        """Initialize the instance.

        Keyword arguments:
            host -- the host IP address
            credential -- the credential string
            credential_file -- the credendtial file generated with ps4-waker
            broadcast -- use broadcast IP address (default False)
        """
        self._host = host
        self._broadcast = broadcast
        self._socket = None
        self._credential = None
        self._status_timer = None
        self._msg_sending = False
        self.keep_alive = False
        self.status = None
        self.connected = False

        if credential:
            self._credential = credential
        if credentials_file:
            creds = open_credential_file(credentials_file)
            self._credential = creds['user-credential']

        self._connection = Connection(host, credential=self._credential)

    def open(self):
        """Open a connection to the PS4."""
        self.get_status()
        if self.is_standby:
            raise NotReady

        if self.connected is False:
            self.wakeup()
            self.launch()
            delay(0.5)
            self._connection.connect()
            login = self._connection.login()
            if login is True:
                self.connected = True
                if self.keep_alive is True:
                    _LOGGER.debug("Keep Alive feature enabled")
                    self._status_timer = StatusTimer(60, self.send_status)
                    self._status_timer.start()

    def close(self):
        """Close the connection to the PS4."""
        self._connection.disconnect()
        self.connected = False
        self.keep_alive = False
        if self._status_timer is not None:
            self._status_timer.cancel()
            self._status_timer = None

    def is_keepalive(self):
        """Check if keep alive should be sent."""
        if self.keep_alive is False:
            self.close()

    def get_status(self):
        """Get current status info."""
        self.status = get_status(self._host)
        return self.status

    def launch(self):
        """Launch."""
        launch(self._host, self._credential)

    def wakeup(self):
        """Wakeup."""
        wakeup(self._host, self._credential)

    def login(self, pin=None):
        """Login."""
        self.open()
        is_login = self._connection.login(pin)
        if is_login is False:
            raise LoginFailed
        self.close()
        return is_login

    def standby(self):
        """Standby."""
        if self.connected is True:
            self.close()
        self.open()
        self._connection.standby()
        self.close()

    def start_title(self, title_id, running_id=None):
        """Start title.

        `title_id`: title to start
        """
        if self.connected is True:
            self.close()
        self.open()
        if self._connection.start_title(title_id):
            if running_id is not None:
                delay(1)
                self.remote_control('enter')
            elif running_id == title_id:
                _LOGGER.warning("Title: %s already started", title_id)
        else:
            self.keep_alive = False
        self.is_keepalive()

    def remote_control(self, button_name, hold_time=0):
        """Send a remote control button press.

        Documentation from ps4-waker source:
        near as I can tell, here's how this works:
         - For a simple tap, you send the key with holdTime=0,
           followed by KEY_OFF and holdTime = 0
         - For a long press/hold, you still send the key with
           holdTime=0, the follow it with the key again, but
           specifying holdTime as the hold duration.
         - After sending a direction, you should send KEY_OFF
           to clean it up (since it can just be held forever).
           Doing this after a long-press of PS just breaks it,
           however.
        """
        if self._msg_sending is True:
            _LOGGER.debug("RC Command in progress")
            return
        self._msg_sending = True
        buttons = {'up': 1,
                   'down': 2,
                   'right': 4,
                   'left': 8,
                   'enter': 16,
                   'back': 32,
                   'option': 64,
                   'ps': 128,
                   'key_off': 256,
                   'cancel': 512,
                   'open_rc': 1024,
                   'close_rc': 2048}
        button_name = button_name.lower()
        if button_name not in buttons.keys():
            raise UnknownButton
        operation = buttons[button_name]
        self.open()
        if not self._connection.remote_control(operation, hold_time):
            self.keep_alive = False
        self._msg_sending = False
        self.is_keepalive()

    def send_status(self):
        """Send connection status to PS4."""
        if self.connected is True:
            while self._msg_sending is True:
                pass
            self._msg_sending = True
            is_loggedin = self._connection.send_status()
            self._msg_sending = False
            if is_loggedin is False:
                self.close()

    def get_ps_store_data(self, title, title_id, region, url=None, search_all=True):  # noqa: pylint: disable=no-self-use
        """Return Title and Cover data."""
        regions = COUNTRIES
        d_regions = DEPRECATED_REGIONS

        if region not in regions:
            if region in d_regions:
                _LOGGER.warning('Region: %s is deprecated', region)
                region = d_regions[region]
            else:
                _LOGGER.error('Region: %s is not valid', region)
                return None
        else:
            region = regions[region]
        try:
            _title, art = ps_data(title, title_id, region, url)
            if _title is None or art is None:
                raise DataNotFound
        except (TypeError, DataNotFound):
            _LOGGER.debug("Could not find title in default database.")
            if search_all is True:
                try:
                    _title, art = _search_all(title, title_id)
                except TypeError:
                    _LOGGER.warning("Could not find cover art for: %s", title)
                    return None, None
        _LOGGER.debug("Found Title: %s, URL: %s", _title, art)
        return _title, art

    @property
    def is_running(self):
        """Return if the PS4 is running."""
        if self.status['status_code'] == self.STATUS_OK:
            return True
        return False

    @property
    def is_standby(self):
        """Return if the PS4 is in standby."""
        if self.status['status_code'] == self.STATUS_STANDBY:
            return True
        return False

    @property
    def system_version(self):
        """Get the system version."""
        return self.status['system-version']

    @property
    def host_id(self):
        """Get the host id."""
        return self.status['host-id']

    @property
    def host_name(self):
        """Get the host name."""
        return self.status['host-name']

    @property
    def running_app_titleid(self):
        """Return the title Id of the running application."""
        return self.status['running-app-titleid']

    @property
    def running_app_name(self):
        """Return the name of the running application."""
        return self.status['running-app-name']
