"""Tests for pyps4_2ndscreen.credential."""
from unittest.mock import MagicMock, patch

import pytest

from pyps4_2ndscreen import credential
from pyps4_2ndscreen.ddp import get_ddp_search_message, get_ddp_wake_message

pytestmark = pytest.mark.asyncio

MOCK_ADDRESS = ("192.168.0.1", 1234)
STANDBY_RESPONSE = (
    "HTTP/1.1 620 Server Standby\n"
    "host-id:1234567890AB\n"
    "host-type:PS4\n"
    "host-name:pyps4-2ndScreen\n"
    "host-request-port:997\n"
    "device-discovery-protocol-version:00020020\n"
)

MOCK_CREDS = "123412341234abcd12341234abcd12341234abcd12341234abcd12341234abcd"


def init_creds(start=True):
    creds = credential.Credentials(start=start)
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


def test_creds_handle_search():
    """Test Service handles search message."""
    mock_response = (get_ddp_search_message().encode(), MOCK_ADDRESS)
    creds = init_creds()
    mock_search = credential.get_ddp_message(
        credential.STANDBY, creds.response
    ).encode()
    creds.sock = MagicMock()
    creds.sock.recvfrom = MagicMock(return_value=mock_response)
    result = creds.listen(0.1)
    creds.sock.sendto.assert_called_with(mock_search, MOCK_ADDRESS)
    assert result is None


def test_creds_handle_wakeup():
    """Test Service handles wakeup message."""
    mock_response = (get_ddp_wake_message(MOCK_CREDS).encode(), MOCK_ADDRESS)
    creds = init_creds()
    creds.sock = MagicMock()
    creds.sock.recvfrom = MagicMock(return_value=mock_response)
    result = creds.listen(0.1)
    assert result == MOCK_CREDS


def test_creds_errors():
    """Test Service error handling."""
    creds = init_creds()
    creds.sock = MagicMock()
    creds.sock.recvfrom = MagicMock(side_effect=credential.socket.error())
    with pytest.raises(credential.CredentialTimeout):
        result = creds.listen(0.1)
        assert result is None

    mock_response = (get_ddp_search_message().encode(), MOCK_ADDRESS)
    creds = init_creds()
    creds.sock = MagicMock()
    creds.sock.recvfrom = MagicMock(return_value=mock_response)
    creds.sock.sendto = MagicMock(side_effect=credential.socket.error())
    result = creds.listen(0.1)
    assert result is None

    # Test invalid msg.
    mock_response = (b"\x00", MOCK_ADDRESS)
    creds = init_creds()
    creds.sock = MagicMock()
    creds.sock.recvfrom = MagicMock(return_value=mock_response)
    result = creds.listen(0.1)
    assert result is None

    creds = init_creds()
    creds.sock = MagicMock()
    creds.sock.recvfrom = MagicMock(side_effect=KeyboardInterrupt)
    result = creds.listen(0.1)
    assert result is None

    with patch(
        "pyps4_2ndscreen.credential.socket.socket", side_effect=credential.socket.error
    ):
        creds = init_creds()
        creds.listen()
        assert creds.sock is None

    with patch(
        "pyps4_2ndscreen.credential.socket.socket.bind",
        side_effect=credential.socket.error,
    ):
        creds = init_creds()
        creds.listen()
        assert creds.sock is None
