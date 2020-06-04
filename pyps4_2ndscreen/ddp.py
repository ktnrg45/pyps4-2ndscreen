# -*- coding: utf-8 -*-
"""Device Discovery Protocol for PS4."""
from __future__ import print_function

import re
import socket
import logging
import select
import asyncio
from typing import Optional

_LOGGER = logging.getLogger(__name__)

BROADCAST_IP = '255.255.255.255'
UDP_IP = '0.0.0.0'
UDP_PORT = 0

DDP_PORT = 987
DDP_VERSION = '00020020'
DDP_TYPE_SEARCH = 'SRCH'
DDP_TYPE_LAUNCH = 'LAUNCH'
DDP_TYPE_WAKEUP = 'WAKEUP'
DDP_MSG_TYPES = (DDP_TYPE_SEARCH, DDP_TYPE_LAUNCH, DDP_TYPE_WAKEUP)

DEFAULT_POLL_COUNT = 5


class DDPProtocol(asyncio.DatagramProtocol):
    """Async UDP Client."""

    def __init__(self, max_polls=DEFAULT_POLL_COUNT):
        """Init Instance."""
        super().__init__()
        self.callbacks = {}
        self.max_polls = max_polls
        self._transport = None
        self._remote_port = DDP_PORT
        self._local_port = UDP_PORT
        self._message = get_ddp_search_message()

    def __repr__(self):
        return (
            "<{}.{} local_port={} max_polls={}>".format(
                self.__module__,
                self.__class__.__name__,
                self.local_port,
                self.max_polls,
            )
        )

    def _set_write_port(self, port):
        """Only used for tests."""
        self._remote_port = port

    def set_max_polls(self, poll_count: int):
        """Set number of unreturned polls neeeded to assume no status."""
        self.max_polls = poll_count

    def connection_made(self, transport):
        """On Connection."""
        self._transport = transport
        sock = self._transport.get_extra_info('socket')
        self._local_port = sock.getsockname()[1]
        _LOGGER.debug("PS4 Transport created with port: %s", self.local_port)

    def send_msg(self, ps4, message=None):
        """Send Message."""
        if message is None:
            message = self._message
        sock = self._transport.get_extra_info('socket')
        _LOGGER.debug("SENT MSG @ DDP Proto: %s", sock.getsockname())
        self._transport.sendto(
            message.encode('utf-8'),
            (ps4.host, self._remote_port))

        # Track polls that were never returned.
        ps4.poll_count += 1

        # Assume PS4 is not available.
        if ps4.poll_count > self.max_polls:
            if not ps4.unreachable:
                _LOGGER.info("PS4 @ %s is unreachable", ps4.host)
                ps4.unreachable = True
            ps4.status = None
            if ps4.host in self.callbacks:
                callback = self.callbacks[ps4.host].get(ps4)
                if callback is not None:
                    callback()

    def datagram_received(self, data, addr):
        """When data is received."""
        if data is not None:
            sock = self._transport.get_extra_info('socket')
            _LOGGER.debug("RECV MSG @ DDP Proto: %s", sock.getsockname())
            self._handle(data, addr)

    def _handle(self, data, addr):
        data = parse_ddp_response(data.decode('utf-8'))
        data[u'host-ip'] = addr[0]

        address = addr[0]

        if address in self.callbacks:
            for ps4, callback in self.callbacks[address].items():
                ps4.poll_count = 0
                ps4.unreachable = False
                old_status = ps4.status
                ps4.status = data
                if old_status != data:
                    _LOGGER.debug("Status: %s", ps4.status)
                    callback()

    def connection_lost(self, exc):
        """On Connection Lost."""
        if self._transport is not None:
            _LOGGER.error("DDP Transport Closed")
            self._transport.close()

    def error_received(self, exc):
        """Handle Exceptions."""
        _LOGGER.warning("Error received at DDP Transport")

    def close(self):
        """Close Transport."""
        self._transport.close()
        self._transport = None
        _LOGGER.info(
            "Closing DDP Transport: %s",
            self._local_port)

    def add_callback(self, ps4, callback):
        """Add callback to list. One per PS4 Object."""
        if ps4.host not in self.callbacks:
            self.callbacks[ps4.host] = {}
        self.callbacks[ps4.host][ps4] = callback

    def remove_callback(self, ps4, callback):
        """Remove callback from list."""
        if ps4.host in self.callbacks:
            if self.callbacks[ps4.host][ps4] == callback:
                self.callbacks[ps4.host].pop(ps4)

                # If no callbacks remove host key also.
                if not self.callbacks[ps4.host]:
                    self.callbacks.pop(ps4.host)

    @property
    def local_port(self):
        """Return local port."""
        return self._local_port

    @property
    def remote_port(self):
        """Return remote port."""
        return self._remote_port


async def async_create_ddp_endpoint(sock=None):
    """Create Async UDP endpoint."""
    local_addr = (UDP_IP, UDP_PORT)
    reuse_port = hasattr(socket, 'SO_REUSEPORT')
    allow_broadcast = True
    loop = asyncio.get_event_loop()
    if sock is not None:
        sock.settimeout(0)
        local_addr = None
        reuse_port = None
        allow_broadcast = None
    connect = loop.create_datagram_endpoint(
        lambda: DDPProtocol(), local_addr=local_addr,  # noqa: pylint: disable=unnecessary-lambda
        reuse_port=reuse_port, allow_broadcast=allow_broadcast, sock=sock)
    transport, protocol = await loop.create_task(connect)
    return transport, protocol


def get_ddp_message(msg_type, data=None):
    """Get DDP message."""
    if msg_type not in DDP_MSG_TYPES:
        raise TypeError(
            "DDP MSG type: '{}' is not a valid type".format(msg_type))
    msg = u'{} * HTTP/1.1\n'.format(msg_type)
    if data is not None:
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
        if re_status.match(line):
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


def get_socket(timeout=3, port: Optional[int] = UDP_PORT):
    """Return DDP socket object."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        if port != UDP_PORT:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        sock.bind((UDP_IP, port))
    except socket.error as error:
        _LOGGER.error(
            "Error getting DDP socket with port: %s: %s", port, error)
        sock = None
    return sock


def _send_recv_msg(host, broadcast, msg, receive=True, sock=None):
    """Send a ddp message and receive the response."""
    if sock is None:
        sock = get_socket()

    if broadcast:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        _host = host or BROADCAST_IP
    else:
        _host = host
    _LOGGER.debug(
        "Sent DDP MSG: SRC=%s DEST=%s", sock.getsockname(), (_host, DDP_PORT))
    sock.sendto(msg.encode('utf-8'), (_host, DDP_PORT))

    if receive:
        available, _, _ = select.select([sock], [], [], 0.01)
        if sock in available:
            return sock.recvfrom(1024)
    return None


def _send_msg(host, broadcast, msg, sock=None):
    """Send a ddp message."""
    return _send_recv_msg(host, broadcast, msg, receive=False, sock=sock)


def send_search_msg(host, sock=None):
    """Send message only."""
    msg = get_ddp_search_message()
    return _send_msg(host, True, msg, sock=sock)


def search(host=None, broadcast=True, sock=None):
    """Discover PS4s."""
    ps_list = None
    msg = get_ddp_search_message()
    data, addr = _send_recv_msg(host, broadcast, msg, sock=sock)
    if data is not None:
        ps_list = []
        data = parse_ddp_response(data.decode('utf-8'))
        data[u'host-ip'] = addr[0]
        ps_list.append(data)
    return ps_list


def get_status(host, sock=None):
    """Get status."""
    try:
        ps_list = search(host=host, sock=sock)
    except TypeError:
        return None
    return ps_list[0]


def wakeup(host, credential, broadcast=False, sock=None):
    """Wakeup PS4s."""
    msg = get_ddp_wake_message(credential)
    _send_msg(host, broadcast, msg, sock)


def launch(host, credential, broadcast=False, sock=None):
    """Launch."""
    msg = get_ddp_launch_message(credential)
    _send_msg(host, broadcast, msg, sock)


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
        null_responses = 0
        try:
            self.send(host)
        except (socket.error, socket.timeout):
            self.sock.close()
            return self.ps_list

        while null_responses < 3:
            try:
                device = self.receive()
                if device is not None:
                    if device not in self.ps_list:
                        self.ps_list.append(device)
                        continue
                null_responses += 1
            except (socket.error, socket.timeout):
                self.sock.close()
                return self.ps_list

        return self.ps_list

    def send(self, host):
        """Broadcast Message."""
        self.sock.sendto(self.msg.encode('utf-8'), (host, DDP_PORT))

    def receive(self):
        """Receive Message."""
        data = None
        available, _, _ = select.select([self.sock], [], [], 0.01)
        if self.sock in available:
            data, addr = self.sock.recvfrom(1024)
            if data is not None:
                data = parse_ddp_response(data.decode('utf-8'))
                data[u'host-ip'] = addr[0]
        return data
