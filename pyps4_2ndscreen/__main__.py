# -*- coding: utf-8 -*-
"""Main File for pyps4-2ndscreen."""
import logging

import click

from .helpers import Helper

_LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@click.group()
def cli():
    """Entry Point for CLI."""
    pass


@cli.command(help='Get PSN Credentials')
def credentials():
    """Get and save credentials."""
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

    creds = helper.get_creds()
    if creds is not None:
        print("PSN Credentials is: '{}'".format(creds))
        file_path = helper.save_files('credentials', creds)
        print("Credentials saved to: {}".format(file_path))
        return creds
    print("No credentials found. Stopped credential service.")


if __name__ == "__main__":
    cli()
