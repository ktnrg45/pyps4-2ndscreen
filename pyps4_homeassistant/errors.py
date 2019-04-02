"""Exceptions Definitions."""

class NotReady(Exception):
    """PS4 no connection."""


class LoginFailed(Exception):
    """PS4 Failed Login."""


class UnknownButton(Exception):
    """Button not valid."""
