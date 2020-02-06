PS4
=====
The PS4 class is the main object for interfacing with a PS4 console. You should only call methods directly from this class.
There are two versions: :class:`pyps4_2ndscreen.ps4.Ps4Async` and :class:`pyps4_2ndscreen.ps4.Ps4Legacy`.


Base Version
-------------

The :class:`pyps4_2ndscreen.ps4.Ps4Base` class should not be used directly.


.. autoclass:: pyps4_2ndscreen.ps4.Ps4Base
    :members:


Async Version
--------------

:class:`pyps4_2ndscreen.ps4.Ps4Async` is the recommended class. It is best suited for runtime applications. You should have an asyncio event loop running to call/await its coroutines.

.. autoclass:: pyps4_2ndscreen.ps4.Ps4Async
    :members:
    :exclude-members: open, launch


Legacy Version
--------------

:class:`pyps4_2ndscreen.ps4.Ps4Legacy` is best suited for one-time commands.

.. autoclass:: pyps4_2ndscreen.ps4.Ps4Legacy
    :members:
    :exclude-members: open, launch, delay
