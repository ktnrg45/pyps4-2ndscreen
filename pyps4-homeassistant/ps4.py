# -*- coding: utf-8 -*-
from __future__ import print_function
from threading import Timer
import json
import logging
import time
import socket

from .connection import Connection
from .ddp import get_status, launch, wakeup
from .errors import NotReady, UnknownButton, LoginFailed

_LOGGER = logging.getLogger(__name__)


def open_credential_file(filename):
    """Open credential file."""
    return json.load(open(filename))


class StatusTimer():
    """Status Thread Class."""

    def __init__(self, seconds, target):
        """Init."""
        self._should_continue = False
        self.is_running = False
        self.seconds = seconds
        self.target = target
        self.thread = None

    def _handle_target(self):
        self.is_running = True
        self.target()
        self.is_running = False
        self._start_timer()

    def _start_timer(self):
        """Restart Timer."""
        if self._should_continue:
            self.thread = Timer(self.seconds, self._handle_target)
            self.thread.start()

    def start(self):
        """Start Timer."""
        if not self._should_continue and not self.is_running:
            self._should_continue = True
            self._start_timer()

    def cancel(self):
        """Cancel Timer."""
        if self.thread is not None:
            self._should_continue = False
            self.thread.cancel()


class Ps4(object):
    """The PS4 object."""

    STATUS_OK = 200
    STATUS_STANDBY = 620

    def __init__(self, host, credential=None, credentials_file=None,
                 broadcast=False):
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
        self._connected = False
        self._status_timer = None
        self.keep_alive = False

        if credential:
            self._credential = credential
        if credentials_file:
            creds = open_credential_file(credentials_file)
            self._credential = creds['user-credential']

        self._connection = Connection(host, credential=self._credential)

    def open(self):
        """Open a connection to the PS4."""
        if self.is_standby():
            raise NotReady

        if self._connected is False:
            self.wakeup()
            self.launch()
            time.sleep(0.5)
            self._connection.connect()
            login = self._connection.login()
            if login is True:
                self._connected = True
                if self.keep_alive is True:
                    _LOGGER.debug("Keep Alive feature enabled")
                    self._status_timer = StatusTimer(30, self.send_status)
                    self._status_timer.start()

    def close(self):
        """Close the connection to the PS4."""
        self._connection.disconnect()
        self._connected = False
        self.keep_alive = False
        if self._status_timer is not None:
            self._status_timer.cancel()
            self._status_timer = None

    def is_keepalive(self):
        """Check if keep alive should be sent."""
        if self.keep_alive is False:
            self.close()

    def get_status(self):
        """Get current status info.

        Return a dictionary with status information.
        """
        return get_status(self._host)

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
            raise LoginFailed
        self.close()
        return is_login

    def standby(self):
        """Standby."""
        if self._connected is True:
            self.close()
        self.open()
        self._connection.standby()
        self.close()

    def start_title(self, title_id, running_id=None):
        """Start title.

        `title_id`: title to start
        """
        self.open()
        self._connection.start_title(title_id)
        if running_id is not None:
            self._connection.remote_control(16, 0)
        elif running_id == title_id:
            _LOGGER.warning("Title: %s already started", title_id)
        self.is_keepalive()

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
        buttons = []
        buttons.append(button_name)

        self.open()

        for button in buttons:
            try:
                operation = {
                    'up': 1,
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
                    'close_rc': 2048,
                }[button.lower()]
            except KeyError:
                raise UnknownButton

            self._connection.remote_control(operation, hold_time)
        self.is_keepalive()

    def send_status(self):
        """Send connection status to PS4."""
        if self._connected is True:
            is_loggedin = self._connection.send_status()
            if is_loggedin is False:
                self.close()

    def get_host_status(self):
        """Get PS4 status code.

        STATUS_OK: 200
        STATUS_STANDBY: 620
        """
        return self.get_status()['status_code']

    def is_running(self):
        """Return if the PS4 is running.

        Returns True or False.
        """
        return True if self.get_host_status() == self.STATUS_OK else False

    def is_standby(self):
        """Return if the PS4 is in standby.

        Returns True or False.
        """
        return True if self.get_host_status() == self.STATUS_STANDBY else False

    def get_system_version(self):
        """Get the system version."""
        return self.get_status()['system-version']

    def get_host_id(self):
        """Get the host id."""
        return self.get_status()['host-id']

    def get_host_name(self):
        """Get the host name."""
        return self.get_status()['host-name']

    def get_running_app_titleid(self):
        """Return the title Id of the running application."""
        return self.get_status()['running-app-titleid']

    def get_running_app_name(self):
        """Return the name of the running application."""
        return self.get_status()['running-app-name']

    def get_ps_store_url(self, title, region):
        """Get URL for title search in PS Store."""
        import urllib
        import re

        regions = {'R1': 'US', 'R2': 'GB', 'R3': 'HK', 'R4': 'AU', 'R5': 'IN'}

        if region not in regions:
            _LOGGER.error('Region: %s is not valid', region)
            return
        else:
            region = regions[region]

        headers = {
            'User-Agent':
                'Mozilla/5.0 '
                '(Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36'
        }

        if title is not None:
            title = re.sub('[^A-Za-z0-9]+', ' ', title)
            title = urllib.parse.quote(title.encode('utf-8'))
            _url = 'https://store.playstation.com/'\
                'valkyrie-api/en/{0}/19/faceted-search/'\
                '{1}?query={1}&platform=ps4'.format(region, title)

        url = [_url, headers]
        return url

    def get_ps_store_data(self, title, title_id, region, url=None):
        """Store cover art from PS store in games map."""
        import requests
        import re

        if url is None:
            url = self.get_ps_store_url(title, region)
        req = None
        match_id = {}
        match_title = {}
        title = re.sub('[^A-Za-z0-9]+', ' ', title)
        type_list = ['Full Game', 'Game', 'PSN Game', 'Bundle', 'App']
        try:
            req = requests.get(url[0], headers=url[1])
            result = req.json()['included']
        except requests.exceptions.HTTPError as warning:
            _LOGGER.warning("PS cover art HTTP error, %s", warning)
            return
        except requests.exceptions.RequestException as warning:
            _LOGGER.warning("PS cover art request failed, %s", warning)
            return

        # Filter through each item in search request

        # Filter each item by prioritized type
        for game_type in type_list:
            for item in result:
                has_parent = False

                # Set each item as Game object
                game = self._game(item)

                # Get Parent attr
                if 'parent' in game:
                    if game['parent'] is not None:
                        has_parent = True
                        parent = game['parent']
                        parent_id = self._parse_id(parent['id'])
                        parent_title = parent['name']
                        parent_art = parent['url']
                        if parent_id == title_id:
                            return parent_title, parent_art

                if self._is_game_type(game, game_type):
                    parse_id = self._parse_id(game['default-sku-id'])
                    title_parse = game['name']

                    # If passed SKU matches object SKU
                    if parse_id == title_id:
                        cover_art = self._get_cover(game)
                        if cover_art is not None:

                            # If true likely a bundle, dlc, deluxe edition
                            if has_parent is False:
                                match_id.update({title_parse: cover_art})

                            # Most likely the intended item so return
                            if title.upper() == title_parse.upper():
                                return title_parse, cover_art

                    # Last resort filter if SKU wrong, but title matches.
                    elif title.upper() == title_parse.upper():
                        cover_art = self._get_cover(game)
                        if cover_art is not None:
                            if has_parent is False:
                                match_title.update({title_parse: cover_art})

        return self._get_similar(title, match_id, match_title)

    def _game(self, item):
        """Create game object."""
        if 'attributes' in item:
            game = item['attributes']
            return game

    def _is_game_type(self, game, game_type):
        """Check if item is a game and has SKU."""
        if 'game-content-type' in game and \
           game['game-content-type'] == game_type:
            if 'default-sku-id' in game:
                return True

    def _parse_id(self, _id):
        """Parse SKU to simplified ID."""
        full_id = _id
        full_id = full_id.split("-")
        full_id = full_id[1]
        full_id = full_id.split("_")
        parse_id = full_id[0]
        return parse_id

    def _get_cover(self, game):
        """Get cover art."""
        if 'thumbnail-url-base' in game:
            cover = 'thumbnail-url-base'
            cover_art = game[cover]
            return cover_art
        return

    def _get_similar(self, title, match_id, match_title):
        """Return similar title."""
        if match_id:
            _LOGGER.info("Found similar titles: %s", match_id)
            for _title, url in match_id.items():
                if title.upper() in _title.upper():
                    _LOGGER.info("Using similar title: %s", _title)
                    cover_art = url
                    return _title, cover_art
        elif match_title:
            _LOGGER.warning(
                "Found matching titles with incorrect SKU: %s", match_title)
            for _title, url in match_title.items():
                    _LOGGER.warning("Using matching title: %s", _title)
                    cover_art = url
                    return _title, cover_art
        return None, None


