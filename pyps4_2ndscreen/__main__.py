# -*- coding: utf-8 -*-
"""Main File for pyps4-2ndscreen."""
import logging

import click

from .helpers import Helper

_LOGGER = logging.getLogger(__name__)


def _get_ps4(ip_address=None, credentials=None, no_creds=False):
    from .ps4 import Ps4Legacy
    helper = Helper()

    if credentials is None:
        data = helper.load_files('credentials')
        credentials = data['credentials']
    if ip_address is not None and credentials is None:
        if not no_creds:
            print('--credentials option required')
            return None
    if ip_address is not None and credentials is not None:
        return Ps4Legacy(ip_address, credentials)

    helper = Helper()
    is_data = helper.check_data('ps4')
    if not is_data:
        print("No configuration found. Configure PS4 then retry.")
        return None
    data = helper.load_files('ps4')
    if len(data) > 1 and ip_address is None:
        print("Multiple PS4 configs found. Specify IP Address.")
        return None
    if ip_address is None:
        for key, value in data.items():
            ip_address = key
            creds = value
    else:
        creds = data.get(ip_address)
    _ps4 = Ps4Legacy(ip_address, creds)
    return _ps4


def _check_creds(credentials):
    helper = Helper()
    existing_creds = False
    if credentials is None:
        _data = helper.load_files('credentials')
        credentials = _data.get('credentials')

        if credentials is not None:
            existing_creds = True
        _credentials = _credentials_func()
        if _credentials is None:
            if existing_creds:
                print('Using existing credentials.')
            else:
                return None
        else:
            credentials = _credentials
    return credentials


def _print_result(success, command):
    if success:
        print("Command Succeeded: {}".format(command))
    else:
        print("Command Failed: {}".format(command))


def _overwrite_creds():
    proceed = input(
        "Overwrite existing credentials? Enter 'y' for yes.\n> ")
    if proceed.lower() != 'y':
        return False
    return True


@click.group()
@click.version_option()
def cli():
    """Pyps4-2ndscreen CLI. Allows for simple commands from terminal."""
    logging.basicConfig(level=logging.INFO)


@cli.command(
    help='Wakeup PS4. Example: pyps4-2ndscreen wakeup '
    '-i 192.168.0.1 -c yourcredentials')
@click.option('-i', '--ip_address')
@click.option('-c', '--credentials')
def wakeup(ip_address=None, credentials=None):
    """Wakeup PS4"""
    _ps4 = _get_ps4(ip_address, credentials)
    if _ps4 is not None:
        _ps4.wakeup()
        print("Wakeup Sent to {}".format(ip_address))


@cli.command(
    help='Place PS4 in Standby. Example: pyps4-2ndscreen standby '
    '-i 192.168.0.1 -c yourcredentials')
@click.option('-i', '--ip_address')
@click.option('-c', '--credentials')
def standby(ip_address=None, credentials=None):
    """Standby."""
    _ps4 = _get_ps4(ip_address, credentials)
    if _ps4 is not None:
        success = _ps4.standby()
        _print_result(success, 'Standby')


@cli.command(
    help='Send Remote Control. Example: pyps4-2ndscreen remote ps '
    '-i 192.168.0.1 -c yourcredentials')
@click.option('-i', '--ip_address')
@click.option('-c', '--credentials')
@click.argument('command', required=True)
def remote(command, ip_address=None, credentials=None):
    """Send remote control."""
    _ps4 = _get_ps4(ip_address, credentials)
    if _ps4 is not None:
        success = _ps4.remote_control(command)
        _print_result(success, "Remote '{}'".format(command))


@cli.command(
    help='Start title. Example: pyps4-2ndscreen start CUSA10000 '
    '-i 192.168.0.1 -c yourcredentials')
@click.option('-i', '--ip_address')
@click.option('-c', '--credentials')
@click.argument('title_id', required=True)
def start(title_id, ip_address=None, credentials=None):
    """Start Title."""
    _ps4 = _get_ps4(ip_address, credentials)
    if _ps4 is not None:
        print("Starting title: {}".format(title_id))
        success = _ps4.start_title(title_id)
        _print_result(success, "Start '{}'".format(title_id))


@cli.command(
    help='Configure/Link PS4. Example: pyps4-2ndscreen link '
    '-i 192.0.0.1 -c yourcredentials')
@click.option('-i', '--ip_address')
@click.option('-c', '--credentials')
def link(ip_address=None, credentials=None):
    """Link or register device with PS4."""
    _link_func(ip_address, credentials)


