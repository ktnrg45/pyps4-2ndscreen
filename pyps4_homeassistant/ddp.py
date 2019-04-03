# -*- coding: utf-8 -*-
"""Device Discovery Protocol for PS4."""
from __future__ import print_function

import re
import socket
import logging

_LOGGER = logging.getLogger(__name__)

UDP_IP = '0.0.0.0'
UDP_PORT = 0

DDP_PORT = 987
DDP_VERSION = '00020020'


def get_ddp_message(msg_type, data=None):
    """Get DDP message."""
    msg = u'{} * HTTP/1.1\n'.format(msg_type)
    if data:
        for key, value in data.items():
            msg += '{}:{}\n'.format(key, value)
    msg += 'device-discovery-protocol-version:{}\n'.format(DDP_VERSION)
    return msg


def parse_ddp_response(rsp):
    """Parse the response."""
    data = {}
    app_name = None
    for line in rsp.splitlines():
        if 'running-app-name' in line:
            app_name = line
            app_name = app_name.replace('running-app-name:', '')
        re_status = re.compile(r'HTTP/1.1 (?P<code>\d+) (?P<status>.*)')
        line = line.strip()
        # skip empty lines
        if not line:
            continue
        elif re_status.match(line):
            data[u'status_code'] = int(re_status.match(line).group('code'))
            data[u'status'] = re_status.match(line).group('status')
        else:
            values = line.split(':')
            data[values[0]] = values[1]
    if app_name is not None:
        data['running-app-name'] = app_name
    return data


def get_ddp_search_message():
    """Get DDP search message."""
    return get_ddp_message('SRCH')


def get_ddp_wake_message(credential):
    """Get DDP wake message."""
    data = {
        'user-credential': credential,
        'client-type': 'a',
        'auth-type': 'C',
    }
    return get_ddp_message('WAKEUP', data)


def get_ddp_launch_message(credential):
    """Get DDP launch message."""
    data = {
        'user-credential': credential,
        'client-type': 'a',
        'auth-type': 'C',
    }
    return get_ddp_message('LAUNCH', data)


def _send_recv_msg(host, broadcast, msg, receive=True):
    """Send a ddp message and receive the response."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.settimeout(3.0)

    if broadcast:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        _host = host or '255.255.255.255'
    else:
        _host = host

    sock.sendto(msg.encode('utf-8'), (_host, DDP_PORT))

    if receive:
        return sock.recvfrom(1024)
    return None


def _send_msg(host, broadcast, msg):
    """Send a ddp message."""
    _send_recv_msg(host, broadcast, msg, receive=False)


def search(host=None, broadcast=True):
    """Discover PS4s."""
    msg = get_ddp_search_message()
    data, addr = _send_recv_msg(host, broadcast, msg)
    if data is not None:
        ps_list = []
        data = parse_ddp_response(data.decode('utf-8'))
        data[u'host-ip'] = addr[0]
        ps_list.append(data)
        return ps_list
    return None


def get_status(host):
    """Get status."""
    ps_list = search(host=host)
    return ps_list[0]


def wakeup(host, credential, broadcast=None):
    """Wakeup PS4s."""
    msg = get_ddp_wake_message(credential)
    _send_msg(host, broadcast, msg)


def launch(host, credential, broadcast=None):
    """Launch."""
    msg = get_ddp_launch_message(credential)
    _send_msg(host, broadcast, msg)


class Discovery:
    """Device Discovery server."""

    def __init__(self):
        """Init."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(6.0)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.msg = get_ddp_search_message()
        self.host = '255.255.255.255'
        self.ps_list = []

    def search(self, host):
        """Search for Devices."""
        if host is None:
            host = self.host
        finished = False
        try:
            self.send(host)
        except (socket.error, socket.timeout):
            self.sock.close()
            return self.ps_list
        while finished is False:
            try:
                device = self.receive()
                if device not in self.ps_list:
                    self.ps_list.append(device)
            except (socket.error, socket.timeout):
                self.sock.close()
                return self.ps_list

    def send(self, host):
        """Broadcast Message."""
        self.sock.sendto(self.msg.encode('utf-8'), (host, DDP_PORT))

    def receive(self):
        """Receive Message."""
        data, addr = self.sock.recvfrom(1024)
        if data is not None:
            data = parse_ddp_response(data.decode('utf-8'))
            data[u'host-ip'] = addr[0]
            return data
        return None
