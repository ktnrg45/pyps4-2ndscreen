"""Exceptions Definitions."""


class PSConnectionError(Exception):
    """PS4 Connection error."""


class CredentialTimeout(Exception):
    """Recieved no credentials or timed out."""


class LoginFailed(Exception):
    """PS4 Failed Login."""


class NotReady(Exception):
    """PS4 no connection."""


class PSDataIncomplete(Exception):
    """PS Store data missing attributes."""


class UnknownButton(Exception):
    """Button not valid."""


class UnknownDDPResponse(Exception):
    """DDP Response is Unknown."""
