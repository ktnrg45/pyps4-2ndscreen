"""Media Art Functions."""
import logging
from ssl import SSLError
import asyncio
import urllib
import aiohttp
from aiohttp.client_exceptions import ContentTypeError

from .errors import PSDataIncomplete

_LOGGER = logging.getLogger(__name__)

DEPRECATED_REGIONS = {'R1': 'en/us', 'R2': 'en/gb',
                      'R3': 'en/hk', 'R4': 'en/au',
                      'R5': 'en/in'}

# Excluded {China, Japan, Phillipines, Serbia, Ukraine, Vietnam}
COUNTRIES = {"Argentina": "en/ar", "Australia": "en/au", "Austria": "de/at",
             "Bahrain": "en/ae", "Belgium": "fr/be", "Brazil": "en/br",
             "Bulgaria": "en/bg", "Canada": "en/ca", "Chile": "en/cl",
             "Columbia": "en/co", "Costa Rica": "es/cr", "Croatia": "en/hr",
             "Cyprus": "en/cy", "Czech Republic": "en/cz", "Denmark": "en/dk",
             "Ecuador": "es/ec", "El Salvador": "es/sv", "Finland": "en/fi",
             "France": "fr/fr", "Germany": "de/de", "Greece": "en/gr",
             "Guatemala": "es/gt", "Honduras": "es/hn", "Hong Kong": "en/hk",
             "Hungary": "en/hu", "Iceland": "en/is", "India": "en/in",
             "Indonesia": "en/id", "Ireland": "en/ie", "Israel": "en/il",
             "Italy": "it/it", "Korea": "ko/kr", "Kuwait": "en/ae",
             "Lebanon": "en/ae", "Luxembourg": "de/lu", "Maylasia": "en/my",
             "Malta": "en/mt", "Mexico": "en/mx", "Middle East": "en/ae",
             "Nederland": "nl/nl", "New Zealand": "en/nz",
             "Nicaragua": "es/ni", "Norway": "en/no", "Oman": "en/ae",
             "Panama": "es/pa", "Peru": "en/pe", "Poland": "en/pl",
             "Portugal": "pt/pt", "Qatar": "en/ae", "Romania": "en/ro",
             "Russia": "ru/ru", "Saudi Arabia": "en/sa", "Singapore": "en/sg",
             "Slovenia": "en/si", "Slovakia": "en/sk", "South Africa": "en/za",
             "Spain": "es/es", "Sweden": "en/se", "Switzerland": "de/ch",
             "Taiwan": "en/tw", "Thailand": "en/th", "Turkey": "en/tr",
             "United Arab Emirates": "en/ae", "United States": "en/us",
             "United Kingdom": "en/gb"}

TYPE_LIST = {
    'de': ['Vollversion', 'Spiel', 'PSN-Spiel', 'Paket', 'App'],
    'en': ['Full Game', 'Game', 'PSN Game', 'Bundle', 'App'],
    'es': ['Juego completo', 'Juego', 'Juego de PSN', 'Paquete', 'App'],
    'fr': ['Jeu complet', 'Jeu', 'Jeu PSN', 'Offre groupée', 'App'],
    'it': ['Gioco completo', 'Gioco', 'Gioco PSN', 'Bundle', 'App'],
    'ko': ['제품판', '게임', 'PSN 게임', '번들', '앱'],
    'nl': ['Volledige game', 'game', 'PSN-game', 'Bundel', 'App'],
    'pt': ['Jogo completo', 'jogo', 'Jogo da PSN', 'Pacote', 'App'],
    'ru': ['Полная версия', 'Игра', 'Игра PSN', 'Комплект', 'Приложение'],
}

DEFAULT_HEADERS = {
    'User-Agent':
        'Mozilla/5.0 '
        '(Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36'
}

FORMATS = ['chars', 'chars+', 'orig', 'tumbler']

BASE_IMAGE_URL = (
    "https://store.playstation.com"
    "/store/api/chihiro/00_09_000/container/us/en/999/"
)

