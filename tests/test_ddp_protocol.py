# -*- coding: utf-8 -*-
"""Mock actual PS4 device/server. Tests for DDP Protocol."""
import asyncio
import logging
import pytest

from pyps4_2ndscreen.ddp import async_create_ddp_endpoint
from pyps4_2ndscreen.credential import get_ddp_message
from pyps4_2ndscreen.ps4 import Ps4Async as ps4, STATUS_STANDBY

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

MOCK_HOST = '127.0.0.2'
MOCK_HOST2 = '127.0.0.3'
MOCK_PORT = 9041  # Random port. Otherwise need sudo.

MOCK_CREDS = '12345678901'
MOCK_CREDS2 = '12345678902'

MOCK_STANDBY = '620 Server Standby'
MOCK_RESPONSE = {
    'host-id': "123456789A",
    'host-type': 'PS4',
    'host-name': 'FakePs4',
    'host-request-port': MOCK_PORT
}

TIMEOUT = 3

"""There are 3 PS4 objects to test, representing 2 PS4 consoles
1. A PS4 object
2. A PS4 object bound to the same IP address as #1. This represents the same
PS4 console, but an additional object using a different account credential.
3. A PS4 object with a different IP Address. Represents a second PS4 console.
"""


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
        msg = get_ddp_message(MOCK_STANDBY, MOCK_RESPONSE)
        msg = msg.encode()
        _LOGGER.debug("Sent: %s to %s", msg, addr)
        self.transport.sendto(msg, addr)

    def close(self):
        """Stop Server."""
        self.transport.close()
        self.transport = None


async def start_mock_ps4(mock_addr):
    """Start a Mock PS4 Server."""
    mock_loop = asyncio.get_event_loop()
    mock_server = mock_loop.create_datagram_endpoint(
        lambda: MockDDPProtocol(), local_addr=(mock_addr, MOCK_PORT),  # noqa: pylint: disable=unnecessary-lambda
        reuse_port=True, allow_broadcast=True)
    _, mock_protocol = await mock_loop.create_task(mock_server)
    return mock_protocol


async def start_mock_instance():
    """Start Tests."""
    _, mock_client_protocol = await async_create_ddp_endpoint()
    assert mock_client_protocol.port == 987
    # Change port to use unpriviliged port.
    mock_client_protocol._set_write_port(MOCK_PORT)  # noqa: pylint: disable=protected-access
    assert mock_client_protocol.port == MOCK_PORT
    mock_protocol1 = await start_mock_ps4(MOCK_HOST)
    mock_protocol2 = await start_mock_ps4(MOCK_HOST2)

    mock_ps4 = ps4(MOCK_HOST, MOCK_CREDS)
    mock_ps4.ddp_protocol = mock_client_protocol

    mock_ps4_creds = ps4(MOCK_HOST, MOCK_CREDS2)
    mock_ps4_creds.ddp_protocol = mock_client_protocol

    mock_ps4_host = ps4(MOCK_HOST2, MOCK_CREDS)
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
    assert len(mock_client_protocol.callbacks[MOCK_HOST]) == 2  # noqa: 2 Callbacks for 2 PS4 Object.
    assert len(mock_client_protocol.callbacks[MOCK_HOST2]) == 1  # noqa: 1 Callback for other PS4 device.

    mock_ps4.get_status()
    mock_ps4_creds.get_status()
    mock_ps4_host.get_status()
    await asyncio.sleep(TIMEOUT)
    assert mock_ps4.status is not None
    assert _status.status0['status_code'] == STATUS_STANDBY
    assert mock_ps4_creds.status is not None
    assert _status.status1['status_code'] == STATUS_STANDBY
    assert mock_ps4_host.status is not None
    assert _status.status2['status_code'] == STATUS_STANDBY

    mock_client_protocol.remove_callback(
        mock_ps4, mock_callbacks[0])
    assert len(mock_client_protocol.callbacks[MOCK_HOST]) == 1
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
