# -*- coding: utf-8 -*-
"""Main File for pyps4-2ndscreen."""
import curses
import logging
import time
from collections import OrderedDict

import click

from .credential import DEFAULT_DEVICE_NAME
from .ddp import DDP_PORT, DEFAULT_UDP_PORT
from .helpers import Helper
from .ps4 import NotReady, Ps4Legacy

_LOGGER = logging.getLogger(__name__)


def _get_ps4(
    ip_address=None,
    credentials=None,
    no_creds=False,
    port=DEFAULT_UDP_PORT
):

    helper = Helper()

    if credentials is None:
        data = helper.load_files('credentials')
        credentials = data.get('credentials')
    if ip_address is not None and credentials is None:
        if not no_creds:
            print('--credentials option required')
            return None
        return Ps4Legacy(ip_address, '', port=port)

    if ip_address is not None and credentials is not None:
        return Ps4Legacy(ip_address, credentials, port=port)

    helper = Helper()
    is_data = helper.check_data('ps4')
    if not is_data:
        prompt_configure = input(
            "No configuration found. Configure? Enter 'y' for yes.\n> ")
        if prompt_configure.lower() == 'y':
            _link_func(ip_address=None, credentials=None, port=port)
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
    _ps4 = Ps4Legacy(ip_address, creds, port=port)
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


def _print_status(d_status):
    if d_status:
        print("\nGot Status for: {}".format(d_status['host-name']))
        for key, value in d_status.items():
            print("{}: {}".format(key, value))


def _overwrite_creds():
    proceed = input(
        "Overwrite existing credentials? Enter 'y' for yes.\n> ")
    if proceed.lower() != 'y':
        return False
    return True


@click.group(invoke_without_command=False)
@click.pass_context
@click.version_option()
@click.option('-v', '--debug', is_flag=True, help="Enable debug logging.")
@click.option(
    '-p',
    '--port',
    type=int,
    default=DEFAULT_UDP_PORT,
    help="Local UDP Port to use.",
)
def cli(ctx=None, debug=False, port=DEFAULT_UDP_PORT):
    """Pyps4-2ndscreen CLI. Allows for simple commands from terminal."""
    level = logging.INFO
    if debug:
        print("Log level set to debug")
        level = logging.DEBUG
    logging.basicConfig(level=level)

    ctx.obj = {}
    ctx.obj['port'] = port
    print("Using local UDP port: {}".format(port))


@cli.command(
    help='Wakeup PS4. Example: pyps4-2ndscreen wakeup '
    '-i 192.168.0.1 -c yourcredentials')
@click.pass_context
@click.option('-i', '--ip_address')
@click.option('-c', '--credentials')
def wakeup(ctx, ip_address=None, credentials=None):
    """Wakeup PS4"""
    _ps4 = _get_ps4(ip_address, credentials, port=ctx.obj['port'])
    if _ps4 is not None:
        _ps4.wakeup()
        print("Wakeup Sent to {}".format(_ps4.host))


@cli.command(
    help='Place PS4 in Standby. Example: pyps4-2ndscreen standby '
    '-i 192.168.0.1 -c yourcredentials')
@click.pass_context
@click.option('-i', '--ip_address')
@click.option('-c', '--credentials')
def standby(ctx, ip_address=None, credentials=None):
    """Standby."""
    _ps4 = _get_ps4(ip_address, credentials, port=ctx.obj['port'])
    if _ps4 is not None:
        success = _ps4.standby()
        _print_result(success, 'Standby')


@cli.command(
    help='Send Remote Control. Example: pyps4-2ndscreen remote ps '
    '-i 192.168.0.1 -c yourcredentials')
@click.pass_context
@click.option('-i', '--ip_address')
@click.option('-c', '--credentials')
@click.argument('command', required=True)
def remote(ctx, command, ip_address=None, credentials=None):
    """Send remote control."""
    _ps4 = _get_ps4(ip_address, credentials, port=ctx.obj['port'])
    if _ps4 is not None:
        success = _ps4.remote_control(command)
        _print_result(success, "Remote '{}'".format(command))


@cli.command(
    help='Start title. Example: pyps4-2ndscreen start CUSA10000 '
    '-i 192.168.0.1 -c yourcredentials')
