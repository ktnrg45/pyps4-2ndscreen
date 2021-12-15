"""Tests for pyps4_2ndscreen.media_art."""
import asyncio
import logging
from unittest.mock import MagicMock, patch

import pytest
from asynctest import CoroutineMock as mock_coro
from asynctest import Mock

from pyps4_2ndscreen import media_art as media
import copy

pytestmark = pytest.mark.asyncio

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

MOCK_LANG = "en"
MOCK_REGION = "US/en"
MOCK_REGION_NAME = "United States"

MOCK_URL = "https://store.playstation.com/store/api/chihiro/00_09_000/titlecontainer/us/en/999/CUSA00129_00/"
MOCK_TITLE = "Netflix"
MOCK_TITLE_ID = "CUSA00129"
MOCK_FULL_ID = "UT0007-CUSA00129_00-NETFLIXPOLLUX001-U099"
MOCK_DATA = {
    "age_limit": 0,
    "attributes": {"facets": {}, "next": []},
    "bucket": "games",
    "container_type": "product",
    "content_origin": 0,
    "content_rating": {},
    "content_type": "1",
    "default_sku": {
        "amortizeFlag": False,
        "bundleExclusiveFlag": False,
        "chargeImmediatelyFlag": False,
        "charge_type_id": 0,
        "credit_card_required_flag": 0,
        "defaultSku": True,
        "display_price": "Free",
        "eligibilities": [],
        "entitlements": [
            {
                "description": None,
                "drms": [],
                "duration": 0,
                "durationOverrideTypeId": None,
                "exp_after_first_use": 0,
                "feature_type_id": 1,
                "id": "UT0007-CUSA00129_00-NETFLIXPOLLUX001",
                "license_type": 0,
                "metadata": None,
                "name": "Netflix",
                "packageType": "PS4GD",
                "packages": [
                    {"platformId": 13, "platformName": "ps4", "size": 26214400}
                ],
                "preorder_placeholder_flag": False,
                "size": 0,
                "subType": 0,
                "subtitle_language_codes": None,
                "type": 5,
                "use_count": 0,
                "voice_language_codes": None,
            }
        ],
        "id": "UT0007-CUSA00129_00-NETFLIXPOLLUX001-U099",
        "is_original": False,
        "platforms": [0, 18, 10, 13],
        "price": 0,
        "rewards": [],
        "seasonPassExclusiveFlag": False,
        "skuAvailabilityOverrideFlag": False,
        "sku_type": 0,
        "type": "standard",
    },
    "dob_required": False,
    "gameContentTypesList": [{"name": "App", "key": "APP"}],
    "game_contentType": "App",
    "id": "UT0007-CUSA00129_00-NETFLIXPOLLUX001",
    "images": [
        {
            "type": 10,
            "url": "some url",
        }
    ],
    "legal_text": "some text",
    "links": [],
    "long_desc": "some text",
    "mediaList": {
        "screenshots": [
            {
                "type": "SCREENSHOT",
                "typeId": 4,
                "source": "PRODUCT_MEDIA",
                "url": "https://example.com/some.jpg",
                "order": 3,
            },
            {
                "type": "SCREENSHOT",
                "typeId": 4,
                "source": "PRODUCT_MEDIA",
                "url": "https://example.com/some.jpg",
                "order": 4,
            },
            {
                "type": "SCREENSHOT",
                "typeId": 4,
                "source": "PRODUCT_MEDIA",
                "url": "https://example.com/some.jpg",
                "order": 1,
            },
            {
                "type": "SCREENSHOT",
                "typeId": 4,
                "source": "PRODUCT_MEDIA",
                "url": "https://example.com/some.jpg",
                "order": 0,
            },
            {
                "type": "SCREENSHOT",
                "typeId": 4,
                "source": "PRODUCT_MEDIA",
                "url": "https://example.com/some.jpg",
                "order": 2,
            },
        ]
    },
    "media_layouts": [{"type": "description", "height": 1, "width": 4}],
    "metadata": {
        "cn_remotePlay": {"name": "cn_remotePlay", "values": ["FALSE"]},
        "cn_vrEnabled": {"name": "cn_vrEnabled", "values": ["FALSE"]},
        "cn_playstationMove": {"name": "cn_playstationMove", "values": ["NOTREQUIRED"]},
        "secondary_classification": {
            "name": "secondary_classification",
            "values": ["APPLICATION"],
        },
        "cn_vrRequired": {"name": "cn_vrRequired", "values": ["FALSE"]},
        "cn_psEnhanced": {"name": "cn_psEnhanced", "values": ["FALSE"]},
        "playable_platform": {"name": "playable_platform", "values": ["PS4™"]},
        "cn_dualshockVibration": {"name": "cn_dualshockVibration", "values": ["FALSE"]},
        "tertiary_classification": {
            "name": "tertiary_classification",
            "values": ["NA"],
        },
        "container_type": {
            "name": "Container Type",
            "values": ["NP_PS4_REPRESENTATIVE"],
        },
        "cn_inGamePurchases": {"name": "cn_inGamePurchases", "values": ["NOTREQUIRED"]},
        "cn_psVrAimRequired": {"name": "cn_psVrAimRequired", "values": ["FALSE"]},
        "cn_playstationCamera": {
            "name": "cn_playstationCamera",
            "values": ["NOTREQUIRED"],
        },
        "cn_singstarMicrophone": {
            "name": "cn_singstarMicrophone",
            "values": ["NOTREQUIRED"],
        },
        "cn_crossPlatformPSVita": {
            "name": "cn_crossPlatformPSVita",
            "values": ["FALSE"],
        },
        "cn_psVrAimEnabled": {"name": "cn_psVrAimEnabled", "values": ["FALSE"]},
        "primary_classification": {
            "name": "primary_classification",
            "values": ["NON_GAME_RELATED"],
        },
    },
    "name": "Netflix",
    "playable_platform": ["PS4™"],
    "promomedia": [],
    "provider_name": "Netflix",
    "release_date": "2013-11-12T00:00:00Z",
    "restricted": False,
    "revision": 50,
    "short_name": "Netflix",
    "size": 0,
    "sku_links": [],
    "skus": [
        {
            "amortizeFlag": False,
            "bundleExclusiveFlag": False,
            "chargeImmediatelyFlag": False,
            "charge_type_id": 0,
            "credit_card_required_flag": 0,
            "defaultSku": True,
            "display_price": "Free",
            "eligibilities": [],
            "entitlements": [
                {
                    "description": None,
                    "drms": [],
                    "duration": 0,
                    "durationOverrideTypeId": None,
                    "exp_after_first_use": 0,
                    "feature_type_id": 1,
                    "id": "UT0007-CUSA00129_00-NETFLIXPOLLUX001",
                    "license_type": 0,
                    "metadata": None,
                    "name": "Netflix",
                    "packageType": "PS4GD",
                    "packages": [
                        {"platformId": 13, "platformName": "ps4", "size": 26214400}
                    ],
                    "preorder_placeholder_flag": False,
                    "size": 0,
                    "subType": 0,
                    "subtitle_language_codes": None,
                    "type": 5,
                    "use_count": 0,
                    "voice_language_codes": None,
                }
            ],
            "id": "UT0007-CUSA00129_00-NETFLIXPOLLUX001-U099",
            "is_original": False,
            "platforms": [0, 18, 10, 13],
            "price": 0,
            "rewards": [],
            "seasonPassExclusiveFlag": False,
            "skuAvailabilityOverrideFlag": False,
            "sku_type": 0,
            "type": "standard",
        }
    ],
    "sort": "static",
    "star_rating": {
        "total": "517608",
        "score": "4.46",
        "count": [
            {"star": 1, "count": 23262},
            {"star": 2, "count": 4749},
            {"star": 3, "count": 61562},
            {"star": 4, "count": 51350},
            {"star": 5, "count": 376685},
        ],
    },
    "start": 0,
    "timestamp": 1607043314000,
    "title_name": "Netflix",
    "top_category": "application",
    "total_results": 0,
}


