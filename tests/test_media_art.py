"""Tests for media_art. Uses actual HTTP response."""
import logging
import asyncio
import time

import pyps4_homeassistant.ps4 as ps4

TEST_LIST = [  # title, titleid, region
    ["Netflix", 'CUSA00129', 'United States'],
    ["Shadow of the Colossus", "CUSA08804", "Taiwan"],
    ["Fortnite", "CUSA07669", "Spain"],
    ["The Last of Us™ Remastered", "CUSA00552", "United States"],
    ["Marvel's Spider-Man", 'CUSA11993', 'Austria'],
    ["Marvel's Spider-Man", 'CUSA11993', 'Nederland'],
    ["Marvel's Spider-Man", 'CUSA11993', 'Italy'],
    ["Marvel's Spider-Man", 'CUSA11994', 'Spain'],
    ["Marvel's Spider-Man", 'CUSA11994', 'Portugal'],
    ["Marvel's Spider-Man", 'CUSA09893', 'Korea'],
    ["For Honor", 'CUSA05265', 'Russia'],
    ["Overwatch: Origins Edition", 'CUSA03975', 'Russia'],
    ["Call of Duty®: WWII", 'CUSA05969', 'United States'],
    ["UNCHARTED: The Lost Legacy", "CUSA07737", 'United States'],
    ["Battlefield™ V", "CUSA08724", 'United States'],
    ["Call of Duty®: Black Ops 4", "CUSA11100", 'United States'],
    ["HITMAN™ 2", "CUSA12421", 'United States'],
    ["inFAMOUS First Light™", 'CUSA00575', 'United States'],
    ["God of War® III Remastered", 'CUSA01623', 'United States'],
    ["WATCH_DOGS® 2", 'CUSA04459', 'United States'],
    ["Gran TurismoSPORT", 'CUSA03220', 'United States'],
    ["Marvel's Spider-Man", 'CUSA11993', 'Sweden'],
    ["Ratchet & Clank™", 'CUSA01073', 'Sweden'],
    ["Uncharted: The Nathan Drake Collection™", 'CUSA02320', 'United States'],
    ["NHL™ 18", 'CUSA07580', 'France'],
    ["Days Gone", 'CUSA08966', 'United States'],
    ["Marvel's Spider-Man", 'CUSA11995', 'Russia']
]

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

TEST_HOST = "192.168.0.1"
TEST_CREDS = "Imatest000"

TEST_PS4 = ps4.Ps4(TEST_HOST, TEST_CREDS)


async def test_sample_list(index_num):
    """Test sample list with asyncio."""
    start = time.time()
    test_item = TEST_LIST.index(index_num)
    item = TEST_LIST[test_item]
    title = item[0]
    title_id = item[1]
    region = item[2]

    result_item = await TEST_PS4.async_get_ps_store_data(
        title, title_id, region)
    if result_item is None:
        result_item = await test_search_all(title, title_id)
    if result_item is not None:
        _LOGGER.info(
            "Result %s: %s",
            TEST_LIST.index(index_num), result_item.name)

    assert result_item is not None
    elapsed = time.time() - start
    _LOGGER.info("Retrieved in %s seconds", elapsed)


async def test_search_all(title, title_id):
    start = time.time()

    result_item = await TEST_PS4.async_search_all_ps_data(
        title, title_id)
    elapsed = time.time() - start
    _LOGGER.info("Search All completed in %s seconds", elapsed)
    assert result_item is not None
    return result_item


async def _get_tests():
    tests = []
    for index_num in TEST_LIST:
        test = test_sample_list(index_num)
        tests.append(test)
    await asyncio.gather(*tests)

    # Test one Item for search_all
    search_all = asyncio.ensure_future(
        test_search_all(TEST_LIST[2][0], TEST_LIST[2][1]))
    await search_all


def main():
    """Run Tests."""
    loop = asyncio.get_event_loop()
    start = time.time()
    loop.run_until_complete(_get_tests())
    elapsed = time.time() - start
    _LOGGER.info("All Tests completed in %s seconds", elapsed)


if __name__ == "__main__":
    main()
