DDP (Device Discovery Protocol)
===============================
The DDP module allows for discovery of PS4 devices.


DDP Protocol
-------------
The :class:`pyps4_2ndscreen.ddp.DDPProtocol` is a handler for DDP/UDP messages. This class must be used in the event loop. It can handle multiple :class:`pyps4_2ndscreen.ps4.Ps4Async` objects.

.. autoclass:: pyps4_2ndscreen.ddp.DDPProtocol
    :members:
    :exclude-members: connection_lost, connection_made, datagram_received, error_received, send_msg

.. automethod:: pyps4_2ndscreen.ddp.async_create_ddp_endpoint
