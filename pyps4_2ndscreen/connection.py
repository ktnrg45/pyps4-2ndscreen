# -*- coding: utf-8 -*-
"""TCP Connection Handling for PS4."""

import binascii
import logging
import socket
import time
import asyncio
from typing import cast, Optional, Union

from construct import (Bytes, Const, Int32ul, Padding, Struct, Container)
from Cryptodome.Cipher import AES, PKCS1_OAEP
from Cryptodome.PublicKey import RSA

_LOGGER = logging.getLogger(__name__)

TIMEOUT = 5
PS_DELAY = 0.5
DEFAULT_LOGIN_DELAY = 1
DEFAULT_HEARTBEAT_TIMEOUT = 15
TCP_PORT = 997

STATUS_REQUEST = \
    b'\x0c\x00\x00\x00\x12\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
RANDOM_SEED = \
    b'\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

PUBLIC_KEY = (
    '-----BEGIN PUBLIC KEY-----\n'
    'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxfAO/MDk5ovZpp7xlG9J\n'
    'JKc4Sg4ztAz+BbOt6Gbhub02tF9bryklpTIyzM0v817pwQ3TCoigpxEcWdTykhDL\n'
    'cGhAbcp6E7Xh8aHEsqgtQ/c+wY1zIl3fU//uddlB1XuipXthDv6emXsyyU/tJWqc\n'
    'zy9HCJncLJeYo7MJvf2TE9nnlVm1x4flmD0k1zrvb3MONqoZbKb/TQVuVhBv7SM+\n'
    'U5PSi3diXIx1Nnj4vQ8clRNUJ5X1tT9XfVmKQS1J513XNZ0uYHYRDzQYujpLWucu\n'
    'ob7v50wCpUm3iKP1fYCixMP6xFm0jPYz1YQaMV35VkYwc40qgk3av0PDS+1G0dCm\n'
    'swIDAQAB\n'
    '-----END PUBLIC KEY-----')


def _get_public_key_rsa() -> RSA.RsaKey:
    """Return RSA Key."""
    key = RSA.importKey(PUBLIC_KEY)
    return key.publickey()


def _handle_response(command: str, msg: bytes) -> bool:
    """Return Pass/Fail for sent message.

    :param command: command to handle
    :param msg: Msg received
    """
    pass_response = {
        'send_status': [18],
        'remote_control': [18],  # Not right
        'start_title': [11, 18],  # 18 Not right
        'standby': [27],
        'login': [0, 17]
    }
    if command is not None:
        _LOGGER.debug("Handling command: %s", command)
        if command == 'login':
            response_byte = msg[8]
            if response_byte in pass_response['login']:
                _LOGGER.debug("Login Successful")
                return True
            _LOGGER.debug("Login Failed")
            return False

        response_byte = msg[4]
        _LOGGER.debug("RECV: %s for Command: %s", response_byte, command)
        if response_byte not in pass_response[command]:
            _LOGGER.warning("Command: %s Failed", command)
            return False
    return True


def _get_hello_request() -> bytes:
    """Return hello request packet."""
    fmt = Struct(
        'length' / Const(b'\x1c\x00\x00\x00'),
        'type' / Const(b'\x70\x63\x63\x6f'),
        'version' / Const(b'\x00\x00\x02\x00'),
        'dummy' / Padding(16),
    )

    msg = fmt.build({})
    return msg


def _parse_hello_request(msg: bytes) -> Container:
    """Parse hello response packet."""
    fmt = Struct(
        'length' / Int32ul,
        'type' / Int32ul,
        'version' / Int32ul,
        'dummy' / Bytes(8),
        'seed' / Bytes(16),
    )

    data = fmt.parse(msg)
    return data


