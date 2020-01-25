"""Tests for pyps4_2ndscreen.credential."""
from pyps4_2ndscreen import credential
from pyps4_2ndscreen.ddp import (
    get_ddp_search_message,
    get_ddp_wake_message,
)


STANDBY_RESPONSE = (
    "HTTP/1.1 620 Server Standby\n"
    "host-id:1234567890AB\n"
    "host-type:PS4\n"
    "host-name:pyps4-2ndScreen\n"
    "host-request-port:997\n"
    "device-discovery-protocol-version:00020020\n"
)

MOCK_CREDS = "123412341234abcd12341234abcd12341234abcd12341234abcd12341234abcd"


def init_creds():
    creds = credential.Credentials()
    return creds


def test_response_standby():
    """Test serialization of standby response msg."""
    creds = init_creds()
    response = credential.get_ddp_message(credential.STANDBY, creds.response).split(
        "\n"
    )
    for item in response:
        if item == "":
            continue
        assert item in STANDBY_RESPONSE


def test_parsing_msg():
    """Test parsing of messages."""
    parse_search = credential.parse_ddp_response(
        get_ddp_search_message().encode("utf-8")
    )
    assert parse_search == credential.PARSE_TYPE_SEARCH
    wakeup_response = get_ddp_wake_message(MOCK_CREDS).encode("utf-8")
    parse_wakeup = credential.parse_ddp_response(wakeup_response)
    assert parse_wakeup == credential.PARSE_TYPE_WAKEUP
    assert MOCK_CREDS == credential.get_creds(wakeup_response)