LEGACY_URL = (
    'https://store.playstation.com/'
    'valkyrie-api/{0}/19/faceted-search/'
    '{1}?query={1}&platform=ps4'
)

TUMBLER_URL = (
    'https://store.playstation.com/valkyrie-api/{}/19/'
    'tumbler-search/{}?suggested_size=9&mode=game'
    '&platform=ps4'
)

PINNED_TITLES = {
    'CUSA01780': {
        'name': 'Spotify',
        'sku_id': 'EP4950-CUSA01780_00-US00000000000000',
        'url': '/1559667794000/image',
        'type': 'App',
    }
}


def _get_pinned_data(data: dict):
    """Format pinned data as if retrieved from request."""
    result_data = {
        'name': data['name'],
        'default-sku-id': data['sku_id'],
        'game-content-type': data['type'],
        'thumbnail-url-base': '{}{}{}'.format(
            BASE_IMAGE_URL, data['sku_id'], data['url']),
    }
    return {'attributes': result_data}


def get_pinned_item(data: dict):
    """Return a pinned ResultItem using pinned data."""
    result_data = _get_pinned_data(data)
    item = ResultItem(result_data, TYPE_LIST['en'])
    return item


def get_region(region):
    """Validate and format region."""
    regions = COUNTRIES
    d_regions = DEPRECATED_REGIONS

    if region not in regions:
        if region in d_regions:
            _LOGGER.warning('Region: %s is deprecated', region)
            return d_regions[region]
        _LOGGER.error('Region: %s is not valid', region)
        return None
    return regions[region]


def get_lang(region) -> str:
    """Get language code from region."""
    regions = COUNTRIES
    lang = regions[region]
    lang = lang.split('/')
    lang = lang[0]
    assert lang in TYPE_LIST.keys()
    return lang


def get_ps_store_url(title, region, reformat='chars', legacy=False):
    """Get URL for title search in PS Store."""
    import html
    import re

    if reformat == 'chars':  # No Special Chars.
        title = re.sub(r'[^A-Za-z0-9\ ]+', '', title)
    elif reformat == 'chars+':  # ignore ' and - and :
        title = re.sub(r'[^A-Za-z0-9\-\'\: ]+', '', title)
    elif reformat == 'orig':
        pass
    title = html.escape(title.rstrip())
    title = urllib.parse.quote(title.encode('utf-8'))
    if legacy is True:
        _url = LEGACY_URL.format(region, title)
    else:
        _url = TUMBLER_URL.format(region, title)

    _LOGGER.debug(_url)

    url = [_url, DEFAULT_HEADERS, region.split('/')[0]]
    return url


def _format_url(url):
    """Format url for aiohttp."""
    f_params = {}
    url = url[0]
    url = url.split('?')
    params = url[1]
    params = params.replace('?', '')
    params = params.split('&')
    for item in params:
        item = item.split('=')
        f_params[item[0]] = item[1]
    url = url[0]
    return url, f_params


async def fetch(url, params, session):
    """Get Request."""
    try:
        response = await session.get(url, params=params, timeout=3)
        return await response.json()
    except (asyncio.TimeoutError, ContentTypeError, SSLError):
        return None


async def async_get_ps_store_requests(title, region,
                                      session: aiohttp.ClientSession) -> list:
    """Return Title and Cover data with aiohttp."""
    responses = []
    region = get_region(region)

    for format_type in FORMATS:
        _url = get_ps_store_url(
            title, region, reformat=format_type, legacy=True)
        url, params = _format_url(_url)

        response = await fetch(url, params, session)
        if response is not None:
            responses.append(response)

    for format_type in FORMATS:
        _url = get_ps_store_url(
            title, region, reformat=format_type, legacy=False)
        url, params = _format_url(_url)

        response = await fetch(url, params, session)
        if response is not None:
            responses.append(response)

    return responses