class Credentials:
    """The PS4 Credentials object. Masquerades as a PS4 to get credentials."""

    standby = '620 Server Standby'
    host_id = '1234567890AB'
    host_name = 'Home-Assistant'
    UDP_IP = '0.0.0.0'
    REQ_PORT = 997
    DDP_PORT = 987
    DDP_VERSION = '00020020'
    msg = None

    """
    PS4 listens on ports 987 and 997 (Priveleged).
    Must run command on python path:
    "sudo setcap 'cap_net_bind_service=+ep' /usr/bin/python3.5"
    """

    def __init__(self):
        """Init Cred Server."""
        self.iswakeup = False
        self.response = {
            'host-id': self.host_id,
            'host-type': 'PS4',
            'host-name': self.host_name,
            'host-request-port': self.REQ_PORT
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
        sock.settimeout(30)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((self.UDP_IP, self.DDP_PORT))
        except socket.error as error:
            _LOGGER.error(
                "Could not bind to port %s; \
                Ensure port is accessible and unused, %s",
                self.DDP_PORT, error)
            return

    def listen(self, timeout=120):
        """Listen and respond to requests."""
        start_time = time.time()
        sock = self.sock
        pings = 0
        while pings < 10:
            if timeout < time.time() - start_time:
                return
            try:
                response = sock.recvfrom(1024)
            except socket.error:
                sock.close()
                pings += 1
            data = response[0]
            address = response[1]
            if not data:
                pings += 1
                break
            if parse_ddp_response(data, 'search') == 'search':
                _LOGGER.debug("Search from: %s", address)
                msg = self.get_ddp_message(self.standby, self.response)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                try:
                    sock.sendto(msg.encode('utf-8'), address)
                except socket.error:
                    sock.close()
            if parse_ddp_response(data, 'wakeup') == 'wakeup':
                self.iswakeup = True
                _LOGGER.debug("Wakeup from: %s", address)
                creds = get_creds(data)
                sock.close()
                return creds
        return

    def get_ddp_message(self, status, data=None):
        """Get DDP message."""
        msg = u'HTTP/1.1 {}\n'.format(status)
        if data:
            for key, value in data.items():
                msg += u'{}:{}\n'.format(key, value)
        msg += u'device-discovery-protocol-version:{}\n'.format(
            self.DDP_VERSION)
        return msg


def parse_ddp_response(response, listen_type):
    """Parse the response."""
    rsp = response.decode('utf-8')
    if listen_type == 'search':
        if 'SRCH' in rsp:
            return 'search'
    elif listen_type == 'wakeup':
        if 'WAKEUP' in rsp:
            return 'wakeup'


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
