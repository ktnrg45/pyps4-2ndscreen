"""Tests for pyps4_2ndscreen/ddp.py"""
import asyncio
import itertools
import logging
import socket
from unittest.mock import MagicMock, patch

import pytest
from asynctest import CoroutineMock as mock_coro
from pyps4_2ndscreen import ddp
from pyps4_2ndscreen.credential import get_ddp_message
from pyps4_2ndscreen.ps4 import STATUS_STANDBY
from pyps4_2ndscreen.ps4 import Ps4Async as ps4

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)


MODULE_NAME = "pyps4_2ndscreen"

MOCK_CREDS = "123412341234abcd12341234abcd12341234abcd12341234abcd12341234abcd"
MOCK_NAME = "ps4 name"
MOCK_HOST = "192.168.0.2"
MOCK_HOST2 = "192.168.0.3"
MOCK_HOST_NAME = "Fake PS4"
MOCK_HOST_ID = "A0000A0AA000"
MOCK_HOST_TYPE = "PS4"
MOCK_STATUS_REST = "Server Standby"
MOCK_STATUS_ON = "Ok"
MOCK_STANDBY_CODE = 620
MOCK_ON_CODE = 200
MOCK_TCP_PORT = 997
MOCK_DDP_PORT = 987
MOCK_DDP_VERSION = "00020020"
MOCK_SYSTEM_VERSION = "01000000"
MOCK_RANDOM_PORT = 1234
MOCK_TITLE_ID = "CUSA00000"
MOCK_TITLE_NAME = "Random Game"

MOCK_DDP_VER = 'device-discovery-protocol-version:{}\n'.format(
    MOCK_DDP_VERSION)

MOCK_DDP_MESSAGE = '{} * HTTP/1.1\n{}'
MOCK_DDP_CRED_DATA = 'user-credential:{}\nclient-type:a\nauth-type:C\n{}'

MOCK_DDP_DICT = {
    "host-type": MOCK_HOST_TYPE,
    "host-ip": MOCK_HOST,
    "host-request-port": MOCK_TCP_PORT,
    "running-app-name": MOCK_TITLE_NAME,
    "running-app-titleid": MOCK_TITLE_ID,
    "host-id": MOCK_HOST_ID,
    "host-name": MOCK_HOST_NAME,
    "status": MOCK_STATUS_ON,
    "status_code": MOCK_ON_CODE,
    "device-discovery-protocol-version": MOCK_DDP_VERSION,
    "system-version": MOCK_SYSTEM_VERSION,
}

MOCK_STANDBY_STATUS = {
    "host-type": MOCK_HOST_TYPE,
    "host-ip": MOCK_HOST,
    "host-request-port": MOCK_TCP_PORT,
    "host-id": MOCK_HOST_ID,
    "host-name": MOCK_HOST_NAME,
    "status": MOCK_STATUS_REST,
    "status_code": MOCK_STANDBY_CODE,
    "device-discovery-protocol-version": MOCK_DDP_VERSION,
    "system-version": MOCK_SYSTEM_VERSION,
}

MOCK_DDP_RESPONSE = '''
    HTTP/1.1 {} {}\n
    host-id:{}\n
    host-type:{}\n
    host-name:{}\n
    host-request-port:{}\n
    running-app-name:{}\n
    running-app-titleid:{}\n
    device-discovery-protocol-version:{}\n
    system-version:{}\n
'''.format(
    MOCK_ON_CODE,
    MOCK_STATUS_ON,
    MOCK_HOST_ID,
    MOCK_HOST_TYPE,
    MOCK_HOST_NAME,
    MOCK_TCP_PORT,
    MOCK_TITLE_NAME,
    MOCK_TITLE_ID,
    MOCK_DDP_VERSION,
    MOCK_SYSTEM_VERSION,
)

MOCK_DDP_RESPONSE_STANDBY = '''
    HTTP/1.1 {} {}\n
    host-id:{}\n
    host-type:{}\n
    host-name:{}\n
    host-request-port:{}\n
    device-discovery-protocol-version:{}\n
    system-version:{}\n
'''.format(
    MOCK_STANDBY_CODE,
    MOCK_STATUS_REST,
    MOCK_HOST_ID,
    MOCK_HOST_TYPE,
    MOCK_HOST_NAME,
    MOCK_TCP_PORT,
    MOCK_DDP_VERSION,
    MOCK_SYSTEM_VERSION,
)


MOCK_DDP_PROTO_HOST = '127.0.0.2'
MOCK_DDP_PROTO_HOST2 = '127.0.0.3'
MOCK_DDP_PROTO_PORT = 9041  # Random port. Otherwise need sudo.

