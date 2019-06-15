# -*- coding: utf-8 -*-
"""Media Art Functions."""
import logging
import asyncio
import urllib
import aiohttp

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

FORMATS = ['chars', 'chars+', 'orig', 'tumbler']


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

    headers = {
        'User-Agent':
            'Mozilla/5.0 '
            '(Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36'
    }

    if reformat == 'chars':  # No Special Chars.
        title = re.sub(r'[^A-Za-z0-9\ ]+', '', title)
    elif reformat == 'chars+':  # ignore ' and - and :
        title = re.sub(r'[^A-Za-z0-9\-\'\:]+', ' ', title)
    elif reformat == 'orig':
        pass
    elif reformat == 'tumbler':
        pass
    title = html.escape(title)
    title = urllib.parse.quote(title.encode('utf-8'))
    if legacy is True:
        _url = 'https://store.playstation.com/'\
            'valkyrie-api/{0}/19/faceted-search/'\
            '{1}?query={1}&platform=ps4'.format(region, title)
    else:
        _url = 'https://store.playstation.com/valkyrie-api/{}/19/'\
               'tumbler-search/{}?suggested_size=9&mode=game'\
               '&platform=ps4'.format(region, title)
    _LOGGER.debug(_url)

    url = [_url, headers, region.split('/')[0]]
    return url


async def async_prepare_tumbler(
        title, title_id, region,
        session: aiohttp.ClientSession) -> dict or None:
    """Try tumbler search. Add chars to search, one by one."""
    lang = get_lang(region)
    _region = get_region(region)
    char_index = 0
    while char_index < (len(title) - 1):
        index = char_index + 1
        current_chars = title[0:index]
        url = get_ps_store_url(
            current_chars, _region, reformat='tumbler')
        url, params = _format_url(url)
        response = await fetch(url, params, session)
        if response is None:
            continue

        data = parse_data(response, title_id, lang)

        # If title not found iterate to next char.
        if data is None:
            remaining_chars = list(title[index:])
            char_index = char_index + 1
            next_chars = response['data']['attributes']['next'] or None

            # If the next char is not in the next attr.
            if next_chars is None:
                return None
            if title[char_index] not in next_chars\
                    if next_chars else None:
                _LOGGER.debug("Starting Tumbler")
                return await async_tumbler_search(
                    current_chars, next_chars, remaining_chars,
                    title_id, region, session)
            continue

        return data


async def async_tumbler_search(
        current_chars: list, next_chars: list, remaining_chars: list,
        title_id, region, session: aiohttp.ClientSession) -> dict or None:
    """Search using tumbler method."""
    _region = get_region(region)
    lang = get_lang(region)
    current = current_chars
    chars = next_chars
    next_list = []
    ignore = ["'", ' ']
    data = None
    for char in chars:
        if char not in remaining_chars or char in ignore:
            continue
        next_str = "{}{}".format(current, char)
        url = get_ps_store_url(next_str, _region, 'tumbler', True)
        url, params = _format_url(url)
        response = await fetch(url, params, session)

        if response is None:
            continue

        data = parse_data(response, title_id, lang)
        if data is not None:
            next_chars = response['data']['attributes']['next'] or None
            if next_chars is not None:
                next_list.append(next_chars)
        else:
            break
    return data or None


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
    from aiohttp.client_exceptions import ContentTypeError
    try:
        async with session.get(url, params=params, timeout=3) as response:
            return await response.json()
    except (asyncio.TimeoutError, ContentTypeError):
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

    @property
    def name(self):
        """Get Item Name."""
        if 'name' in self.data:
            return self.data['name']
        return None

    @property
    def game_type(self):
        """Get Game Type."""
        game_type = None
        if 'game-content-type' in self.data:
            game_type = self.data['game-content-type']
        if game_type is not None:
            if game_type == self.type_list[4]:
                return 'App'
            return game_type
        return None

    @property
    def sku_id(self):
        """Get SKU."""
        full_id = None
        if 'default-sku-id' in self.data:
            full_id = self.data['default-sku-id']
        if full_id is not None:
            return parse_id(full_id)
        return None

    @property
    def cover_art(self):
        """Get Art URL."""
        if 'thumbnail-url-base' in self.data:
            return self.data['thumbnail-url-base']
        return None

    @property
    def parent(self):
        """Get Parents."""
        if self.game_type is not None:
            if 'parent' in self.data and self.data['parent'] != 'null':
                if self.data['parent'] is not None:
                    return ParentItem(
                        self.data['parent'],
                        self.game_type)
        return None


class ParentItem():
    """Item object."""

    def __init__(self, data, game_type=None):
        """Init Class."""
        self.data = data
        self._game_type = game_type

    @property
    def name(self):
        """Parent Name."""
        if 'name' in self.data:
            return self.data['name']
        return None

    @property
    def sku_id(self):
        """Parent SKU."""
        full_id = None
        if 'id' in self.data:
            full_id = self.data['id']
        if full_id is not None:
            return parse_id(full_id)
        return None

    @property
    def cover_art(self):
        """Parent Art."""
        if 'url' in self.data:
            return "{}{}".format(self.data['url'], "/image")
        return None

    @property
    def game_type(self):
        """Parent Game type."""
        return self._game_type
