PyPS4-2ndScreen
==========================================

|BuildStatus| |PypiVersion| |PyPiPythonVersions| |CodeCov|

|Docs|

Description
--------------------
A full Python implementation based on the Node.js package, ps4-waker.
This is an unofficial API for the PS4 2nd Screen App.

This module is mainly targeted towards developers although the module does include a basic CLI.


**Disclaimer**:
This project/module and I are not affiliated with or endorsed by Sony Interactive Entertainment LLC. As such this project may break at any time.

Compatibility
--------------------
Tested on:
Python 3.5/3.6/3.7

Installation
--------------------
Package can be installed with pip or from source.

It is advised to install the module in a virtual env.

Create virtual env first:

.. code:: bash

    python -m venv .

    source bin/activate

To install run:

.. code:: bash

    pip install pyps4-2ndscreen

To install from source clone this repository and run from top-level:

.. code:: bash

    python setup.py install

Protocol
--------------------
UDP is used to get status updates and retrieve user credentials. TCP is used to send commands to the PS4 Console.

Ports
--------------------
PS4 listens on ports 987 (Priveleged) to fetch user PSN credentials.
Must run command on python path if no access.

In order to obtain user credentials, the Python Interpreter needs access to port 987 on the host system.
The credential service pretends to be a PS4 console and will receive broadcast packets from the PS4 2nd Screen app on port 987.

Example:

.. code:: bash

    sudo setcap 'cap_net_bind_service=+ep' /usr/bin/python3.5
    
This is so you do not need sudo/root priveleges to run.


Cover Art Issues
--------------------
If you find that media art cannot be found. Please post an issue with your Region, Country, Title of game, an ID of game.

Known Issues
--------------------
- PS Command inconsistent.
- On-Screen Keyboard is not implemented.


Credits
--------------------
Thanks to hthiery for writing the underlying socket protocol in Python. https://github.com/hthiery/python-ps4

References
--------------------

- https://github.com/dsokoloski/ps4-wake
- https://github.com/dhleong/ps4-waker
- https://github.com/hthiery/python-ps4


.. |BuildStatus| image:: https://travis-ci.org/ktnrg45/pyps4-2ndscreen.png?branch=master
                 :target: https://travis-ci.org/ktnrg45/pyps4-2ndscreen
.. |PyPiVersion| image:: https://badge.fury.io/py/pyps4-2ndscreen.svg
                 :target: http://badge.fury.io/py/pyps4-2ndscreen
.. |PyPiPythonVersions| image:: https://img.shields.io/pypi/pyversions/pyps4-2ndscreen.svg
                        :alt: Python versions
                        :target: http://badge.fury.io/py/pyps4-2ndscreen
.. |Docs| image:: https://readthedocs.org/projects/pyps4-2ndscreen/badge/?version=dev
          :target: https://pyps4-2ndscreen.readthedocs.io/en/dev/?badge=dev
          :alt: Documentation Status
.. |CodeCov| image:: https://codecov.io/gh/ktnrg45/pyps4-2ndscreen/branch/dev/graph/badge.svg               
             :target: https://codecov.io/gh/ktnrg45/pyps4-2ndscreen/
             :alt: Code Coverage
