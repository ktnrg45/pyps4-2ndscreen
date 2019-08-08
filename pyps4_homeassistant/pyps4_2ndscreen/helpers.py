"""Helpers."""
import logging

from .errors import NotReady, LoginFailed

_LOGGER = logging.getLogger(__name__)


class Helper:
    """Helpers for PS4."""

    def __init__(self):
        """Init Class."""

    def has_devices(self, host=None):  # noqa: pylint: disable=no-self-use
        """Return if there are devices that can be discovered."""
        from .ddp import Discovery

        _LOGGER.debug("Searching for PS4 Devices")
        discover = Discovery()
        devices = discover.search(host)
        for device in devices:
            _LOGGER.debug("Found PS4 at: %s", device['host-ip'])
        return devices

    def link(self, host, creds, pin, device_name=None):  # noqa: pylint: disable=no-self-use
        """Perform pairing with PS4."""
        from .ps4 import Ps4

        ps4 = Ps4(host, creds, device_name=device_name)
        is_ready = True
        is_login = True
        try:
            ps4.login(pin)
        except NotReady:
            is_ready = False
        except LoginFailed:
            is_login = False
        return is_ready, is_login

    def get_creds(self, device_name=None):  # noqa: pylint: disable=no-self-use
        """Return Credentials."""
        from .credential import Credentials

        credentials = Credentials(device_name)
        return credentials.listen()

    def port_bind(self, ports):  # noqa: pylint: disable=no-self-use
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
            return None
