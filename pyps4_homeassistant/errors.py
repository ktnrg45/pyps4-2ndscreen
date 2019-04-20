"""Exceptions Definitions."""


class CredentialTimeout(Exception):
    """Recieved no credentials or timed out."""


class NotReady(Exception):
    """PS4 no connection."""


class PSDataIncomplete(Exception):
    """PS Store data missing attributes."""


class LoginFailed(Exception):
    """PS4 Failed Login."""


class UnknownButton(Exception):
    """Button not valid."""


class UnknownDDPResponse(Exception):
    """DDP Response is Unknown."""
