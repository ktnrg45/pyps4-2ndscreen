# -*- coding: utf-8 -*-
"""Methods for PS4 Object."""
from __future__ import print_function
import json
import logging
import time
import asyncio

from .connection import Connection, AsyncConnection
from .ddp import (get_status, launch, wakeup,
                  get_ddp_launch_message, get_ddp_wake_message)
from .errors import (NotReady, PSDataIncomplete,
                     UnknownButton, LoginFailed)
from .media_art import (get_ps_store_data as ps_data,
                        async_get_ps_store_requests,
                        get_region, parse_data, prepare_tumbler,
                        COUNTRIES)

_LOGGER = logging.getLogger(__name__)

BUTTONS = {'up': 1,
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

STATUS_OK = 200
STATUS_STANDBY = 620


def opencredential_file(filename):
    """Open credential file."""
    return json.load(open(filename))


def delay(seconds):
    """Delay in seconds."""
    start_time = time.time()
    while time.time() - start_time < seconds:
        pass


class Ps4():
    """The PS4 object."""

    def __init__(self, host, credential=None, credentials_file=None,
                 broadcast=False, device_name=None):
        """Initialize the instance.

        Keyword arguments:
            host -- the host IP address
            credential -- the credential string
            credential_file -- the credendtial file generated with ps4-waker
            broadcast -- use broadcast IP address (default False)
        """
        self.host = host
        self._broadcast = broadcast
        self._socket = None
        self.credential = None
        self.msg_sending = False
        self.status = None
        self.connected = False
        self.client = None
        self.ps_cover = None
        self.ps_name = None
        self.loggedin = False
        self.device_name = device_name

        if credential:
            self.credential = credential
        if credentials_file:
            creds = opencredential_file(credentials_file)
            self.credential = creds['user-credential']

        self.connection = Connection(host, credential=self.credential)

        if self.client is not None:
            self.client.add_ps4(ps4=self)

    def _prepare_connection(self):
        self.launch()
        delay(0.5)
        _LOGGER.debug("Connection prepared")

    def open(self):
        """Open a connection to the PS4."""
        if self.status is None:
            self.get_status()
        if not self.is_running:
            raise NotReady("PS4 is not On")

        self._prepare_connection()
        if self.connected is False:
            self.connection.connect()
            login = self.connection.login()
            if login is True:
                self.connected = True
                return True
            return False
        return True

    def close(self):
        """Close the connection to the PS4."""
        self.connection.disconnect()
        self.connected = False
        _LOGGER.debug("Disconnecting from PS4 @ %s", self.host)
        return True

    def get_status(self) -> dict:
        """Get current status info."""
        import socket

        try:
            self.status = get_status(self.host)
        except socket.timeout:
            _LOGGER.debug("PS4 @ %s status timed out", self.host)
            return None
        else:
            if self.is_standby:
                self.connected = False
                self.loggedin = False
        return self.status

    def launch(self):
        """Launch."""
        launch(self.host, self.credential)

    def wakeup(self):
        """Wakeup."""
        wakeup(self.host, self.credential)

    def login(self, pin=None):
        """Login."""
        self.open()
        is_login = self.connection.login(self.device_name, pin)
        if is_login is False:
            raise LoginFailed("PS4 Refused Connection")
        self.close()
        return is_login

    def standby(self, retry=2):
        """Standby."""
        retries = 0
        while retries < retry:
            self.open()
            if self.connection.standby():
                self.close()
                return True
            self.close()
            retries += 1
        return False

    def start_title(self, title_id, running_id=None, retry=2):
        """Start title.

        `title_id`: title to start
        'running_id': Title currently running,
        Use to confirm closing of current title.
        """
        if self.msg_sending:
            _LOGGER.warning("PS4 already sending message.")
            return False
        retries = 0
        while retries < retry:
            self.msg_sending = True
            if self.open():
                if self.connection.start_title(title_id):

                    # Auto confirm prompt to close title.
                    if running_id is not None:
                        delay(1)
                        self.remote_control('enter')
                    elif running_id == title_id:
                        _LOGGER.warning("Title: %s already started", title_id)
                    self.msg_sending = False
                    return True
                else:
                    self.close()
                    retries += 1
                    delay(1)
        self.msg_sending = False
        return False

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
        if self.msg_sending:
            _LOGGER.warning("PS4 already sending message.")
            return
        self.msg_sending = True
        button_name = button_name.lower()
        if button_name not in BUTTONS.keys():
            raise UnknownButton("Button: {} is not valid".format(button_name))
        operation = BUTTONS[button_name]
        if self.open():
            _LOGGER.debug("Sending RC Command: %s", button_name)
            if not self.connection.remote_control(operation, hold_time):
                self.close()
        self.msg_sending = False

    def send_status(self):
        """Send connection status to PS4."""
        if self.connected is True:
            is_loggedin = self.connection.send_status()
            if is_loggedin is False:
                self.close()

    def get_ps_store_data(self, title, title_id, region, url=None):
        """Return Title and Cover data."""
        region = get_region(region)
        try:
            _LOGGER.debug("Searching using legacy API")
            result_item = ps_data(title, title_id, region, url, legacy=True)
        except (TypeError, AttributeError):
            result_item = None
            raise PSDataIncomplete
        if result_item is not None:
            _LOGGER.debug("Found Title: %s, URL: %s",
                          result_item.name, result_item.cover_art)
            return result_item

        try:
            result_item = ps_data(title, title_id, region, url)
        except (TypeError, AttributeError):
            result_item = None
            raise PSDataIncomplete
        if result_item is not None:
            _LOGGER.debug("Found Title: %s, URL: %s",
                          result_item.name, result_item.cover_art)
            self.ps_name = result_item.name
            self.ps_cover = result_item.cover_art
            return result_item
        return None

    async def async_get_ps_store_data(self, title, title_id, region):
        """Parse Responses."""
        regions = COUNTRIES
        lang = regions[region]
        lang = lang.split('/')
        lang = lang[0]
        _LOGGER.debug("Searching...")
        responses = await async_get_ps_store_requests(
            title, region)
        for response in responses:
            try:
                result_item = parse_data(response, title_id, lang)
            except (TypeError, AttributeError):
                result_item = None
                raise PSDataIncomplete
            if result_item is not None:
                break

        if result_item is None:
            region = get_region(region)
            loop = asyncio.get_event_loop()
            try:
                result_item = await loop.run_in_executor(
                    None, prepare_tumbler, title, title_id, region)
            except (TypeError, AttributeError):
                result_item = None
                raise PSDataIncomplete

        if result_item is not None:
            _LOGGER.debug("Found Title: %s, URL: %s",
                          result_item.name, result_item.cover_art)
            self.ps_name = result_item.name
            self.ps_cover = result_item.cover_art
            return result_item
        return None

    @property
    def is_running(self):
        """Return if the PS4 is running."""
        if self.status['status_code'] == STATUS_OK:
            return True
        return False

    @property
    def is_standby(self):
        """Return if the PS4 is in standby."""
        if self.status['status_code'] == STATUS_STANDBY:
            self.loggedin = False
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

    @property
    def running_app_ps_cover(self):
        """Return the URL for the title cover art."""
        return self.ps_cover

    @property
    def running_app_ps_name(self):
        """Return the name fetched from PS Store."""
        return self.ps_name


class Ps4Async(Ps4):
    """Async Version of Ps4 Class."""

    def __init__(self, host, credential=None, credentials_file=None,
                 broadcast=False, device_name=None):
        """Inherit Class."""
        super().__init__(host, credential, credentials_file,
                         broadcast, device_name)
        self.ddp_protocol = None
        self.tcp_protocol = None
        self.connection = AsyncConnection(self.host, self.credential)
        self.loop = None

    def open(self):
        """Not Implemented."""
        raise NotImplementedError

    def get_status(self) -> dict:
        """Get current status info."""
        if self.ddp_protocol is not None:
            try:
                self.ddp_protocol.send_msg(self)
            except Exception:
                pass
            finally:
                if self.is_standby:
                    self.connected = False
                    self.loggedin = False
                _LOGGER.debug(
                    "connected: %s, loggedin: %s",
                    self.connected, self.loggedin)
                return self.status
        else:
            return super().get_status()

    def launch(self):
        """Launch."""
        if self.ddp_protocol is None:
            _LOGGER.error("DDP Protocol does not exist")
        else:
            self.ddp_protocol.send_msg(
                self, get_ddp_launch_message(self.credential))

    def wakeup(self):
        """Wakeup."""
        if self.ddp_protocol is None:
            _LOGGER.error("DDP Protocol does not exist")
        else:
            self.ddp_protocol.send_msg(
                self, get_ddp_wake_message(self.credential))

    async def standby(self):
        """Standby."""
        if self.tcp_protocol is None:
            _LOGGER.error("TCP Protocol does not exist")
        else:
            await self.tcp_protocol.standby()

    async def start_title(self, title_id, running_id=None):
        """Start title."""
        if self.tcp_protocol is None:
            _LOGGER.error("TCP Protocol does not exist")
        else:
            await self.tcp_protocol.start_title(title_id, running_id)

    async def remote_control(self, button_name, hold_time=0):
        """Remote Control."""
        if self.tcp_protocol is None:
            _LOGGER.error("TCP Protocol does not exist")
        else:
            button_name = button_name.lower()
            if button_name not in BUTTONS.keys():
                raise UnknownButton(
                    "Button: {} is not valid".format(button_name))
            operation = BUTTONS[button_name]
            await self.tcp_protocol.remote_control(operation, hold_time)

    async def close(self):
        """Close Transport."""
        if self.tcp_protocol is None:
            _LOGGER.error("TCP Protocol does not exist")
        else:
            await self.tcp_protocol.close()

    async def async_connect(self):
        """Connect."""
        self. loop = asyncio.get_event_loop()
        if self.status is None:
            self.get_status()
        if not self.is_running:
            raise NotReady("PS4 is not On")
        try:
            self._prepare_connection()
            transport, protocol = await self.connection.async_connect(self)
            self.tcp_protocol = protocol
            self.connected = True
        except (OSError, ConnectionRefusedError):
            _LOGGER.error("PS4 Refused Connection")
            self.connected = False
            self.loggedin = False
