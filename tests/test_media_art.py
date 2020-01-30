"""Tests for pyps4_2ndscreen.media_art."""
import html
import urllib
import pytest
from unittest.mock import MagicMock, patch
from asynctest import CoroutineMock as mock_coro

from pyps4_2ndscreen import media_art as media

MOCK_REGION = "US/en"
MOCK_REGION_NAME = "United States"

MOCK_URL = (
    "https://store.playstation.com/store/api/chihiro/00_09_000/container/"
    "US/en/19/UT0007-CUSA00129_00-NETFLIXPOLLUX001/1580172945000/image"
)

MOCK_TITLE = "Netflix"
MOCK_TITLE_ID = "CUSA00129"
MOCK_DATA = {
    "included": [
        {
            "attributes": {
                "badge-info": {"non-plus-user": None, "plus-user": None},
                "cero-z-status": {"is-allowed-in-cart": False, "is-on": False},
                "content-rating": {
                    "content-descriptors": [],
                    "contentInteractiveElement": [],
                    "rating-system": "",
                    "url": "",
                },
                "content-type": "1",
                "default-sku-id": "UT0007-CUSA00129_00-NETFLIXPOLLUX001-U099",
                "dob-required": False,
                "file-size": {"unit": "MB", "value": 26.21},
                "game-content-type": "App",
                "genres": [],
                "is-igc-upsell": False,
                "is-multiplayer-upsell": False,
                "kamaji-relationship": "extras",
                "legal-text": "",
                "long-description": "Some extremely long description.",
                "macross-brain-context": "game",
                "media-list": {
                    "preview": [],
                    "promo": {"images": [], "videos": []},
                    "screenshots": [{"url": "https://someimage.jpg",},],
                },
                "name": "Netflix",
                "nsx-confirm-message": "",
                "parent": None,
                "platforms": ["PS4"],
                "plus-reward-description": None,
                "primary-classification": "NON_GAME_RELATED",
                "provider-name": "Netflix",
                "ps-camera-compatibility": "incompatible",
                "ps-move-compatibility": "incompatible",
                "ps-vr-compatibility": "incompatible",
                "release-date": "2013-11-12T00:00:00Z",
                "secondary-classification": "APPLICATION",
                "skus": [
                    {
                        "entitlements": [{"duration": 0, "exp-after-first-use": 0}],
                        "id": "UT0007-CUSA00129_00-NETFLIXPOLLUX001-U099",
                        "is-preorder": False,
                        "multibuy": None,
                        "playability-date": "",
                        "plus-reward-description": None,
                        "prices": {
                            "non-plus-user": {
                                "actual-price": {"display": "Free", "value": 0},
                                "availability": {"end-date": None, "start-date": None},
                                "discount-percentage": 0,
                                "is-plus": False,
                                "strikethrough-price": None,
                                "upsell-price": None,
                            },
                            "plus-user": {
                                "actual-price": {"display": "Free", "value": 0},
                                "availability": {"end-date": None, "start-date": None},
                                "discount-percentage": 0,
                                "is-plus": False,
                                "strikethrough-price": None,
                                "upsell-price": None,
                            },
                        },
                    }
                ],
                "star-rating": {"score": 4.49, "total": 435164},
                "subtitle-language-codes": [],
                "tertiary-classification": "NA",
                "thumbnail-url-base": MOCK_URL,
                "top-category": "application",
                "upsell-info": None,
                "voice-language-codes": [],
            }
        }
    ]
}


def test_get_pinned_item():
    """Test Pinned Item retrieval."""
    title_id = next(iter(media.PINNED_TITLES))
    title_data = media.PINNED_TITLES[title_id]
    result = media.get_pinned_item(title_data)
    assert result.name == title_data["name"]
    assert result.game_type == title_data["type"]
    assert result.cover_art == "{}{}{}".format(
        media.BASE_IMAGE_URL, title_data["sku_id"], title_data["url"]
    )
    assert result.sku_id == title_id


def test_get_region():
    """Test region retrieval."""
    valid_region = media.get_region(next(iter(media.COUNTRIES)))
    assert valid_region in media.COUNTRIES.values()

    deprecated_region = media.get_region(next(iter(media.DEPRECATED_REGIONS)))
    assert deprecated_region in media.DEPRECATED_REGIONS.values()

    invalid_region = media.get_region("Invalid")
    assert invalid_region is None


def test_get_lang():
    """Test lang retrieval."""
    lang = media.get_lang(next(iter(media.COUNTRIES)))
    assert len(lang) == 2
    assert lang.isalpha()


def test_get_url():
    """Test building of search url."""
    mock_input = "Random Game's 2©: The-Title™"

    # Test Tumbler url.
    result_url = media.get_ps_store_url(mock_input, MOCK_REGION, reformat="tumbler")
    assert "tumbler-search" in result_url[0]

    # Test no formatting.
    mock_final = urllib.parse.quote(html.escape(mock_input).encode())
    result_url = media.get_ps_store_url(
        mock_input, MOCK_REGION, reformat="orig", legacy=True
    )
    result_url = result_url[0].split("/faceted-search/")
    result_url = result_url[1].split("?")
    result_title = result_url[0]
    assert result_title == mock_final

    # Test chars only.
    mock_title = "Random Games 2 TheTitle"
    mock_final = urllib.parse.quote(html.escape(mock_title).encode())
    result_url = media.get_ps_store_url(
        mock_input, MOCK_REGION, reformat="chars", legacy=True
    )
    result_url = result_url[0].split("/faceted-search/")
    result_url = result_url[1].split("?")
    result_title = result_url[0]
    assert result_title == mock_final

    # Test chars with "', -, :".
    mock_title = "Random Game's 2: The-Title"
    mock_final = urllib.parse.quote(html.escape(mock_title).encode())

    result_url = media.get_ps_store_url(
        mock_input, MOCK_REGION, reformat="chars+", legacy=True
    )
    result_url = result_url[0].split("/faceted-search/")
    result_url = result_url[1].split("?")
    result_title = result_url[0]
    assert result_title == mock_final


@pytest.mark.asyncio
async def test_search_ps_store():
    with patch(
        "pyps4_2ndscreen.media_art.fetch", new=mock_coro(return_value=MOCK_DATA)
    ):
        result = await media.async_search_ps_store(
            MOCK_TITLE, MOCK_TITLE_ID, MOCK_REGION_NAME
        )
    assert result.name == MOCK_TITLE
    assert MOCK_TITLE_ID in result.cover_art
