# -*- coding: utf-8 -*-
"""Mock actual PS4 device/server. Tests for DDP Protocol."""
import asyncio
import logging

from pyps4_homeassistant.ddp import async_create_ddp_endpoint
from pyps4_homeassistant.credential import get_ddp_message
from pyps4_homeassistant.ps4 import Ps4Async as ps4, STATUS_STANDBY

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

TIMEOUT = 1

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


class TestPS4DDPServer():
    """Class for tests."""

    def __init__(self):
        """Init."""
        self.mock_protocol = None
        self.mock_protocol2 = None
        self.mock_client_protocol = None
        self.mock_ps4 = None
        self.mock_ps4_creds = None
        self.mock_ps4_host = None
        self.mock_status_ps4 = None
        self.mock_status_ps4_creds = None
        self.mock_status_ps4_host = None
        self.tests_ran = 0

    def stop_tests(self):
        """Close all transports."""
        self.mock_protocol.close()
        self.mock_protocol2.close()
        self.mock_client_protocol.close()

    def mock_callback(self):
        """Mock Status callback"""
        self.mock_status_ps4 = self.mock_ps4.status
        _LOGGER.debug("Callback called: %s", self.mock_ps4.host)

    def mock_callback_creds(self):
        """Mock Status callback for PS4 with different creds"""
        self.mock_status_ps4_creds = self.mock_ps4_creds.status
        _LOGGER.debug(
            "Callback called: %s : Creds", self.mock_ps4_creds.host)

    def mock_callback_host(self):
        """Mock Status callback for PS4 with different IP."""
        self.mock_status_ps4_host = self.mock_ps4_host.status
        _LOGGER.debug("Callback called: %s", self.mock_ps4_host.host)

    async def start_mock_ps4(self, mock_addr):
        """Start a Mock PS4 Server."""
        mock_loop = asyncio.get_event_loop()
        mock_server = mock_loop.create_datagram_endpoint(
            lambda: MockDDPProtocol(), local_addr=(mock_addr, MOCK_PORT),  # noqa: pylint: disable=unnecessary-lambda
            reuse_address=True, reuse_port=True, allow_broadcast=True)
        _, mock_protocol = await mock_loop.create_task(mock_server)
        return mock_protocol

    async def start_tests(self):
        """Start Tests."""

        _, self.mock_client_protocol = await async_create_ddp_endpoint()
        assert self.mock_client_protocol.port == 987
        # Change port to use unpriviliged port.
        self.mock_client_protocol._set_write_port(MOCK_PORT)  # noqa: pylint: disable=protected-access
        assert self.mock_client_protocol.port == MOCK_PORT
        self.mock_protocol = await self.start_mock_ps4(MOCK_HOST)
        self.mock_protocol2 = await self.start_mock_ps4(MOCK_HOST2)

        self.mock_ps4 = ps4(MOCK_HOST, MOCK_CREDS)
        self.mock_ps4.ddp_protocol = self.mock_client_protocol

        self.mock_ps4_creds = ps4(MOCK_HOST, MOCK_CREDS2)
        self.mock_ps4_creds.ddp_protocol = self.mock_client_protocol

        self.mock_ps4_host = ps4(MOCK_HOST2, MOCK_CREDS)
        self.mock_ps4_host.ddp_protocol = self.mock_client_protocol

        # Run Tests.

        self.test_callback_add()
        assert len(self.mock_client_protocol.callbacks) == 2
        assert len(self.mock_client_protocol.callbacks[MOCK_HOST]) == 2
        assert len(self.mock_client_protocol.callbacks[MOCK_HOST2]) == 1
        self.tests_ran += 1

        self.test_ps4()
        _LOGGER.debug("Test 1")
        await asyncio.sleep(TIMEOUT)
        assert self.mock_status_ps4['status_code'] == STATUS_STANDBY
        self.tests_ran += 1

        _LOGGER.debug("Test 2")
        self.test_ps4_creds()
        await asyncio.sleep(TIMEOUT)
        assert self.mock_status_ps4['status_code'] == STATUS_STANDBY
        assert self.mock_status_ps4_creds['status_code'] == STATUS_STANDBY
        self.tests_ran += 1

        _LOGGER.debug("Test 3")
        self.test_ps4_host()
        await asyncio.sleep(TIMEOUT)
        assert self.mock_status_ps4['status_code'] == STATUS_STANDBY
        assert self.mock_status_ps4_creds['status_code'] == STATUS_STANDBY
        assert self.mock_status_ps4_host['status_code'] == STATUS_STANDBY
        self.tests_ran += 1

        self.test_callback_remove()
        assert len(self.mock_client_protocol.callbacks) == 0
        self.tests_ran += 1

        assert self.tests_ran == 5

        self.stop_tests()

    def test_callback_add(self):
        """Test that Callbacks are added."""
        self.mock_client_protocol.add_callback(
            self.mock_ps4, self.mock_callback)
        self.mock_client_protocol.add_callback(
            self.mock_ps4_creds, self.mock_callback_creds)
        self.mock_client_protocol.add_callback(
            self.mock_ps4_host, self.mock_callback_host)

    def test_callback_remove(self):
        """Test that PS4 objects and callback are removed."""
        self.mock_client_protocol.remove_callback(
            self.mock_ps4, self.mock_callback)
        self.mock_client_protocol.remove_callback(
            self.mock_ps4_creds, self.mock_callback_creds)
        self.mock_client_protocol.remove_callback(
            self.mock_ps4_host, self.mock_callback_host)

    def test_reset(self):
        """Reset Tests."""
        self.mock_ps4.status = None
        self.mock_ps4_creds.status = None
        self.mock_ps4_host.status = None
        self.mock_status_ps4 = None
        self.mock_status_ps4_creds = None
        self.mock_status_ps4_host = None

    def test_ps4(self):
        """Test status update for a PS4 Device."""
        self.test_reset()
        self.mock_ps4.get_status()

    def test_ps4_creds(self):
        """Test status updates for two ps4 objects with
        different creds for the same PS4 Device."""
        self.test_reset()
        self.mock_ps4.get_status()
        self.mock_ps4_creds.get_status()

    def test_ps4_host(self):
        """Test status updates for two ps4 objects with
        different creds for the same PS4 Device and a 2nd PS4 Device."""
        self.test_reset()
        self.mock_ps4.get_status()
        self.mock_ps4_creds.get_status()
        self.mock_ps4_host.get_status()


def main():
    """Setup tests."""
    mock_loop = asyncio.get_event_loop()
    tests = TestPS4DDPServer()
    mock_loop.run_until_complete(tests.start_tests())


if __name__ == "__main__":
    main()
