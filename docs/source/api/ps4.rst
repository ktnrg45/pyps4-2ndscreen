PS4
=====
The PS4 class is the main object for interfacing with a PS4 console. You should only call methods directly from this class.
There are two versions: Ps4Async and Ps4Legacy. You may instantiate either, but you should not use the Ps4Base class directly.

Ps4Async is the recommended class. You should have an asyncio event loop running to call/await its coroutines.
Ps4Legacy is provided for reference and is deprecated. Some of its methods may be broken.

.. automodule:: pyps4_2ndscreen.ps4

    .. autoclass:: Ps4Base
        :members:

    .. autoclass:: Ps4Async
        :members:
    
    .. autoclass:: Ps4Legacy
        :members:
