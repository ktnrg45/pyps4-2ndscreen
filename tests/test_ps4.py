"""Tests for pyps4_2ndscreen.ps4."""

from unittest.mock import patch, MagicMock
import pytest
import socket
from asynctest import CoroutineMock as mock_coro
from pyps4_2ndscreen import ps4
from pyps4_2ndscreen.media_art import PINNED_TITLES, PSDataIncomplete
from pyps4_2ndscreen.ddp import (
    DDPProtocol,
    get_ddp_launch_message,
    get_ddp_wake_message,
)

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
MOCK_PORT = 1234


def test_get_status():
    """Test get_status call."""
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)
    with patch(
        "pyps4_2ndscreen.ps4.get_status", return_value=MOCK_DDP_DICT
    ) as mock_call:
        mock_status = mock_ps4.get_status()
    assert mock_status is not None
    assert mock_ps4.status_code == MOCK_DDP_DICT['status_code']
    assert len(mock_call.mock_calls) == 1
    assert mock_call.call_args[0] == (MOCK_HOST, mock_ps4._socket)
    # Sock should be none if no port specified
    assert mock_ps4._socket is None


def test_get_status_port():
    """Test get_status call with specific port."""
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS, port=MOCK_PORT)
    with patch(
        "pyps4_2ndscreen.ps4.get_status", return_value=MOCK_DDP_DICT
    ) as mock_call:
        mock_status = mock_ps4.get_status()
    assert mock_status is not None
    assert mock_ps4.status_code == MOCK_DDP_DICT['status_code']
    assert len(mock_call.mock_calls) == 1
    assert mock_call.call_args[0] == (MOCK_HOST, mock_ps4._socket)
    assert mock_ps4._socket is not None
    assert mock_ps4._socket.getsockname()[1] == MOCK_PORT


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
    assert mock_ps4.status_code is None
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
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)

    # Standby.
    with patch(
        "pyps4_2ndscreen.ps4.get_status", return_value=MOCK_STANDBY_STATUS
    ) as mock_call:
        mock_status = mock_ps4.get_status()
    assert mock_status is not None
    assert len(mock_call.mock_calls) == 1
    assert mock_ps4.running_app_titleid is None
    assert mock_ps4.running_app_name is None
    assert mock_ps4.running_app_ps_cover is None
    assert mock_ps4.running_app_ps_name is None
    assert mock_ps4.is_running is False
    assert mock_ps4.is_standby is True
    assert mock_ps4.is_available is True

    # On and Playing.
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

    # No Response.
    with patch("pyps4_2ndscreen.ps4.get_status", return_value=None) as mock_call:
        mock_status = mock_ps4.get_status()
    assert mock_status is None
    assert len(mock_call.mock_calls) == 1
    assert mock_ps4.running_app_titleid is None
    assert mock_ps4.running_app_name is None
    assert mock_ps4.running_app_ps_cover is None
    assert mock_ps4.running_app_ps_name is None
    assert mock_ps4.is_running is False
    assert mock_ps4.is_standby is False
    assert mock_ps4.is_available is False


@pytest.mark.asyncio
async def test_get_ps_store_data():
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)
    mock_ps4.status = MOCK_DDP_DICT
    mock_result = MagicMock()
    mock_result.name = MOCK_TITLE_NAME
    mock_result.cover_art = MOCK_COVER_URL

    with patch(
        "pyps4_2ndscreen.media_art.async_get_ps_store_requests",
        new=mock_coro(return_value=[MagicMock()]),
    ) as mock_call, patch(
        "pyps4_2ndscreen.media_art.parse_data", return_value=mock_result
    ):
        result_item = await mock_ps4.async_get_ps_store_data(
            MOCK_TITLE_NAME, MOCK_TITLE_ID, MOCK_REGION
        )
        assert len(mock_call.mock_calls) == 1
        assert result_item.name == mock_result.name
        assert result_item.cover_art == mock_result.cover_art
        assert mock_ps4.running_app_ps_name == MOCK_TITLE_NAME
        assert mock_ps4.running_app_ps_cover == MOCK_COVER_URL

    # Test errors with search
    with patch(
        "pyps4_2ndscreen.media_art.async_get_ps_store_requests",
        new=mock_coro(return_value=[MagicMock()]),
    ) as mock_call, patch(
        "pyps4_2ndscreen.media_art.parse_data", side_effect=(TypeError, AttributeError)
    ), pytest.raises(
        PSDataIncomplete
    ):
        result_item = await mock_ps4.async_get_ps_store_data(
            MOCK_TITLE_NAME, MOCK_TITLE_ID, MOCK_REGION
        )
        assert len(mock_call.mock_calls) == 1
        assert result_item is None

    # Test no item found
    with patch(
        "pyps4_2ndscreen.media_art.async_get_ps_store_requests",
        new=mock_coro(return_value=[]),
    ) as mock_call, patch(
        "pyps4_2ndscreen.media_art.parse_data", return_value=None
    ):
        result_item = await mock_ps4.async_get_ps_store_data(
            MOCK_TITLE_NAME, MOCK_TITLE_ID, MOCK_REGION
        )
        assert len(mock_call.mock_calls) == 1
        assert result_item is None


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