@click.pass_context
@click.option('-i', '--ip_address')
@click.option('-c', '--credentials')
@click.argument('title_id', required=True)
def start(ctx, title_id, ip_address=None, credentials=None):
    """Start Title."""
    _ps4 = _get_ps4(ip_address, credentials, port=ctx.obj['port'])
    if _ps4 is not None:
        print("Starting title: {}".format(title_id))
        success = _ps4.start_title(title_id)
        _print_result(success, "Start '{}'".format(title_id))


@cli.command(
    help='Configure/Link PS4. Example: pyps4-2ndscreen link '
    '-i 192.0.0.1 -c yourcredentials')
@click.pass_context
@click.option('-i', '--ip_address')
@click.option('-c', '--credentials')
def link(ctx, ip_address=None, credentials=None):
    """Link or register device with PS4."""
    _link_func(ip_address, credentials, port=ctx.obj['port'])


# pylint: disable=too-many-return-statements
def _link_func(ip_address, credentials, port):
    helper = Helper()
    credentials = _check_creds(credentials)
    if credentials is None:
        return False

    device_list = _search_func(port=port)
    if not device_list:
        return False
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
    is_ready, is_login = helper.link(ip_address, credentials, pin, port=port)
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
@click.pass_context
def search(ctx) -> list:
    """Search LAN for PS4's."""
    port = ctx.obj['port']
    _search_func(port)


def _search_func(port=DEFAULT_UDP_PORT):
    helper = Helper()
    devices = helper.has_devices(port=port)
    device_list = [device["host-ip"] for device in devices]
    print("Found {} devices:".format(len(device_list)))
    for ip_address in device_list:
        print(ip_address)
    return device_list


@cli.command(
    help='Get status of PS4. Example: pyps4-2ndscreen status -i 192.168.0.1 ')
@click.pass_context
@click.option('-i', '--ip_address')
def status(ctx, ip_address=None):
    """Get Status of PS4."""
    port = ctx.obj['port']
    d_status = {}
    if ip_address is None:
        print("Getting status for any...")
        helper = Helper()
        devices = helper.has_devices(ip_address, port=port)
        if devices:
            for d_status in devices:
                _print_status(d_status)
            return True
        print("Try using --ip_address option.")
    else:
        _ps4 = _get_ps4(
            ip_address=ip_address,
            credentials=None,
            no_creds=True,
            port=port,
        )
        if _ps4 is not None:
            d_status = _ps4.get_status()

        if d_status:
            _print_status(d_status)
            return True
        print(
            "PS4 @ {} can not be found."
            .format(ip_address))
    return False


@cli.command(help='Get PSN Credentials. Example: pyps4-2ndscreen credentials ')
def credential():
    """Get and save credentials."""
    _credentials_func()


def _credentials_func():
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
@click.pass_context
@click.option('-i', '--ip_address')
@click.option('-c', '--credentials')
def interactive(ctx, ip_address=None, credentials=None):
    """Interactive."""
    _ps4 = _get_ps4(ip_address, credentials, port=ctx.obj['port'])
    if _ps4 is not None:
        curses.wrapper(_interactive, _ps4)


# pylint: disable=no-member
def _interactive(stdscr, ps4):
    key_mapping = {
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

    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_GREEN, curses.COLOR_BLACK)
    ps4.auto_close = False
    _status = ps4.get_status()
    _handle_status(stdscr, _status, key_mapping)
    _run(stdscr, ps4, key_mapping)
    ps4.close()


# pylint: disable=no-member
def _write_str(
        stdscr, text, color=1):
    stdscr.clrtoeol()
    stdscr.addstr(text, curses.color_pair(color))


# pylint: disable=no-member
def _init_window(stdscr, _status, key_mapping):
    stdscr.addstr(
        0, 0,
        "Interactive mode, press 'q' to exit\n",
    )
    if _status is not None:
        stdscr.addstr(
            1, 0,
            "Info: IP: {}, MAC: {}, Name: {}\n"
            "Status: {} | Playing: {} ({})\n\n".format(
                _status.get('host-ip'),
                _status.get('host-id'),
                _status.get('host-name'),
                _status.get('status'),
                _status.get('running-app-name'),
                _status.get('running-app-titleid'),
            ), curses.color_pair(2))
    else:
        stdscr.addstr(
            1, 0,
            "Status: {}\n".format('Not Available'),
            curses.color_pair(3))
    _show_mapping(stdscr, key_mapping)
    win_size = stdscr.getmaxyx()
    stdscr.setscrreg(stdscr.getyx()[0], win_size[0] - 1)
    stdscr.refresh()


