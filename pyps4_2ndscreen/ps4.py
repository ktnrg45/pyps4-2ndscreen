# -*- coding: utf-8 -*-
"""Methods for PS4 Object."""
from __future__ import print_function
import logging
import time
import asyncio

import aiohttp

from .connection import LegacyConnection, AsyncConnection, DEFAULT_LOGIN_DELAY
from .credential import DEFAULT_DEVICE_NAME
from .ddp import (get_status, launch, wakeup,
                  get_ddp_launch_message, get_ddp_wake_message)
from .errors import (NotReady, PSDataIncomplete,
                     UnknownButton, LoginFailed)
from .media_art import (async_get_ps_store_requests,
                        get_lang, parse_data, COUNTRIES,
                        async_prepare_tumbler, PINNED_TITLES,
                        get_pinned_item, ResultItem)

_LOGGER = logging.getLogger(__name__)

BUTTONS = {
    'up': 1,
    'down': 2,
    'right': 4,
    'left': 8,
    'enter': 16,
    'back': 32,
    'option': 64,
    'ps': 128,
    'ps_hold': 128,
    'key_off': 256,
    'cancel': 512,
    'open_rc': 1024,
    'close_rc': 2048
}

PS_HOLD_TIME = 2000

STATUS_OK = 200
STATUS_STANDBY = 620


class Ps4Base():
    """The PS4 object.

    :param host: The host PS4 IP address
    :param credential: The credentials of a PSN account
    :param device_name: Name for device
    """

    def __init__(self, host: str, credential: str,
                 device_name=DEFAULT_DEVICE_NAME):
        self.host = host
        self.credential = None
        self.device_name = device_name
        self._socket = None
        self._power_on = False
        self._power_off = False
        self.msg_sending = False
        self.status = None
        self.connected = False
        self.ps_cover = None
        self.ps_name = None
        self.loggedin = False
        self.credential = credential

    def get_status(self) -> dict:
        """Return current status info."""
        import socket

        try:
            self.status = get_status(self.host)
        except socket.timeout:
            _LOGGER.debug("PS4 @ %s status timed out", self.host)
            self.status = None
            return self.status
        if self.status is not None:
            if self.is_standby:
                self.connected = False
                self.loggedin = False
            return self.status
        return None

    async def async_get_ps_store_data(
            self, title: str, title_id: str, region: str) -> ResultItem:
        """Return title data from PS Store."""
        # Check if title is a pinned title first and return.
        pinned = None
        pinned = PINNED_TITLES.get(title_id)
        if pinned is not None:
            return get_pinned_item(pinned)

        # Conduct Search Requests.
        lang = get_lang(region)
        _LOGGER.debug("Starting search request")
        async with aiohttp.ClientSession() as session:
            responses = await async_get_ps_store_requests(
                title, region, session)
            for response in responses:
                try:
                    result_item = parse_data(response, title_id, lang)
                except (TypeError, AttributeError):
                    result_item = None
                    raise PSDataIncomplete
                if result_item is not None:
                    break

            if result_item is None:
                try:
                    result_item = await async_prepare_tumbler(
                        title, title_id, region, session)
                except (TypeError, AttributeError):
                    result_item = None
                    raise PSDataIncomplete

            await session.close()

            if result_item is not None:
                _LOGGER.debug("Found Title: %s, URL: %s",
                              result_item.name, result_item.cover_art)
                self.ps_name = result_item.name
                self.ps_cover = result_item.cover_art
                return result_item

            return None

    async def async_search_all_ps_data(self, title, title_id, timeout=10):
        """Search for title in all regions."""
        _LOGGER.debug("Searching all databases...")
        tasks = []
        for region in COUNTRIES:
            search_func = self.async_get_ps_store_data(title, title_id, region)
            task = asyncio.ensure_future(
                self._async_search_region(search_func))
            tasks.append(task)

        done, pending = await asyncio.wait(
            tasks, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)

        # Return First Result.
        data = None
        for completed in done:
            try:
                data = completed.result()
            except asyncio.InvalidStateError:
                data = None
            if data is not None:
                for task in pending:
                    task.cancel()
                return data
        return None

    async def _async_search_region(self, task):
        result_item = await task
        if result_item is not None:
            return result_item
        return None

    @property
    def is_running(self):
        """Return True if the PS4 is running."""
        if self.status is not None:
            if self.status['status_code'] == STATUS_OK:
                return True
        return False

    @property
    def is_standby(self):
        """Return True if the PS4 is in standby."""
        if self.status is not None:
            if self.status['status_code'] == STATUS_STANDBY:
                return True
        return False

    @property
    def is_available(self):
        """Return if the PS4 is available."""
        if self.status is not None:
            return True
        return False

    @property
    def system_version(self):
        """Get the system version."""
        if self.status is not None:
            return self.status['system-version']
        return None

    @property
    def host_id(self):
        """Get the host id."""
        if self.status is not None:
            return self.status['host-id']
        return None

    @property
    def host_name(self):
        """Get the host name."""
        if self.status is not None:
            return self.status['host-name']
        return None

    @property
    def running_app_titleid(self):
        """Return the title Id of the running application."""
        if self.status is not None:
            if 'running-app-titleid' in self.status:
                return self.status['running-app-titleid']
        return None

    @property
    def running_app_name(self):
        """Return the name of the running application."""
        if self.status is not None:
            if 'running-app-name' in self.status:
                return self.status['running-app-name']
        return None

    @property
    def running_app_ps_cover(self):
        """Return the URL for the title cover art."""
        if self.running_app_titleid is None:
            self.ps_cover = None
        return self.ps_cover

    @property
    def running_app_ps_name(self):
        """Return the name fetched from PS Store."""
        if self.running_app_titleid is None:
            self.ps_name = None
        return self.ps_name