def _get_handshake_request(seed: bytes) -> bytes:
    """Return handshake request from received seed."""
    fmt = Struct(
        'length' / Const(b'\x18\x01\x00\x00'),
        'type' / Const(b'\x20\x00\x00\x00'),
        'key' / Bytes(256),
        'seed' / Bytes(16),
    )

    recipient_key = _get_public_key_rsa()
    cipher_rsa = PKCS1_OAEP.new(recipient_key)
    key = cipher_rsa.encrypt(RANDOM_SEED)

    _LOGGER.debug('key %s', binascii.hexlify(key))

    msg = fmt.build({'key': key, 'seed': seed})
    return msg


def _get_login_request(
        credential: str, name: str, pin: Optional[str] = '') -> bytes:
    """Return Login Request.

    :param credential: 64 char sha256 hash of PSN account ID
    :param name: Name that will be used for model and app_label
    :param pin: 8 digit pin as str
    """
    fmt = Struct(
        'length' / Const(b'\x80\x01\x00\x00'),
        'type' / Const(b'\x1e\x00\x00\x00'),
        'pass_code' / Const(b'\x00\x00\x00\x00'),
        'magic_number' / Const(b'\x01\x02\x00\x00'),
        'account_id' / Bytes(64),
        'app_label' / Bytes(256),
        'os_version' / Bytes(16),
        'model' / Bytes(16),
        'pin_code' / Bytes(16),
    )

    pin = pin.encode()
    name = name.encode()

    config = {
        # This label appears in the notification when logging in.
        'app_label': name.ljust(256, b'\x00'),
        'account_id': credential.encode().ljust(64, b'\x00'),
        'os_version': b'4.4'.ljust(16, b'\x00'),
        # Used when linking, will be the name of device in settings.
        'model': name.ljust(16, b'\x00'),
        'pin_code': pin.ljust(16, b'\x00'),
    }

    _LOGGER.debug('config %s', config)

    msg = fmt.build(config)
    return msg


def _get_standby_request() -> bytes:
    """Return standby packet."""
    fmt = Struct(
        'length' / Const(b'\x08\x00\x00\x00'),
        'type' / Const(b'\x1a\x00\x00\x00'),
        'dummy' / Padding(8),
    )

    msg = fmt.build({})
    return msg


def _get_boot_request(title_id: str) -> bytes:
    """Return boot packet.

    :param title_id: Title ID to boot; CUSA00000
    """
    fmt = Struct(
        'length' / Const(b'\x18\x00\x00\x00'),
        'type' / Const(b'\x0a\x00\x00\x00'),
        'title_id' / Bytes(16),
        'dummy' / Padding(8),
    )

    msg = fmt.build({'title_id': title_id.encode().ljust(16, b'\x00')})
    return msg


def _get_remote_control_request(operation: int, hold_time: int) -> list:
    """Return list of remote control command packets.

    :param operation: Operation to perform
    :param hold_time: Time to hold in millis
    """
    msg = []
    # Prebuild required remote messages.

    if operation == 128:
        msg.append(_get_remote_control_msg(operation, 0))
        msg.append(_get_remote_control_msg(operation, hold_time))

    else:
        msg.append(_get_remote_control_msg(operation, hold_time))
        msg.append(_get_remote_control_key_off_request())

    return msg


def _get_remote_control_msg(operation: int, hold_time: int) -> bytes:
    """Return remote control command msg."""
    fmt = Struct(
        'length' / Const(b'\x10\x00\x00\x00'),
        'type' / Const(b'\x1c\x00\x00\x00'),
        'op' / Int32ul,
        'hold_time' / Int32ul,
    )

    msg = fmt.build({'op': operation, 'hold_time': hold_time})
    return msg


def _get_remote_control_open_request() -> bytes:
    """Return RC Open packet."""
    msg = _get_remote_control_msg(1024, 0)
    return msg


def _get_remote_control_close_request() -> bytes:
    """Return RC Close packet."""
    msg = _get_remote_control_msg(2048, 0)
    return msg


def _get_remote_control_key_off_request(hold_time: Optional[int] = 0) -> bytes:
    """Return RC Key Off Packet."""
    msg = _get_remote_control_msg(256, hold_time)
    return msg


