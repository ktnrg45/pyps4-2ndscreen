# -*- coding: utf-8 -*-
"""Credential fetcher for 2nd Screen app."""
import logging
import socket
import time

from .errors import CredentialTimeout, UnknownDDPResponse

_LOGGER = logging.getLogger(__name__)


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
                return None
            try:
                response = sock.recvfrom(1024)
                data = response[0]
                address = response[1]
            except socket.error:
                sock.close()
                pings += 1
            except UnboundLocalError:
                raise CredentialTimeout
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
        return None

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
