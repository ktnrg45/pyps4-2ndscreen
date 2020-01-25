"""Credential fetcher for 2nd Screen app."""
import logging
import socket

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
    """The PS4 Credentials object. Masquerades as a PS4 to get credentials.

    PS4 listens on ports 987 (Priveleged).
    Must run command on python path:
    "sudo setcap 'cap_net_bind_service=+ep' /usr/bin/python3.5"
    """

    def __init__(self, device_name=DEFAULT_DEVICE_NAME):
        """Init Cred Server."""
        self.sock = None
        self.response = {
            'host-id': HOST_ID,
            'host-type': 'PS4',
            'host-name': device_name,
            'host-request-port': REQ_PORT
        }
        self.start()

    def start(self):
        """Start Cred Server."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock = sock
        except socket.error:
            _LOGGER.error("Failed to create socket")
            return
        sock.settimeout(3)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        try:
            sock.bind((UDP_IP, DDP_PORT))
        except socket.error as error:
            _LOGGER.error(
                "Could not bind to port %s; \
                Ensure port is accessible and unused, %s",
                DDP_PORT, error)
            return

    def listen(self, timeout=120):
        """Listen and respond to requests."""
        self.sock.settimeout(timeout)
        data = None
        address = None
        response = None
        _LOGGER.info(
            "Starting Credential Service with Timeout of %s seconds",
            timeout)
        while 1:
            try:
                parse_type = None
                try:
                    response = self.sock.recvfrom(1024)
                except socket.error:
                    self.sock.close()
                if not response:
                    _LOGGER.info(
                        "Credential service has timed out with no response")
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


def get_ddp_message(status, data=None):
    """Get DDP message."""
    msg = u'HTTP/1.1 {}\n'.format(status)
    if data is not None:
        for key, value in data.items():
            msg += u'{}:{}\n'.format(key, value)
    msg += u'device-discovery-protocol-version:{}\n'.format(DDP_VERSION)
    return msg


def parse_ddp_response(response):
    """Parse the response."""
    rsp = response.decode('utf-8')
    if DDP_TYPE_SEARCH in rsp:
        return 'search'
    if DDP_TYPE_WAKEUP in rsp:
        return 'wakeup'
    raise UnknownDDPResponse


def get_creds(response):
    """Return creds."""
    keys = {}
    data = response.decode('utf-8')
    for line in data.splitlines():
        line = line.strip()
        if ":" in line:
            value = line.split(':')
            keys[value[0]] = value[1]
    cred = keys['user-credential']
    return cred
