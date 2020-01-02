"""Tests for pyps4_2ndscreen/ddp.py"""
from unittest.mock import patch
from pyps4_2ndscreen import ddp

MODULE_NAME = "pyps4_2ndscreen"

MOCK_CREDS = "123412341234abcd12341234abcd12341234abcd12341234abcd12341234abcd"
MOCK_NAME = "ha_ps4_name"
MOCK_HOST = "192.168.0.2"
MOCK_HOST_NAME = "Fake PS4"
MOCK_HOST_ID = "A0000A0AA000"
MOCK_HOST_VERSION = "09879011"
MOCK_HOST_TYPE = "PS4"
MOCK_STATUS_REST = "Server Standby"
MOCK_STATUS_ON = "Ok"
MOCK_STANDBY_CODE = 620
MOCK_ON_CODE = 200
MOCK_TCP_PORT = 997
MOCK_DDP_PORT = 987
MOCK_DDP_VERSION = "00020020"
MOCK_SYSTEM_VERSION = "01000000"
MOCK_RANDOM_PORT = 1234
MOCK_TITLE_ID = "CUSA00000"
MOCK_TITLE_NAME = "Random Game"

MOCK_DDP_VER = 'device-discovery-protocol-version:{}\n'.format(
    MOCK_DDP_VERSION)

MOCK_DDP_MESSAGE = '{} * HTTP/1.1\n{}'
MOCK_DDP_CRED_DATA = 'user-credential:{}\nclient-type:a\nauth-type:C\n{}'

MOCK_DDP_DICT = {
    "host-type": MOCK_HOST_TYPE,
    "host-ip": MOCK_HOST,
    "host-request-port": MOCK_TCP_PORT,
    "running-app-name": MOCK_TITLE_NAME,
    "running-app-id": MOCK_TITLE_ID,
    "host-id": MOCK_HOST_ID,
    "host-name": MOCK_HOST_NAME,
    "status": MOCK_STATUS_ON,
    "status_code": MOCK_ON_CODE,
    "device-discovery-protocol-version": MOCK_DDP_VERSION,
    "system-version": MOCK_HOST_VERSION,
}

MOCK_DDP_RESPONSE = '''
    HTTP/1.1 {} {}\n
    host-id:{}\n
    host-type:{}\n
    host-name:{}\n
    host-request-port:{}\n
    running-app-name:{}\n
    running-app-id:{}\n
    device-discovery-protocol-version:{}\n
    system-version:{}\n
'''.format(
    MOCK_ON_CODE,
    MOCK_STATUS_ON,
    MOCK_HOST_ID,
    MOCK_HOST_TYPE,
    MOCK_HOST_NAME,
    MOCK_TCP_PORT,
    MOCK_TITLE_NAME,
    MOCK_TITLE_ID,
    MOCK_DDP_VERSION,
    MOCK_SYSTEM_VERSION,
)


def test_ddp_messages():
    """Test that DDP messages to send are correct."""
    msg = ddp.get_ddp_search_message()
    assert msg == MOCK_DDP_MESSAGE.format(ddp.DDP_TYPE_SEARCH, MOCK_DDP_VER)

    cred_data = MOCK_DDP_CRED_DATA.format(MOCK_CREDS, MOCK_DDP_VER)

    msg = ddp.get_ddp_launch_message(MOCK_CREDS)
    assert msg == MOCK_DDP_MESSAGE.format(ddp.DDP_TYPE_LAUNCH, cred_data)

    msg = ddp.get_ddp_wake_message(MOCK_CREDS)
    assert msg == MOCK_DDP_MESSAGE.format(ddp.DDP_TYPE_WAKEUP, cred_data)


def test_get_status():
    """Test that get_status returns correctly parsed response."""
    with patch(
        'pyps4_2ndscreen.ddp._send_recv_msg',
        return_value=(
            MOCK_DDP_RESPONSE.encode('utf-8'),
            (MOCK_HOST, MOCK_RANDOM_PORT)),
    ) as mock_send:
        parsed = ddp.get_status(host=MOCK_HOST)

    assert len(mock_send.mock_calls) == 1

    for key, value in parsed.items():
        assert key in MOCK_DDP_DICT
        assert value == parsed[key]
    assert len(parsed) == len(MOCK_DDP_DICT)