def _link_func(ip_address, credentials):
    helper = Helper()
    credentials = _check_creds(credentials)
    if credentials is None:
        return False

    device_list = _search_func()
    if ip_address not in device_list and ip_address is not None:
        print(
            "PS4 @ {} can not be found. Ensure PS4 is on and connected."
            .format(ip_address))
        return False

    if ip_address is None and len(device_list) > 1:
        ip_address = input("Enter IP Address you would like to link:\n> ")
        if ip_address not in device_list:
            print("IP Address not found.")
            return False
    else:
        ip_address = device_list[0]

    pin = input(
        "On PS4, Go to:\n\nSettings -> Mobile App Connection Settings -> "
        "Add Device\n\nEnter pin that is displayed:\n> "
    )
    pin = pin.replace(' ', '')
    if not pin.isdigit() or len(pin) != 8:
        print("PIN Invalid. Must be 8 numbers.")
        return False
    is_ready, is_login = helper.link(ip_address, credentials, pin)
    if is_ready and is_login:
        print('\nPS4 Successfully Linked.')
        file_name = helper.check_files('ps4')
        data = {ip_address: credentials}
        helper.save_files(data, file_type='ps4')
        print("PS4 Data saved to: {}".format(file_name))
        return True
    print("Linking Failed.")
    if not is_ready:
        print("PS4 not On or connected.")
    else:
        print("Login failed. Check pin code and try again.")
    return False


@cli.command(help='Search for PS4 devices. Example: pyps4-2ndscreen search')
def search() -> list:
    """Search LAN for PS4's."""
    _search_func()


def _search_func():
    helper = Helper()
    devices = helper.has_devices()
    device_list = [device["host-ip"] for device in devices]
    print("Found {} devices:".format(len(device_list)))
    for ip_address in device_list:
        print(ip_address)
    return device_list


@cli.command(
    help='Get status of PS4. Example: pyps4-2ndscreen status -i 192.168.0.1 ')
@click.option('-i', '--ip_address')
def status(ip_address=None):
    """Get Status of PS4."""
    d_status = {}
    if ip_address is not None:
        helper = Helper()
        devices = helper.has_devices(ip_address)
        if devices:
            d_status = devices[0]

    else:
        _ps4 = _get_ps4(ip_address, None, True)
        if _ps4 is not None:
            d_status = _ps4.get_status()
            ip_address = _ps4.host

    if d_status:
        print("\nGot Status for {}:\n".format(ip_address))
        for key, value in d_status.items():
            print("{}: {}".format(key, value))

    elif ip_address is not None:
        print(
            "PS4 @ {} can not be found."
            .format(ip_address))
    else:
        print("Or use --ip_address option.")


@cli.command(help='Get PSN Credentials. Example: pyps4-2ndscreen credentials ')
def credential():
    """Get and save credentials."""
    _credentials_func()


def _credentials_func():
    from .credential import DEFAULT_DEVICE_NAME
    from .ddp import DDP_PORT

    helper = Helper()
    is_creds = helper.check_data('credentials')
    if is_creds:
        if not _overwrite_creds():
            print('Aborting Credential Service...\n')
            return None
    error = helper.port_bind([DDP_PORT])
    if error is not None:
        return None

    print("\nWith the PS4 2nd Screen app, refresh devices "
          "and select the device '{}'.\n".format(DEFAULT_DEVICE_NAME))
    print("To cancel press 'CTRL + C'.\n")

    creds = helper.get_creds()
    data = {'credentials': creds}
    if creds is not None:
        print("PSN Credentials is: '{}'".format(creds))
        file_name = helper.check_files('credentials')
        helper.save_files(
            data=data, file_type='credentials')
        print("Credentials saved to: {}\n".format(file_name))
        return creds
    print("No credentials found. Stopped credential service.")
    return None


@cli.command(
    help='Toggle interactive mode for continuous control. '
    'Example: pyps4-2ndscreen interactive '
    '-i 192.168.0.1 -c yourcredentials')
@click.option('-i', '--ip_address')
@click.option('-c', '--credentials')
def interactive(ip_address=None, credentials=None):
    """Interactive."""
    import curses

    _ps4 = _get_ps4(ip_address, credentials)
    if _ps4 is not None:
        curses.wrapper(_interactive, _ps4)


