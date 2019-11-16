# -*- coding: utf-8 -*-
"""TCP Handling for PS4."""
from __future__ import print_function

import binascii
import logging
import socket
import time
import asyncio
from typing import cast

from construct import (Bytes, Const, Int32ul, Padding, Struct)
from Cryptodome.Cipher import AES, PKCS1_OAEP
from Cryptodome.PublicKey import RSA

_LOGGER = logging.getLogger(__name__)

TCP_PORT = 997
STATUS_REQUEST = \
    b'\x0c\x00\x00\x00\x12\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
RANDOM_SEED = \
    b'\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
TIMEOUT = 5
PS_DELAY = 1

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


def _get_public_key_rsa():
    """Get RSA Key."""
    key = RSA.importKey(PUBLIC_KEY)
    return key.publickey()


def _handle_response(command, msg):
    """Return Pass/Fail for sent message."""
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
        if command == 'send_status':
            return True

        response_byte = msg[4]
        _LOGGER.debug("RECV: %s for Command: %s", response_byte, command)
        if response_byte not in pass_response[command]:
            _LOGGER.warning("Command: %s Failed", command)
            return False
    return True


def _get_hello_request():
    fmt = Struct(
        'length' / Const(b'\x1c\x00\x00\x00'),
        'type' / Const(b'\x70\x63\x63\x6f'),
        'version' / Const(b'\x00\x00\x02\x00'),
        'dummy' / Padding(16),
    )

    msg = fmt.build({})
    return msg


def _parse_hello_request(msg):
    fmt = Struct(
        'length' / Int32ul,
        'type' / Int32ul,
        'version' / Int32ul,
        'dummy' / Bytes(8),
        'seed' / Bytes(16),
    )

    data = fmt.parse(msg)
    return data


def _get_handshake_request(seed):
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


def _get_login_request(credential, name=None, pin=None):
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

    if pin is None:
        pin = b''
    else:
        pin = pin.encode()

    name = name.encode()

    config = {
        'app_label': b'PlayStation'.ljust(256, b'\x00'),
        'account_id': credential.encode().ljust(64, b'\x00'),
        'os_version': b'4.4'.ljust(16, b'\x00'),
        'model': name.ljust(16, b'\x00'),
        'pin_code': pin.ljust(16, b'\x00'),
    }

    _LOGGER.debug('config %s', config)

    msg = fmt.build(config)
    return msg


def _get_standby_request():
    fmt = Struct(
        'length' / Const(b'\x08\x00\x00\x00'),
        'type' / Const(b'\x1a\x00\x00\x00'),
        'dummy' / Padding(8),
    )

    msg = fmt.build({})
    return msg


def _get_boot_request(title_id):
    fmt = Struct(
        'length' / Const(b'\x18\x00\x00\x00'),
        'type' / Const(b'\x0a\x00\x00\x00'),
        'title_id' / Bytes(16),
        'dummy' / Padding(8),
    )

    msg = fmt.build({'title_id': title_id.encode().ljust(16, b'\x00')})
    return msg


def _get_remote_control_request(operation, hold_time) -> list:
    fmt = Struct(
        'length' / Const(b'\x10\x00\x00\x00'),
        'type' / Const(b'\x1c\x00\x00\x00'),
        'op' / Int32ul,
        'hold_time' / Int32ul,
    )
    # Prebuild required remote messages."""
    msg = []
    if operation != 128:
        msg.append(fmt.build({'op': 1024, 'hold_time': 0}))  # Open RC
        msg.append(fmt.build({'op': operation, 'hold_time': hold_time}))
        msg.append(fmt.build({'op': 256, 'hold_time': 0}))  # Key Off
        msg.append(fmt.build({'op': 2048, 'hold_time': 0}))  # Close RC
    else:  # PS
        msg.append(fmt.build({'op': 1024, 'hold_time': 0}))  # Open RC
        msg.append(fmt.build({'op': operation, 'hold_time': hold_time}))
        msg.append(fmt.build({'op': operation, 'hold_time': 1}))
        msg.append(fmt.build({'op': 256, 'hold_time': 0}))  # Key Off

    return msg


def _get_remote_control_open_request():
    fmt = Struct(
        'length' / Const(b'\x10\x00\x00\x00'),
        'type' / Const(b'\x1c\x00\x00\x00'),
        'op' / Int32ul,
        'hold_time' / Int32ul,
    )

    msg = fmt.build({'op': 1024, 'hold_time': 0})  # open RC
    return msg


def _get_remote_control_close_request():
    fmt = Struct(
        'length' / Const(b'\x10\x00\x00\x00'),
        'type' / Const(b'\x1c\x00\x00\x00'),
        'op' / Int32ul,
        'hold_time' / Int32ul,
    )

    msg = fmt.build({'op': 2048, 'hold_time': 0})  # Close RC
    return msg


