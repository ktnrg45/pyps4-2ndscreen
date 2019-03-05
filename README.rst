pyps4-homeassistant

============================

|PypiVersion| |PyPiPythonVersions|

Purpose
----------
To add a pure python implementation of ps4-waker. Including PS4 credential creation.
Integration with Home-Assistant. 

Compatibility
----------
Tested on:
Python 3.5/3.6/3.7
Home-Assistant/Hass.IO 0.89


**This package can be used as a standalone api. It does not require the use of Home Assistant.

Installation
----------
run "pip install pyps4-homeassistant"

Ports
----------
PS4 listens on ports 987 and 997 (Priveleged).
Must run command on python path if no access:

"sudo setcap 'cap_net_bind_service=+ep' /usr/bin/python3.5"

To Do List:
----------
- Port TCP and UDP functions to Asyncio.



References
----------

- https://github.com/dsokoloski/ps4-wake
- https://github.com/dhleong/ps4-waker
- https://github.com/hthiery/python-ps4

.. _ps4-waker: https://github.com/dhleong/ps4-waker


.. |PyPiVersion| image:: https://badge.fury.io/py/pyps4-homeassistant.svg
                 :target: http://badge.fury.io/py/pyps4-homeassistant
.. |PyPiPythonVersions| image:: https://img.shields.io/pypi/pyversions/pyps4-homeassistant.svg
                        :alt: Python versions
                        :target: http://badge.fury.io/py/pyps4-homeassistant
