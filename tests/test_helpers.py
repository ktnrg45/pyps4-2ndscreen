"""Tests for pyps4_2ndscreen.helpers."""
from unittest.mock import MagicMock, mock_open, patch

from pyps4_2ndscreen import helpers

MOCK_HOST = "192.168.0.1"
MOCK_CREDS = "abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234"
MOCK_PIN = "12345678"
MOCK_BAD_PIN = "1234567a"
MOCK_FILE_PATH = "/path/afile.json"
MOCK_PATH = "/path/"
MOCK_DATA = '{"something": "somethingelse"}'
MOCK_DICT = {"something": "somethingelse"}


def test_has_devices():
    """Test has_devices."""
    helper = helpers.Helper()
    mock_devices = [{"host-ip": MOCK_HOST}]
    with patch(
        "pyps4_2ndscreen.helpers.search",
        return_value=mock_devices,
    ) as mock_search:
        assert helper.has_devices()
        assert len(mock_search.mock_calls) == 1


def test_link():
    """Test Link Helper."""
    helper = helpers.Helper()
    mock_ps4 = MagicMock()

    with patch("pyps4_2ndscreen.helpers.Ps4Legacy", return_value=mock_ps4):
        ready, login = helper.link(MOCK_HOST, MOCK_CREDS, MOCK_PIN)
        mock_ps4.login.assert_called_once_with(MOCK_PIN)
        assert len(mock_ps4.close.mock_calls) == 1
        assert ready
        assert login

    # Test non-numeric pin
    mock_ps4 = MagicMock()
    with patch("pyps4_2ndscreen.helpers.Ps4Legacy", return_value=mock_ps4):
        ready, login = helper.link(MOCK_HOST, MOCK_CREDS, MOCK_BAD_PIN)
        assert not mock_ps4.login.mock_calls
        assert ready
        assert not login

    # Test login failed.
    mock_ps4 = MagicMock()
    mock_ps4.login.side_effect = helpers.LoginFailed
    with patch("pyps4_2ndscreen.helpers.Ps4Legacy", return_value=mock_ps4):
        ready, login = helper.link(MOCK_HOST, MOCK_CREDS, MOCK_PIN)
        mock_ps4.login.assert_called_once_with(MOCK_PIN)
        assert ready
        assert not login

    # Test not ready.
    mock_ps4 = MagicMock()
    mock_ps4.login.side_effect = helpers.NotReady
    with patch("pyps4_2ndscreen.helpers.Ps4Legacy", return_value=mock_ps4):
        ready, login = helper.link(MOCK_HOST, MOCK_CREDS, MOCK_PIN)
        mock_ps4.login.assert_called_once_with(MOCK_PIN)
        assert not ready


def test_creds():
    """Test get creds."""
    helper = helpers.Helper()
    mock_creds = MagicMock()
    with patch("pyps4_2ndscreen.helpers.Credentials", return_value=mock_creds):
        helper.get_creds()
        assert len(mock_creds.listen.mock_calls) == 1


def test_save_creds():
    """Test save creds."""
    helper = helpers.Helper()
    cred_result = {"credentials": MOCK_CREDS}
    helper.save_files = MagicMock()
    helper.get_creds = MagicMock(return_value=MOCK_CREDS)
    assert helper.save_creds()
    helper.save_files.assert_called_once_with(helpers.DEFAULT_CREDS_FILE, cred_result)

    # Test no creds received.
    helper.save_files = MagicMock()
    helper.get_creds = MagicMock(return_value=None)
    assert not helper.save_creds()
    assert not helper.save_files.mock_calls


def test_port_bind():
    """Test port bind."""
    helper = helpers.Helper()
    ports = [987, 997]
    with patch(
        "pyps4_2ndscreen.helpers.socket.socket", return_value=MagicMock()
    ) as mock_sock:
        assert not helper.port_bind(ports)

    # Test first port that fails returns.
    mock_sock = MagicMock()
    with patch("pyps4_2ndscreen.helpers.socket.socket", return_value=mock_sock):
        mock_sock.bind.side_effect = helpers.socket.error
        assert helper.port_bind(ports) == 987