# ##### Ps4Legacy Tests ######


def test_send_status():
    """Test send_status command."""
    mock_ps4 = ps4.Ps4Legacy(MOCK_HOST, MOCK_CREDS)
    mock_call = mock_ps4.connection.send_status = MagicMock()

    # Test status not sent since not logged in.
    mock_result = mock_ps4.send_status()
    assert mock_result is False
    assert len(mock_call.mock_calls) == 0

    mock_ps4._connected = True  # noqa: pylint: disable=protected-access
    mock_result = mock_ps4.send_status()
    assert mock_result is False
    assert len(mock_call.mock_calls) == 0

    # If logged in and connected, should send status.
    mock_ps4._connected = True  # noqa: pylint: disable=protected-access
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
    mock_ps4.connection.connect = MagicMock(return_value=True)
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

    # Test no remote call if title_id == running_id.
    mock_ps4.remote_control = MagicMock()
    mock_ps4.start_title(MOCK_TITLE_ID, MOCK_TITLE_ID)
    assert len(mock_ps4.remote_control.mock_calls) == 0

    # Test return False if login fails.
    mock_ps4.msg_sending = False
    mock_ps4.login = MagicMock(return_value=False)
    assert not mock_ps4.start_title(MOCK_TITLE_ID)


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

    # Test Unknown Button
    with pytest.raises(ps4.UnknownButton):
        mock_ps4.remote_control("Not Valid")

    # Test return False if login fails.
    mock_ps4.msg_sending = False
    mock_ps4.login = MagicMock(return_value=False)
    assert not mock_ps4.remote_control(MOCK_RC_ENTER)


# ##### Ps4Async Tests ######


def test_async_open_exception():
    """Test open raises exception."""
    mock_ps4 = ps4.Ps4Async(MOCK_HOST, MOCK_CREDS)
    with pytest.raises(NotImplementedError):
        mock_ps4.open()


def test_set_login_delay():
    """Test Login delay is set."""
    mock_ps4 = ps4.Ps4Async(MOCK_HOST, MOCK_CREDS)
    mock_login_delay = 5
    mock_ps4.set_login_delay(mock_login_delay)
    assert mock_ps4.login_delay == mock_login_delay


def test_async_ddp_protocol_attach():
    """Test methods to attach ddp protocol."""
    mock_ps4 = ps4.Ps4Async(MOCK_HOST, MOCK_CREDS)
    mock_ddp = DDPProtocol()
    mock_cb = MagicMock()

    mock_ps4.add_callback(mock_cb)
    assert mock_ps4.ddp_protocol is None
    mock_ps4.set_protocol(mock_ddp)
    assert mock_ps4.ddp_protocol == mock_ddp
    mock_ps4.add_callback(mock_cb)
    assert mock_ddp.callbacks[mock_ps4.host][mock_ps4] == mock_cb


def test_async_get_status():
    """Test get status method."""
    mock_ps4 = ps4.Ps4Async(MOCK_HOST, MOCK_CREDS)
    mock_ddp = DDPProtocol()
    mock_ddp.send_msg = MagicMock()
    mock_tcp = MagicMock()
    mock_ps4.tcp_protocol = mock_tcp
    mock_ps4._close = MagicMock()

    # Test socket.socket version is called if no ddp_protocol.
    with patch("pyps4_2ndscreen.ps4.get_status", return_value=None) as mock_call:
        mock_ps4.get_status()
    assert len(mock_call.mock_calls) == 1
    len(mock_ddp.send_msg.mock_calls) == 0

    mock_ps4.set_protocol(mock_ddp)
    mock_ps4.get_status()
    assert len(mock_ddp.send_msg.mock_calls) == 1
    assert mock_ps4.status is None

    # Test standby status closes connection.
    mock_ps4._connected = True  # noqa: pylint: disable=protected-access
    mock_ps4.loggedin = True
    mock_ps4.status = MOCK_STANDBY_STATUS
    mock_ps4.get_status()
    assert len(mock_ddp.send_msg.mock_calls) == 2
    assert len(mock_ps4._close.mock_calls) == 1
    assert not mock_ps4.connected
    assert not mock_ps4.loggedin
    assert mock_ps4.is_standby

    # Test running status leaves connection open.
    mock_ps4._connected = True  # noqa: pylint: disable=protected-access
    mock_ps4.loggedin = True
    mock_ps4.status = MOCK_DDP_DICT
    mock_ps4.get_status()
    assert len(mock_ddp.send_msg.mock_calls) == 3
    assert len(mock_ps4._close.mock_calls) == 1
    assert mock_ps4.connected
    assert mock_ps4.loggedin
    assert mock_ps4.is_running