async def async_search_ps_store(title: str, title_id: str, region: str):
    """Search PS Store for title data."""
    # Check if title is a pinned title first and return.
    pinned = None
    pinned = PINNED_TITLES.get(title_id)
    if pinned is not None:
        return get_pinned_item(pinned)

    # Conduct Search Requests.
    lang = get_lang(region)
    result_item = None
    _LOGGER.debug("Starting search request")

    async with aiohttp.ClientSession() as session:
        responses = await async_get_ps_store_requests(
            title, region, session)
        for response in responses:
            try:
                result_item = parse_data(response, title_id, lang)
            except (TypeError, AttributeError):
                result_item = None
                raise PSDataIncomplete
            if result_item is not None:
                break
        await session.close()
    return result_item


def parse_data(result, title_id, lang):
    """Filter through each item in search request."""
    item_list = []
    type_list = TYPE_LIST[lang]
    parent_list = []

    for item in result['included']:
        item_list.append(ResultItem(item, type_list))

    # Filter each item by prioritized type
    for g_type in type_list:
        for item in item_list:
            if item.game_type == g_type:
                if item.sku_id == title_id:
                    _LOGGER.debug(
                        "Item: %s, %s", item.name, item.sku_id)
                    if not item.parent or item.parent.data is None:
                        _LOGGER.info("Direct Match")
                        return item
                    parent_list.append(item.parent)

    for item in parent_list:
        if item.data is not None:
            if item.sku_id == title_id:
                _LOGGER.info("Parent Match")
                return item
    return None


def parse_id(sku_id):
    """Format SKU."""
    try:
        sku_id = sku_id.split("-")
        sku_id = sku_id[1].split("_")
        parsed_id = sku_id[0]
        return parsed_id
    except IndexError:
        return None


class ResultItem():
    """Item object."""

    def __init__(self, data, type_list):
        """Init Class."""
        self.type_list = type_list
        self.data = data['attributes']

    def __repr__(self):
        return (
            "<{}.{} Name: {}, SKU ID: {}, Game Type: {}, "
            "Parent: {}>".format(
                self.__module__, self.__class__.__name__, self.name,
                self.sku_id, self.game_type, self.parent is not None,
            )
        )

    @property
    def name(self):
        """Get Item Name."""
        return self.data.get('name')

    @property
    def game_type(self):
        """Get Game Type."""
        game_type = self.data.get('game-content-type')
        if game_type is not None:
            if game_type == self.type_list[4]:
                game_type = 'App'
        return game_type

    @property
    def sku_id(self):
        """Get SKU."""
        sku_id = self.data.get('default-sku-id')
        if sku_id is not None:
            sku_id = parse_id(sku_id)
        return sku_id

    @property
    def cover_art(self):
        """Get Art URL."""
        return self.data.get('thumbnail-url-base')

    @property
    def parent(self):
        """Get Parents."""
        parent = self.data.get('parent')
        if self.game_type is not None and parent is not None \
                and parent != 'null':
            return ParentItem(parent, self.game_type)
        return None


class ParentItem():
    """Item object."""

    def __init__(self, data, game_type=None):
        """Init Class."""
        self.data = data
        self._game_type = game_type

    def __repr__(self):
        return (
            "<{}.{} Name: {}, SKU ID: {}, Game Type: {}>"
            .format(
                self.__module__, self.__class__.__name__, self.name,
                self.sku_id, self.game_type,
            )
        )

    @property
    def name(self):
        """Parent Name."""
        return self.data.get('name')

    @property
    def sku_id(self):
        """Parent SKU."""
        sku_id = self.data.get('id')
        if sku_id is not None:
            sku_id = parse_id(sku_id)
        return sku_id

    @property
    def cover_art(self):
        """Parent Art."""
        url = self.data.get('url')
        if url is not None:
            url = "{}{}".format(url, "/image")
        return url

    @property
    def game_type(self):
        """Parent Game type."""
        return self._game_type
