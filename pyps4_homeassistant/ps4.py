# -*- coding: utf-8 -*-
"""Methods for PS4 Object."""
from __future__ import print_function
import json
import logging
import time

from .connection import Connection
from .ddp import get_status, launch, wakeup
from .errors import (NotReady, PSDataIncomplete,
                     UnknownButton, LoginFailed)
from .media_art import (get_ps_store_data as ps_data,
                        get_ps_store_url as ps_url,
                        parse_data, FORMATS)
from .media_art import COUNTRIES, DEPRECATED_REGIONS

_LOGGER = logging.getLogger(__name__)


def open_credential_file(filename):
    """Open credential file."""
    return json.load(open(filename))


def delay(seconds):
    """Delay in seconds."""
    start_time = time.time()
    while time.time() - start_time < seconds:
        pass


def _format_url(url):
    f_params = {}
    url = url[0]
    url = url.split('?')
    params = url[1]
    params = params.replace('?', '')
    params = params.split('&')
    for item in params:
        item = item.split('=')
        f_params[item[0]] = item[1]
    url = url[0]
    return url, f_params


async def fetch(url, params, session):
    """Get Request."""
    async with session.get(url, params=params) as response:
        return await response.json()


async def async_get_ps_store_requests(title, title_id, region):
    """Return Title and Cover data with aiohttp."""
    import aiohttp

    requests = []
    regions = COUNTRIES
    d_regions = DEPRECATED_REGIONS

    if region not in regions:
        if region in d_regions:
            _LOGGER.warning('Region: %s is deprecated', region)
            region = d_regions[region]
        else:
            _LOGGER.error('Region: %s is not valid', region)
            return None
    else:
        region = regions[region]

    async with aiohttp.ClientSession() as session:
        for format_type in FORMATS:
            _url = ps_url(title, region, reformat=format_type, legacy=True)
            url, params = _format_url(_url)

            request = await fetch(url, params, session)
            requests.append(request)

        for format_type in FORMATS:
            _url = ps_url(
                title, region, reformat=format_type, legacy=False)
            url, params = _format_url(_url)

            request = await fetch(url, params, session)
            requests.append(request)
        return requests