def test_async_launch():
    """Test launch method."""
    mock_ps4 = ps4.Ps4Async(MOCK_HOST, MOCK_CREDS)
    mock_ddp = DDPProtocol()
    mock_ddp.send_msg = MagicMock()
    mock_launch_msg = get_ddp_launch_message(MOCK_CREDS)

    mock_ps4.launch()
    assert len(mock_ddp.send_msg.mock_calls) == 0

    mock_ps4.set_protocol(mock_ddp)
    mock_ps4.launch()
    mock_ddp.send_msg.assert_called_once_with(mock_ps4, mock_launch_msg)


def test_async_wakeup():
    """Test wakeup method."""
    mock_ps4 = ps4.Ps4Async(MOCK_HOST, MOCK_CREDS)
    mock_ddp = DDPProtocol()
    mock_ddp.send_msg = MagicMock()
    mock_wake_msg = get_ddp_wake_message(MOCK_CREDS)

    mock_ps4.wakeup()
    assert len(mock_ddp.send_msg.mock_calls) == 0

    mock_ps4.set_protocol(mock_ddp)
    mock_ps4.wakeup()
    mock_ddp.send_msg.assert_called_once_with(mock_ps4, mock_wake_msg)
    assert mock_ps4._power_on
    assert not mock_ps4._power_off


@pytest.mark.asyncio
async def test_async_login():
    """Test Login."""
    mock_ps4 = ps4.Ps4Async(MOCK_HOST, MOCK_CREDS)
    mock_tcp = MagicMock()
    mock_tcp.login = mock_coro()

    await mock_ps4.login()
    assert len(mock_tcp.login.mock_calls) == 0

    mock_ps4.tcp_protocol = mock_tcp
    await mock_ps4.login()
    mock_ps4.tcp_protocol.login.assert_called_once_with(
        '', mock_ps4._power_on, mock_ps4.login_delay
    )


@pytest.mark.asyncio
async def test_async_standby():
    """Test Standby."""
    mock_ps4 = ps4.Ps4Async(MOCK_HOST, MOCK_CREDS)
    mock_tcp = MagicMock()
    mock_tcp.standby = mock_coro()

    await mock_ps4.standby()
    assert len(mock_tcp.standby.mock_calls) == 0
    assert not mock_ps4._power_off

    mock_ps4.tcp_protocol = mock_tcp
    await mock_ps4.standby()
    assert len(mock_ps4.tcp_protocol.standby.mock_calls) == 1
    assert mock_ps4._power_off


@pytest.mark.asyncio
async def test_async_start_title():
    """Test Start Title."""
    mock_ps4 = ps4.Ps4Async(MOCK_HOST, MOCK_CREDS)
    mock_ps4.status = MOCK_STANDBY_STATUS
    mock_ps4.wakeup = MagicMock()
    mock_tcp = MagicMock()
    mock_tcp.start_title = mock_coro()
    mock_start_id = "CUSA10001"
    mock_task = ("start_title", mock_start_id, None)

    await mock_ps4.start_title(mock_start_id, None)
    assert len(mock_tcp.start_title.mock_calls) == 0
    assert mock_ps4.task_queue == mock_task
    assert len(mock_ps4.wakeup.mock_calls) == 1

    mock_ps4.status = MOCK_DDP_DICT
    mock_ps4.tcp_protocol = mock_tcp
    await mock_ps4.start_title(mock_start_id)
    mock_ps4.tcp_protocol.start_title.assert_called_once_with(
        mock_start_id, mock_ps4.running_app_titleid
    )


@pytest.mark.asyncio
async def test_async_remote_control():
    """Test Remote Control."""
    mock_ps4 = ps4.Ps4Async(MOCK_HOST, MOCK_CREDS)
    mock_ps4.status = MOCK_STANDBY_STATUS
    mock_ps4.wakeup = MagicMock()
    mock_tcp = MagicMock()
    mock_tcp.remote_control = mock_coro()
    mock_rc_command = "ps"
    mock_rc_int = ps4.BUTTONS.get("ps")
    mock_hold_time = 0
    mock_task = ("remote_control", mock_rc_int, mock_hold_time)

    await mock_ps4.remote_control(mock_rc_command)
    assert len(mock_tcp.remote_control.mock_calls) == 0
    assert mock_ps4.task_queue == mock_task
    assert len(mock_ps4.wakeup.mock_calls) == 1

    mock_ps4.status = MOCK_DDP_DICT
    mock_ps4.tcp_protocol = mock_tcp
    await mock_ps4.remote_control(mock_rc_command)
    mock_ps4.tcp_protocol.remote_control.assert_called_once_with(
        mock_rc_int, mock_hold_time
    )

    # Test PS Hold
    await mock_ps4.remote_control("ps_hold")
    mock_ps4.tcp_protocol.remote_control.assert_called_with(
        mock_rc_int, ps4.PS_HOLD_TIME
    )

    # Test Unknown Button
    with pytest.raises(ps4.UnknownButton):
        await mock_ps4.remote_control("Not valid")


