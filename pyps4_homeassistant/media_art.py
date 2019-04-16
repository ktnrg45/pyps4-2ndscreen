# -*- coding: utf-8 -*-
"""Media Art Functions."""
import logging

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


def search_all(title, title_id):
    """Search all databases."""
    for country in COUNTRIES:
        region = COUNTRIES[country]
        (_title, art) = get_ps_store_data(title, title_id, region)
        _LOGGER.debug(_title)
        if _title is not None:
            return _title, art
    return None, None


def get_ps_store_url(title, region, reformat='chars'):
    """Get URL for title search in PS Store."""
    import html
    import urllib
    import re

    headers = {
        'User-Agent':
            'Mozilla/5.0 '
            '(Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36'
    }

    region = COUNTRIES[region]

    if title is not None:
        if reformat == 'chars':
            title = re.sub('[^A-Za-z0-9\']+', ' ', title)
        title = html.escape(title)
        title = urllib.parse.quote(title.encode('utf-8'))
        _url = 'https://store.playstation.com/valkyrie-api/{}/19/'\
               'tumbler-search/{}?suggested_size=5&mode=game'\
               '&platform=ps4'.format(region, title)
        print(_url)

    url = [_url, headers, region.split('/')[0]]
    return url


def get_ps_store_data(title, title_id, region, url=None, reformat='chars'):
    """Get cover art from database."""
    import requests
    import re

    if url is None:
        url = get_ps_store_url(title, region)
    req = None

    if reformat == 'chars':
        title = re.sub('[^A-Za-z0-9]+', ' ', title)
    try:
        req = requests.get(url[0], headers=url[1])
        result = req.json()
        if not result:
            title = title.split(' ')
            title = title[0]
            url = get_ps_store_url(title, region)
            req = requests.get(url[0], headers=url[1])
            result = req.json()
    except requests.exceptions.HTTPError as warning:
        _LOGGER.warning("PS cover art HTTP error, %s", warning)
        return None, None
    except requests.exceptions.RequestException as warning:
        _LOGGER.warning("PS cover art request failed, %s", warning)
        return None, None
    return parse_data(result, title, title_id, region, url[2])


def parse_data(result, title, title_id, region, lang):
    """Filter through each item in search request."""
    type_list = {
        'de': ['Vollversion', 'Spiel', 'PSN-Spiel', 'Paket', 'App'],
        'en': ['Full Game', 'Game', 'PSN Game', 'Bundle', 'App'],
        'es': ['Juego Completo', 'Juego', 'Juego de PSN', 'Paquete', 'App'],
        'fr': ['Jeu complet', 'Jeu', 'Jeu PSN', 'Offre groupée', 'App'],
        'it': ['Gioco completo', 'Gioco', 'Gioco PSN', 'Bundle', 'App'],
        'ko': ['제품판', '게임', 'PSN 게임', '번들', '앱'],
        'nl': ['Volledige game', 'game', 'PSN-game', 'Bundel', 'App'],
        'pt': ['Jogo completo', 'jogo', 'Jogo da PSN', 'Pacote', 'App'],
        'ru': ['Полная версия', 'Игра', 'Игра PSN', 'Комплект', 'Приложение'],
    }
    item_list = []
    type_list = type_list[lang]
    parent_list = []
    # type_list = ['Full Game', 'Game', 'PSN Game', 'Bundle', 'App']

    for item in result['included']:
        item_list.append(ResultItem(item))

    # Filter each item by prioritized type
    for g_type in type_list:
        print("Searching type: {}".format(g_type))
        for item in item_list:
            print(item.game_type)
            if item.game_type == g_type:
                print("Item: {}, {}, {}".format(
                    item.name, item.sku_id, item.parent))
                if item.sku_id == title_id:
                    if not item.parent:
                        return item
                    parent_list.append(item.parent)

    for item in parent_list:
        if item.data is not None:
            if item.sku_id == title_id:
                return item
    return None


def parse_id(sku_id):
    """Format SKU."""
    try:
        sku_id = sku_id.split("-")
        sku_id = sku_id[1].split("_")
        parse_id = sku_id[0]
        return parse_id
    except IndexError:
        return None


class ResultItem():
    """Item object."""

    def __init__(self, data):
        """Init Class."""
        self.data = data['attributes']

    @property
    def name(self):
        """Get Item Name."""
        return self.data['name'] if not None else None

    @property
    def game_type(self):
        """Get Game Type."""
        return self.data['game-content-type'] if not None else None

    @property
    def sku_id(self):
        """Get SKU."""
        full_id = self.data['default-sku-id'] if not None else None
        if full_id:
            return parse_id(full_id)
        return None

    @property
    def cover_art(self):
        """Get Art URL."""
        return self.data['thumbnail-url-base'] if not None else None

    @property
    def parent(self):
        """Get Parents."""
        if self.game_type:
            return ParentItem(
                self.data['parent'],
                self.game_type) if not None else None


class ParentItem():
    """Item object."""

    def __init__(self, data, game_type):
        """Init Class."""
        self.data = data

    @property
    def name(self):
        """Parent Name."""
        return self.data['name'] if not None else None

    @property
    def sku_id(self):
        """Parent SKU."""
        full_id = self.data['id'] if not None else None
        if full_id:
            return parse_id(full_id)
        return None

    @property
    def cover_art(self):
        """Parent Art."""
        return self.data['parent']['url'] if not None else None

    @property
    def game_type(self):
        """Parent Game type."""
        return self.game_type