class Ps4Legacy(Ps4Base):
    """Legacy PS4 Class. Sync Version."""

    def __init__(
            self, host, credential,
            device_name=DEFAULT_DEVICE_NAME, auto_close=True):
        super().__init__(host, credential, device_name)
        self.auto_close = auto_close
        self.connection = LegacyConnection(self, credential=self.credential)

    # noqa: pylint: disable=no-self-use
    def delay(self, seconds):
        """Delay in seconds."""
        start_time = time.time()
        while time.time() - start_time < seconds:
            pass

    def _prepare_connection(self):
        self.launch()
        self.delay(0.5)
        _LOGGER.debug("Connection prepared")

    def open(self):
        """Open a connection to the PS4."""
        self.get_status()
        if not self.is_running:
            raise NotReady("PS4 is not On")

        self._prepare_connection()
        if not self.connected:
            self.connection.connect()
        self.connected = True

    def close(self):
        """Close the connection to the PS4."""
        self.connection.disconnect()
        self.connected = False
        self.loggedin = False
        self.msg_sending = False
        _LOGGER.debug("Disconnecting from PS4 @ %s", self.host)
        return True

    def launch(self):
        """Launch."""
        launch(self.host, self.credential)

    def wakeup(self):
        """Wakeup."""
        wakeup(self.host, self.credential)
        self._power_on = True

    def login(self, pin=None) -> bool:
        """Login."""
        if self.loggedin:
            return True
        self.open()
        is_login = self.connection.login(pin)
        if not is_login:
            self.close()
            raise LoginFailed("PS4 Refused Connection")
        self.loggedin = True
        return is_login

    def standby(self):
        """Standby."""
        if self.login():
            if self.connection.standby():
                self.close()
                return True
        self.close()
        return False

    def start_title(self, title_id, running_id=None):
        """Start title.

        Close current title if title_id is running_id

        :param title_id: Title to start; CUSA00000
        :param running_id: Title currently running
        """
        if self.msg_sending:
            _LOGGER.warning("PS4 already sending message.")
            return False
        self.msg_sending = True
        if self.login():
            if self.connection.start_title(title_id):
                # Auto confirm prompt to close title.
                if running_id is not None:
                    self.delay(1)
                    self.remote_control('enter')
                elif running_id == title_id:
                    _LOGGER.warning("Title: %s already started", title_id)
                self.msg_sending = False
                if self.auto_close:
                    self.close()
                return True
        self.msg_sending = False
        return False

    def remote_control(self, button_name, hold_time=0):
        """Send a remote control button press."""
        if self.msg_sending:
            _LOGGER.warning("PS4 already sending message.")
            return False
        self.msg_sending = True
        button_name = button_name.lower()
        if button_name not in BUTTONS.keys():
            raise UnknownButton("Button: {} is not valid".format(button_name))
        if button_name == 'ps_hold':
            hold_time = PS_HOLD_TIME
        operation = BUTTONS[button_name]
        if self.login():
            _LOGGER.debug("Sending RC Command: %s", button_name)
            self.connection.remote_control(operation, hold_time)
            self.msg_sending = False
            if self.auto_close:
                self.close()
        return True

    def send_status(self):
        """Send connection status to PS4."""
        if self.connected and self.loggedin:
            self.connection.send_status()
            return True
        _LOGGER.error("PS4 is not connected")
        return False


