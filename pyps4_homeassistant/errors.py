"""Exceptions Definitions."""


class CredentialTimeout(Exception):
    """Recieved no credentials or timed out."""


class NotReady(Exception):
    """PS4 no connection."""


class PSStoreDataNotFound(Exception):
    """No PS Store Data Found."""


class LoginFailed(Exception):
    """PS4 Failed Login."""


class UnknownButton(Exception):
    """Button not valid."""


class UnknownDDPResponse(Exception):
    """DDP Response is Unknown."""
