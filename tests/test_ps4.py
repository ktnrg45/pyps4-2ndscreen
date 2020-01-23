"""Tests for pyps4_2ndscreen.ps4."""
import asyncio
from unittest.mock import patch, MagicMock
import pytest
import socket
from pyps4_2ndscreen import ps4
from pyps4_2ndscreen.media_art import PINNED_TITLES

from .test_ddp import (
    MOCK_HOST_ID,
    MOCK_HOST_TYPE,
    MOCK_HOST_NAME,
    MOCK_TCP_PORT,
    MOCK_TITLE_NAME,
    MOCK_TITLE_ID,
    MOCK_DDP_VERSION,
    MOCK_SYSTEM_VERSION,
    MOCK_CREDS,
    MOCK_HOST,
    MOCK_DDP_DICT,
    MOCK_STATUS_REST,
    MOCK_STANDBY_CODE,
)

MOCK_STANDBY_STATUS = {
    "host-type": MOCK_HOST_TYPE,
    "host-ip": MOCK_HOST,
    "host-request-port": MOCK_TCP_PORT,
    "host-id": MOCK_HOST_ID,
    "host-name": MOCK_HOST_NAME,
    "status": MOCK_STATUS_REST,
    "status_code": MOCK_STANDBY_CODE,
    "device-discovery-protocol-version": MOCK_DDP_VERSION,
    "system-version": MOCK_SYSTEM_VERSION,
}

MOCK_COVER_URL = "https://someurl.com"
MOCK_REGION = "United States"
MOCK_RC_PS_HOLD = "ps_hold"
MOCK_RC_ENTER = "enter"


def test_get_status():
    """Test get_status call."""
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)
    with patch(
        "pyps4_2ndscreen.ps4.get_status", return_value=MOCK_DDP_DICT
    ) as mock_call:
        mock_status = mock_ps4.get_status()
    assert mock_status is not None
    assert len(mock_call.mock_calls) == 1


def test_state_off():
    """Test state ff is properly set."""
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)
    with patch(
        "pyps4_2ndscreen.ps4.get_status", return_value=MOCK_STANDBY_STATUS
    ) as mock_call:
        mock_status = mock_ps4.get_status()
    assert mock_status is not None
    assert len(mock_call.mock_calls) == 1
    assert mock_ps4.is_running is False
    assert mock_ps4.is_standby is True
    assert mock_ps4.is_available is True


def test_state_on():
    """Test state on is properly set."""
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)
    with patch(
        "pyps4_2ndscreen.ps4.get_status", return_value=MOCK_DDP_DICT
    ) as mock_call:
        mock_status = mock_ps4.get_status()
    assert mock_status is not None
    assert len(mock_call.mock_calls) == 1
    assert mock_ps4.is_running is True
    assert mock_ps4.is_standby is False
    assert mock_ps4.is_available is True


def test_no_response():
    """Test no response handling."""
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)
    with patch(
        "pyps4_2ndscreen.ps4.get_status", side_effect=socket.timeout
    ) as mock_call:
        mock_status = mock_ps4.get_status()
    assert mock_status is None
    assert len(mock_call.mock_calls) == 1
    assert mock_ps4.is_running is False
    assert mock_ps4.is_standby is False
    assert mock_ps4.is_available is False
    assert mock_ps4.system_version is None
    assert mock_ps4.host_id is None
    assert mock_ps4.host_name is None


def test_properties():
    """Test properties are set."""
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)
    with patch(
        "pyps4_2ndscreen.ps4.get_status", return_value=MOCK_DDP_DICT
    ) as mock_call:
        mock_status = mock_ps4.get_status()
    assert mock_status is not None
    assert len(mock_call.mock_calls) == 1
    assert mock_ps4.system_version == MOCK_SYSTEM_VERSION
    assert mock_ps4.host_id == MOCK_HOST_ID
    assert mock_ps4.host_name == MOCK_HOST_NAME
    assert mock_ps4.running_app_titleid == MOCK_TITLE_ID
    assert mock_ps4.running_app_name == MOCK_TITLE_NAME


