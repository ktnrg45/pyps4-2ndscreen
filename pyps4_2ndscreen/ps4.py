"""Methods for interfacing with a PlayStation 4 Console."""
import logging
import time
import socket
import asyncio
from typing import Optional, Union

from .connection import LegacyConnection, AsyncConnection, DEFAULT_LOGIN_DELAY
from .credential import DEFAULT_DEVICE_NAME
from .ddp import (
    DDPProtocol,
    get_status,
    launch,
    wakeup,
    get_ddp_launch_message,
    get_ddp_wake_message,
    async_create_ddp_endpoint,
    get_socket,
    UDP_PORT,
    STATUS_OK,
    STATUS_STANDBY,
)
from .errors import NotReady, UnknownButton, LoginFailed
from .media_art import async_search_ps_store, ResultItem

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


class Ps4Base():
    """The PS4 base object. Should not be initialized directly.

    :param host: The host PS4 IP address
    :param credential: The credentials of a PSN account
    :param device_name: Name for client device
    :param port: Local UDP Port to use
    """

    def __init__(self, host: str, credential: str,
                 device_name: Optional[str] = DEFAULT_DEVICE_NAME,
                 port: Optional[int] = UDP_PORT):
        self.host = host
        self.credential = None
        self.device_name = device_name
        self._port = port
        self._power_on = False
        self._power_off = False
        self.msg_sending = False
        self.status = None
        self._connected = False
        self.ps_cover = None
        self.ps_name = None
        self.loggedin = False
        self.credential = credential

    def __repr__(self):
        return (
            "<{}.{} ip_address={} name={} status_code={}>".format(
                self.__module__,
                self.__class__.__name__,
                self.host,
                self.host_name,
                self.status_code,
            )
        )

    def change_port(self, port):
        """Change DDP Port."""
        self._port = port

    def _get_socket(self):
        return get_socket(port=self.port)

    def get_status(self) -> dict:
        """Return current status info."""
        sock = None
        if self.port != UDP_PORT:
            sock = self._get_socket()
        try:
            self.status = get_status(self.host, sock=sock)
        except socket.timeout:
            _LOGGER.debug("PS4 @ %s status timed out", self.host)
            self.status = None
            return self.status
        if self.status is not None:
            if self.is_standby:
                self._connected = False
                self.loggedin = False
            return self.status
        return None

    async def async_get_ps_store_data(
            self,
            title: str,
            title_id: str,
            region: str) -> ResultItem:
        """Return title data from PS Store."""
        _LOGGER.debug(
            "Searching for title: Name: %s, SKU_ID: %s", title, title_id)
        result_item = await async_search_ps_store(title_id, region)
        if result_item is not None:
            _LOGGER.debug("Found Title: %s, URL: %s",
                          result_item.name, result_item.cover_art)
            self.ps_name = result_item.name
            self.ps_cover = result_item.cover_art
            return result_item

        return None

    @property
    def port(self):
        """Return local port."""
        return self._port

    @property
    def status_code(self):
        """Return status code."""
        if self.status is not None:
            return self.status['status_code']
        return None

    @property
    def is_running(self) -> bool:
        """Return True if the PS4 is running."""
        if self.status is not None:
            if self.status['status_code'] == STATUS_OK:
                return True
        return False

    @property
    def is_standby(self) -> bool:
        """Return True if the PS4 is in standby."""
        if self.status is not None:
            if self.status['status_code'] == STATUS_STANDBY:
                return True
        return False

    @property
    def is_available(self) -> bool:
        """Return True if the PS4 is available."""
        if self.status is not None:
            return True
        return False

    @property
    def connected(self) -> bool:
        """Return True if connected to PS4."""
        return self._connected

    @property
    def system_version(self) -> dict:
        """Return the system version."""
        if self.status is not None:
            return self.status['system-version']
        return None

    @property
    def host_id(self) -> str:
        """Return the host id/MAC address."""
        if self.status is not None:
            return self.status['host-id']
        return None

    @property
    def host_name(self) -> str:
        """Return the host name."""
        if self.status is not None:
            return self.status['host-name']
        return None

    @property
    def running_app_titleid(self) -> str:
        """Return the title ID of the running application."""
        if self.status is not None:
            if 'running-app-titleid' in self.status:
                return self.status['running-app-titleid']
        return None

    @property
    def running_app_name(self) -> str:
        """Return the name of the running application."""
        if self.status is not None:
            if 'running-app-name' in self.status:
                return self.status['running-app-name']
        return None

    @property
    def running_app_ps_cover(self) -> str:
        """Return the URL for the title cover art."""
        if self.running_app_titleid is None:
            self.ps_cover = None
        return self.ps_cover

    @property
    def running_app_ps_name(self) -> str:
        """Return the name fetched from PS Store."""
        if self.running_app_titleid is None:
            self.ps_name = None
        return self.ps_name


