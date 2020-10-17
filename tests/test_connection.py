"""Tests for pyps4_2ndscreen.connection."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from asynctest import CoroutineMock as mock_coro

from pyps4_2ndscreen import connection as c

pytestmark = pytest.mark.asyncio

MOCK_SEED = bytes(
    [
        0x00,
        0x01,
        0x02,
        0x03,
        0x04,
        0x05,
        0x06,
        0x07,
        0x08,
        0x09,
        0x0A,
        0x0B,
        0x0C,
        0x0D,
        0x0E,
        0x0F,
    ]
)

MOCK_HELLO_REQUEST = bytes(
    [
        0x1C,
        0x00,
        0x00,
        0x00,
        0x70,
        0x63,
        0x63,
        0x6F,
        0x00,
        0x00,
        0x02,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
    ]
)

MOCK_STANDBY = bytes(
    [
        0x08,
        0x00,
        0x00,
        0x00,
        0x1A,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
    ]
)


MOCK_LOGIN = bytes(
    [
        0x80,
        0x01,
        0x00,
        0x00,
        0x1E,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x01,
        0x02,
        0x00,
        0x00,
        0x61,
        0x62,
        0x63,
        0x64,
        0x31,
        0x32,
        0x33,
        0x34,
        0x61,
        0x62,
        0x63,
        0x64,
        0x31,
        0x32,
        0x33,
        0x34,
        0x61,
        0x62,
        0x63,
        0x64,
        0x31,
        0x32,
        0x33,
        0x34,
        0x61,
        0x62,
        0x63,
        0x64,
        0x31,
        0x32,
        0x33,
        0x34,
        0x61,
        0x62,
        0x63,
        0x64,
        0x31,
        0x32,
        0x33,
        0x34,
        0x61,
        0x62,
        0x63,
        0x64,
        0x31,
        0x32,
        0x33,
        0x34,
        0x61,
        0x62,
        0x63,
        0x64,
        0x31,
        0x32,
        0x33,
        0x34,
        0x61,
        0x62,
        0x63,
        0x64,
        0x31,
        0x32,
        0x33,
        0x34,
        0x6E,
        0x61,
        0x6D,
        0x65,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x34,
        0x2E,
        0x34,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x6E,
        0x61,
        0x6D,
        0x65,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x31,
        0x32,
        0x33,
        0x34,
        0x35,
        0x36,
        0x37,
        0x38,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
    ]
)


MOCK_STATUS_ACK = bytes(
    [
        0x0C,
        0x00,
        0x00,
        0x00,
        0x14,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
    ]
)


MOCK_BOOT = bytes(
    [
        0x18,
        0x00,
        0x00,
        0x00,
        0x0A,
        0x00,
        0x00,
        0x00,
        0x43,
        0x55,
        0x53,
        0x41,
        0x30,
        0x30,
        0x30,
        0x30,
        0x30,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
    ]
)

MOCK_RC_OPEN = bytes(
    [
        0x10,
        0x00,
        0x00,
        0x00,
        0x1C,
        0x00,
        0x00,
        0x00,
        0x00,
        0x04,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
    ]
)

MOCK_RC_CLOSE = bytes(
    [
        0x10,
        0x00,
        0x00,
        0x00,
        0x1C,
        0x00,
        0x00,
        0x00,
        0x00,
        0x08,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
    ]
)

MOCK_RC_KEY_OFF = bytes(
    [
        0x10,
        0x00,
        0x00,
        0x00,
        0x1C,
        0x00,
        0x00,
        0x00,
        0x00,
        0x01,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
    ]
)

MOCK_RC_KEY_ENTER = bytes(
    [
        0x10,
        0x00,
        0x00,
        0x00,
        0x1C,
        0x00,
        0x00,
        0x00,
        0x00,
        0x10,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
    ]
)

MOCK_HOST = "192.168.0.1"

MOCK_CREDS = "abcd1234abcd1234" "abcd1234abcd1234" "abcd1234abcd1234" "abcd1234abcd1234"

MOCK_PIN = "12345678"
MOCK_NAME = "name"
MOCK_TITLE_ID = "CUSA00000"

MOCK_LOGIN_SUCCESS = bytes(8) + b"\x11"
MOCK_BOOT_SUCCESS = bytes(4) + b"\x0b"
MOCK_STANDBY_SUCCESS = bytes(4) + b"\x1b"


def test_pub_key():
    """Test pub key serialization."""
    pub_len = c._get_public_key_rsa().size_in_bytes()
    assert pub_len == 256


def test_hello_request():
    """Test Hello Request."""
    hello = c._get_hello_request()
    assert hello == MOCK_HELLO_REQUEST


def test_parse_hello_request():
    """Test parsing of hello request."""
    request = bytes(20) + MOCK_SEED
    parsed = c._parse_hello_request(request)
    assert parsed.seed == MOCK_SEED


def test_handshake_request():
    """Test Handshake Request."""
    seed = bytes(16)
    handshake = bytearray(c._get_handshake_request(seed))
    assert len(handshake) == 280
    assert int.from_bytes(handshake[0:4], "little") == 280
    assert handshake[4:8] == b"\x20\x00\x00\x00"
    assert handshake[-16:] == seed


def test_login_request():
    """Test login request."""
    login = c._get_login_request(MOCK_CREDS, MOCK_NAME, MOCK_PIN)
    assert login == MOCK_LOGIN


def test_standby():
    """Test Standby."""
    standby = c._get_standby_request()
    assert standby == MOCK_STANDBY


def test_status_ack():
    """Test status ack."""
    request = c._get_status_ack()
    assert request == MOCK_STATUS_ACK


def test_boot_request():
    """Test boot request."""
    request = c._get_boot_request(MOCK_TITLE_ID)
    assert request == MOCK_BOOT


def test_remote_control():
    """Test remote control."""
    request = c._get_remote_control_open_request()
    assert request == MOCK_RC_OPEN
    request = c._get_remote_control_close_request()
    assert request == MOCK_RC_CLOSE
    request = c._get_remote_control_key_off_request()
    assert request == MOCK_RC_KEY_OFF


def test_wrong_response():
    """Test wrong response."""
    assert not c._handle_response("start_title", bytes(8) + b"\x00")


# Legacy Connection Tests


def setup_connection():
    """Setup Connection."""
    mock_ps4 = MagicMock()
    mock_ps4.host = MOCK_HOST
    mock_ps4.credential = MOCK_CREDS
    mock_ps4.device_name = MOCK_NAME
    mock_connection = c.LegacyConnection(mock_ps4, MOCK_CREDS)
    return mock_connection


def test_connect():
    """Test Connect."""
    mock_connection = setup_connection()
    mock_connection._send_msg = MagicMock()
    mock_sock = MagicMock()
    request = bytes(20) + MOCK_SEED
    mock_sock.recv.return_value = request
    with patch("pyps4_2ndscreen.connection.socket.socket", return_value=mock_sock):
        mock_connection.connect()
    assert len(mock_connection._send_msg.mock_calls) == 2


def test_disconnect():
    """Test disconnect."""
    mock_connection = setup_connection()
    mock_connection._socket = MagicMock()

    mock_connection.disconnect()
    assert len(mock_connection._socket.close.mock_calls) == 1


def test_legacy_login():
    """Test Legacy Login."""
    mock_connection = setup_connection()
    mock_connection._cipher = MagicMock()
    mock_connection._decipher = MagicMock()
    mock_connection._socket = MagicMock()
    msg = MOCK_LOGIN_SUCCESS
    mock_connection._socket.recv.return_value = msg
    mock_connection._decipher.decrypt.return_value = msg
    assert mock_connection.login(pin=MOCK_PIN) is True


def test_legacy_standby():
    """Test Legacy Standby."""
    mock_connection = setup_connection()
    mock_connection._cipher = MagicMock()
    mock_connection._socket = MagicMock()
    msg = MOCK_STANDBY_SUCCESS
    mock_connection._recv_msg = MagicMock(return_value=msg)
    assert mock_connection.standby() is True


def test_legacy_start_title():
    """Test Legacy start_title."""
    mock_connection = setup_connection()
    mock_connection._cipher = MagicMock()
    mock_connection._socket = MagicMock()
    msg = MOCK_BOOT_SUCCESS
    mock_connection._recv_msg = MagicMock(return_value=msg)
    assert mock_connection.start_title(MOCK_TITLE_ID) is True


def test_legacy_remote_control():
    """Test Legacy remote control."""
    mock_connection = setup_connection()
    mock_connection._send_msg = MagicMock()
    assert mock_connection.remote_control(16, 0) is True
    assert len(mock_connection._send_msg.mock_calls) == 3

    # Test PS
    mock_connection._send_msg = MagicMock()
    assert mock_connection.remote_control(128, 0) is True
    assert len(mock_connection._send_msg.mock_calls) == 4

    # Test socket error
    mock_connection._send_msg = MagicMock(side_effect=c.socket.error)
    assert mock_connection.remote_control(128, 0) is False

    # Test socket timeout
    mock_connection._send_msg = MagicMock(side_effect=c.socket.timeout)
    assert mock_connection.remote_control(128, 0) is False


def test_legacy_send_status():
    """Test Legacy send status."""
    mock_connection = setup_connection()
    mock_connection._send_msg = MagicMock()
    mock_connection.send_status()
    mock_connection._send_msg.assert_called_once_with(MOCK_STATUS_ACK, encrypted=True)


def test_legacy_send():
    """Test Legacy Send."""
    mock_connection = setup_connection()
    mock_connection.encrypt_message = MagicMock()
    mock_connection._socket = MagicMock()
    msg = b"\x00"
    mock_connection._send_msg(msg, encrypted=True)
    mock_connection.encrypt_message.assert_called_once_with(msg)

    # Test broken pipe
    mock_connection._socket.send = MagicMock(side_effect=BrokenPipeError)
    mock_connection._send_msg(msg, encrypted=True)
    assert len(mock_connection.ps4.close.mock_calls) == 1


# Async Connection Tests


def setup_mock_protocol():
    mock_ps4 = MagicMock()
    mock_ps4.host = MOCK_HOST
    mock_ps4.credential = MOCK_CREDS
    mock_ps4.device_name = MOCK_NAME
    mock_ps4.loggedin = False
    mock_ps4.connection = MagicMock()
    loop = asyncio.get_event_loop()
    mock_protocol = c.TCPProtocol(mock_ps4, loop)
    return mock_protocol, mock_ps4


async def test_async_connect():
    """Test Async connect."""
    mock_transport = MagicMock()
    mock_protocol = MagicMock()
    loop = asyncio.get_event_loop()
    loop.sock_connect = mock_connect = mock_coro()
    loop.sock_sendall = mock_send = mock_coro()
    loop.sock_recv = mock_recv = mock_coro(return_value=bytes(20) + MOCK_SEED)
    loop.create_connection = mock_create = mock_coro(
        return_value=(mock_transport, mock_protocol)
    )

    mock_ps4 = MagicMock()
    mock_ps4.host = MOCK_HOST

    mock_connection = c.AsyncConnection(mock_ps4, MOCK_CREDS)
    await mock_connection.async_connect(mock_ps4)

    assert len(mock_connect.mock_calls) == 1
    assert len(mock_send.mock_calls) == 2
    assert len(mock_recv.mock_calls) == 1
    assert len(mock_create.mock_calls) == 1


def test_connection_made():
    """Test Connection Made."""
    mock_protocol, mock_ps4 = setup_mock_protocol()
    mock_ps4.task_queue = None
    mock_protocol.connection_made(MagicMock())
    assert mock_protocol.task_available.is_set()


async def test_connection_made_task_queue():
    """Test task queue."""
    mock_protocol, mock_ps4 = setup_mock_protocol()
    mock_protocol.start_title = mock_coro()
    mock_ps4.task_queue = ("start_title", MOCK_TITLE_ID)
    mock_ps4.loggedin = True
    mock_protocol.connection_made(MagicMock())
    await asyncio.sleep(0)
    assert mock_protocol.task_available.is_set()
    assert len(mock_protocol.start_title.mock_calls) == 1


def test_connection_lost():
    """Test Connection lost."""
    mock_protocol, mock_ps4 = setup_mock_protocol()
    mock_protocol.connection_made(MagicMock())

    mock_protocol._hb_handler = MagicMock()
    mock_protocol.connection_lost(None)
    assert len(mock_ps4._closed.mock_calls) == 1
    assert len(mock_protocol._hb_handler.cancel.mock_calls) == 1


def test_async_disconnect():
    """Test disconnect."""
    mock_protocol, mock_ps4 = setup_mock_protocol()
    mock_transport = MagicMock()
    mock_protocol.transport = mock_transport

    mock_protocol.disconnect()
    assert len(mock_transport.close.mock_calls) == 1
    assert mock_protocol.transport is None


async def test_async_send():
    """Test async send."""
    mock_protocol, mock_ps4 = setup_mock_protocol()
    mock_transport = MagicMock()
    mock_protocol.transport = mock_transport
    msg = b"\x00"
    mock_ps4.connection.encrypt_message = MagicMock(return_value=msg)
    await mock_protocol.send(msg)
    mock_protocol.transport.write.assert_called_once_with(msg)

    # Test sync send
    mock_protocol.sync_send(msg)
    mock_protocol.transport.write.assert_called_with(msg)
    assert len(mock_protocol.transport.write.mock_calls) == 2


def test_data_recv():
    """Test data recv."""
    mock_protocol, mock_ps4 = setup_mock_protocol()

    # Test status request
    msg = c.STATUS_REQUEST
    mock_ps4.connection._decipher.decrypt = MagicMock(return_value=msg)
    mock_protocol._ack_status = mock_coro()
    mock_protocol.data_received(msg)
    assert len(mock_protocol._ack_status.mock_calls) == 1

    # Test login response
    mock_protocol.task = "login"
    msg = MOCK_LOGIN_SUCCESS
    mock_ps4.connection._decipher.decrypt = MagicMock(return_value=msg)
    mock_protocol.data_received(msg)
    assert mock_protocol.login_success.is_set()
    assert mock_ps4.loggedin is True
    assert mock_protocol.task is None

    # Test login fail response
    mock_protocol.task = "login"
    msg = bytes(8) + b"\x12"
    mock_ps4.connection._decipher.decrypt = MagicMock(return_value=msg)
    mock_protocol.data_received(msg)
    assert mock_ps4.loggedin is False


async def test_async_login():
    """Test async login."""
    mock_protocol, mock_ps4 = setup_mock_protocol()

    mock_protocol.send = mock_coro()
    mock_protocol.sync_send = MagicMock()
    mock_protocol._send_remote_control_request_sync = MagicMock()

    asyncio.ensure_future(mock_protocol.login(pin=MOCK_PIN, delay=0.1, power_on=False))
    await asyncio.sleep(0)
    # Mock login success.
    msg = MOCK_LOGIN_SUCCESS
    mock_ps4.connection._decipher.decrypt = MagicMock(return_value=msg)
    mock_protocol.data_received(msg)
    mock_protocol.send.assert_called_once_with(MOCK_LOGIN)
    mock_protocol.login_success.set()
    # Test RC Open sent.
    await asyncio.sleep(1)
    mock_protocol.sync_send.assert_called_once_with(MOCK_RC_OPEN)
    # Test RC PS is sent if not powering on.
    await asyncio.sleep(1)
    assert len(mock_protocol._send_remote_control_request_sync.mock_calls) == 1

    # Test login with no pin and powering on.
    mock_protocol._send_remote_control_request_sync = MagicMock()
    asyncio.ensure_future(mock_protocol.login(delay=0.1, power_on=True))
    await asyncio.sleep(0)
    # Mock login success.
    msg = MOCK_LOGIN_SUCCESS
    mock_ps4.connection._decipher.decrypt = MagicMock(return_value=msg)
    mock_protocol.data_received(msg)
    mock_protocol.send.assert_called_once_with(MOCK_LOGIN)
    mock_protocol.login_success.set()
    # Test RC Open sent.
    await asyncio.sleep(1)
    mock_protocol.sync_send.assert_called_once_with(MOCK_RC_OPEN)
    # Test RC PS not sent if not powering on.
    await asyncio.sleep(1)
    assert not mock_protocol._send_remote_control_request_sync.mock_calls

    # Test only one login task scheduled at a time.
    mock_protocol.task = "login"
    mock_protocol.add_task = mock_coro()
    await mock_protocol.login()
    assert not mock_protocol.add_task.mock_calls


async def test_async_standby():
    """Test async standby."""
    mock_protocol, mock_ps4 = setup_mock_protocol()
    mock_protocol.login = mock_coro()
    mock_protocol.send = mock_coro()

    asyncio.ensure_future(mock_protocol.standby())
    await asyncio.sleep(0)
    # Mock login success.
    msg = MOCK_LOGIN_SUCCESS
    mock_ps4.connection._decipher.decrypt = MagicMock(return_value=msg)
    mock_protocol.data_received(msg)
    await asyncio.sleep(0)
    msg = MOCK_STANDBY_SUCCESS
    mock_ps4.connection._decipher.decrypt = MagicMock(return_value=msg)
    mock_protocol.data_received(msg)
    assert mock_protocol.task is None


async def test_async_start_title():
    """Test async start_title."""
    mock_protocol, mock_ps4 = setup_mock_protocol()
    mock_protocol.login = mock_coro()
    mock_protocol.send = mock_coro()
    mock_protocol._send_remote_control_request_sync = MagicMock()

    asyncio.ensure_future(
        mock_protocol.start_title(MOCK_TITLE_ID, running_id="Some ID")
    )
    # Mock login success.
    await asyncio.sleep(0)
    msg = MOCK_LOGIN_SUCCESS
    mock_ps4.connection._decipher.decrypt = MagicMock(return_value=msg)
    mock_protocol.data_received(msg)
    await asyncio.sleep(0)
    mock_protocol.send.assert_called_with(MOCK_BOOT)
    msg = MOCK_BOOT_SUCCESS
    mock_ps4.connection._decipher.decrypt = MagicMock(return_value=msg)
    mock_protocol.data_received(msg)
    assert mock_protocol.task is None
    await asyncio.sleep(1)
    mock_protocol._send_remote_control_request_sync.assert_called_with(
        c._get_remote_control_request(16, 0), 16
    )


async def test_async_remote_control():
    """Test async remote_control."""
    mock_protocol, mock_ps4 = setup_mock_protocol()
    mock_protocol.login = mock_coro()
    mock_protocol.send = mock_coro()
    mock_protocol.sync_send = MagicMock()

    asyncio.ensure_future(mock_protocol.remote_control(128, 0))
    # Mock login success.
    await asyncio.sleep(0)
    msg = MOCK_LOGIN_SUCCESS
    mock_ps4.connection._decipher.decrypt = MagicMock(return_value=msg)
    mock_protocol.data_received(msg)
    await asyncio.sleep(1)
    assert mock_protocol.task is None
    assert len(mock_protocol.sync_send.mock_calls) == 3

    # Test ps_hold.
    mock_protocol.sync_send = MagicMock()
    asyncio.ensure_future(mock_protocol.remote_control(128, 2000))
    await asyncio.sleep(2)
    assert mock_protocol.task is None
    assert len(mock_protocol.sync_send.mock_calls) == 3

    # Test Enter.
    mock_protocol.sync_send = MagicMock()
    asyncio.ensure_future(mock_protocol.remote_control(16, 0))
    await asyncio.sleep(1)
    assert mock_protocol.task is None
    assert len(mock_protocol.sync_send.mock_calls) == 2


async def test_heartbeat():
    """Test async heartbeat."""
    mock_protocol, mock_ps4 = setup_mock_protocol()
    mock_protocol.sync_send = MagicMock()
    mock_protocol.heartbeat_timeout = 1
    msg = c.STATUS_REQUEST
    mock_ps4.connection._decipher.decrypt = MagicMock(return_value=msg)

    assert mock_protocol.heartbeat_delta is None
    mock_protocol.data_received(msg)
    await asyncio.sleep(0)
    assert mock_protocol.heartbeat_delta is not None

    # Test connection closed if heartbeat times out.
    await asyncio.sleep(1.1)
    assert len(mock_ps4._close.mock_calls) == 1