def test_get_region():
    """Test region retrieval."""
    valid_region = media.get_region(next(iter(media.COUNTRIES)))
    assert valid_region in media.COUNTRIES.values()

    deprecated_region = media.get_region(next(iter(media.DEPRECATED_REGIONS)))
    assert deprecated_region in media.DEPRECATED_REGIONS.values()

    invalid_region = media.get_region("Invalid")
    assert invalid_region is None


async def test_search_ps_store():
    """Test PS store search."""
    mock_response = Mock()
    mock_response.status = media.HTTP_STATUS_OK
    mock_response.json.return_value = asyncio.Future()
    mock_response.json.return_value.set_result(MOCK_DATA)

    with patch(
        "pyps4_2ndscreen.media_art.fetch", new=mock_coro(return_value=mock_response)
    ):
        result = await media.async_search_ps_store(
            MOCK_TITLE_ID, MOCK_REGION_NAME
        )
    assert result.name == MOCK_TITLE
    assert MOCK_TITLE_ID in result.cover_art
    assert result.game_type == media.TYPE_APP
    assert result.sku_id == MOCK_TITLE_ID


async def test_search_ps_store_errors():
    """Test PS store search errors."""
    mock_response = Mock()
    mock_response.json.return_value = asyncio.Future()
    mock_response.json.return_value.set_result({})
    with patch(
        "pyps4_2ndscreen.media_art.fetch", new=mock_coro(return_value=mock_response)
    ) as mock_fetch:
        result = await media.async_search_ps_store(
            MOCK_TITLE_ID, MOCK_REGION_NAME
        )
        assert result is None
        assert len(mock_fetch.mock_calls) == 1