def _interactive(stdscr, ps4):
    import curses
    import time
    from .ps4 import NotReady

    MAPPINGS = {
        'W': ('wakeup', ps4.wakeup),
        'S': ('standby', ps4.standby),
        'B': ('start_title', ps4.start_title),
        's': ('status_request', ps4.get_status),
        'KEY_LEFT': ('remote', ps4.remote_control, 'left'),
        'KEY_RIGHT': ('remote', ps4.remote_control, 'right'),
        'KEY_UP': ('remote', ps4.remote_control, 'up'),
        'KEY_DOWN': ('remote', ps4.remote_control, 'down'),
        '\n': ('remote', ps4.remote_control, 'enter'),
        'KEY_BACKSPACE': ('remote', ps4.remote_control, 'back'),
        'o': ('remote', ps4.remote_control, 'option'),
        'p': ('remote', ps4.remote_control, 'ps'),
        'P': ('remote', ps4.remote_control, 'ps_hold'),
    }

    def _init_window(stdscr, status):
        stdscr.erase()
        stdscr.move(stdscr.getyx()[0], 0)
        stdscr.addstr(
            "Interactive mode, press 'q' to exit. "
            "Press 'k' for key mappings.\n")
        if status is not None:
            stdscr.addstr(
                "Info: IP: {}, MAC: {}, Name: {}\n"
                "Status: {} | Playing: {} ({})\n".format(
                    status.get('host-ip'),
                    status.get('host-id'),
                    status.get('host-name'),
                    status.get('status'),
                    status.get('running-app-name'),
                    status.get('running-app-titleid'),
                ), curses.color_pair(1))
        else:
            stdscr.addstr(
                "Status: {}\n".format('Not Available'), curses.color_pair(2))
        stdscr.move(stdscr.getyx()[0] + 1, 0)

    def _show_mapping(stdscr):
        stdscr.addstr(
            "Key : Action |\n",
            curses.color_pair(3))

        for key, values in MAPPINGS.items():
            if key == '\n':
                key = 'KEY_ENTER'
            if values[0] == 'remote':
                value = values[2]
            else:
                value = values[0]
            stdscr.addstr(
                "{} : {} | ".format(key, value),
                curses.color_pair(3))
        stdscr.addstr('\n>')

    def _handle_status(stdscr, status):
        helper = Helper()
        games = helper.load_files('games')
        stdscr.addstr(
            "Status Updated: {} | {}\n".format(
                status.get('status'), status.get('running-app-name')),
            curses.color_pair(1))
        title_id = status.get('running-app-titleid')
        if title_id is not None:
            if title_id not in games:
                games[title_id] = status.get('running-app-name')
                helper.save_files(games, 'games')

    def _show_game_mapping():
        mapping = {}
        helper = Helper()
        games = helper.load_files('games')
        if games:
            x = 1
            mapping['0'] = ('', 'Cancel')
            for key, value in games.items():
                mapping[str(x)] = (key, value)
                x += 1
        return mapping

    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_WHITE)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_WHITE)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)
    ps4.auto_close = False
    status = None
    height, width = stdscr.getmaxyx()
    status = ps4.get_status()
    _handle_status(stdscr, status)
    _init_window(stdscr, status)
    _show_mapping(stdscr)

    running = True
    key = None
    start_timer = 0
    while running:
        fail = False
        stdscr.nodelay(True)
        if time.time() - start_timer > 10:
            start_timer = time.time()
            ps4.get_status()
            if ps4.loggedin:
                ps4.send_status()
        try:
            arg = ''
            if status != ps4.status:
                status = ps4.status
                if status is not None:
                    _handle_status(stdscr, status)

            key = stdscr.getkey()
        except curses.error:
            continue
        try:
            if key == "q":
                running = False
            elif key == "k":
                _show_mapping(stdscr)
            elif key in MAPPINGS:
                mapping = MAPPINGS.get(key)
                action = mapping[0]
                command = mapping[1]
                if action == 'status_request':
                    status = command()
                    if status is not None:
                        for item, value in status.items():
                            stdscr.addstr('{}: {}\n'.format(item, value))
                        stdscr.addstr('\n')
                elif action == 'wakeup':
                    command()
                else:
                    try:
                        if action == 'remote':
                            arg = mapping[2]
                            command(arg)
                        elif action == 'start_title':
                            stdscr.nodelay(False)
                            mapping = _show_game_mapping()
                            if mapping:
                                stdscr.addstr(
                                    "Options:\n", curses.color_pair(3))
                                for key, value in mapping.items():
                                    stdscr.addstr(
                                        "{}: {}\n".format(key, value[1]),
                                        curses.color_pair(3))

                                stdscr.addstr(
                                    "Select number of title to start.\n> ")
                                title_index = stdscr.getkey()
                                if title_index != '0':
                                    try:
                                        title = mapping[title_index]
                                        title_id = title[0]
                                        arg = title[1]
                                        command(title_id)
                                    except KeyError:
                                        stdscr.addstr(
                                            "Invalid Title",
                                            curses.color_pair(2))
                                        fail = True
                                else:
                                    stdscr.addstr(
                                        "Cancelled",
                                        curses.color_pair(2))
                                    fail = True
                        else:
                            command()
                    except NotReady:
                        stdscr.addstr(
                            "Wakeup PS4 first.", curses.color_pair(2))
                        stdscr.move(stdscr.getyx()[0] + 1, 0)
                        continue
                if not fail:
                    stdscr.addstr(
                        'Sent {}: {} '.format(action, arg),
                        curses.color_pair(4))
                stdscr.move(stdscr.getyx()[0] + 1, 0)
                stdscr.addstr(">")
        except curses.error:
            _init_window(stdscr, status)
        finally:
            curses.flushinp()


if __name__ == "__main__":
    cli()
