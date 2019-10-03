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


# noqa: pylint: disable=no-self-use
class Helper:
    """Helpers for PS4. Used as class for simpler importing."""

    def __init__(self):
        """Init Class."""

    def has_devices(self, host=None):
        """Return status if there are devices that can be discovered."""
        from .ddp import Discovery

        _LOGGER.debug("Searching for PS4 Devices")
        discover = Discovery()
        devices = discover.search(host)
        for device in devices:
            _LOGGER.debug("Found PS4 at: %s", device['host-ip'])
        return devices

    def link(self, host, creds, pin, device_name=None):
        """Perform pairing with PS4."""
        from .ps4 import Ps4Legacy
        from .credential import DEFAULT_DEVICE_NAME

        if device_name is None:
            device_name = DEFAULT_DEVICE_NAME
        ps4 = Ps4Legacy(host, creds, device_name=device_name)
        is_ready = True
        is_login = True
        try:
            ps4.login(pin)
        except NotReady:
            is_ready = False
        except LoginFailed:
            is_login = False
        return is_ready, is_login

    def get_creds(self, device_name=None):
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

    def port_bind(self, ports: list):
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

    def check_data(self, file_type):
        """Return True if data is present in file."""
        file_name = self.check_files(file_type)
        with open(file_name, "r") as _r_file:
            data = json.load(_r_file)
            _r_file.close()
        if data:
            return True
        return False

    def check_files(self, file_type, file_path=None):
        """Create file if it does not exist. Return path."""
        if file_path is None:
            file_path = DEFAULT_PATH
        if not os.path.exists(file_path):
            os.mkdir(file_path)
        if file_type in FILE_TYPES:
            file_name = FILE_TYPES[file_type]
            if not os.path.isfile(file_name):
                with open(file_name, "w+") as _file_name:
                    json.dump(fp=_file_name, obj={})
                    _file_name.close()
            return file_name
        return None

    def load_files(self, file_type) -> dict:
        """Load data as JSON. Return data."""
        file_name = self.check_files(file_type)
        with open(file_name, "r") as _r_file:
            data = json.load(_r_file)
            _r_file.close()
        return data

    def save_files(self, data: dict, file_type=None, file_name=None):
        """Save file with data dict. Return file path."""
        if data is None:
            return None
        if file_type in FILE_TYPES:
            file_name = FILE_TYPES[file_type]
        else:
            return None

        _data = data
        with open(file_name, "w+") as _w_file:
            json.dump(fp=_w_file, obj=_data)
            _w_file.close()
        return file_name