def _get_status_ack():
    fmt = Struct(
        'length' / Const(b'\x0c\x00\x00\x00'),
        'type' / Const(b'\x14\x00\x00\x00'),
        'status' / Const(b'\x00\x00\x00\x00'),
        'dummy' / Padding(4),
    )

    msg = fmt.build({})
    return msg


class BaseConnection():
    """The TCP connection class."""

    def __init__(self, ps4, credential=None, port=997):
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

    def set_socket(self, sock):
        """Set socket."""
        self._socket = sock

    def _set_crypto_init_vector(self, init_vector):
        self._cipher = AES.new(RANDOM_SEED, AES.MODE_CBC, init_vector)
        self._decipher = AES.new(RANDOM_SEED, AES.MODE_CBC, init_vector)

    def _reset_crypto_init_vector(self):
        self._cipher = None
        self._decipher = None

    def encrypt_message(self, msg):
        """Encrypt message."""
        data = self._cipher.encrypt(msg)
        return data


class LegacyConnection(BaseConnection):
    """Legacy Connection for Legacy PS4 object."""

    # noqa: pylint: disable=no-self-use
    def delay(self, seconds):
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

    def login(self, pin=None):
        """Login."""
        _LOGGER.debug('Login')
        self._send_login_request(pin=pin)
        msg = self._recv_msg()
        return _handle_response('login', msg)

    def standby(self):
        """Request standby."""
        _LOGGER.debug('Request standby')
        self._send_standby_request()
        msg = self._recv_msg()
        return _handle_response('standby', msg)

    def start_title(self, title_id):
        """Start an application/game title."""
        _LOGGER.debug('Start title: %s', title_id)
        self._send_boot_request(title_id)
        msg = self._recv_msg()
        return _handle_response('start_title', msg)

    def remote_control(self, operation, hold_time=0):
        """Send remote control command."""
        _LOGGER.debug('Remote control: %s (%s)', operation, hold_time)
        return self._send_remote_control_request(operation, hold_time)

    def send_status(self):
        """Send client connection status."""
        _LOGGER.debug('Sending Status: Connected')
        self._send_status_ack()
        msg = self._recv_msg()
        return _handle_response('send_status', msg)

    def _send_msg(self, msg, encrypted=False):
        _LOGGER.debug('TX: %s %s', len(msg), binascii.hexlify(msg))
        if encrypted:
            msg = self.encrypt_message(msg)
        self._socket.send(msg)

    def _recv_msg(self, decrypt=True):
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
        if msg is not None:
            data = _parse_hello_request(msg)
            return data
        return None

    def _send_handshake_request(self, seed):
        """Finish handshake."""
        self._send_msg(_get_handshake_request(seed))

    def _send_login_request(self, pin=None):
        name = self.ps4.device_name
        msg = _get_login_request(self._credential, name, pin)
        self._send_msg(msg, encrypted=True)

    def _send_standby_request(self):
        self._send_msg(_get_standby_request(), encrypted=True)

    def _send_boot_request(self, title_id):
        self._send_msg(_get_boot_request(title_id), encrypted=True)

    def _send_remote_control_request(self, operation, hold_time=0):
        # Prebuild required remote messages."""
        msg = _get_remote_control_request(operation, hold_time)

        for message in msg:
            try:
                self._send_msg(message, encrypted=True)
            except (socket.error, socket.timeout):
                _LOGGER.debug("Failed to send Remote MSG")

        # Delay Close RC for PS
        if operation == 128:
            _LOGGER.debug("Delaying RC off for PS Command")
            self.delay(1)
            try:
                self._send_msg(
                    _get_remote_control_request(operation, hold_time),
                    encrypted=True)
            except (socket.error, socket.timeout):
                _LOGGER.debug("Failed to send Remote Close MSG")

    def _send_status_ack(self):
        """Send ACK for connection status."""
        self._send_msg(_get_status_ack(), encrypted=True)


class AsyncConnection(BaseConnection):
    """Connection using Asyncio."""

    async def async_connect(self, ps4):
        """Create asyncio TCP connection."""
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

    async def _async_tcp_handshake(self, sock, loop):
        await loop.sock_connect(sock, (self._host, TCP_PORT))
        msg = _get_hello_request()
        await loop.sock_sendall(sock, msg)
        response = await loop.sock_recv(sock, 1024)
        data = _parse_hello_request(response)
        self._set_crypto_init_vector(data.seed)
        msg = _get_handshake_request(data.seed)
        await loop.sock_sendall(sock, msg)