@pytest.mark.asyncio
async def test_async_close():
    """Test close methods."""
    mock_ps4 = ps4.Ps4Async(MOCK_HOST, MOCK_CREDS)
    mock_tcp = MagicMock()
    mock_tcp.disconnect = MagicMock()

    # Test Closed Callback.
    mock_ps4.loggedin = True
    mock_ps4._connected = True  # noqa: pylint: disable=protected-access
    mock_ps4.tcp_transport = MagicMock()
    mock_ps4._closed()
    assert mock_ps4.tcp_transport is None
    assert mock_ps4.tcp_protocol is None
    assert not mock_ps4.loggedin
    assert not mock_ps4.connected

    # Test Close method.
    mock_ps4.loggedin = True
    mock_ps4._connected = True  # noqa: pylint: disable=protected-access
    mock_ps4.tcp_transport = MagicMock()
    mock_ps4.tcp_protocol = mock_tcp
    await mock_ps4.close()
    assert len(mock_ps4.tcp_protocol.disconnect.mock_calls) == 1


@pytest.mark.asyncio
async def test_async_connect():
    """Test connect method."""
    mock_ps4 = ps4.Ps4Async(MOCK_HOST, MOCK_CREDS)
    mock_ps4.get_status = MagicMock()
    mock_tcp = MagicMock()
    mock_tcp_transport = MagicMock()
    mock_ps4.launch = MagicMock()
    mock_ps4.connection.async_connect = mock_coro()
    mock_ps4.login = mock_coro()

    # Test that don't try to connect if connected.
    mock_ps4._connected = True  # noqa: pylint: disable=protected-access
    await mock_ps4.async_connect()
    assert len(mock_ps4.connection.async_connect.mock_calls) == 0

    mock_ps4._connected = False

    # Test Exception Raised if no status
    mock_ps4.status = None
    with pytest.raises(ps4.NotReady):
        await mock_ps4.async_connect()

    # Test Exception Raised if standby
    mock_ps4.status = MOCK_STANDBY_STATUS
    with pytest.raises(ps4.NotReady):
        await mock_ps4.async_connect()

    mock_ps4.status = MOCK_DDP_DICT

    # Test don't connect if powering off.
    mock_ps4._power_off = True
    await mock_ps4.async_connect()
    assert len(mock_ps4.connection.async_connect.mock_calls) == 0

    mock_ps4._power_off = False
    mock_ps4._power_on = True

    # Test connection refused.
    mock_ps4.connection.async_connect = mock_coro(
        side_effect=(OSError, ConnectionRefusedError)
    )
    await mock_ps4.async_connect()
    assert len(mock_ps4.connection.async_connect.mock_calls) == 1
    assert not mock_ps4.connected
    assert not mock_ps4.loggedin

    # Test Connection Successful
    mock_ps4.connection.async_connect = mock_coro(
        return_value=(mock_tcp_transport, mock_tcp)
    )
    await mock_ps4.async_connect()
    assert len(mock_ps4.connection.async_connect.mock_calls) == 1
    assert mock_ps4.connected
    assert mock_ps4.tcp_protocol == mock_tcp
    assert mock_ps4.tcp_transport == mock_tcp_transport
    # Assert that auto login performed, since powering on.
    assert len(mock_ps4.login.mock_calls) == 1
    assert not mock_ps4._power_on


@pytest.mark.asyncio
async def test_async_get_ddp_endpoint():
    """Test get_ddp_endpoint."""
    mock_ps4 = ps4.Ps4Async(MOCK_HOST, MOCK_CREDS)
    await mock_ps4.get_ddp_endpoint()
    assert mock_ps4.ddp_protocol is not None

    # Test with specific port
    mock_ps4 = ps4.Ps4Async(MOCK_HOST, MOCK_CREDS, port=MOCK_PORT)
    assert mock_ps4.port == MOCK_PORT
    await mock_ps4.get_ddp_endpoint()
    assert mock_ps4.ddp_protocol is not None
    assert mock_ps4.ddp_protocol.local_port == MOCK_PORT
    mock_ps4.ddp_protocol.close()

    # Test fail
    mock_ps4 = ps4.Ps4Async(MOCK_HOST, MOCK_CREDS, port=MOCK_PORT)
    with patch('pyps4_2ndscreen.ps4.async_create_ddp_endpoint', new=mock_coro(return_value=(None, None))):
        assert not await mock_ps4.get_ddp_endpoint()
