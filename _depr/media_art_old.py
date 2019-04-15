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


def get_ps_store_url(title, region, reformat=None):
    """Get URL for title search in PS Store."""
    import urllib
    import re

    headers = {
        'User-Agent':
            'Mozilla/5.0 '
            '(Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36'
    }

    if title is not None:
        if reformat is True:
            title = re.sub('[^A-Za-z0-9]+', ' ', title)
        title = urllib.parse.quote(title.encode('utf-8'))
        _url = 'https://store.playstation.com/'\
            'valkyrie-api/{0}/19/faceted-search/'\
            '{1}?query={1}&platform=ps4'.format(region, title)

    url = [_url, headers]
    return url


def get_ps_store_data(title, title_id, region, url=None, reformat=None):
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
        result = req.json()['included']
        if not result:
            title = title.split(' ')
            title = title[0]
            url = get_ps_store_url(title, region)
            req = requests.get(url[0], headers=url[1])
            result = req.json()['included']
    except requests.exceptions.HTTPError as warning:
        _LOGGER.warning("PS cover art HTTP error, %s", warning)
        return None, None
    except requests.exceptions.RequestException as warning:
        _LOGGER.warning("PS cover art request failed, %s", warning)
        return None, None
    return parse_data(result, title, title_id, region, reformat)


def parse_data(result, title, title_id, region, reformat):  # noqa: pylint: disable=too-many-locals, too-many-branches
    """Filter through each item in search request."""
    match_id = {}
    match_title = {}
    type_list = ['Full Game', 'Game', 'PSN Game', 'Bundle', 'App']

    # Filter each item by prioritized type
    for game_type in type_list:
        for item in result:

            # Set each item as Game object
            game = Game(item, reformat)
            if 'default-sku-id' in game.game:
                game.title_id = _parse_id(game.game['default-sku-id'])
                game.title = game.game['name']
                _LOGGER.debug('Item: %s', game.title)

            parent_match = _filter_parent(game, title_id, title)
            if parent_match is not None:
                return parent_match

            game.cover_art = _get_cover(game.game)
            if game.cover_art is None:
                break

            # Direct Match Filter
            if _is_game_type(game.game, game_type):
                game.type = game_type
                title_matched = False
                id_matched = False

                # Check if item has no parent.
                if not game.parent:
                    # If title matches and has no parent.
                    if title.upper() == _format_title(game.title, reformat):
                        title_matched = True
                        match_title.update({game.title: game.cover_art})

                    # If passed SKU matches object SKU.
                    if game.title_id == title_id:
                        id_matched = True
                        match_id.update({game.title: game.cover_art})

                if title_matched and id_matched:
                    # Most likely the intended item so return
                    _LOGGER.debug("Direct Match")
                    return game.title, game.cover_art

    s_title, s_art = _get_similar(title, match_id, match_title, reformat)
    if s_title is None or s_art is None:
        if reformat is None:
            _LOGGER.debug("Retrying with no special chars")
            return get_ps_store_data(title, title_id, region, reformat='chars')
        if reformat == 'chars':
            _LOGGER.debug("Retrying with partial title")
            title = title.split(' ')
            title = title[0]
            return get_ps_store_data(
                title, title_id, region, reformat='partial')
    return s_title, s_art


def _is_game_type(game, game_type):
    """Check if item is a game and has SKU."""
    if 'game-content-type' in game and \
       game['game-content-type'] == game_type:
        if 'default-sku-id' in game:
            return True
    return None


def _parse_id(_id):
    """Parse SKU to simplified ID."""
    try:
        full_id = _id
        full_id = full_id.split("-")
        full_id = full_id[1]
        full_id = full_id.split("_")
        parse_id = full_id[0]
    except IndexError:
        parse_id = None
    return parse_id


def _format_title(title, reformat):
    """Format Title."""
    import re

    if reformat is None:
        title = re.sub('[^A-Za-z0-9]+', ' ', title)
    title = title.upper()
    return title


def _get_cover(game):
    """Get cover art."""
    if 'thumbnail-url-base' in game:
        cover = 'thumbnail-url-base'
        cover_art = game[cover]
        return cover_art
    return None


def _get_similar(title, match_id, match_title, reformat):
    """Return similar title."""
    if match_id:
        for _title, url in match_id.items():
            if title.upper() in _format_title(_title, reformat):
                cover_art = url
                _LOGGER.debug("Similar Title Match")
                return _title, cover_art
    elif match_title:
        for _title, url in match_title.items():
            cover_art = url
            _LOGGER.debug("Wrong ID Match")
            return _title, cover_art
    return None, None


def _filter_parent(game, title_id, title):
    # Filter with Parent
    if game.parent:
        parent_match = False
        if game.parent['id'] == title_id:
            _LOGGER.debug("Parent ID Match")
            parent_match = True
        if title.upper() == game.parent['title_format']:
            _LOGGER.debug("Parent Title Match")
            parent_match = True
        if title.upper() in game.parent['title_format']:
            _LOGGER.debug("Parent Similar Title Match")
            parent_match = True

        if parent_match is True:
            return game.parent['title'], game.parent['art']
    return None


class Game():
    """Game object."""

    def __init__(self, data, reformat):
        """Init."""
        self.data = data
        self.game = None
        self.title = None
        self.title_id = None
        self.cover_art = None
        self.type = None
        self.parent = {}

        self.get_game()
        self.get_parent(reformat)

    def get_game(self):
        """Create game object."""
        if 'attributes' in self.data:
            self.game = self.data['attributes']

    def get_parent(self, reformat):
        """Get Parent attr."""
        if 'parent' in self.game:
            if self.game['parent'] is not None:
                parent = self.game['parent']
                self.parent['id'] = _parse_id(parent['id'])
                self.parent['title'] = parent['name']
                self.parent['art'] = "{}/image".format(parent['url'])
                self.parent['title_format'] = _format_title(
                    self.parent['title'], reformat)