class Ps4Legacy(Ps4Base):
    """Legacy PS4 Class. Sync Version.

    :param host: The host PS4 IP address
    :param credential: The credentials of a PSN account
    :param device_name: Name for device
    """

    def __init__(
            self, host: str, credential: str,
            device_name: Optional[str] = DEFAULT_DEVICE_NAME,
            auto_close: Optional[bool] = True,
            port: Optional[int] = UDP_PORT):
        super().__init__(host, credential, device_name, port)
        self.auto_close = auto_close
        self.connection = LegacyConnection(self, credential=self.credential)

    # noqa: pylint: disable=no-self-use
    def delay(self, seconds: Union[float, str]):
        """Delay in seconds.

        :param seconds: Seconds to delay
        """
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
        if not self._connected:
            self.connection.connect()
        self._connected = True

    def close(self):
        """Close the connection to the PS4."""
        self.connection.disconnect()
        self._connected = False
        self.loggedin = False
        self.msg_sending = False
        _LOGGER.debug("Disconnecting from PS4 @ %s", self.host)
        return True

    def launch(self):
        """Send Launch Packet."""
        sock = self._get_socket()
        launch(self.host, self.credential, sock=sock)

    def wakeup(self):
        """Send Wakeup Packet."""
        sock = self._get_socket()
        wakeup(self.host, self.credential, sock=sock)
        self._power_on = True

    def login(self, pin: Optional[str] = '') -> bool:
        """Send Login Packet.

        :param pin: Pin to send. Requred when linking.
        """
        if self.loggedin:
            return True
        self.open()
        is_login = self.connection.login(pin)
        if not is_login:
            self.close()
            raise LoginFailed("PS4 Refused Connection")
        self.loggedin = True
        return is_login

    def standby(self) -> bool:
        """Send Standby Packet."""
        if self.login():
            if self.connection.standby():
                self.close()
                return True
        self.close()
        return False

    def start_title(self, title_id, running_id: Optional[str] = None) -> bool:
        """Send Start title packet.

        Close current title if title_id is running_id

        :param title_id: Title to start; CUSA00000
        :param running_id: Title currently running
        """
        if self.login():
            if self.connection.start_title(title_id):
                # Auto confirm prompt to close title.
                if running_id != title_id:
                    self.delay(1)
                    self.remote_control('enter')
                if self.auto_close:
                    self.close()
                return True
        return False

    def remote_control(
            self, button_name, hold_time: Optional[int] = 0) -> bool:
        """Send remote control command packet.

        :param button_name: Button to send to PS4.
        :param hold_time: Time to hold in millis. Only affects PS command.
        """
        button_name = button_name.lower()
        if button_name not in BUTTONS.keys():
            raise UnknownButton("Button: {} is not valid".format(button_name))
        if button_name == 'ps_hold':
            hold_time = PS_HOLD_TIME
        operation = BUTTONS[button_name]
        if self.login():
            _LOGGER.debug("Sending RC Command: %s", button_name)
            self.connection.remote_control(operation, hold_time)
            if self.auto_close:
                self.close()
            return True
        return False

    def send_status(self) -> bool:
        """Send connection status ack to PS4."""
        if self._connected and self.loggedin:
            self.connection.send_status()
            return True
        _LOGGER.error("PS4 is not connected")
        return False