MOCK_DDP_PROTO_CREDS =\
    '223412341234abcd12341234abcd12341234abcd12341234abcd12341234abcd'
MOCK_DDP_PROTO_CREDS2 =\
    '323412341234abcd12341234abcd12341234abcd12341234abcd12341234abcd'

MOCK_DDP_PROTO_STANDBY = '620 Server Standby'
MOCK_DDP_PROTO_RESPONSE = {
    'host-id': "123456789A",
    'host-type': 'PS4',
    'host-name': 'FakePs4',
    'host-request-port': MOCK_DDP_PROTO_PORT
}

DDP_PROTO_TIMEOUT = 3


def test_ddp_messages():
    """Test that DDP messages to send are correct."""
    msg = ddp.get_ddp_search_message()
    msg = msg.split('\n')
    for item in msg:
        assert item in MOCK_DDP_MESSAGE.format(
            ddp.DDP_TYPE_SEARCH, MOCK_DDP_VER)

    cred_data = MOCK_DDP_CRED_DATA.format(MOCK_CREDS, MOCK_DDP_VER)

    msg = ddp.get_ddp_launch_message(MOCK_CREDS)
    msg = msg.split('\n')
    for item in msg:
        assert item in MOCK_DDP_MESSAGE.format(ddp.DDP_TYPE_LAUNCH, cred_data)

    msg = ddp.get_ddp_wake_message(MOCK_CREDS)
    msg = msg.split('\n')
    for item in msg:
        assert item in MOCK_DDP_MESSAGE.format(ddp.DDP_TYPE_WAKEUP, cred_data)


def test_incorrect_ddp_msg_type():
    """Test incorrect ddp msg type."""
    with pytest.raises(TypeError):
        ddp.get_ddp_message('Random', b'')


def test_wakeup():
    """Test Wakeup call."""
    mock_sock = MagicMock()
    ddp.wakeup(MOCK_HOST, MOCK_CREDS, sock=mock_sock)
    assert len(mock_sock.sendto.mock_calls) == 1


def test_launch():
    """Test Launch call."""
    mock_sock = MagicMock()
    ddp.launch(MOCK_HOST, MOCK_CREDS, sock=mock_sock)
    assert len(mock_sock.sendto.mock_calls) == 1


def test_send_search():
    """Test send search."""
    mock_sock = MagicMock()
    ddp.send_search_msg(MOCK_HOST, sock=mock_sock)
    assert len(mock_sock.sendto.mock_calls) == 1


def test_search():
    """Test Search."""
    mock_sock = MagicMock()
    mock_sock.recvfrom.return_value = (
        MOCK_DDP_RESPONSE.encode(), (MOCK_HOST, MOCK_RANDOM_PORT))
    with patch(
        'pyps4_2ndscreen.ddp.select.select',
            return_value=([mock_sock], [MagicMock()], [MagicMock()])):
        mock_result = ddp.search(MOCK_HOST, sock=mock_sock)[0]
        assert MOCK_HOST in mock_result.values()


def test_get_status():
    """Test that get_status returns correctly parsed response."""
    with patch(
        'pyps4_2ndscreen.ddp._send_recv_msg',
        return_value=(
            MOCK_DDP_RESPONSE.encode('utf-8'),
            (MOCK_HOST, MOCK_RANDOM_PORT)),
    ) as mock_send:
        parsed = ddp.get_status(host=MOCK_HOST)

    assert len(mock_send.mock_calls) == 1

    for key, value in parsed.items():
        assert key in MOCK_DDP_DICT
        assert value == parsed[key]
    assert len(parsed) == len(MOCK_DDP_DICT)


def test_no_status():
    """Test no status."""
    assert ddp.get_status(MOCK_HOST) is None


def test_protocol_connection_lost():
    """Test protocol connection lost."""
    mock_ddp = ddp.DDPProtocol()
    mock_ddp._transport = MagicMock()
    mock_ddp.error_received(ConnectionError)
    mock_ddp.connection_lost(ConnectionError)
    assert len(mock_ddp._transport.close.mock_calls) == 1


def test_protocol_close():
    """Test protocol close."""
    mock_ddp = ddp.DDPProtocol()
    mock_ddp._transport = MagicMock()
    mock_close = mock_ddp._transport.close
    mock_ddp.close()
    assert len(mock_close.mock_calls) == 1


