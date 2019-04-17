# -*- coding: utf-8 -*-
"""TCP Handling for PS4."""
from __future__ import print_function

import binascii
import logging
import socket
import time

from construct import (Bytes, Const, Int32ul, Padding, Struct)
from Cryptodome.Cipher import AES, PKCS1_OAEP
from Cryptodome.PublicKey import RSA

_LOGGER = logging.getLogger(__name__)

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
        'remote_control': [18],
        'start_title': [11, 18],
        'standby': [27],
        'login': [0, 17]
    }

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


def delay(seconds):
    """Delay in seconds."""
    start_time = time.time()
    while time.time() - start_time < seconds:
        pass


class Connection():  # noqa: pylint: disable=too-many-instance-attributes
    """The TCP connection class."""

    def __init__(self, host, credential=None, port=997):
        """Init Class."""
        self._host = host
        self._credential = credential.encode()
        self._port = port
        self._socket = None
        self._cipher = None
        self._decipher = None
        self._random_seed = None
        self.pin = None

    def connect(self):
        """Open the connection."""
        _LOGGER.debug('Connect')
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self._host, self._port))
        self._random_seed = \
            b'\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        self._send_hello_request()
        data = self._recv_hello_request()
        self._set_crypto_init_vector(data.seed)
        self._send_handshake_request(data.seed)

    def disconnect(self):
        """Close the connection."""
        self._socket.close()
        self._reset_crypto_init_vector()
        self._random_seed = None

    def login(self, pin=None):
        """Login."""
        _LOGGER.debug('Login')
        if pin is None:
            self._send_login_request()
        else:
            self._send_login_request(pin)
        msg = self._recv_msg()
        msg = self._decipher.decrypt(msg)
        _LOGGER.debug('RX: %s %s', len(msg), binascii.hexlify(msg))
        return _handle_response('login', msg)

    def standby(self):
        """Request standby."""
        _LOGGER.debug('Request standby')
        self._send_standby_request()
        msg = self._recv_msg()
        msg = self._decipher.decrypt(msg)
        _LOGGER.debug('RX: %s %s', len(msg), binascii.hexlify(msg))
        return _handle_response('standby', msg)

    def start_title(self, title_id):
        """Start an application/game title."""
        _LOGGER.debug('Start title: %s', title_id)
        self._send_boot_request(title_id)
        msg = self._recv_msg()
        msg = self._decipher.decrypt(msg)
        _LOGGER.debug('RX: %s %s', len(msg), binascii.hexlify(msg))
        return _handle_response('start_title', msg)

    def remote_control(self, operation, hold_time=0):
        """Send remote control command."""
        _LOGGER.debug('Remote control: %s (%s)', operation, hold_time)
        return self._send_remote_control_request(operation, hold_time)

    def send_status(self):
        """Send client connection status."""
        _LOGGER.debug('Sending Status: Connected')
        self._send_status()
        msg = self._recv_msg()
        msg = self._decipher.decrypt(msg)
        _LOGGER.debug('RX: %s %s', len(msg), binascii.hexlify(msg))
        return _handle_response('send_status', msg)

    def _send_msg(self, msg, encrypted=False):
        _LOGGER.debug('TX: %s %s', len(msg), binascii.hexlify(msg))
        if encrypted:
            msg = self._cipher.encrypt(msg)
        self._socket.send(msg)

    def _recv_msg(self):
        msg = self._socket.recv(1024)
        return msg

    def _set_crypto_init_vector(self, init_vector):
        self._cipher = AES.new(self._random_seed, AES.MODE_CBC, init_vector)
        self._decipher = AES.new(self._random_seed, AES.MODE_CBC, init_vector)

    def _reset_crypto_init_vector(self):
        self._cipher = None
        self._decipher = None

    def _send_hello_request(self):
        fmt = Struct(
            'length' / Const(b'\x1c\x00\x00\x00'),
            'type' / Const(b'\x70\x63\x63\x6f'),
            'version' / Const(b'\x00\x00\x02\x00'),
            'dummy' / Padding(16),
        )

        msg = fmt.build({})
        self._send_msg(msg)

    def _recv_hello_request(self):
        fmt = Struct(
            'length' / Int32ul,
            'type' / Int32ul,
            'version' / Int32ul,
            'dummy' / Bytes(8),
            'seed' / Bytes(16),
        )

        msg = self._recv_msg()
        data = fmt.parse(msg)
        return data

    def _send_handshake_request(self, seed):
        fmt = Struct(
            'length' / Const(b'\x18\x01\x00\x00'),
            'type' / Const(b'\x20\x00\x00\x00'),
            'key' / Bytes(256),
            'seed' / Bytes(16),
        )

        recipient_key = _get_public_key_rsa()
        cipher_rsa = PKCS1_OAEP.new(recipient_key)
        key = cipher_rsa.encrypt(self._random_seed)

        _LOGGER.debug('key %s', binascii.hexlify(key))

        msg = fmt.build({'key': key, 'seed': seed})
        self._send_msg(msg)

    def _send_login_request(self, pin=None):
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
            self.pin = b''
        else:
            self.pin = pin.encode()

        config = {
            'app_label': b'PlayStation'.ljust(256, b'\x00'),
            'account_id': self._credential.ljust(64, b'\x00'),
            'os_version': b'4.4'.ljust(16, b'\x00'),
            'model': b'Home-Assistant'.ljust(16, b'\x00'),
            'pin_code': self.pin.ljust(16, b'\x00'),
        }

        _LOGGER.debug('config %s', config)

        msg = fmt.build(config)
        self._send_msg(msg, encrypted=True)

    def _send_standby_request(self):
        fmt = Struct(
            'length' / Const(b'\x08\x00\x00\x00'),
            'type' / Const(b'\x1a\x00\x00\x00'),
            'dummy' / Padding(8),
        )

        msg = fmt.build({})
        self._send_msg(msg, encrypted=True)

    def _send_boot_request(self, title_id):
        fmt = Struct(
            'length' / Const(b'\x18\x00\x00\x00'),
            'type' / Const(b'\x0a\x00\x00\x00'),
            'title_id' / Bytes(16),
            'dummy' / Padding(8),
        )

        msg = fmt.build({'title_id': title_id.encode().ljust(16, b'\x00')})
        self._send_msg(msg, encrypted=True)

    def _send_remote_control_request(self, operation, hold_time=0):
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

        # Send Messages
        for message in msg:
            try:
                self._send_msg(message, encrypted=True)
            except (socket.error, socket.timeout):
                _LOGGER.debug("Failed to send Remote MSG")
                return False

        # Delay Close RC for PS
        if operation == 128:
            _LOGGER.debug("Delaying RC off for PS Command")
            message = fmt.build({'op': 2048, 'hold_time': 0})  # Close RC
            delay(1)
            try:
                self._send_msg(message, encrypted=True)
            except (socket.error, socket.timeout):
                _LOGGER.debug("Failed to send Remote MSG")
                return False
        return True

    def _send_status(self):
        fmt = Struct(
            'length' / Const(b'\x0c\x00\x00\x00'),
            'type' / Const(b'\x14\x00\x00\x00'),
            'status' / Const(b'\x00\x00\x00\x00'),
            'dummy' / Padding(4),
        )

        msg = fmt.build({})
        self._send_msg(msg, encrypted=True)
