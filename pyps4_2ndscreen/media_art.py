"""Media Art Functions."""
import asyncio
import logging
from ssl import SSLError

import aiohttp
from aiohttp.client_exceptions import ContentTypeError

from .errors import PSDataIncomplete

_LOGGER = logging.getLogger(__name__)

DEPRECATED_REGIONS = {
    "R1": "en/us",
    "R2": "en/gb",
    "R3": "en/hk",
    "R4": "en/au",
    "R5": "en/in",
}

"""
Excluded Countries:

China: Store closed by Sony
Phillipines: Store not available
Serbia: Store not available
Vietnam: Store not available
"""

COUNTRIES = {
    "Argentina": "en/ar",
    "Australia": "en/au",
    "Austria": "de/at",
    "Bahrain": "en/ae",
    "Belgium": "fr/be",
    "Brazil": "en/br",
    "Bulgaria": "en/bg",
    "Canada": "en/ca",
    "Chile": "en/cl",
    "Columbia": "en/co",
    "Costa Rica": "es/cr",
    "Croatia": "en/hr",
    "Cyprus": "en/cy",
    "Czech Republic": "en/cz",
    "Denmark": "en/dk",
    "Ecuador": "es/ec",
    "El Salvador": "es/sv",
    "Finland": "en/fi",
    "France": "fr/fr",
    "Germany": "de/de",
    "Greece": "en/gr",
    "Guatemala": "es/gt",
    "Honduras": "es/hn",
    "Hong Kong": "en/hk",
    "Hungary": "en/hu",
    "Iceland": "en/is",
    "India": "en/in",
    "Indonesia": "en/id",
    "Ireland": "en/ie",
    "Israel": "en/il",
    "Italy": "it/it",
    "Japan": "ja/jp",
    "Korea": "ko/kr",
    "Kuwait": "en/ae",
    "Lebanon": "en/ae",
    "Luxembourg": "de/lu",
    "Maylasia": "en/my",
    "Malta": "en/mt",
    "Mexico": "en/mx",
    "Middle East": "en/ae",
    "Nederland": "nl/nl",
    "New Zealand": "en/nz",
    "Nicaragua": "es/ni",
    "Norway": "en/no",
    "Oman": "en/ae",
    "Panama": "es/pa",
    "Peru": "en/pe",
    "Poland": "en/pl",
    "Portugal": "pt/pt",
    "Qatar": "en/ae",
    "Romania": "en/ro",
    "Russia": "ru/ru",
    "Saudi Arabia": "en/sa",
    "Singapore": "en/sg",
    "Slovenia": "en/si",
    "Slovakia": "en/sk",
    "South Africa": "en/za",
    "Spain": "es/es",
    "Sweden": "en/se",
    "Switzerland": "de/ch",
    "Taiwan": "en/tw",
    "Thailand": "en/th",
    "Turkey": "en/tr",
    "Ukraine": "ru/ua",
    "United Arab Emirates": "en/ae",
    "United States": "en/us",
    "United Kingdom": "en/gb",
}

TYPE_APP = "APP"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36"
}

BASE_URL = (
    "https://store.playstation.com/store/api/chihiro/00_09_000/"
    "titlecontainer/{}/{}/999/{}_00"
)

BASE_IMAGE_URL = "{}/image"

HTTP_STATUS_OK = 200


def get_region(region: str) -> str:
    """Validate and format region."""
    regions = COUNTRIES
    d_regions = DEPRECATED_REGIONS

    if region not in regions:
        if region in d_regions:
            _LOGGER.warning("Region: %s is deprecated", region)
            return d_regions[region]
        _LOGGER.error("Region: %s is not valid", region)
        return None
    return regions[region]


def get_region_codes(region: str) -> list:
    """Return list of country and language codes."""
    region = get_region(region)
    codes = region.split("/")
    return codes


async def fetch(
    url: str, params: dict, session: aiohttp.client.ClientSession
) -> aiohttp.client_reqrep.ClientResponse:
    """Return response from Get Request."""
    try:
        _LOGGER.debug("PS Store GET %s", url)
        response = await session.get(url, params=params, timeout=3)
        if response.status != HTTP_STATUS_OK:
            content = await response.json()
            _LOGGER.error("PS Store HTTP Error; Reason: %s", response.reason)
            _LOGGER.debug("PS Store HTTP response: %s", content)
            return None
        return response
    except (asyncio.TimeoutError, ContentTypeError, SSLError):
        return None


class ResultItem:
    """Title data results from search."""

    def __init__(self, title_id: str, image_url: str, data: dict):
        """Init Class."""
        self._data = data
        self._sku_id = title_id
        self._cover_art = image_url

    def __repr__(self):
        return "<{}.{} name={} sku_id={} game_type={}>".format(
            self.__module__,
            self.__class__.__name__,
            self.name,
            self.sku_id,
            self.game_type,
        )

    @property
    def name(self) -> str:
        """Return Item Name."""
        return self.data.get("title_name")

    @property
    def game_type(self) -> str:
        """Return Game Type."""
        game_type = None
        game_types = self.data.get("gameContentTypesList")
        if game_types and isinstance(game_types, list):
            _game_types = game_types[0]
            if isinstance(_game_types, dict):
                game_type = _game_types.get("key")
        return game_type

    @property
    def sku_id(self) -> str:
        """Return SKU."""
        return self._sku_id

    @property
    def cover_art(self) -> str:
        """Return Art URL."""
        return self._cover_art

    @property
    def data(self) -> dict:
        """Return dict of data attributes."""
        return self._data


async def async_search_ps_store(title_id: str, region: str) -> ResultItem:
    """Search PS Store for title data."""
    _LOGGER.debug("Starting search request")
    result_item = None
    data = None
    codes = get_region_codes(region)
    data_url = BASE_URL.format(codes[1], codes[0], title_id)
    image_url = BASE_IMAGE_URL.format(data_url)
    params = DEFAULT_HEADERS

    async with aiohttp.ClientSession() as session:
        resp = await fetch(data_url, params, session)
        if resp is not None:
            data = await resp.json()

    if data is None or not data or not isinstance(data, dict):
        return None

    if data.get("gameContentTypesList") is None or data.get("title_name") is None:
        raise PSDataIncomplete("Title data missing keys")

    result_item = ResultItem(title_id, image_url, data)
    return result_item
