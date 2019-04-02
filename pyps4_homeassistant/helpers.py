"""Helpers."""
import logging

from .credentials import Credentials
from .ps4 import Discovery, Ps4
from .errors import NotReady, LoginFailed

_LOGGER = logging.getLogger(__name__)


class Helper:
    """Helpers for PS4."""

    def __init__(self):
        """Init Class."""
        pass

    def has_devices(self, host=None):
        """Return if there are devices that can be discovered."""
        _LOGGER.debug("Searching for PS4 Devices")
        discover = Discovery()
        devices = discover.search(host)
        for device in devices:
            _LOGGER.debug("Found PS4 at: %s", device['host-ip'])
        return devices

    def link(self, host, creds, pin):
        """Perform pairing with PS4."""
        ps4 = Ps4(host, creds)
        is_ready = True
        is_login = True
        try:
            ps4.login(pin)
        except NotReady:
            is_ready = False
        except LoginFailed:
            is_login = False
        return is_ready, is_login

    def get_creds(self):
        """Return Credentials."""
        credentials = Credentials()
        return credentials.listen()

    def port_bind(self, ports):
        """Try binding to ports."""
        import socket
        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(1)
                sock.bind(('0.0.0.0', port))
                sock.close()
            except socket.error:
                sock.close()
                return int(port)
        return
