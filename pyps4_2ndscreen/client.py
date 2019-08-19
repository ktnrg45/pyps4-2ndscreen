# -*- coding: utf-8 -*-
"""Asyncio Client Example for PS4."""
import asyncio
import logging

from .ddp import async_create_ddp_endpoint
from .ps4 import Ps4Async
from .errors import NotReady

_LOGGER = logging.getLogger(__name__)


class Client():
    """Status Client Class for PS4."""

    def __init__(self, loop=None):
        """Init."""
        self.task = None
        self.last_poll = 0
        self.poll_interval = 0
        self.ddp_protocol = None
        self.ps4_devices = []
        self.callbacks = {}
        self.running = False

        if loop is None:
            self.loop = asyncio.get_event_loop()

    def add_ps4(self, ip_address, creds):
        """Add PS4 to Client."""
        ps4 = Ps4Async(ip_address, creds)
        self.ps4_devices.append(ps4)

    async def init_ps4(self, ps4=None):
        """Init PS4 devices and DDP Protocol."""
        if ps4 is not None and self.ddp_protocol is not None:
            await self.loop.run_in_executor(None, ps4.get_status())
            ps4.set_protocol(self.ddp_protocol)
        else:
            _, self.ddp_protocol = await async_create_ddp_endpoint()

            for device in self.ps4_devices:
                await self.loop.run_in_executor(None, device.get_status)
                device.set_protocol(self.ddp_protocol)
                device.add_callback(self.status_callback)

    def start(self, poll_interval=10):
        """Start client/loop."""
        if not self.ps4_devices:
            return

        self.poll_interval = poll_interval
        if self.poll_interval < 1:
            raise RuntimeError(
                "Polling Interval must be greater than 1 second")
        try:
            _LOGGER.info("Starting Client...")
            self.running = True
            self.task = asyncio.ensure_future(self.run_client())
            self.loop.run_until_complete(self.task)
        except KeyboardInterrupt:
            self.stop()
        finally:
            _LOGGER.info("Client Stopped")

    def stop(self):
        """Stop Client."""
        if self.task:
            _LOGGER.info("Stopping Client...")
            self.running = False
            try:
                self.task.cancel()
                self.task.exception()
                self.loop.close()
            except asyncio.InvalidStateError:
                pass

    def status_callback(self):
        """Callback for PS4 Status Changed."""
        _LOGGER.debug("Callback called by DDP Protocol")
        for ps4 in self.ps4_devices:
            status = self.ps4.status
            _LOGGER.info(status)

    async def run_client(self):
        """Running Loop."""
        # Create DDP transport for status updates.
        if self.ddp_protocol is None:
            await self.init_ps4()
            _LOGGER.debug("Client Started")

        if self.running:
            await self.status_handler()
        else:
            self.ddp_protocol.close()

    async def status_handler(self):
        """Poll PS4 for status."""
        if self.loop.time() - self.last_poll > self.poll_interval:
            polled_hosts = []

            for ps4 in self.ps4_devices:
                if ps4.host not in polled_hosts:
                    _LOGGER.debug("Getting status for: %s", ps4.host)
                    ps4.get_status()
                    polled_hosts.append(ps4.host)

                if not ps4.connected and not ps4.is_standby \
                        and ps4.is_available:
                    try:
                        await ps4.async_connect()
                    except NotReady:
                        pass

            self.last_poll = self.loop.time()
        await asyncio.sleep(1.0)
        await self.run_client()