def _show_mapping(stdscr, key_mapping):
    item = 3
    _key_mapping = OrderedDict()
    _key_mapping.update({'Key': ['Action']})
    _key_mapping.update(key_mapping)

    for key, values in _key_mapping.items():
        if key == '\n':
            key = 'KEY_ENTER'
        if values[0] == 'remote':
            value = values[2]
        else:
            value = values[0]
        _write_str(stdscr, key, 5)
        stdscr.addstr(' : ')
        _write_str(stdscr, value, 4)
        item += 1
        if item >= 4:
            item = 0
            stdscr.addstr('\n')
        else:
            stdscr.addstr(' | ')
    stdscr.addstr('\n\n')


def _handle_status(stdscr, _status, key_mapping):
    helper = Helper()
    games = helper.load_files('games')
    _write_str(
        stdscr,
        "Status Updated: {} | {}\n".format(
            _status.get('status'), _status.get('running-app-name')), 2)
    title_id = _status.get('running-app-titleid')
    if title_id is not None:
        if title_id not in games:
            games[title_id] = _status.get('running-app-name')
            helper.save_files(games, 'games')
    cur_pos = stdscr.getyx()
    _init_window(stdscr, _status, key_mapping)
    stdscr.move(cur_pos[0], cur_pos[1])


def _show_game_mapping():
    mapping = {}
    helper = Helper()
    games = helper.load_files('games')
    if games:
        g_index = 1
        mapping['0'] = ('', 'Cancel')
        for key, value in games.items():
            mapping[str(g_index)] = (key, value)
            g_index += 1
    return mapping


def _get_title_map(stdscr):
    stdscr.nodelay(False)
    mapping = _show_game_mapping()
    if mapping:
        _write_str(
            stdscr,
            "Options:\n", 4)
        for key, value in mapping.items():
            _write_str(
                stdscr,
                "{}: {}\n".format(key, value[1]), 4)

        _write_str(
            stdscr,
            "Select number of title to start.\n> ")
    return mapping


def _handle_require_on(stdscr, mapping):
    fail = False
    action = mapping[0]
    command = mapping[1]
    arg = ''
    try:
        if action == 'remote':
            arg = mapping[2]
            command(arg)
        elif action == 'start_title':
            mapping = _get_title_map(stdscr)
            title_index = stdscr.getkey()
            if title_index != '0':
                try:
                    title = mapping[title_index]
                    title_id = title[0]
                    arg = title[1]
                    command(title_id)
                except KeyError:
                    _write_str(
                        stdscr,
                        "Invalid Title\n", 3)
                    fail = True
            else:
                _write_str(
                    stdscr,
                    "Cancelled\n", 3)
                fail = True
        else:
            command()
    except NotReady:
        _write_str(
            stdscr,
            "> Wakeup PS4 first.\n", 3)
        fail = True
    return (fail, arg)


# pylint: disable=no-member
def _handle_key(stdscr, key, key_mapping):
    fail = False
    arg = ''

    if key == "q":
        return False
    if key in key_mapping:
        mapping = key_mapping.get(key)
        action = mapping[0]
        command = mapping[1]
        if action == 'status_request':
            _status = command()
            if _status is not None:
                _write_str(stdscr, 'Status Updated\n', 2)
        elif action == 'wakeup':
            command()
        else:
            fail, arg = _handle_require_on(stdscr, mapping)
        if not fail and action != 'status_request':
            _write_str(
                stdscr,
                '> Sent {}: {}\n'.format(action, arg), 5)
    curses.flushinp()
    return True


# pylint: disable=no-member
def _run(stdscr, ps4, key_mapping):
    _status = ps4.get_status()
    stdscr.scrollok(True)
    _init_window(stdscr, _status, key_mapping)
    running = True
    key = None
    start_timer = 0
    while running:
        stdscr.nodelay(True)
        if time.time() - start_timer > 5:
            start_timer = time.time()
            if ps4.loggedin:
                ps4.send_status()
            new_status = ps4.get_status()
            if _status != new_status:
                _status = new_status
                if _status is not None:
                    _handle_status(stdscr, _status, key_mapping)
        try:
            key = stdscr.getkey()
            running = _handle_key(stdscr, key, key_mapping)
        except curses.error:
            pass


if __name__ == "__main__":
    cli()