def test_state_changed():
    """Test state change is handled."""
    # On and Playing.
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)
    with patch(
        "pyps4_2ndscreen.ps4.get_status", return_value=MOCK_DDP_DICT
    ) as mock_call:
        mock_status = mock_ps4.get_status()
    assert mock_status is not None
    assert len(mock_call.mock_calls) == 1
    assert mock_ps4.running_app_titleid == MOCK_TITLE_ID
    assert mock_ps4.running_app_name == MOCK_TITLE_NAME
    assert mock_ps4.is_running is True
    assert mock_ps4.is_standby is False
    assert mock_ps4.is_available is True

    # Standby.
    with patch(
        "pyps4_2ndscreen.ps4.get_status", return_value=MOCK_STANDBY_STATUS
    ) as mock_call:
        mock_status = mock_ps4.get_status()
    assert mock_status is not None
    assert len(mock_call.mock_calls) == 1
    assert mock_ps4.running_app_titleid is None
    assert mock_ps4.running_app_name is None
    assert mock_ps4.ps_cover is None
    assert mock_ps4.ps_name is None
    assert mock_ps4.is_running is False
    assert mock_ps4.is_standby is True
    assert mock_ps4.is_available is True

    # No Response.
    with patch("pyps4_2ndscreen.ps4.get_status", return_value=None) as mock_call:
        mock_status = mock_ps4.get_status()
    assert mock_status is None
    assert len(mock_call.mock_calls) == 1
    assert mock_ps4.running_app_titleid is None
    assert mock_ps4.running_app_name is None
    assert mock_ps4.ps_cover is None
    assert mock_ps4.ps_name is None
    assert mock_ps4.is_running is False
    assert mock_ps4.is_standby is False
    assert mock_ps4.is_available is False


@pytest.mark.asyncio
async def test_get_ps_store_data():
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)
    mock_coro = asyncio.Future()
    mock_coro.set_result([MagicMock()])

    mock_ps4.status = MOCK_DDP_DICT
    mock_result = MagicMock()
    mock_result.name = MOCK_TITLE_NAME
    mock_result.cover_art = MOCK_COVER_URL

    with patch(
        "pyps4_2ndscreen.ps4.async_get_ps_store_requests", return_value=mock_coro
    ) as mock_call, patch("pyps4_2ndscreen.ps4.parse_data", return_value=mock_result):
        mock_result_item = await mock_ps4.async_get_ps_store_data(
            MOCK_TITLE_NAME, MOCK_TITLE_ID, MOCK_REGION
        )
    assert len(mock_call.mock_calls) == 1
    assert mock_ps4.running_app_ps_name == MOCK_TITLE_NAME
    assert mock_ps4.running_app_ps_cover == MOCK_COVER_URL


@pytest.mark.asyncio
async def test_get_pinned_data():
    """Test pinned data retrieved."""
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)
    title_id, data = next(iter(PINNED_TITLES.items()))
    result_item = await mock_ps4.async_get_ps_store_data(
        data["name"], title_id, MOCK_REGION
    )
    assert result_item.name == data["name"]
    assert data["sku_id"] in result_item.cover_art


# Ps4Legacy


def test_send_status():
    """Test send_status command."""
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)
    mock_call = mock_ps4.connection.send_status = MagicMock()

    # Test status not sent since not logged in.
    mock_result = mock_ps4.send_status()
    assert mock_result is False
    assert len(mock_call.mock_calls) == 0

    mock_ps4.connected = True
    mock_result = mock_ps4.send_status()
    assert mock_result is False
    assert len(mock_call.mock_calls) == 0

    # If logged in and connected, should send status.
    mock_ps4.connected = True
    mock_ps4.loggedin = True
    mock_result = mock_ps4.send_status()
    assert mock_result is True
    assert len(mock_call.mock_calls) == 1


def test_launch():
    """Test launch command."""
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)
    with patch("pyps4_2ndscreen.ps4.launch", side_effect=MagicMock()) as mock_call:
        mock_ps4.launch()
    assert len(mock_call.mock_calls) == 1


def test_wakeup():
    """Test Wakeup command."""
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)
    with patch("pyps4_2ndscreen.ps4.wakeup", side_effect=MagicMock()) as mock_call:
        mock_ps4.wakeup()
    assert len(mock_call.mock_calls) == 1