async def test_fetch():
    """Test fetch coro."""
    session = Mock()
    mock_response = Mock()
    mock_response.status = media.HTTP_STATUS_OK
    session.get.return_value = asyncio.Future()
    session.get.return_value.set_result(mock_response)
    result = await media.fetch(MagicMock(), MagicMock(), session)
    assert result == mock_response


async def test_fetch_http_errors():
    """Test fetch http errors."""
    session = Mock()
    mock_response = Mock()
    mock_response.status = 404
    session.get.return_value = asyncio.Future()
    session.get.return_value.set_result(mock_response)
    mock_response.json.return_value = asyncio.Future()
    mock_response.json.return_value.set_result({'reason': 'does not exist'})
    result = await media.fetch(MagicMock(), MagicMock(), session)
    assert result is None


async def test_fetch_errors():
    """Test fetch errors."""
    session = Mock()
    mock_json = Mock()
    mock_json.json.return_value = asyncio.Future()
    mock_json.json.side_effect = (
        media.asyncio.TimeoutError,
        media.aiohttp.client_exceptions.ContentTypeError,
        media.SSLError,
    )
    session.get.return_value = asyncio.Future()
    session.get.return_value.set_result(mock_json)
    result = await media.fetch(MagicMock(), MagicMock(), session)
    assert result is None


async def test_result_item_missing_data():
    """Test Parsing with missing keys returns None."""
    data = copy.deepcopy(MOCK_DATA)
    data.pop("gameContentTypesList")
    data.pop("title_name")
    mock_response = Mock()
    mock_response.status = media.HTTP_STATUS_OK
    mock_response.json.return_value = asyncio.Future()
    mock_response.json.return_value.set_result(data)

    with patch(
        "pyps4_2ndscreen.media_art.fetch", new=mock_coro(return_value=mock_response)
    ) as mock_fetch, pytest.raises(media.PSDataIncomplete):
        await media.async_search_ps_store(MOCK_TITLE_ID, MOCK_REGION_NAME)
        assert len(mock_fetch.mock_calls) == 2