class Ps4Async(Ps4Base):
    """Async Version of Ps4 Class."""

    def __init__(self, host, credential=None, device_name=DEFAULT_DEVICE_NAME):
        """Inherit Class."""
        super().__init__(host, credential, device_name)
        self._login_delay = DEFAULT_LOGIN_DELAY
        self.ddp_protocol = None
        self.tcp_transport = None
        self.tcp_protocol = None
        self.task_queue = None
        self.poll_count = 0
        self.unreachable = False

        self.connection = AsyncConnection(self, self.credential)

    def open(self):
        """Not Implemented."""
        raise NotImplementedError

    def _prepare_connection(self):
        """Send launch msg."""
        self.launch()
        _LOGGER.debug("Connection prepared")

    def set_login_delay(self, value: int):
        """Set delay for login."""
        self._login_delay = value

    def set_protocol(self, ddp_protocol):
        """Attach DDP protocol."""
        self.ddp_protocol = ddp_protocol

    def add_callback(self, callback):
        """Add status updated callback."""
        if self.ddp_protocol is None:
            _LOGGER.error("DDP protocol is not set")
        else:
            self.ddp_protocol.add_callback(self, callback)

    def get_status(self) -> dict:
        """Get current status info."""
        if self.ddp_protocol is not None:
            self.ddp_protocol.send_msg(self)
            if self.status is not None:
                if self.is_standby:
                    self.connected = False
                    self.loggedin = False

                    # Ensure that connection is closed.
                    if self.tcp_protocol is not None:
                        self._close()

                return self.status
            return None
        return super().get_status()

    def launch(self):
        """Launch."""
        if self.ddp_protocol is None:
            _LOGGER.error("DDP Protocol does not exist/Not ready")
        else:
            self.ddp_protocol.send_msg(
                self, get_ddp_launch_message(self.credential))

    def wakeup(self):
        """Wakeup."""
        if self.ddp_protocol is None:
            _LOGGER.error("DDP Protocol does not exist")
        else:
            self._power_on = True
            self._power_off = False
            self.ddp_protocol.send_msg(
                self, get_ddp_wake_message(self.credential))

    async def login(self, pin=None):
        """Login."""
        if self.tcp_protocol is None:
            _LOGGER.info("Login failed: TCP Protocol does not exist")
        else:
            power_on = self._power_on
            await self.tcp_protocol.login(pin, power_on, self.login_delay)

    async def standby(self, retry=None):
        """Standby."""
        if retry is not None:
            _LOGGER.info("Retries not implemented")
        if self.tcp_protocol is None:
            _LOGGER.info("Standby Failed: TCP Protocol does not exist")
        else:
            await self.tcp_protocol.standby()
            self._power_off = True

    async def start_title(self, title_id, running_id=None, retry=None):
        """Start title."""
        if running_id is None:
            if self.running_app_titleid is not None:
                running_id = self.running_app_titleid

        if retry is not None:
            _LOGGER.info("Retries not implemented")
        if self.tcp_protocol is None:
            _LOGGER.info("TCP Protocol does not exist")

            # Queue task upon login.
            task = ('start_title', title_id, running_id)
            self.task_queue = task
            self.wakeup()

        else:
            await self.tcp_protocol.start_title(title_id, running_id)

    async def remote_control(self, button_name: str, hold_time=0):
        """Send remote control command.

        :param button_name: Button to send to PS4.
        :param hold_time: Time to hold in millis. Only affects PS command.
        """
        button_name = button_name.lower()
        if button_name not in BUTTONS.keys():
            raise UnknownButton(
                "Button: {} is not valid".format(button_name))
        if button_name == 'ps_hold':
            hold_time = PS_HOLD_TIME
        operation = BUTTONS[button_name]

        if self.tcp_protocol is None:
            _LOGGER.info("TCP Protocol does not exist")

            # Queue task upon login.
            task = ('remote_control', operation, hold_time)
            self.task_queue = task
            self.wakeup()

        else:
            await self.tcp_protocol.remote_control(operation, hold_time)

    async def close(self):
        """Close Transport."""
        if self.tcp_protocol is not None:
            self.tcp_protocol.disconnect()

    def _close(self):
        if self.tcp_protocol is not None:
            self.tcp_protocol.disconnect()

    def _closed(self):
        """Callback function called by protocol connection lost."""
        if self.tcp_protocol is None:
            _LOGGER.info("TCP Protocol @ %s already disconnected", self.host)
        else:
            self.tcp_transport = None
            self.tcp_protocol = None
            self.loggedin = False
            self.connected = False

    async def async_connect(self, auto_login=True):
        """Connect."""
        if not self.connected:
            if self.status is None:
                self.get_status()
            if not self.is_available:
                raise NotReady(
                    "PS4 is not available or powered off. Check connection.")
            if not self._power_off:
                if self.is_standby:
                    raise NotReady("PS4 is not On")
                try:
                    self._prepare_connection()
                    tcp_transport, tcp_protocol =\
                        await self.connection.async_connect(self)
                except (OSError, ConnectionRefusedError):
                    _LOGGER.info("PS4 Refused Connection")
                    self.connected = False
                    self.loggedin = False
                else:
                    self.tcp_transport = tcp_transport
                    self.tcp_protocol = tcp_protocol
                    self.connected = True
                    if self._power_on:
                        if auto_login:
                            await self.login()
                    self._power_on = False

    @property
    def login_delay(self):
        """Return login delay value."""
        return self._login_delay