def _get_status_ack() -> bytes:
    """Return Status Ack packet."""
    fmt = Struct(
        'length' / Const(b'\x0c\x00\x00\x00'),
        'type' / Const(b'\x14\x00\x00\x00'),
        'status' / Const(b'\x00\x00\x00\x00'),
        'dummy' / Padding(4),
    )

    msg = fmt.build({})
    return msg


class BaseConnection():
    """The TCP connection class.

    Represents a connection to a PS4 Device.
    :param ps4: PS4 object to attach to.
    :param credential: PSN credentials to use.
    :param port: Remote port to connect to.
    """

    def __init__(
            self, ps4, credential: Optional[str] = None,
            port: Optional[int] = 997):
        """Init Class."""
        self.ps4 = ps4
        self._host = ps4.host
        self._credential = credential
        self._port = port
        self._socket = None
        self._cipher = None
        self._decipher = None
        self._random_seed = None
        self.pin = None

    def set_socket(self, sock: socket.socket):
        """Set socket."""
        self._socket = sock

    def _set_crypto_init_vector(self, init_vector: bytes):
        self._cipher = AES.new(RANDOM_SEED, AES.MODE_CBC, init_vector)
        self._decipher = AES.new(RANDOM_SEED, AES.MODE_CBC, init_vector)

    def _reset_crypto_init_vector(self):
        self._cipher = None
        self._decipher = None

    def encrypt_message(self, msg: bytes):
        """Encrypt message."""
        data = self._cipher.encrypt(msg)
        return data


class LegacyConnection(BaseConnection):
    """Legacy Connection for Legacy PS4 object."""

    # noqa: pylint: disable=no-self-use
    def _delay(self, seconds: Union[float, int]):
        """Delay in seconds."""
        start_time = time.time()
        while time.time() - start_time < seconds:
            pass

    def connect(self):
        """Open the connection."""
        _LOGGER.debug('Connect')
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self._host, self._port))
        self._send_hello_request()
        data = self._recv_hello_request()
        self._set_crypto_init_vector(data.seed)
        self._send_handshake_request(data.seed)

    def disconnect(self):
        """Close the connection."""
        self._socket.close()
        self._reset_crypto_init_vector()

    def login(self, pin: str):
        """Login."""
        _LOGGER.debug('Login')
        self._send_login_request(pin=pin)
        msg = self._recv_msg()
        response = _handle_response('login', msg)
        return response

    def standby(self):
        """Request standby."""
        _LOGGER.debug('Request standby')
        self._send_standby_request()
        msg = self._recv_msg()
        return _handle_response('standby', msg)

    def start_title(self, title_id: str):
        """Start an application/game title."""
        _LOGGER.debug('Start title: %s', title_id)
        self._send_boot_request(title_id)
        msg = self._recv_msg()
        return _handle_response('start_title', msg)

    def remote_control(self, operation: int, hold_time: Optional[int] = 0):
        """Send remote control command."""
        _LOGGER.debug('Remote control: %s (%s)', operation, hold_time)
        return self._send_remote_control_request(operation, hold_time)

    def send_status(self):
        """Send client connection status."""
        _LOGGER.debug('Sending Status: Connected')
        self._send_status_ack()
        return True

    def _send_msg(self, msg: bytes, encrypted: Optional[bool] = False):
        _LOGGER.debug('TX: %s %s', len(msg), binascii.hexlify(msg))
        if encrypted:
            msg = self.encrypt_message(msg)
        try:
            self._socket.send(msg)
        except BrokenPipeError:
            _LOGGER.error("Connection error")
            self.ps4.close()

    def _recv_msg(self, decrypt: Optional[bool] = True):
        msg = self._socket.recv(1024)
        if decrypt:
            msg = self._decipher.decrypt(msg)
        _LOGGER.debug('RX: %s %s', len(msg), binascii.hexlify(msg))
        return msg

    def _send_hello_request(self):
        """Send SYN Message."""
        self._send_msg(_get_hello_request())

    def _recv_hello_request(self):
        """Receive ACK."""
        msg = self._recv_msg(decrypt=False)
        data = _parse_hello_request(msg)
        return data

    def _send_handshake_request(self, seed: bytes):
        """Finish handshake."""
        self._send_msg(_get_handshake_request(seed))

    def _send_login_request(self, pin: str):
        name = self.ps4.device_name
        msg = _get_login_request(self._credential, name, pin)
        self._send_msg(msg, encrypted=True)

    def _send_standby_request(self):
        self._send_msg(_get_standby_request(), encrypted=True)

    def _send_boot_request(self, title_id: str):
        self._send_msg(_get_boot_request(title_id), encrypted=True)

    def _send_remote_control_request(
            self, operation: int, hold_time: Optional[int] = 0):
        # Prebuild required remote messages."""
        msg = _get_remote_control_request(operation, hold_time)

        try:
            # Open RC
            self._send_msg(
                _get_remote_control_open_request(), encrypted=True)
            for message in msg:
                self._send_msg(message, encrypted=True)

            # Delay Close RC for PS
            if operation == 128:
                self._delay(DEFAULT_LOGIN_DELAY)
                self._send_msg(
                    _get_remote_control_key_off_request(),
                    encrypted=True)

        except (socket.error, socket.timeout):
            _LOGGER.debug("Failed to send Remote MSG")
            return False
        return True

    def _send_status_ack(self):
        """Send ACK for connection status."""
        self._send_msg(_get_status_ack(), encrypted=True)


