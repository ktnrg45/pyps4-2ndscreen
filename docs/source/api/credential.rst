Credential
===============================
The `Credential` module allows for fetching of PSN user credentials using the official **PS4 2nd Screen App** on iOS and Android.


Service
-------------
The :class:`pyps4_2ndscreen.credential.Credentials` class is a service to allow fetching of PSN credentials.
**Note:** The service requires `port 987`. This is a priveleged port so some operating systems will not allow you to use this port without root/sudo privileges. If you would like to use the service with normal privileges you can try the command below:

.. code:: bash

	sudo setcap ‘cap_net_bind_service=+ep’ /usr/bin/python3.5

This command works for Debian based systems. The `/usr/bin/python3.5` should be replaced with the absolute path to your Python interpreter.


.. autoclass:: pyps4_2ndscreen.credential.Credentials
    :members:
    :exclude-members: get_ddp_message, parse_ddp_response, get_creds, start