class Ps4():   # noqa: pylint: disable=too-many-instance-attributes, too-many-arguments
    """The PS4 object."""

    STATUS_OK = 200
    STATUS_STANDBY = 620

    def __init__(self, host, credential=None, credentials_file=None,
                 broadcast=False, client=None):
        """Initialize the instance.

        Keyword arguments:
            host -- the host IP address
            credential -- the credential string
            credential_file -- the credendtial file generated with ps4-waker
            broadcast -- use broadcast IP address (default False)
        """
        self._host = host
        self._broadcast = broadcast
        self._socket = None
        self._credential = None
        self._msg_sending = False
        self.status = None
        self.connected = False
        self.client = client
        self.ps_cover = None
        self.ps_name = None

        if credential:
            self._credential = credential
        if credentials_file:
            creds = open_credential_file(credentials_file)
            self._credential = creds['user-credential']

        self._connection = Connection(host, credential=self._credential)

        if self.client is not None:
            self.client.add_ps4(ps4=self)

    def _prepare_connection(self):
        self.wakeup()
        self.launch()
        delay(0.5)
        _LOGGER.debug("Connection prepared")

    def open(self):
        """Open a connection to the PS4."""
        if self.status is None:
            self.get_status()
        if not self.is_running:
            raise NotReady("PS4 is not On")

        self._prepare_connection()
        if self.connected is False:
            self._connection.connect()
            login = self._connection.login()
            if login is True:
                self.connected = True
                return True
            return False
        return True

    def close(self):
        """Close the connection to the PS4."""
        self._connection.disconnect()
        self.connected = False
        _LOGGER.debug("Disconnecting from PS4 @ %s", self._host)

    def get_status(self):
        """Get current status info."""
        import socket

        try:
            self.status = get_status(self._host)
        except socket.timeout:
            _LOGGER.debug("PS4 @ %s status timed out", self._host)
            return None
        return self.status

    def launch(self):
        """Launch."""
        launch(self._host, self._credential)

    def wakeup(self):
        """Wakeup."""
        wakeup(self._host, self._credential)

    def login(self, pin=None):
        """Login."""
        self.open()
        is_login = self._connection.login(pin)
        if is_login is False:
            raise LoginFailed("PS4 Refused Connection")
        self.close()
        return is_login

    def standby(self):
        """Standby."""
        self.open()
        self._connection.standby()
        self.close()

    def start_title(self, title_id, running_id=None):
        """Start title.

        `title_id`: title to start
        """
        self.open()
        if self._connection.start_title(title_id):
            if running_id is not None:
                delay(1)
                self.remote_control('enter')
            elif running_id == title_id:
                _LOGGER.warning("Title: %s already started", title_id)
        else:
            self.close()

    def remote_control(self, button_name, hold_time=0):
        """Send a remote control button press.

        Documentation from ps4-waker source:
        near as I can tell, here's how this works:
         - For a simple tap, you send the key with holdTime=0,
           followed by KEY_OFF and holdTime = 0
         - For a long press/hold, you still send the key with
           holdTime=0, the follow it with the key again, but
           specifying holdTime as the hold duration.
         - After sending a direction, you should send KEY_OFF
           to clean it up (since it can just be held forever).
           Doing this after a long-press of PS just breaks it,
           however.
        """
        if self._msg_sending is True:
            _LOGGER.debug("RC Command in progress")
            return
        self._msg_sending = True
        buttons = {'up': 1,
                   'down': 2,
                   'right': 4,
                   'left': 8,
                   'enter': 16,
                   'back': 32,
                   'option': 64,
                   'ps': 128,
                   'key_off': 256,
                   'cancel': 512,
                   'open_rc': 1024,
                   'close_rc': 2048}
        button_name = button_name.lower()
        if button_name not in buttons.keys():
            raise UnknownButton("Button: {} is not valid".format(button_name))
        operation = buttons[button_name]
        self.open()
        if not self._connection.remote_control(operation, hold_time):
            self.close()
        self._msg_sending = False

    def send_status(self):
        """Send connection status to PS4."""
        if self.connected is True:
            while self._msg_sending is True:
                pass
            self._msg_sending = True
            is_loggedin = self._connection.send_status()
            self._msg_sending = False
            if is_loggedin is False:
                self.close()

    def get_ps_store_data(self, title, title_id, region, url=None):
        """Return Title and Cover data."""
        regions = COUNTRIES
        d_regions = DEPRECATED_REGIONS

        if region not in regions:
            if region in d_regions:
                _LOGGER.warning('Region: %s is deprecated', region)
                region = d_regions[region]
            else:
                _LOGGER.error('Region: %s is not valid', region)
                return None
        else:
            region = regions[region]
        try:
            _LOGGER.debug("Searching using legacy API")
            result_item = ps_data(title, title_id, region, url, legacy=True)
        except (TypeError, AttributeError):
            result_item = None
            raise PSDataIncomplete
        if result_item is not None:
            _LOGGER.debug("Found Title: %s, URL: %s",
                          result_item.name, result_item.cover_art)
            return result_item

        try:
            result_item = ps_data(title, title_id, region, url)
        except (TypeError, AttributeError):
            result_item = None
            raise PSDataIncomplete
        if result_item is not None:
            _LOGGER.debug("Found Title: %s, URL: %s",
                          result_item.name, result_item.cover_art)
            self.ps_name = result_item.name
            self.ps_cover = result_item.cover_art
            return result_item
        return None

    async def async_get_ps_store_data(self, title, title_id, region):
        """Parse Responses."""
        regions = COUNTRIES
        lang = regions[region]
        lang = lang.split('/')
        lang = lang[0]
        _LOGGER.debug("Searching...")
        responses = await async_get_ps_store_requests(
            title, title_id, region)
        for response in responses:
            try:
                result_item = parse_data(response, title_id, lang)
            except (TypeError, AttributeError):
                result_item = None
                raise PSDataIncomplete
            if result_item is not None:
                _LOGGER.debug("Found Title: %s, URL: %s",
                              result_item.name, result_item.cover_art)
                self.ps_name = result_item.name
                self.ps_cover = result_item.cover_art
                return result_item
            return None

    @property
    def is_running(self):
        """Return if the PS4 is running."""
        if self.status['status_code'] == self.STATUS_OK:
            return True
        return False

    @property
    def is_standby(self):
        """Return if the PS4 is in standby."""
        if self.status['status_code'] == self.STATUS_STANDBY:
            return True
        return False

    @property
    def system_version(self):
        """Get the system version."""
        return self.status['system-version']

    @property
    def host_id(self):
        """Get the host id."""
        return self.status['host-id']

    @property
    def host_name(self):
        """Get the host name."""
        return self.status['host-name']

    @property
    def running_app_titleid(self):
        """Return the title Id of the running application."""
        return self.status['running-app-titleid']

    @property
    def running_app_name(self):
        """Return the name of the running application."""
        return self.status['running-app-name']

    @property
    def running_app_ps_cover(self):
        """Return the URL for the title cover art."""
        return self.ps_cover

    @property
    def running_app_ps_name(self):
        """Return the name fetched from PS Store."""
        return self.ps_name
