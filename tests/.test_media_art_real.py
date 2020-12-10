"""Tests for media_art. Uses actual HTTP response."""
import logging
import asyncio
import time
import itertools

import pyps4_2ndscreen.ps4 as ps4
from pyps4_2ndscreen.errors import PSDataIncomplete
from pyps4_2ndscreen.__version__ import __version__

TEST_LIST = [  # title, titleid, region
    ["Marvel's Spider-Man", 'CUSA11994', 'Australia'],  # Search All
    ["Marvel's Spider-Man", 'CUSA02299', 'Argentina'],
    ["Marvel's Spider-Man", 'CUSA11993', 'Australia'],
    ["Marvel's Spider-Man", 'CUSA11993', 'Austria'],
    ["Marvel's Spider-Man", 'CUSA11993', 'France'],
    ["Marvel's Spider-Man", 'CUSA11993', 'Italy'],
    ["Marvel's Spider-Man", 'CUSA09751', 'Japan'],
    ["Marvel's Spider-Man", 'CUSA09893', 'Korea'],
    ["Marvel's Spider-Man", 'CUSA11993', 'Nederland'],
    ["Marvel's Spider-Man", 'CUSA11994', 'Portugal'],
    ["Marvel's Spider-Man", 'CUSA11995', 'Russia'],
    ["Marvel's Spider-Man", 'CUSA11994', 'Spain'],
    ["Marvel's Spider-Man", 'CUSA11993', 'Sweden'],
    ["Spotify", 'CUSA01780', 'United Kingdom'],
    ["Netflix", 'CUSA00129', 'United States'],
    ["Netflix", 'CUSA00127', 'Spain'],
    ["Youtube", 'CUSA01116', 'Portugal'],
    ["Netflix", 'CUSA00127', 'Portugal'],
    ["Fortnite", 'CUSA07669', 'Portugal'],
    ["Beyond: Two Souls\u2122", 'CUSA00512', 'Portugal'],
    ["Shadow of the Colossus", "CUSA08804", "Taiwan"],
    ["Fortnite", "CUSA07669", "Spain"],
    ["The Last of Us™ Remastered", "CUSA00552", "United States"],
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
    ["Ratchet & Clank™", 'CUSA01073', 'Sweden'],
    ["Uncharted: The Nathan Drake Collection™", 'CUSA02320', 'United States'],
    ["NHL™ 18", 'CUSA07580', 'France'],
    ["Days Gone", 'CUSA08966', 'United States'],
    ["Battlefield™ V", 'CUSA08670', 'Portugal'],
    ["Diablo III: Reaper of Souls \u2013 Ultimate Evil Edition", 'CUSA00433', 'France'],
    ["Uncharted 4: A Thief’s End", 'CUSA04529', 'Ukraine'],
    ["The Last of Us™ Remastered", "CUSA00554", "Japan"],
]

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

TEST_HOST = "192.168.0.1"
TEST_CREDS = "Imatest000"

TEST_PS4 = ps4.Ps4Async(TEST_HOST, TEST_CREDS)


class MediaArtTest():
    def __init__(self):
        self.results = list(itertools.repeat(None, len(TEST_LIST)))

    def _print_results(self):
        for index, test_item in enumerate(TEST_LIST):
            result_item = self.results[index]
            if index == 0:
                index = "0 (Search All)"
            if result_item is None:
                _LOGGER.info(
                    "\nResult %s:"
                    "\n--> Failed"
                    "\n-------------"
                    "\nSearch Query:\n--> Title: %s\n--> SKU ID: %s\n--> Region: %s\n",
                    index,
                    test_item[0],
                    test_item[1],
                    test_item[2],
                )
                continue

            _LOGGER.info(
                "\nResult %s:"
                "\n--> Title: %s\n--> Cover URL: %s"
                "\n-------------"
                "\nSearch Time: %s seconds"
                "\nSearch Query:\n--> Title: %s\n--> SKU ID: %s\n--> Region: %s\n",
                index,
                result_item['name'],
                result_item['cover'],
                result_item['elapsed'],
                test_item[0],
                test_item[1],
                test_item[2],
            )

    async def _get_cover_art(self, item, search_all):
        """Return result if fail."""
        start = time.time()
        test_index = TEST_LIST.index(item)
        title = item[0]
        title_id = item[1]
        region = item[2]

        try:
            result_item = await TEST_PS4.async_get_ps_store_data(
                title, title_id, region, search_all=search_all)
        except PSDataIncomplete:
            _LOGGER.error(
                "PS Data Incomplete: %s, %s, %s", title, title_id, region)
            return item

        try:
            assert result_item is not None
            assert title_id in result_item.cover_art
        except AssertionError:
            _LOGGER.info("Search Failed: %s, %s, %s\n", title, title_id, region)
            return item

        if result_item is not None:
            elapsed = time.time() - start
            data = {
                'name': result_item.name,
                'cover': result_item.cover_art,
                'elapsed': round(elapsed, 2),
            }
            self.results.pop(test_index)
            self.results.insert(test_index, data)
        return None

    async def _get_tests(self):
        tests = []
        fails = False
        for item in TEST_LIST:
            test = self._get_cover_art(item, search_all=False)
            tests.append(test)
        # tests.pop(0)
#        test_search_all = self._get_cover_art(TEST_LIST[0], search_all=True)

        results = await asyncio.gather(*tests)
        _LOGGER.info("\nStarting Search All Test:\n")
#        search_all_result = await test_search_all
        self._print_results()
        for index, item in enumerate(results):
            if item is not None:
                fails = True
                _LOGGER.info("Failed: %s", item)
        # if search_all_result is not None:
        #     fails = True
        #     _LOGGER.info("Search All Test Failed")

        if not fails:
            _LOGGER.info("All Tests Passed")
            return True
        return False


def main():
    """Run Tests."""
    _LOGGER.info(
        "\nTest last ran on %s\nVersion: %s\n", time.ctime(), __version__)
    test_case = MediaArtTest()
    loop = asyncio.get_event_loop()
    start = time.time()
    success = loop.run_until_complete(test_case._get_tests())
    loop.stop()
    elapsed = time.time() - start
    _LOGGER.info("All Tests completed in %s seconds", elapsed)
    _LOGGER.info("Success: %s", success)


if __name__ == "__main__":
    main()