def test_ps4_unavailable():
    """Tests for ps4 unavailable."""
    mock_ddp = ddp.DDPProtocol()
    mock_ddp._transport = MagicMock()
    mock_ddp.set_max_polls(1)
    mock_cb = MagicMock()
    mock_ps4 = ps4(MOCK_HOST, MOCK_CREDS)
    mock_ps4.set_protocol(mock_ddp)
    mock_ps4.add_callback(mock_cb)
    mock_ps4.status = MOCK_DDP_DICT

    mock_ddp.send_msg(mock_ps4)
    assert len(mock_ddp._transport.sendto.mock_calls) == 1
    assert not mock_ps4.unreachable
    assert mock_ps4.poll_count == 1
    assert mock_ps4.status is not None
    assert not mock_cb.mock_calls

    mock_ddp.send_msg(mock_ps4)
    assert len(mock_ddp._transport.sendto.mock_calls) == 2
    assert mock_ps4.unreachable is True
    assert mock_ps4.status is None
    assert len(mock_cb.mock_calls) == 1


def test_ddp_disable_polls():
    """Tests for diabling polls."""
    mock_ddp = ddp.DDPProtocol()
    mock_ddp._transport = MagicMock()
    mock_cb = MagicMock()
    mock_ps4 = ps4(MOCK_HOST, MOCK_CREDS)
    mock_ps4.set_protocol(mock_ddp)
    mock_ps4.add_callback(mock_cb)
    mock_ps4.status = MOCK_DDP_DICT

    mock_ddp.send_msg(mock_ps4)
    assert len(mock_ddp._transport.sendto.mock_calls) == 1
    assert mock_ps4.status is not None
    assert not mock_ddp.polls_disabled

    # Diabled polls
    mock_ddp._handle(
        MOCK_DDP_RESPONSE_STANDBY.encode(),
        (mock_ps4.host, MOCK_RANDOM_PORT))
    mock_ddp.send_msg(mock_ps4)
    assert len(mock_ddp._transport.sendto.mock_calls) == 1
    assert mock_ddp.polls_disabled

    # Disabled timer expires
    mock_ddp._standby_start = 0
    mock_ddp.send_msg(mock_ps4)
    assert len(mock_ddp._transport.sendto.mock_calls) == 2
    assert not mock_ddp.polls_disabled


def test_discovery():
    """Tests for discovery."""
    mock_disc = ddp.Discovery()
    mock_disc.sock = MagicMock()
    mock_recv = (
        MOCK_DDP_RESPONSE.encode(),
        (MOCK_HOST, MOCK_RANDOM_PORT),
    )
    mock_recv2 = (
        MOCK_DDP_RESPONSE.encode(),
        (MOCK_HOST2, MOCK_RANDOM_PORT),
    )

    mock_disc.sock.recvfrom.return_value = mock_recv
    with patch(
        'pyps4_2ndscreen.ddp.select.select',
        return_value=([mock_disc.sock], [MagicMock()], [MagicMock()]),
    ):
        assert mock_disc.search(None)[0]['host-ip'] == MOCK_HOST
    # Test that sock is closed on success
    assert len(mock_disc.sock.close.mock_calls) == 1

    # Test two hosts responding once each
    mock_disc.sock.recvfrom.side_effect = [mock_recv, mock_recv2]
    with patch(
        'pyps4_2ndscreen.ddp.select.select',
        side_effect=itertools.chain(
            [
                ([mock_disc.sock], [MagicMock()], [MagicMock()]),
                ([mock_disc.sock], [MagicMock()], [MagicMock()]),
            ],
            itertools.repeat(([], [], [])),
        ),
    ):
        mock_discovered = mock_disc.search(None)
        assert mock_discovered[0]['host-ip'] == MOCK_HOST
        assert mock_discovered[1]['host-ip'] == MOCK_HOST2
        assert len(mock_discovered) == 2

    assert len(mock_disc.sock.close.mock_calls) == 2


def test_discovery_errors():
    """Test discovery Errors."""
    mock_disc = ddp.Discovery()
    mock_disc.sock = MagicMock()

    # Test receive search message
    with patch(
        'pyps4_2ndscreen.ddp.select.select',
        return_value=([mock_disc.sock], [MagicMock()], [MagicMock()]),
    ):
        mock_disc.sock.recvfrom.return_value = (
            ddp.get_ddp_search_message().encode(),
            (MOCK_HOST, MOCK_RANDOM_PORT),
        )
        assert not mock_disc.search(None)
    assert len(mock_disc.sock.close.mock_calls) == 1

    # Test send error
    mock_disc.sock.recvfrom.return_value = (
        MOCK_DDP_RESPONSE.encode(), (MOCK_HOST, MOCK_RANDOM_PORT))
    mock_disc.send = MagicMock(
        side_effect=(ddp.socket.error, ddp.socket.timeout))
    mock_disc.search(None)
    assert len(mock_disc.sock.close.mock_calls) == 2

    # Test receive error
    mock_disc.send = MagicMock()
    mock_disc.receive = MagicMock(
        side_effect=(ddp.socket.error, ddp.socket.timeout))
    mock_disc.search(None)
    assert len(mock_disc.sock.close.mock_calls) == 3


