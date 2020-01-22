"""Tests for pyps4_2ndscreen.ps4."""
import asyncio
from unittest.mock import patch, MagicMock
import pytest
from pyps4_2ndscreen import ps4

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
    with patch("pyps4_2ndscreen.ps4.get_status", return_value=None) as mock_call:
        mock_status = mock_ps4.get_status()
    assert mock_status is None
    assert len(mock_call.mock_calls) == 1
    assert mock_ps4.is_running is False
    assert mock_ps4.is_standby is False
    assert mock_ps4.is_available is False


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
    assert mock_ps4.is_running is False
    assert mock_ps4.is_standby is False
    assert mock_ps4.is_available is False


@pytest.mark.asyncio
async def test_get_ps_store_data():
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)
    mock_coro = asyncio.Future()
    mock_coro.set_result([MagicMock()])

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
    assert mock_ps4.ps_name == MOCK_TITLE_NAME
    assert mock_ps4.ps_cover == MOCK_COVER_URL
