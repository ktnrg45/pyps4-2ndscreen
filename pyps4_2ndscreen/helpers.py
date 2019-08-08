"""Helpers."""
import logging
import os
from pathlib import Path
import json

from .errors import NotReady, LoginFailed

_LOGGER = logging.getLogger(__name__)

DEFAULT_PATH = str('{}{}'.format(Path.home(), '/.pyps4-2ndscreen'))
DEFAULT_PS4_FILE = "{}/.ps4_info.json".format(DEFAULT_PATH)
DEFAULT_CREDS_FILE = "{}/.ps4_creds.json".format(DEFAULT_PATH)
DEFAULT_GAMES_FILE = "{}/.ps4_games.json".format(DEFAULT_PATH)

FILE_TYPES = {
    'ps4': DEFAULT_PS4_FILE,
    'credentials': DEFAULT_CREDS_FILE,
    'games': DEFAULT_GAMES_FILE
}


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
        from .credential import Credentials, DEFAULT_DEVICE_NAME

        if device_name is None:
            device_name = DEFAULT_DEVICE_NAME

        credentials = Credentials(device_name)
        return credentials.listen()

    def save_creds(self):
        """Save Creds to file."""
        creds = self.get_creds()
        if creds is not None:
            data = {'credentials': creds}
            self.save_files(DEFAULT_CREDS_FILE, data)
            return True
        return False

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

    def check_files(self, file_type):  # noqa: pylint: disable=no-self-use
        """Create file if it does not exist."""
        if file_type in FILE_TYPES:
            file_name = FILE_TYPES[file_type]
            if not os.path.exists(DEFAULT_PATH):
                os.mkdir(DEFAULT_PATH)
            if not os.path.isfile(file_name):
                with open(file_name, "w+") as _file_name:
                    json.dump(fp=_file_name, obj={})
                    _file_name.close()
            return file_name

    def save_files(self, file_type, data: str):
        """Save file with data dict."""
        if data is None:
            return
        file_name = self.check_files(file_type)
        with open(file_name, "r") as _r_file:
            _data = json.load(_r_file)
            _r_file.close()
        if data not in _data.values():
            _data['credentials'] = data

            with open(file_name, "w+") as _w_file:
                json.dump(fp=_w_file, obj=_data)
                _w_file.close()
        else:
            _LOGGER.info('Credentials already saved')
        return file_name
