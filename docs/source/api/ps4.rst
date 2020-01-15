PS4
=====
The PS4 class is the main object for interfacing with a PS4 console. You should only call methods directly from this class.
There are two versions: :class:`pyps4_2ndscreen.ps4.Ps4Async` and :class:`pyps4_2ndscreen.ps4.Ps4Legacy`. You may instantiate either, but you should not use the :class:`pyps4_2ndscreen.ps4.Ps4Base` class directly.

:class:`pyps4_2ndscreen.ps4.Ps4Async` is the recommended class. You should have an asyncio event loop running to call/await its coroutines.
:class:`pyps4_2ndscreen.ps4.Ps4Legacy` is provided for reference and is deprecated. Some of its methods may be broken.


.. autoclass:: pyps4_2ndscreen.ps4.Ps4Base
    :noindex:
    :members:

.. autoclass:: pyps4_2ndscreen.ps4.Ps4Async
    :noindex:
    :members:
    :show-inheritance:

.. autoclass:: pyps4_2ndscreen.ps4.Ps4Legacy
    :noindex:
    :members:
    :show-inheritance:
