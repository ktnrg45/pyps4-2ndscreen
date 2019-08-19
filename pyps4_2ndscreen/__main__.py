# -*- coding: utf-8 -*-
"""Main File for pyps4-2ndscreen."""
import logging
import json

import click

from .helpers import Helper
from .client import Client

_LOGGER = logging.getLogger(__name__)


@click.group()
@click.version_option()
def cli():
    """Pyps4-2ndscreen CLI. Allows for simple commands from terminal."""
    logging.basicConfig(level=logging.INFO)


@cli.command(help='Run polling status client. Example: pyps4-2ndscreen client')
def client():
    """Run Status Client"""
    helper = Helper()
    is_data = helper.check_data('ps4')
    if not is_data:
        _input = input(
            "No Config found. Enter 'Y' to configure: > ")
        if _input.upper() == 'Y':
            config_successful = _configure_func()
            if not config_successful:
                return
        else:
            return

    data = helper.load_files('ps4')
    status_client = Client()
    for ip_address in data:
        creds = data[ip_address]
        status_client.add_ps4(ip_address, creds)
    print("Starting Status Client")
    print("To cancel press 'CTRL + C'.")
    status_client.start()


@cli.command(help='Configure a PS4 console. Example: pyps4-2ndscreen configure')
def configure():
    """Configure a PS4 console."""
    _configure_func()


def _configure_func():
    creds = _credentials_func()
    if creds is None:
        return False
    _search_func()
    ip_address = input("Enter the IP Address for the PS4 you would like to link: > ")

    linked = _link_func(ip_address, creds)
    if not linked:
        return False
    print("Configuration Successful.")
    return True


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


@cli.command(help='Get status of PS4. Example: pyps4-2ndscreen status 192.168.0.1')
@click.argument('ip_address', required=True)
def status(ip_address):
    """Get Status of PS4."""
    helper = Helper()
    devices = helper.has_devices(ip_address)
    if devices:
        d_status = devices[0]
        print("\nGot Status for {}:\n".format(ip_address))
        for key, value in d_status.items():
            print("{}: {}".format(key, value))
    else:
        print(
            "PS4 @ {} can not be found. Ensure PS4 is on and connected."
            .format(ip_address))


@cli.command(help='Get PSN Credentials. Example: pyps4-2ndscreen credentials')
def credentials():
    """Get and save credentials."""
    _credentials_func()


def _credentials_func():
    from .credential import DEFAULT_DEVICE_NAME
    from .ddp import DDP_PORT

    helper = Helper()
    error = helper.port_bind([DDP_PORT])
    if error is not None:
        print("Error binding to port. Try again as sudo.")
        return None
    else:
        print("With the PS4 2nd Screen app, refresh devices "
              "and select the device '{}'.".format(DEFAULT_DEVICE_NAME))
        print("To cancel press 'CTRL + C'.")

    creds = helper.get_creds()
    data = {'credentials': creds}
    if creds is not None:
        print("PSN Credentials is: '{}'".format(creds))
        file_name = helper.check_files('credentials')
        helper.save_files(data=data, file_type='credentials', file_name=file_name)
        print("Credentials saved to: {}".format(file_name))
        return creds
    print("No credentials found. Stopped credential service.")
    return None


@cli.command(help='Link PS4. Example: pyps4-2ndscreen link 192.0.0.1 credentials')
@click.argument('ip_address', required=True)
@click.argument('credentials', default=None, required=False)
def link(ip_address, _credentials):
    """Link or register device with PS4."""
    _link_func(ip_address, _credentials)


def _link_func(ip_address, _credentials):
    helper = Helper()
    if _credentials is None:
        creds_file = helper.check_files('credentials')
        with open(creds_file, "r") as _r_file:
            _data = json.load(_r_file)
            _r_file.close()
        if _data.get('credentials') is None:
            print("No credentials in {} and credentials not given.".format(creds_file))
            return False
        _credentials = _data['credentials']
    devices = helper.has_devices(ip_address)
    device_list = [device["host-ip"] for device in devices]
    if ip_address not in device_list:
        print(
            "PS4 @ {} can not be found. Ensure PS4 is on and connected."
            .format(ip_address))
        return False
    pin = input(
        "On PS4, Go to settings->Mobile App Connection Settings->"
        "Add Device and enter pin that is displayed: > "
    )
    is_ready, is_login = helper.link(ip_address, _credentials, pin)
    if is_ready and is_login:
        print('PS4 Successfully Linked.')
        file_name = helper.check_files('ps4')
        data = {ip_address: _credentials}
        helper.save_files(data, file_type='ps4', file_name=file_name)
        return True
    print("Linking Failed.")
    if not is_ready:
        print("PS4 not On or connected.")
    else:
        print("Login failed. Check pin code and try again.")
    return False


if __name__ == "__main__":
    cli()