def test_check_data():
    """Tests check data."""
    helper = helpers.Helper()
    helper.check_files = MagicMock(return_value=helpers.DEFAULT_PS4_FILE)

    with patch(
        "pyps4_2ndscreen.helpers.open", mock_open(read_data=MOCK_DATA)
    ) as mock_file, patch("pyps4_2ndscreen.helpers.os.mkdir"), patch(
        "pyps4_2ndscreen.helpers.os.path.isfile", return_value=True
    ):
        assert helper.check_data("ps4")
        mock_file.assert_called_once_with(helpers.DEFAULT_PS4_FILE, "r")

        assert helper.check_data(file_name=MOCK_FILE_PATH)
        mock_file.assert_called_with(MOCK_FILE_PATH, "r")

    with patch("pyps4_2ndscreen.helpers.open", mock_open(read_data="{}")), patch(
        "pyps4_2ndscreen.helpers.os.mkdir"
    ), patch("pyps4_2ndscreen.helpers.os.path.isfile", return_value=True):
        assert not helper.check_data("ps4")


def test_check_files():
    """Tests check files."""
    helper = helpers.Helper()
    with patch("pyps4_2ndscreen.helpers.open", mock_open(read_data=MOCK_DATA)), patch(
        "pyps4_2ndscreen.helpers.os.mkdir"
    ), patch("pyps4_2ndscreen.helpers.os.path.isfile", return_value=True):
        assert helper.check_files("ps4") == helpers.FILE_TYPES['ps4']
        assert helper.check_files("random type") is None

    with patch("pyps4_2ndscreen.helpers.open", mock_open(read_data=MOCK_DATA)), patch(
        "pyps4_2ndscreen.helpers.os.path.exists", return_value=False
    ), patch("pyps4_2ndscreen.helpers.os.mkdir") as mock_mkdir, patch(
        "pyps4_2ndscreen.helpers.os.path.isfile", return_value=True
    ):
        assert helper.check_files("ps4") == helpers.FILE_TYPES['ps4']
        mock_mkdir.assert_called_once_with(str(helpers.DEFAULT_PATH))

    with patch(
        "pyps4_2ndscreen.helpers.open", mock_open(read_data=MOCK_DATA)
    ) as mock_create_file, patch(
        "pyps4_2ndscreen.helpers.os.path.exists", return_value=True
    ), patch(
        "pyps4_2ndscreen.helpers.os.mkdir"
    ), patch(
        "pyps4_2ndscreen.helpers.os.path.isfile", return_value=False
    ):
        assert helper.check_files("ps4") == helpers.FILE_TYPES['ps4']
        mock_mkdir.assert_called_once_with(str(helpers.DEFAULT_PATH))
        mock_create_file.assert_called_once_with(helpers.FILE_TYPES['ps4'], "w+")


def test_load_files():
    """Tests load files."""
    helper = helpers.Helper()
    helper.check_files = MagicMock(return_value=helpers.DEFAULT_PS4_FILE)
    with patch("pyps4_2ndscreen.helpers.open", mock_open(read_data=MOCK_DATA)), patch(
        "pyps4_2ndscreen.helpers.os.mkdir"
    ), patch("pyps4_2ndscreen.helpers.os.path.isfile", return_value=True):
        assert helper.load_files("ps4") == MOCK_DICT


def test_save_files():
    """Test save files."""
    helper = helpers.Helper()
    with patch(
        "pyps4_2ndscreen.helpers.open", mock_open(read_data=MOCK_DATA)
    ) as mock_open_file, patch("pyps4_2ndscreen.helpers.os.mkdir"), patch(
        "pyps4_2ndscreen.helpers.os.path.isfile", return_value=True
    ):
        assert helper.save_files(MOCK_DICT, file_type="ps4") == helpers.FILE_TYPES['ps4']
        mock_open_file.assert_called_once_with(helpers.FILE_TYPES['ps4'], "w+")
        assert helper.save_files([]) is None
        assert helper.save_files({}) is None
        assert helper.save_files(MOCK_DICT, file_type="random type") is None


def test_get_exec_path():
    """Test get exec path."""
    helper = helpers.Helper()
    config = helpers.sysconfig.get_config_vars()
    version = config["py_version_short"]
    base = config["projectbase"]
    mock_home = "/usr/bin"
    mock_reg = "{}/python{}".format(base, version)
    mock_path = MagicMock()

    # Test path is regular file.
    mock_path.is_symlink.return_value = False
    helpers.sys.executable = mock_reg
    helpers.sys._home = mock_home
    with patch("pyps4_2ndscreen.helpers.Path", return_value=mock_path):
        result = helper.get_exec_path()
        assert result == mock_reg

    # Test path is symlink.
    mock_path.is_symlink.return_value = True
    with patch("pyps4_2ndscreen.helpers.Path", return_value=mock_path):
        result = helper.get_exec_path()
        assert result == helpers.sys.executable

    # Test exception returns sys.executable
    with patch("pyps4_2ndscreen.helpers.Path", side_effect=(KeyError, AttributeError)):
        result = helper.get_exec_path()
        assert result == helpers.sys.executable
