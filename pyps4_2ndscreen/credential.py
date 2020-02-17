"""Credential fetcher for PS4 2nd Screen app."""
import logging
import socket
import time
from typing import Optional

from .ddp import (
    DDP_PORT,
    DDP_VERSION,
    DDP_TYPE_SEARCH,
    DDP_TYPE_WAKEUP,
    UDP_IP,
)

from .errors import CredentialTimeout, UnknownDDPResponse

_LOGGER = logging.getLogger(__name__)

DEFAULT_DEVICE_NAME = 'pyps4-2ndScreen'
STANDBY = '620 Server Standby'
HOST_ID = '1234567890AB'
REQ_PORT = 997

PARSE_TYPE_SEARCH = 'search'
PARSE_TYPE_WAKEUP = 'wakeup'


class Credentials:
    """The PSN Credentials Service. Masquerades as a PS4 to get credentials.

    Service listens on port 987 (Priveleged).

    :param device_name: Name to display as
    """

    def __init__(self, device_name: Optional[str] = DEFAULT_DEVICE_NAME):

        self.sock = None
        self.response = {
            'host-id': HOST_ID,
            'host-type': 'PS4',
            'host-name': device_name,
            'host-request-port': REQ_PORT
        }
        self.start()

    def start(self):
        """Start Cred Service."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock = sock
        except socket.error:
            _LOGGER.error("Failed to create socket")
            return
        sock.settimeout(3)
        # REUSEADDR used instead of REUSEPORT for binding issues.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((UDP_IP, DDP_PORT))
        except socket.error as error:
            _LOGGER.error(
                "Could not bind to port %s; \
                Ensure port is accessible and unused, %s",
                DDP_PORT, error)
            return

    def listen(self, timeout: Optional[int] = 120):
        """Listen and respond to requests.

        :param timeout: Timeout in seconds
        """
        self.sock.settimeout(timeout)
        data = None
        address = None
        response = None
        start = time.time()
        _LOGGER.info(
            "Starting Credential Service with Timeout of %s seconds",
            timeout)
        while time.time() - start < timeout:
            try:
                parse_type = None
                try:
                    response = self.sock.recvfrom(1024)
                except socket.error:
                    self.sock.close()
                if not response:
                    _LOGGER.info(
                        "Credential service has timed out with no response")
                    self.sock.close()
                    raise CredentialTimeout
                data = response[0]
                address = response[1]
                try:
                    parse_type = parse_ddp_response(data)
                except UnknownDDPResponse:
                    _LOGGER.warning("Received unknown DDP Response")
                if parse_type == PARSE_TYPE_SEARCH:
                    _LOGGER.debug("Search from: %s", address)
                    msg = get_ddp_message(STANDBY, self.response)
                    self.sock.setsockopt(
                        socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    try:
                        self.sock.sendto(msg.encode('utf-8'), address)
                    except socket.error:
                        self.sock.close()
                elif parse_type == PARSE_TYPE_WAKEUP:
                    _LOGGER.debug("Wakeup from: %s", address)
                    creds = get_creds(data)
                    self.sock.close()
                    return creds
            except KeyboardInterrupt:
                self.sock.close()
                return None
        return None


def get_ddp_message(status: str, data: Optional[dict] = None) -> bytes:
    """Return DDP message.

    :param status: Status type to respond with
    :param data: Attributes to respond with
    """
    msg = u'HTTP/1.1 {}\n'.format(status)
    if data is not None:
        for key, value in data.items():
            msg += u'{}:{}\n'.format(key, value)
    msg += u'device-discovery-protocol-version:{}\n'.format(DDP_VERSION)
    return msg


def parse_ddp_response(response: bytes) -> str:
    """Parse the response. Return type.

    :param response: Response received by client app
    """
    rsp = response.decode('utf-8')
    if DDP_TYPE_SEARCH in rsp:
        return 'search'
    if DDP_TYPE_WAKEUP in rsp:
        return 'wakeup'
    raise UnknownDDPResponse


def get_creds(response: bytes) -> str:
    """Return creds.

    :param response: Response received from client with creds
    """
    keys = {}
    data = response.decode('utf-8')
    for line in data.splitlines():
        line = line.strip()
        if ":" in line:
            value = line.split(':')
            keys[value[0]] = value[1]
    cred = keys['user-credential']
    return cred
