*************
Command Line
*************

Usage: pyps4-2ndscreen [OPTIONS] COMMAND [ARGS]...

  Pyps4-2ndscreen CLI. Allows for simple commands from terminal.

Example:

.. code:: bash

    pyps4-2ndscreen start CUSA10000 -i 192.168.0.1 -c yourCredentials

Options:
  --version          Show the version and exit.
  --help             Show this message and exit.
  --ip_address, -i   IP Address of PS4.
  --credentials, -c  Credentials to use.

Commands
----------
.. list-table:: Commands
   :widths: 25 25
   :header-rows: 1

   * - Command
     - Description
   * - credential
     - Get PSN Credentials.
   * - link
     - Configure/Link PS4.
   * - remote
     - Send Remote Control.
   * - search
     - Search for PS4 devices.
   * - standby
     - Place PS4 in Standby.
   * - start
     - Start title.
   * - status
     - Get status of PS4.
   * - wakeup
     - Wakeup PS4.
   * - interactive
     - Toggle interactive mode for continuous control.

Arguments
----------
.. list-table:: Arguments
   :widths: 25 25
   :header-rows: 1

   * - Argument
     - Description
   * - Title ID
     - Title ID when using command `start`.
   * - Button
     - Button when using command `remote`.

Buttons
----------
**Note:** Not to be confused with DualShock4 Buttons.

.. list-table:: Buttons
   :widths: 25 25
   :header-rows: 1

   * - Button
     - Description
   * - ps
     - PS (PlayStation)
   * - ps_hold
     - PS Hold/Long Press
   * - enter
     - Enter
   * - option
     - Option
   * - left
     - Swipe Left
   * - right
     - Swipe Right
   * - up
     - Swipe Up
   * - down
     - Swipe Down
