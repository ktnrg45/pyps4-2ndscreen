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


def get_ps_store_url(title, region, reformat='chars', legacy=False):
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

    if reformat == 'chars':
        title = re.sub('[^A-Za-z0-9]+', ' ', title)
    elif reformat == 'chars+':  # ignore ' and -
        title = re.sub('[^A-Za-z0-9\-\']+', ' ', title)
    elif reformat == 'orig':
        pass
    elif reformat == 'tumbler':
        title = re.sub('[^A-Za-z0-9]+', ' ', title)
        title = title.split(' ')[0]
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
    import requests

    formats = ['chars', 'chars+', 'orig', 'tumbler']
    f_index = 0

    while f_index != len(formats):

        if url is None:
            url = get_ps_store_url(
                title, region, reformat=formats[f_index], legacy=legacy)
        req = None

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
            return None
        except requests.exceptions.RequestException as warning:
            _LOGGER.warning("PS cover art request failed, %s", warning)
            return None

        data = parse_data(result, title, title_id, region, url[2])
        _LOGGER.debug(data)
        if data is not None:
            return data
        url = None
        f_index += 1
    return None


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

    for item in result['included']:
        item_list.append(ResultItem(item, type_list))

    # Filter each item by prioritized type
    for g_type in type_list:
        _LOGGER.debug("Searching type: {}".format(g_type))
        for item in item_list:
            if item.game_type == g_type:
                if item.sku_id == title_id:
                    _LOGGER.debug("Item: {}, {}, {}".format(
                        item.name, item.sku_id, vars(item.parent)))
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
        parse_id = sku_id[0]
        return parse_id
    except IndexError:
        return None


class ResultItem():
    """Item object."""

    def __init__(self, data, type_list):
        """Init Class."""
        self.data = data['attributes']
        self.type_list = type_list

    @property
    def name(self):
        """Get Item Name."""
        return self.data['name'] if not None else None

    @property
    def game_type(self):
        """Get Game Type."""
        game_type = self.data['game-content-type'] if not None else None
        if game_type:
            if game_type == self.type_list[4]:
                return 'App'
            return game_type

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
        self._game_type = game_type

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
        return self.data['url'] if not None else None

    @property
    def game_type(self):
        """Parent Game type."""
        return self._game_type
