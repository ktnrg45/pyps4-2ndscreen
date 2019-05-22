# -*- coding: utf-8 -*-
"""Media Art Functions."""
import logging
import urllib
import requests

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


def get_ps_store_data(title, title_id, region, url=None, legacy=False):
    """Get cover art from database."""
    formats = FORMATS
    f_index = 0

    # Try to find title in data. Reformat title of punctuation.
    while f_index != len(formats):

        if url is None:
            url = get_ps_store_url(
                title, region, reformat=formats[f_index], legacy=legacy)
            result = get_request(url)
            if not result:
                continue

        # Try tumbler search. Add chars to search, one by one.
        if formats[f_index] == 'tumbler' and legacy is False:
            char_index = 0
            while char_index < (len(title) - 1):
                index = char_index + 1
                current_chars = title[0:index]
                url = get_ps_store_url(
                    current_chars, region, reformat=formats[f_index],
                    legacy=legacy)
                result = get_request(url)
                data = parse_data(result, title_id, url[2])
                if not data:
                    remaining_chars = list(title[index:])
                    char_index = char_index + 1
                    next_chars = result['data']['attributes']['next'] or None

                    # If the next char is not in the next attr.
                    if title[char_index] not in next_chars\
                            if next_chars else None:
                        _LOGGER.debug("Starting Tumbler")
                        return tumbler_search(
                            current_chars, next_chars, remaining_chars,
                            title_id, region)
                    continue
                return data

        elif formats[f_index] == 'tumbler' and legacy is True:
            return None

        data = parse_data(result, title_id, url[2])
        _LOGGER.debug(data)
        if data is not None:
            return data
        url = None
        f_index += 1
    return None


def tumbler_search(  # noqa: pylint: disable=too-many-arguments
        current_chars, next_chars, remaining_chars,
        title_id, region, reformat='tumbler', legacy=False):
    """Search using tumbler method."""
    current = current_chars
    chars = next_chars
    next_list = []
    data = None
    for char in chars:
        if char not in remaining_chars:
            continue
        next_str = "{}{}".format(current, char)
        url = get_ps_store_url(next_str, region, reformat, legacy)
        result = get_request(url)
        data = parse_data(result, title_id, url[2])
        if not data:
            next_chars = result['data']['attributes']['next'] or None
            if next_chars is not None:
                next_list.append(next_chars)
        else:
            break
    return data or None


def get_request(url, retry=2):
    """Get HTTP request."""
    retries = 0
    while retries < retry:
        try:
            req = requests.get(url[0], headers=url[1], timeout=3)
            result = req.json()
            if not result:
                retries += 1
                continue
            return result
        except requests.exceptions.HTTPError as warning:
            _LOGGER.warning("PS cover art HTTP error, %s", warning)
            retries += 1
            continue
        except requests.exceptions.RequestException as warning:
            _LOGGER.warning("PS cover art request failed, %s", warning)
            retries += 1
            continue


def parse_data(result, title_id, lang):
    """Filter through each item in search request."""
    item_list = []
    type_list = TYPE_LIST[lang]
    parent_list = []

    for item in result['included']:
        item_list.append(ResultItem(item, type_list))

    # Filter each item by prioritized type
    for g_type in type_list:
        _LOGGER.debug("Searching type: %s", g_type)
        for item in item_list:
            if item.game_type == g_type:
                if item.sku_id == title_id:
                    _LOGGER.debug(
                        "Item: %s, %s, %s", item.name, item.sku_id,
                        vars(item.parent))
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