class Ps4Async(Ps4Base):
    """Async Version of Ps4 Class.

    :param host: The host PS4 IP address
    :param credential: The credentials of a PSN account
    :param device_name: Name for device
    """

    def __init__(
            self, host: str, credential: str,
            device_name: Optional[str] = DEFAULT_DEVICE_NAME,
            port: Optional[int] = UDP_PORT):

        super().__init__(host, credential, device_name, port)
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

    def set_protocol(self, ddp_protocol: DDPProtocol):
        """Attach DDP protocol.

        :param ddp_protocol: :class: `pyps4_2ndscreen.ddp.DDPProtocol`
        """
        self.ddp_protocol = ddp_protocol
        self._port = self.ddp_protocol.local_port

    def _detach_protocol(self):
        """Detach from protcocol. Return current protocol and callback."""
        protocol = None
        callback = None
        if self.ddp_protocol is not None:
            host = self.ddp_protocol.callbacks.get(self.host)
            if host is not None:
                callback = host.get(self)
                self.ddp_protocol.remove_callback(self, callback)
            protocol = self.ddp_protocol
            self.ddp_protocol = None
        return protocol, callback

    def add_callback(self, callback: callable):
        """Add status updated callback.

        :param callback: Callback to call on status updated; No args
        """
        if self.ddp_protocol is None:
            _LOGGER.error("DDP protocol is not set")
        else:
            self.ddp_protocol.add_callback(self, callback)

    def get_status(self) -> dict:
        """Get current status info."""
        if self.ddp_protocol is not None:
            self.ddp_protocol.send_msg(self)
            if self.status is not None:
                if not self.is_running:
                    self._connected = False
                    self.loggedin = False

                    # Ensure that connection is closed.
                    if self.tcp_protocol is not None:
                        self._close()

                return self.status
            return None
        return super().get_status()

    def launch(self):
        """Send Launch packet."""
        if self.ddp_protocol is None:
            _LOGGER.error("DDP Protocol does not exist/Not ready")
        else:
            self.ddp_protocol.send_msg(
                self, get_ddp_launch_message(self.credential))

    def wakeup(self, ignore_conflict=False):
        """Send Wakeup packet."""
        if self.ddp_protocol is None:
            _LOGGER.error("DDP Protocol does not exist")
        else:
            if self.is_standby:
                self._power_on = True
                self._power_off = False
                self.ddp_protocol.send_msg(
                    self, get_ddp_wake_message(self.credential))
                _LOGGER.debug("Command: Wakeup")
            elif self.is_running and ignore_conflict:
                _LOGGER.debug("Status is 'running'; Trying Command: Standby")
                asyncio.ensure_future(self.standby())

    async def change_ddp_endpoint(self, port: int, close_old: bool = False):
        """Return True if new endpoint is created."""
        if self.ddp_protocol is None:
            _LOGGER.warning("No DDP protocol set")
            return False
        if self.port == port:
            _LOGGER.warning("Port is already: %s", self.port)
            return False

        old_protocol, callback = self._detach_protocol()
        old_port = self._port
        self._port = port

        _LOGGER.debug("Changing Port from %s to %s", old_port, self._port)

        success = await self.get_ddp_endpoint()

        # Restore old protocol
        if not success:
            self._port = old_port
            self.ddp_protocol = old_protocol
            if callback is not None:
                self.add_callback(callback)
            _LOGGER.warning(
                "Failed to get new protocol; Reverting to port: %s",
                self._port)
            return False

        if close_old:
            _LOGGER.debug("Closing old protocol: %s", self.ddp_protocol)
            old_protocol.close()
        return True

    async def get_ddp_endpoint(self):
        """Return True if endpoint is created from socket."""
        protocol = None
        sock = None
        if self.port != UDP_PORT:
            sock = self._get_socket()
        _, protocol = await async_create_ddp_endpoint(
            sock=sock)
        if protocol is not None:
            self.ddp_protocol = protocol
            return True
        return False

    async def login(self, pin: Optional[str] = ''):
        """Send Login Packet.

        :param pin: Pin to send. Requred when linking.
        """
        if self.tcp_protocol is None:
            _LOGGER.info("Login failed: TCP Protocol does not exist")
            if self.is_running:
                await self.async_connect()

        if self.tcp_protocol is not None:
            power_on = self._power_on
            _LOGGER.debug("Logging in with PSN user: %s", self.credential)
            await self.tcp_protocol.login(pin, power_on, self.login_delay)

    async def standby(self, ignore_conflict=False):
        """Send Standby Packet."""
        if self.is_standby:
            if ignore_conflict:
                self.wakeup()
                _LOGGER.debug("Status is 'standby'; Trying Command: Wakeup")
        elif self.is_running:
            if self.tcp_protocol is None:
                _LOGGER.info("Standby Failed: TCP Protocol does not exist")
                await self.async_connect()
            if self.tcp_protocol is not None:
                self._power_off = True
                await self.tcp_protocol.standby()
                _LOGGER.debug("Command: Standby")

    async def toggle(self):
        """Toggle Power."""
        if self.is_standby:
            self.wakeup()
        elif self.is_running:
            await self.standby()

    async def start_title(
            self, title_id: str, running_id: Optional[str] = None):
        """Send start title packet.

        Closes current title if title_id is running_id

        :param title_id: Title to start; CUSA00000
        :param running_id: Title currently running
        """
        if running_id is None:
            if self.running_app_titleid is not None:
                running_id = self.running_app_titleid

        if self.tcp_protocol is None:
            _LOGGER.debug("Start Title failed: TCP Protocol does not exist")

            # Queue task upon login.
            task = ('start_title', title_id, running_id)
            self.task_queue = task
            _LOGGER.info(
                "Queuing Command: Start Title: title_id=%s, running_id=%s",
                title_id, running_id)
            if self.is_standby:
                self.wakeup()
            elif self.is_running:
                await self.async_connect()

        if self.tcp_protocol is not None:
            await self.tcp_protocol.start_title(title_id, running_id)
            _LOGGER.debug(
                "Command: Start Title: title_id=%s, running_id=%s",
                title_id, running_id)

    async def remote_control(
            self, button_name: str, hold_time: Optional[int] = 0):
        """Send remote control command packet. Is coroutine.

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
            _LOGGER.debug("Remote Control failed: TCP Protocol does not exist")

            # Queue task upon login.
            task = ('remote_control', operation, hold_time)
            self.task_queue = task
            _LOGGER.info(
                "Queuing Command: Remote Control: button=%s",
                button_name)
            if self.is_standby:
                self.wakeup()
            elif self.is_running:
                await self.async_connect()

        if self.tcp_protocol is not None:
            await self.tcp_protocol.remote_control(operation, hold_time)
            _LOGGER.debug(
                "Command: Remote Control: button=%s",
                button_name)

    async def close(self):
        """Close Connection."""
        self._close()
        _LOGGER.debug("Closing PS4 TCP connection")

    def _close(self):
        """Close Transport."""
        if self.tcp_protocol is not None:
            self.tcp_protocol.disconnect()

    def _closed(self):
        """Callback function called by protocol connection lost."""
        if self.tcp_protocol is None:
            _LOGGER.info("TCP Protocol @ %s already disconnected", self.host)
        self.tcp_transport = None
        self.tcp_protocol = None
        self.loggedin = False
        self._connected = False

    async def async_connect(self, auto_login: Optional[bool] = True):
        """Connect.

        :param auto_login: If true will login automatically if powering on.
        """
        if not self._connected:
            if self.status is None and self.ddp_protocol is not None:
                self.get_status()
            if not self.is_available:
                raise NotReady(
                    "PS4 is not available or powered off. Check connection.")
            if not self._power_off:  # If not powering off
                if self.is_standby:
                    raise NotReady("PS4 is not On")
                try:
                    _LOGGER.debug("Attempting connection with PS4")
                    self._prepare_connection()
                    tcp_transport, tcp_protocol =\
                        await self.connection.async_connect(self)
                except (OSError, ConnectionRefusedError):
                    _LOGGER.info("PS4 Refused Connection")
                    self._connected = False
                    self.loggedin = False
                else:
                    self.tcp_transport = tcp_transport
                    self.tcp_protocol = tcp_protocol
                    self._connected = True
                    if self._power_on:  # If powering on
                        if auto_login:
                            await self.login()
                    self._power_on = False

    @property
    def login_delay(self) -> int:
        """Return login delay value."""
        return self._login_delay