def test_get_socket_error():
    """Tests handling of get_socket errors."""
    with patch(
        'pyps4_2ndscreen.ddp.socket.socket.bind',
            side_effect=socket.error):
        sock = ddp.get_socket()
        assert sock is None


@pytest.mark.asyncio
async def test_create_ddp_protocol():
    """Test DDP Protocol init."""
    with patch(
        "pyps4_2ndscreen.ddp.asyncio.get_event_loop",
            return_value=MagicMock()) as mock_loop:
        mock_loop = mock_loop()
        mock_create_task = mock_coro(return_value=(MagicMock(), MagicMock()))
        mock_call = mock_coro(return_value=(MagicMock(), MagicMock()))
        mock_loop.create_datagram_endpoint = mock_call
        mock_loop.create_task = mock_create_task

        local_addr = (ddp.UDP_IP, ddp.UDP_PORT)
        reuse_port = hasattr(socket, "SO_REUSEPORT")
        allow_broadcast = True
        sock = None
        mock_kwargs = {
            'local_addr': local_addr,
            'reuse_port': reuse_port,
            'allow_broadcast': allow_broadcast,
            'sock': sock,
        }
        _, mock_ddp = await ddp.async_create_ddp_endpoint()
        mock_ddp.close()
        args, kwargs = mock_call.call_args
        assert callable(args[0])  # Hack for lambda: DDPProtocol()
        for key, value in kwargs.items():
            assert mock_kwargs[key] == value


@pytest.mark.asyncio
async def test_create_ddp_protocol_sock():
    """Test DDP Protocol init with socket."""
    with patch(
        "pyps4_2ndscreen.ddp.asyncio.get_event_loop",
            return_value=MagicMock()) as mock_loop:
        mock_loop = mock_loop()
        mock_create_task = mock_coro(return_value=(MagicMock(), MagicMock()))
        mock_call = mock_coro(return_value=(MagicMock(), MagicMock()))
        mock_loop.create_datagram_endpoint = mock_call
        mock_loop.create_task = mock_create_task
        mock_port = 1234
        mock_timeout = 3

        local_addr = None
        reuse_port = None
        allow_broadcast = None
        sock = ddp.get_socket(timeout=mock_timeout, port=mock_port)

        assert sock.gettimeout() > 0
        assert sock.getsockname() == (ddp.UDP_IP, mock_port)
        mock_kwargs = {
            'local_addr': local_addr,
            'reuse_port': reuse_port,
            'allow_broadcast': allow_broadcast,
            'sock': sock,
        }
        _, mock_ddp = await ddp.async_create_ddp_endpoint(sock=sock)
        mock_ddp.close()
        args, kwargs = mock_call.call_args
        assert callable(args[0])  # Hack for lambda: DDPProtocol()
        for key, value in kwargs.items():
            assert mock_kwargs[key] == value
        # Test if socket is changed to nonblocking
        assert kwargs['sock'].gettimeout() == 0


# Test DDP Protocol instance.


class MockDDPProtocol():
    """Mock DDP Server; PS4."""

    def connection_made(self, transport):
        self.transport = transport

    def connection_lost(self, exc):
        """On Connection Lost."""
        if self.transport is not None:
            _LOGGER.error("Mock DDP Transport Closed")
            self.transport.close()

    def datagram_received(self, data, addr):
        message = data.decode()
        _LOGGER.debug("RECV: %s", message)
        msg = get_ddp_message(MOCK_DDP_PROTO_STANDBY, MOCK_DDP_PROTO_RESPONSE)
        msg = msg.encode()
        _LOGGER.debug("Sent: %s to %s", msg, addr)
        self.transport.sendto(msg, addr)

    def close(self):
        """Stop Server."""
        self.transport.close()
        self.transport = None


async def start_mock_ps4(mock_addr):
    """Start a Mock PS4 Server."""
    reuse_port = hasattr(socket, 'SO_REUSEPORT')
    mock_loop = asyncio.get_event_loop()
    mock_server = mock_loop.create_datagram_endpoint(
        lambda: MockDDPProtocol(), local_addr=(mock_addr, MOCK_DDP_PROTO_PORT),  # noqa: pylint: disable=unnecessary-lambda
        reuse_port=reuse_port, allow_broadcast=True)
    _, mock_protocol = await mock_loop.create_task(mock_server)
    return mock_protocol


