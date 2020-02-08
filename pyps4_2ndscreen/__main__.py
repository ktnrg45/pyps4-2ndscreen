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
    help='Wakeup PS4. Example: pyps4-2ndscreen wakeup'
    '-i 192.168.86.29 -c yourcredentials')
@click.option('-i', '--ip_address')
@click.option('-c', '--credentials')
def wakeup(ip_address=None, credentials=None):
    """Wakeup PS4"""
    _ps4 = _get_ps4(ip_address, credentials)
    if _ps4 is not None:
        _ps4.wakeup()
        print("Wakeup Sent to {}".format(ip_address))


@cli.command(
    help='Place PS4 in Standby. Example: pyps4-2ndscreen standby'
    '-i 192.168.86.29 -c yourcredentials')
@click.option('-i', '--ip_address')
@click.option('-c', '--credentials')
def standby(ip_address=None, credentials=None):
    """Standby."""
    _ps4 = _get_ps4(ip_address, credentials)
    if _ps4 is not None:
        success = _ps4.standby()
        _print_result(success, 'Standby')


@cli.command(
    help='Send Remote Control. Example: pyps4-2ndscreen remote ps'
    '-i 192.168.86.29 -c yourcredentials')
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
    help='Start title. Example: pyps4-2ndscreen start CUSA10000'
    '-i 192.168.86.29 -c yourcredentials')
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
    help='Configure/Link PS4. Example: pyps4-2ndscreen link'
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
    help='Get status of PS4. Example: pyps4-2ndscreen status -i 192.168.0.1')
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


@cli.command(help='Get PSN Credentials. Example: pyps4-2ndscreen credentials')
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
        py_path = helper.get_exec_path()
        print(
            "\nError binding to port.\n\n"
            "- Try again as sudo.\n\n"
        )
        if py_path is not None:
            print(
                "- Or try setcap command:\n\n"
                "  > setcap 'cap_net_bind_service=+ep' {}"
                .format(py_path)
            )
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


if __name__ == "__main__":
    cli()
