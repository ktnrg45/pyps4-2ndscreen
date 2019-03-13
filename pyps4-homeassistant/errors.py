"""Exceptions Definitions."""

class NotReady(Exception):
    """PS4 no connection."""
    pass


class LoginFailed(Exception):
    """PS4 Failed Login."""
    pass


class UnknownButton(Exception):
    """Button not valid."""
    pass