async def start_mock_instance():
    """Start Tests.

    There are 3 PS4 objects to test, representing 2 PS4 consoles:
    1. A PS4 object
    2. A PS4 object bound to the same IP address as #1.
    This represents the same PS4 console,
    but an additional object using a different account credential.
    3. A PS4 object with a different IP Address.
    Represents a second PS4 console.
    """
    _, mock_client_protocol = await ddp.async_create_ddp_endpoint()
    assert mock_client_protocol.remote_port == 987
    # Change port to use unpriviliged port.
    mock_client_protocol._set_write_port(MOCK_DDP_PROTO_PORT)  # noqa: pylint: disable=protected-access
    assert mock_client_protocol.remote_port == MOCK_DDP_PROTO_PORT
    mock_protocol1 = await start_mock_ps4(MOCK_DDP_PROTO_HOST)
    mock_protocol2 = await start_mock_ps4(MOCK_DDP_PROTO_HOST2)

    mock_ps4 = ps4(MOCK_DDP_PROTO_HOST, MOCK_DDP_PROTO_CREDS)
    mock_ps4.ddp_protocol = mock_client_protocol

    mock_ps4_creds = ps4(MOCK_DDP_PROTO_HOST, MOCK_DDP_PROTO_CREDS2)
    mock_ps4_creds.ddp_protocol = mock_client_protocol

    mock_ps4_host = ps4(MOCK_DDP_PROTO_HOST2, MOCK_DDP_PROTO_CREDS)
    mock_ps4_host.ddp_protocol = mock_client_protocol

    return (
        mock_client_protocol,
        (mock_ps4, mock_ps4_creds, mock_ps4_host),
        (mock_protocol1, mock_protocol2),
    )


def _add_callbacks(client_protocol, ps4_obj, callbacks):
    client_protocol.add_callback(
        ps4_obj[0], callbacks[0])
    client_protocol.add_callback(
        ps4_obj[1], callbacks[1])
    client_protocol.add_callback(
        ps4_obj[2], callbacks[2])


class CBStatus():
    def __init__(self, ps4_obj):
        self.ps40 = ps4_obj[0]
        self.ps41 = ps4_obj[1]
        self.ps42 = ps4_obj[2]
        self.status0 = None
        self.status1 = None
        self.status2 = None

    def _update0(self):
        self.status0 = self.ps40.status

    def _update1(self):
        self.status1 = self.ps41.status

    def _update2(self):
        self.status2 = self.ps42.status


@pytest.mark.asyncio
async def test_status():
    """Test status update for a PS4 Devices."""
    mock_client_protocol, mock_ps4s, mock_devices = await start_mock_instance()
    mock_ps4 = mock_ps4s[0]
    mock_ps4_creds = mock_ps4s[1]
    mock_ps4_host = mock_ps4s[2]

    _status = CBStatus(mock_ps4s)
    mock_callbacks = (_status._update0, _status._update1, _status._update2)
    _add_callbacks(mock_client_protocol, mock_ps4s, mock_callbacks)

    assert len(mock_client_protocol.callbacks) == 2  # 2 PS4 Devices.
    assert len(mock_client_protocol.callbacks[MOCK_DDP_PROTO_HOST]) == 2  # noqa: 2 Callbacks for 2 PS4 Object.
    assert len(mock_client_protocol.callbacks[MOCK_DDP_PROTO_HOST2]) == 1  # noqa: 1 Callback for other PS4 device.

    mock_ps4.get_status()
    mock_ps4_creds.get_status()
    mock_ps4_host.get_status()
    await asyncio.sleep(DDP_PROTO_TIMEOUT)
    assert mock_ps4.status is not None
    assert _status.status0['status_code'] == STATUS_STANDBY
    assert mock_ps4_creds.status is not None
    assert _status.status1['status_code'] == STATUS_STANDBY
    assert mock_ps4_host.status is not None
    assert _status.status2['status_code'] == STATUS_STANDBY

    mock_client_protocol.remove_callback(
        mock_ps4, mock_callbacks[0])
    assert len(mock_client_protocol.callbacks[MOCK_DDP_PROTO_HOST]) == 1
    # Should be 1 callback for this PS4 device.
    mock_client_protocol.remove_callback(
        mock_ps4_creds, mock_callbacks[1])
    # Device should be removed since no callbacks remaining.
    assert len(mock_client_protocol.callbacks) == 1
    mock_client_protocol.remove_callback(
        mock_ps4_host, mock_callbacks[2])
    assert len(mock_client_protocol.callbacks) == 0

    mock_devices[0].close()
    mock_devices[1].close()
