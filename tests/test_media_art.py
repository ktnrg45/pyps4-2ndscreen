"""Tests for media_art. Uses actual HTTP response."""
import logging
import pyps4_homeassistant.ps4 as ps4

TEST_LIST = [  # title, titleid, region
    ["Marvel's Spider-Man", 'CUSA11995', 'Russia'],
    ["For Honor", 'CUSA05265', 'Russia'],
    ["Overwatch: Origins Edition", 'CUSA03975', 'Russia'],
    ["inFAMOUS First Light™", 'CUSA00575', 'United States'],
    ["God of War® III Remastered", 'CUSA01623', 'United States'],
    ["WATCH_DOGS® 2", 'CUSA04459', 'United States'],
    ["Gran TurismoSPORT", 'CUSA03220', 'United States'],
    ["Metro Exodus", 'CUSA11407', 'United States'],
    ["Marvel's Spider-Man", 'CUSA11993', 'Sweden'],
    ["Ratchet & Clank™", 'CUSA01073', 'Sweden'],
    ["Uncharted: The Nathan Drake Collection™", 'CUSA02320', 'United States'],
    ["NHL™ 18", 'CUSA07580', 'France']
]

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

TEST_HOST = "192.168.0.1"
TEST_CREDS = "Imatest000"

TEST_PS4 = ps4.Ps4(TEST_HOST, TEST_CREDS)


def test_sample_list():
    """Tests if art can be retrieved."""
    for x in TEST_LIST:
        test_item = TEST_LIST.index(x)
        item = TEST_LIST[test_item]
        title = item[0]
        title_id = item[1]
        region = item[2]
        result_title, result_art = TEST_PS4.get_ps_store_data(
            title, title_id, region)
        _LOGGER.info(
            "Result %s: %s, %s",
            TEST_LIST.index(x), result_title, result_art)
        assert result_title is not None


test_sample_list()