class AsyncConnection(BaseConnection):
    """Connection using Asyncio."""

    async def async_connect(self, ps4):
        """Create asyncio TCP connection.

        :param ps4: :class: PS4Async Object to attach to.
        """
        loop = asyncio.get_event_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        await self._async_tcp_handshake(sock, loop)
        connect = loop.create_connection(
            lambda: TCPProtocol(ps4, loop), sock=sock)
        transport, protocol = await loop.create_task(connect)
        self.set_socket(protocol)
        return transport, protocol

    async def _async_tcp_handshake(self, sock: socket.socket, loop):
        """Perform TCP Handshake.
        :param sock: :class: socket.socket to use.
        :param loop: Asyncio Loop to use in.
        """
        await loop.sock_connect(sock, (self._host, TCP_PORT))
        msg = _get_hello_request()
        await loop.sock_sendall(sock, msg)
        response = await loop.sock_recv(sock, 1024)
        data = _parse_hello_request(response)
        self._set_crypto_init_vector(data.seed)
        msg = _get_handshake_request(data.seed)
        await loop.sock_sendall(sock, msg)


class TCPProtocol(asyncio.Protocol):
    """Asyncio TCP Protocol.

    :param ps4: :class: PS4Async Object to attach to.
    :param loop: Asyncio Loop to use in.
    """

    def __init__(self, ps4, loop):
        """Init."""
        self.loop = loop
        self.ps4 = ps4
        self._host = ps4.host
        self.callback = _handle_response
        self.transport = None
        self.connection = ps4.connection
        self.task = None
        self.task_available = asyncio.Event()
        self.login_success = asyncio.Event()
        self.ps_delay = PS_DELAY
        self.heartbeat_timeout = DEFAULT_HEARTBEAT_TIMEOUT
        self._last_heartbeat = None
        self._hb_handler = None

    def connection_made(self, transport: asyncio.Transport):
        """When connected.

        :param transport: asyncio.Transport class
        """
        self.transport = cast(asyncio.Transport, transport)
        self.ps4.connected = True
        _LOGGER.debug("PS4 Transport Connected @ %s", self.ps4.host)

        if self.ps4.task_queue is not None:
            valid_initial_tasks = {'start_title': self.start_title,
                                   "remote_control": self.remote_control}
            args = None
            initial_task = self.ps4.task_queue
            self.ps4.task_queue = None
            args = initial_task[1:]
            initial_task = initial_task[0]
            task = valid_initial_tasks.get(initial_task)
            if task is not None:
                _LOGGER.info("Queued command: %s", initial_task)
                self.task_available.set()
                asyncio.ensure_future(task(*args))
        else:
            self.task_available.set()

    def data_received(self, data: bytes):
        """Call when data received.

        :param data: Bytes Received.
        """
        data = self.connection._decipher.decrypt(data)  # noqa: pylint: disable=protected-access
        self._handle(data)

    def connection_lost(self, exc: Exception):
        """Call if connection lost.

        :param exc: Exception
        """
        if self._hb_handler is not None:
            self._hb_handler.cancel()
        self.ps4._closed()  # noqa: pylint: disable=protected-access
        self.ps4 = None
        self.connection = None

    def _complete_task(self):
        """Complete task/signal done."""
        self.task = None
        self.task_available.set()

    async def add_task(self, task_name: str, func: callable, *args: tuple):
        """Add task to queue.

        :param task_name: Name of task
        :param func: Callable to call
        :param args: Tuple of args to pass
        """
        task = func(*args)

        await self.task_available.wait()
        self.task_available.clear()
        self.task = task_name
        await task

    async def send(self, msg: bytes):
        """Send Message.

        :param msg: Message to send.
        """
        _LOGGER.debug('TX: %s %s', len(msg), binascii.hexlify(msg))
        msg = self.connection.encrypt_message(msg)
        self.transport.write(msg)

    def sync_send(self, msg: bytes):
        """Send Message synchronously.

        :param msg: Message to send.
        """
        _LOGGER.debug('TX: %s %s', len(msg), binascii.hexlify(msg))
        msg = self.connection.encrypt_message(msg)
        self.transport.write(msg)

    def _handle(self, data: bytes):
        """Handle messages received.

        :param data: Message to handle.
        """
        _LOGGER.debug('RX: %s %s', len(data), binascii.hexlify(data))
        if data == STATUS_REQUEST:
            asyncio.ensure_future(self._ack_status())
        elif self.task != 'remote_control':
            success = self.callback(self.task, data)
            if success:
                _LOGGER.debug("Command successful: %s", self.task)
                if self.task == 'login':
                    self.ps4.loggedin = True
                    self.login_success.set()
            else:
                if self.task == 'login':
                    self.ps4.loggedin = False
                    _LOGGER.error("Failed to login, Closing connection")
                    self.disconnect()
            self._complete_task()

    async def login(
            self,
            pin: Optional[str] = '',
            power_on: Optional[bool] = False,
            delay: Optional[int] = DEFAULT_LOGIN_DELAY):
        """Send Login Command.

        :param pin: Pin to use for linking.
        :param power_on: True if powering on from standby.
        :param delay: Delay to wait after logging in.
        """
        if not self.task == 'login':  # Only schedule one login task.
            self.login_success.clear()
            task_name = 'login'
            msg = _get_login_request(
                self.ps4.credential, self.ps4.device_name, pin)
            task = self.add_task(task_name, self.send, msg)  # noqa: pylint: disable=assignment-from-no-return
            await task
            await self.login_success.wait()
            await asyncio.sleep(delay)

            self.sync_send(_get_remote_control_open_request())  # Open RC
            # If not powering on, Send PS to switch user screens.
            if not power_on:
                msg = _get_remote_control_request(128, 0)
                self._send_remote_control_request_sync(msg, 128)

            # Delay to allow time to login/switch users.
            await asyncio.sleep(delay)
        else:
            _LOGGER.debug("Login Task already scheduled")

    async def standby(self):
        """Send Standby Command."""
        if not self.ps4.loggedin:
            await self.login()
        task_name = 'standby'
        msg = _get_standby_request()
        task = self.add_task(task_name, self.send, msg)  # noqa: pylint: disable=assignment-from-no-return
        asyncio.ensure_future(task)

    def disconnect(self):
        """Close the connection."""
        if self.transport is not None:
            self.transport.close()
            self.transport = None
            _LOGGER.debug("Transport @ %s is disconnected", self.ps4.host)
        self.connection._reset_crypto_init_vector()  # noqa: pylint: disable=protected-access

    async def start_title(
            self, title_id: str, running_id: Optional[str] = None):
        """Send Start Title Command.

        :param title_id: Title Id to boot.
        :param running_id: Title Id of running title.
        """
        if not self.ps4.loggedin:
            await self.login()
        task_name = 'start_title'
        msg = _get_boot_request(title_id)
        task = self.add_task(task_name, self.send, msg)  # noqa: pylint: disable=assignment-from-no-return
        asyncio.ensure_future(task)

        await self.task_available.wait()
        if running_id is not None and running_id != title_id:
            msg = _get_remote_control_request(16, 0)
            self.loop.call_later(
                1.0, self._send_remote_control_request_sync, msg, 16)

    async def remote_control(
            self, operation: int, hold_time: Optional[str] = 0):
        """Send Remote Control Command.

        :param operation: Operation to perform.
        :param hold_time: Time to hold in millis.
        """
        if not self.ps4.loggedin:
            await self.login()
        task_name = 'remote_control'
        msg = _get_remote_control_request(operation, hold_time)
        task = self.add_task(task_name, self._send_remote_control_request,  # noqa: pylint: disable=assignment-from-no-return
                             msg, operation, hold_time)
        asyncio.ensure_future(task)

    async def _send_remote_control_request(
            self, msg: list, operation: int, hold_time: Optional[str] = 0):
        """Send messages for remote control.

        :param msg: Messages to send
        :param operation: Operation to perform.
        :param hold_time: Time to hold in millis.
        """
        self._send_remote_control_request_sync(msg, operation, hold_time)

    def _send_remote_control_request_sync(
            self, msg: list, operation: int, hold_time: Optional[str] = 0):
        """Sync Wrapper for Remote Control.

        :param msg: Messages to send
        :param operation: Operation to perform.
        :param hold_time: Time to hold in millis.
        """
        for message in msg:
            # Messages are time sensitive.
            # Needs to be immediately sent in order.
            self.sync_send(message)

        # For 'PS' command.
        if operation == 128:

            # PS tap is unreliable/needs specific delay?
            if hold_time == 0:
                ps_delay = self.ps_delay

            # Delay for PS hold.
            else:
                ps_delay = 1

            # End command using key_off.
            self.loop.call_later(
                ps_delay, self.sync_send,
                _get_remote_control_key_off_request()
            )
            self.loop.call_later(
                ps_delay, self._complete_task)
        else:
            # Don't handle or wait for a response
            self._complete_task()

    async def _ack_status(self):
        """Sends msg in response to heartbeat message."""
        # Update state as well, no need to manage polling now.
        self._last_heartbeat = time.time()
        self.ps4.get_status()
        self.sync_send(_get_status_ack())
        _LOGGER.debug("Sending Hearbeat response")
        self._hb_handler = self.loop.create_task(self._check_heartbeat())

    async def _check_heartbeat(self):
        """Check if heartbeat msg is overdue and schedule next check."""
        await asyncio.sleep(self.heartbeat_timeout)
        hb_delta = self.heartbeat_delta
        if hb_delta is not None:
            _LOGGER.debug("Heartbeat Delta: %s", hb_delta)
            if hb_delta > self.heartbeat_timeout:
                _LOGGER.warning(
                    "Timed out waiting for PS4 heartbeat status; Closing...")
                self.ps4._close()  # noqa: pylint: disable=protected-access

    @property
    def heartbeat_delta(self) -> float:
        """Return time delta in seconds from last hearbeat."""
        if self._last_heartbeat is None:
            return None
        return time.time() - self._last_heartbeat