def test_login():
    """Test Login command."""
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)
    mock_call = mock_ps4.connection.login = MagicMock()
    mock_connect = mock_ps4.connection.connect = MagicMock(return_value=True)
    mock_ps4.connection.disconnect = MagicMock()

    # Test login with no status raises exception.
    with patch("pyps4_2ndscreen.ps4.get_status", return_value=None), pytest.raises(
        ps4.NotReady
    ):
        mock_ps4.login()
    assert len(mock_call.mock_calls) == 0
    assert mock_ps4.status is None
    assert mock_ps4.connected is False
    assert mock_ps4.loggedin is False

    # Test login with standby status raises exception.
    with patch(
        "pyps4_2ndscreen.ps4.get_status", return_value=MOCK_STANDBY_STATUS
    ), pytest.raises(ps4.NotReady):
        mock_ps4.login()
    assert len(mock_call.mock_calls) == 0
    assert mock_ps4.is_standby is True
    assert mock_ps4.connected is False
    assert mock_ps4.loggedin is False

    # Test login succeeds.
    mock_call.return_value = True
    with patch("pyps4_2ndscreen.ps4.get_status", return_value=MOCK_DDP_DICT):
        assert mock_ps4.login()
    assert len(mock_call.mock_calls) == 1
    assert mock_ps4.is_running is True
    assert mock_ps4.connected is True
    assert mock_ps4.loggedin is True

    # Test login fails.
    mock_call.return_value = False
    mock_ps4.loggedin = False
    with patch(
        "pyps4_2ndscreen.ps4.get_status", return_value=MOCK_DDP_DICT
    ), pytest.raises(ps4.LoginFailed):
        assert not mock_ps4.login()
    assert len(mock_call.mock_calls) == 2
    assert mock_ps4.is_running is True
    assert mock_ps4.connected is False
    assert mock_ps4.loggedin is False

    # Test login call is not called if already logged in.
    mock_ps4.loggedin = True
    assert mock_ps4.login()
    assert len(mock_call.mock_calls) == 2


def test_standby():
    """Test Standby command."""
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)
    mock_ps4.login = MagicMock(return_value=True)
    mock_ps4.connection.disconnect = MagicMock()

    mock_ps4.connection.standby = MagicMock(return_value=True)
    with patch("pyps4_2ndscreen.ps4.get_status", return_value=MOCK_DDP_DICT):
        mock_standby = mock_ps4.standby()
    assert mock_standby is True
    assert len(mock_ps4.connection.standby.mock_calls) == 1

    mock_ps4.connection.standby = MagicMock(return_value=False)
    with patch("pyps4_2ndscreen.ps4.get_status", return_value=MOCK_DDP_DICT):
        mock_standby = mock_ps4.standby()
    assert mock_standby is False
    assert len(mock_ps4.connection.standby.mock_calls) == 1


def test_start_title():
    """Test Start Title command."""
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)
    mock_ps4.login = MagicMock(return_value=True)
    mock_ps4.connection.disconnect = MagicMock()
    mock_ps4.remote_control = MagicMock()

    mock_call = mock_ps4.connection.start_title = MagicMock(return_value=True)
    mock_ps4.start_title(MOCK_TITLE_ID)
    mock_call.assert_called_with(MOCK_TITLE_ID)

    # Test auto closing of title
    mock_ps4.start_title(MOCK_TITLE_ID, "CUSA10001")
    assert len(mock_call.mock_calls) == 2
    mock_ps4.remote_control.assert_called_with(MOCK_RC_ENTER)


def test_remote_control():
    """Test Remote Control command."""
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)
    mock_ps4.login = MagicMock(return_value=True)
    mock_ps4.connection.disconnect = MagicMock()

    mock_call = mock_ps4.connection.remote_control = MagicMock()
    mock_ps4.remote_control(MOCK_RC_ENTER)
    mock_call.assert_called_with(ps4.BUTTONS[MOCK_RC_ENTER], 0)

    # Test PS Hold
    mock_call = mock_ps4.connection.remote_control = MagicMock()
    mock_ps4.remote_control(MOCK_RC_PS_HOLD)
    mock_call.assert_called_with(ps4.BUTTONS[MOCK_RC_PS_HOLD], ps4.PS_HOLD_TIME)