class TCPProtocol(asyncio.Protocol):
    """Asyncio TCP Protocol."""

    def __init__(self, ps4, loop):
        """Init."""
        self.loop = loop
        self.ps4 = ps4
        self.callback = _handle_response
        self.transport = None
        self.connection = ps4.connection
        self.task = None
        self.task_available = asyncio.Event()
        self.login_success = asyncio.Event()
        self.ps_delay = None

    def connection_made(self, transport):
        """When connected."""
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
                if args is not None:
                    asyncio.ensure_future(task(*args))
                else:
                    asyncio.ensure_future(task())
        else:
            self.task_available.set()

    def data_received(self, data):
        """Call when data received."""
        data = self.connection._decipher.decrypt(data)  # noqa: pylint: disable=protected-access
        self._handle(data)

    def connection_lost(self, exc):
        """Call if connection lost."""
        self.ps4._closed()  # noqa: pylint: disable=protected-access

    def _complete_task(self):
        self.task = None
        self.task_available.set()

    async def add_task(self, task_name, func, *args):
        """Add task to queue."""
        if args:
            task = func(*args)
        else:
            task = func()

        await self.task_available.wait()
        self.task_available.clear()
        self.task = task_name
        await task

    async def send(self, msg):
        """Send Message."""
        _LOGGER.debug('TX: %s %s', len(msg), binascii.hexlify(msg))
        msg = self.connection.encrypt_message(msg)
        self.transport.write(msg)

    def sync_send(self, msg):
        """Send Message synchronously."""
        _LOGGER.debug('TX: %s %s', len(msg), binascii.hexlify(msg))
        msg = self.connection.encrypt_message(msg)
        self.transport.write(msg)

    def _handle(self, data):
        _LOGGER.debug('RX: %s %s', len(data), binascii.hexlify(data))
        if data == STATUS_REQUEST:
            if self.task != 'send_status':
                task = self.add_task('send_status', self._ack_status)  # noqa: pylint: disable=assignment-from-no-return
                asyncio.ensure_future(task)
        elif self.task == 'remote_control':
            pass
        else:
            success = self.callback(self.task, data)
            if success:
                _LOGGER.debug("Command successful: %s", self.task)
                if self.task == 'login':
                    self.ps4.loggedin = True
                    self.login_success.set()
                self._complete_task()
            else:
                if self.task == 'login':
                    self.ps4.loggedin = False
                    _LOGGER.info("Failed to login, Closing connection")
                    self.disconnect()

    async def login(self, pin=None, power_on=False, delay=2):
        """Login."""
        if not self.task == 'login':  # Only schedule one login task.
            self.login_success.clear()
            task_name = 'login'
            name = self.ps4.device_name
            msg = _get_login_request(self.ps4.credential, name, pin)
            task = self.add_task(task_name, self.send, msg)  # noqa: pylint: disable=assignment-from-no-return
            await task
            await self.login_success.wait()
            await asyncio.sleep(delay)

            # If not powering on, Send PS to switch user screens.
            if not power_on:
                msg = _get_remote_control_request(128, 0)
                self._send_remote_control_request_sync(msg, 128)

            # Delay to allow time to login/switch users.
            await asyncio.sleep(delay)
        else:
            _LOGGER.debug("Login Task already scheduled")

    async def standby(self):
        """Standby."""
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

    async def start_title(self, title_id, running_id=None):
        """Start Title."""
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

    async def remote_control(self, operation, hold_time=0):
        """Remote Control."""
        if not self.ps4.loggedin:
            await self.login()
        task_name = 'remote_control'
        msg = _get_remote_control_request(operation, hold_time)
        task = self.add_task(task_name, self._send_remote_control_request,  # noqa: pylint: disable=assignment-from-no-return
                             msg, operation)
        asyncio.ensure_future(task)

    async def _send_remote_control_request(self, msg, operation):
        """Send messages for remote control."""
        self._send_remote_control_request_sync(msg, operation)

    def _send_remote_control_request_sync(self, msg, operation):
        """Sync Wrapper for Remote Control."""
        for message in msg:
            # Messages are time sensitive.
            # Needs to be immediately sent in order.
            self.sync_send(message)

        # For 'PS' command.
        if operation == 128:
            # Even more time sensitive. Delay of around 1 Second needed.
            if self.ps_delay is None:
                ps_delay = PS_DELAY
            else:
                ps_delay = self.ps_delay
            self.loop.call_later(
                ps_delay, self.sync_send, _get_remote_control_close_request())
            self.loop.call_later(
                ps_delay, self._complete_task)
        else:
            # Don't handle or wait for a response
            self._complete_task()

    async def _ack_status(self):
        """Sends msg in response to heartbeat message."""
        # Update state as well, no need to manage polling now.
        self.ps4.get_status()
        self.sync_send(_get_status_ack())
        _LOGGER.debug("Sending Hearbeat response")
        self.loop.call_later(0.2, self._complete_task)
